# database.py
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, MetaData, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import Text
from datetime import datetime
from enum import Enum
from sqlalchemy import Enum as SQLAlchemyEnum


DATABASE_URL = "sqlite:///./history.db"

# Tạo engine và session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Khởi tạo Base và metadata
Base = declarative_base()
metadata = MetaData()



# Tạo bảng User
class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True, index=True, unique=True)
    display_name = Column(String)

# Tạo bảng Thread với thread_id auto increment
class Thread(Base):
    __tablename__ = "threads"
    thread_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'))
    user = relationship("User")
    communi_thread_id = Column(String)
    
    # Thêm các trường mới cho đánh giá
    rating = Column(Integer, nullable=True)  # Điểm đánh giá từ 1-5
    rated_at = Column(DateTime, nullable=True)  # Thời điểm được đánh giá
    message_pairs_count = Column(Integer, default=0)  # Số cặp hỏi đáp
    last_bot_response = Column(DateTime)  # Thời điểm bot trả lời cuối cùng
    last_rating_sent = Column(DateTime)  # Thời điểm gửi yêu cầu đánh giá cuối
    last_rating_count = Column(Integer, default=0)



    
    # Thêm các trường mới
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ConversationCache(Base):
    __tablename__ = "conversation_cache"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    thread_id = Column(Integer, unique=True)
    conversation_data = Column(Text)  # JSON string của conversation history
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class Bot(Base):
    __tablename__ = "bots"
    bot_id = Column(String, primary_key=True, index=True, unique=True)
    bot_name = Column(String)
    bot_token = Column(String)

# Tạo bảng ChatHistory để lưu trữ lịch sử chat
class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    thread_id = Column(Integer, ForeignKey('threads.thread_id'))
    user_id = Column(String, ForeignKey('users.user_id'))
    display_name = Column(String)  # Add display_name column
    conversation = Column(String)
    summary = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
# Khởi tạo bảng trong cơ sở dữ liệu
Base.metadata.create_all(bind=engine)
