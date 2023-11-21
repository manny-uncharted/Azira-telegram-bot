from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    chat_id = Column(Integer, primary_key=True)
    jwt_token = Column(Text)
    subscribed_tokens = Column(Text)


DATABASE_URL = "sqlite:///bot.db"  # SQLite URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def store_jwt_token(chat_id, jwt_token):
    db = next(get_db())
    user = db.query(User).filter(User.chat_id == chat_id).first()
    if user is None:
        user = User(chat_id=chat_id, jwt_token=jwt_token)
        db.add(user)
    else:
        user.jwt_token = jwt_token
    db.commit()


def get_jwt_token(chat_id):
    db = next(get_db())
    user = db.query(User).filter(User.chat_id == chat_id).first()
    return user.jwt_token if user else None

def get_subscribed_users():
    db = next(get_db())
    try:
        users = db.query(User).all()
        subscribed_users = {user.chat_id: user.jwt_token for user in users if user.jwt_token}
        return subscribed_users
    finally:
        db.close()

def unsubscribe_user(chat_id):
    db = next(get_db())
    user = db.query(User).filter(User.chat_id == chat_id).first()
    if user:
        user.jwt_token = None  # or user.subscribed_tokens = None, depending on your logic
        db.commit()

def format_message(message):
    try:
        # Try parsing the message as JSON
        message_dict = json.loads(message)
        # Format the message as needed, assuming it's a dictionary
        return f"Token: {message_dict['token']}\n, Current Price: {message_dict['current_price']}\n Name: {message_dict['name']}\n, Market Cap: {message_dict['market_cap']}"
    except json.JSONDecodeError:
        # If it's not JSON, just return the message as is
        return message

