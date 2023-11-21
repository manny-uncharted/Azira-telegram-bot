import telebot
import os
from telebot import types
import asyncio
from asyncio import run_coroutine_threadsafe
from threading import Thread
from aziraclient.auth.auth_client import AuthClient
from aziraclient.subscription.subscription import SubscribeToToken
from dotenv import load_dotenv
load_dotenv()


from utils import *

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)


init_db()
subscribed_users = get_subscribed_users()

def start_asyncio_forever(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

loop = asyncio.get_event_loop()
t = Thread(target=start_asyncio_forever, args=(loop,))
t.start()

async def stream_data_to_users(tester):
    await tester.connector.connect()
    await tester.connector.send_message(tester.action, [tester.token])

    try:
        while True:
            message = await tester.connector.receive_message()
            if message:
                try:
                    formatted_message = format_message(message)  # Attempt to format the message
                    for chat_id in subscribed_users.keys():
                        try:
                            bot.send_message(chat_id, formatted_message)
                        except Exception as e:
                            print(f"Error sending message to chat_id {chat_id}: {e}")
                except json.JSONDecodeError:
                    print(f"Received invalid JSON: {message}")
    except Exception as e:
        print(f"Error in stream_data_to_users: {e}")

# Handlers
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! I can provide you real-time crypto tokens data.\n"
                          "Here are the commands you can use:\n"
                          "/register - Register a new user\n"
                          "/login - Log in to an existing account\n"
                          "/subscribe - Subscribe to a token\n"
                          "/unsubscribe - Unsubscribe from a token")

@bot.message_handler(commands=['register'])
def register_user(message):
    msg = bot.reply_to(message, "Enter your username for registration:")
    bot.register_next_step_handler(msg, process_register_username_step)

def process_register_username_step(message):
    try:
        username = message.text
        msg = bot.reply_to(message, 'Enter your password for registration:')
        bot.register_next_step_handler(msg, process_register_password_step, username)
    except Exception as e:
        bot.reply_to(message, 'Oops, something went wrong!')

def process_register_password_step(message, username):
    try:
        password = message.text
        auth = AuthClient()
        register = auth.register_user(username, password=password)
        bot.send_message(message.chat.id, f"User registration response: {register}")
    except Exception as e:
        bot.reply_to(message, 'Oops, something went wrong!')

@bot.message_handler(commands=['login'])
def login_user(message):
    msg = bot.reply_to(message, "Enter your username for login:")
    bot.register_next_step_handler(msg, process_login_username_step)

def process_login_username_step(message):
    try:
        username = message.text
        msg = bot.reply_to(message, 'Enter your password for login:')
        bot.register_next_step_handler(msg, process_login_password_step, username)
    except Exception as e:
        bot.reply_to(message, 'Oops, something went wrong!')

def process_login_password_step(message, username):
    try:
        password = message.text
        auth = AuthClient()
        login = auth.login_user(username, password)
        if len(login['message']) == len('Login successful.'):
            store_jwt_token(message.chat.id, login["access_token"])
            bot.send_message(message.chat.id, "Login successful.")
        else:
            bot.send_message(message.chat.id, "Login failed.")
    except Exception as e:
        bot.reply_to(message, 'Oops, something went wrong!')




@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    chat_id = message.chat.id
    jwt_token = get_jwt_token(chat_id)

    if jwt_token:
        store_jwt_token(chat_id, jwt_token)
        msg = bot.reply_to(message, f"Enter your username to subscribe:")
        bot.register_next_step_handler(msg, process_token_name_step, jwt_token)
    else:
        bot.reply_to(message, "Please log in first.")
def process_token_name_step(message, jwt_token):
    try:
        username = message.text
        msg = bot.reply_to(message, 'Enter the Token identifier:')
        bot.register_next_step_handler(msg, process_token_step, username, jwt_token)
    except Exception as e:
        bot.reply_to(message, 'Oops, something went wrong!')

def process_token_step(message, username, jwt_token):
    token_name = message.text.strip()
    tester = SubscribeToToken(username, jwt_token, 'subscribe', token_name)
    run_coroutine_threadsafe(stream_data_to_users(tester), loop)

    bot.reply_to(message, "You are now subscribed to updates.")


@bot.message_handler(commands=['unsubscribe'])
def unsubscribe(message):
    chat_id = message.chat.id
    jwt_token = get_jwt_token(chat_id)

    if jwt_token:
        store_jwt_token(chat_id, jwt_token)
        msg = bot.reply_to(message, f"Enter your username to subscribe:")
        bot.register_next_step_handler(msg, process_unsubscribe_token_name_step, jwt_token, chat_id)
    else:
        bot.reply_to(message, "Please log in first.")
def process_unsubscribe_token_name_step(message, jwt_token, chat_id):
    try:
        username = message.text
        msg = bot.reply_to(message, 'Enter the Token identifier:')
        bot.register_next_step_handler(msg, process_unsubscribe_token_step, username, jwt_token, chat_id)
    except Exception as e:
        bot.reply_to(message, 'Oops, something went wrong!')

def process_unsubscribe_token_step(message, username, jwt_token, chat_id):
    token_name = message.text.strip()
    tester = SubscribeToToken(username, jwt_token, 'unsubscribe', token_name)
    run_coroutine_threadsafe(stream_data_to_users(tester), loop)
    unsubscribe_user(chat_id)
    bot.reply_to(message, "You are now unsubscribed from updates.")



# Polling
bot.polling(none_stop=True)
