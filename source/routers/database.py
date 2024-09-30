# database.py
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DATABASE_URL = "sqlite:///./test.db"

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
# Tạo bảng ChatHistory để lưu trữ lịch sử chat
class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    thread_id = Column(Integer, ForeignKey('threads.thread_id'))
    user_id = Column(String, ForeignKey('users.user_id'))
    conversation = Column(String)
    
    
# Khởi tạo bảng trong cơ sở dữ liệu
Base.metadata.create_all(bind=engine)
