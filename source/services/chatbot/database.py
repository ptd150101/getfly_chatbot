from sqlalchemy import(
    Column, String, DateTime,
    ForeignKey, Text, JSON, Boolean,
    Integer, create_engine, UniqueConstraint, Index
)
from datetime import datetime
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from source.config.env_config import DATABASE_URL
from pgvector.sqlalchemy import Vector
import structlog
import json
import pytz


vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')

"""
### Cấu hình database
"""
engine = create_engine(DATABASE_URL, json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


"""
### Hàm tiện ích
"""
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""
### Cấu hình logging
"""

def encode_unicode(logger, method_name, event_dict):
    """
    Encode unicode values in event_dict
    """
    for key, value in event_dict.items():
        if isinstance(value, str):
            event_dict[key] = value.encode('utf-8', errors='replace').decode('utf-8')
    return event_dict


structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        encode_unicode,
        structlog.processors.JSONRenderer(ensure_ascii=False),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()


"""
### Định nghĩa các bảng
"""


class Embedding(Base):
    __tablename__ = "embeddings"
    chunk_id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(255), ForeignKey("documents.doc_id"))
    embedding = Column(Vector(1024))
    embedding_enrichment = Column(Vector(1024))
    page_content = Column(Text)
    enriched_content = Column(Text, nullable=True)
    language = Column(String(255), nullable=True)
    text = Column(Text)
    url = Column(String(255))
    archived = Column(Boolean, default=False)
    customer_id = Column(String(255))
    content_hash = Column(String(255), nullable=True)
    images = Column(JSON, nullable=True)
    videos = Column(JSON, nullable=True)
    chunk_index = Column(Integer, nullable=True)
    child_link = Column(String(255), nullable=True)


    """# -------------- Relationships --------------"""
    document = relationship("Document", back_populates="embeddings")

    """# -------------- Indexes --------------"""
    # Thêm unique constraint cho cặp doc_id và content_hash
    __table_args__ = (
        UniqueConstraint('doc_id', 'content_hash', name='uix_doc_id_content_hash'),
        Index('idx_customer_id', customer_id),
        Index('idx_doc_id', doc_id),
    )

class Document(Base):
    __tablename__ = "documents"
    doc_id = Column(String(255), primary_key=True)
    url = Column(String(255), nullable=True)
    url_id = Column(String(255), nullable=True)
    title = Column(Text)
    text = Column(Text)
    customer_id = Column(String(255), nullable=True)
    context = Column(JSON)  # Chứa các title của parent doc id dưới dạng JSON
    parent_doc_id = Column(String(255), nullable=True)
    collection_id = Column(String(255), ForeignKey("collections.collection_id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)
    archived = Column(Boolean, default=False)


    """# -------------- Relationships --------------"""
    bots = relationship("BotDocument", back_populates="document")
    embeddings = relationship("Embedding", back_populates="document")



    """# -------------- Indexes --------------"""
    __table_args__ = (
        Index('idx_customer_id', customer_id),
        Index('idx_url_id', url_id),
        Index('idx_created_at', created_at),
    )
    
class Collection(Base):
    __tablename__ = "collections"
    collection_id = Column(String(255), primary_key=True)
    url = Column(String)
    url_id = Column(String)
    name = Column(String)


    """# -------------- Relationships --------------"""
    bots = relationship("BotCollection", back_populates="collection")



class Bot(Base):
    __tablename__ = "bots"
    bot_id = Column(String(255), primary_key=True)
    name = Column(String(255), unique=True)
    description = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    """# -------------- Relationships --------------"""
    collections = relationship("BotCollection", back_populates="bot")
    documents = relationship("BotDocument", back_populates="bot")

class BotCollection(Base):
    __tablename__ = "bot_collections"
    bot_id = Column(String(255), ForeignKey("bots.bot_id"), primary_key=True)
    collection_id = Column(String(255), ForeignKey("collections.collection_id"), primary_key=True)
    created_at = Column(DateTime)

    """# -------------- Relationships --------------"""
    bot = relationship("Bot", back_populates="collections")
    collection = relationship("Collection", back_populates="bots")

class BotDocument(Base):
    __tablename__ = "bot_documents"
    doc_id = Column(String(255), ForeignKey("documents.doc_id"), primary_key=True)
    bot_id = Column(String(255), ForeignKey("bots.bot_id"), primary_key=True)
    is_removed_from_bot = Column(Boolean, default=False)
    created_at = Column(DateTime)
    removed_at = Column(DateTime(timezone=True))

    """# -------------- Relationships --------------"""
    document = relationship("Document", back_populates="bots")
    bot = relationship("Bot", back_populates="documents")


class GitbookCollection(Base):
    __tablename__ = 'gitbook_collections'
    
    id = Column(Integer, primary_key=True)
    # IDs thường có độ dài cố định hoặc giới hạn nhỏ
    collection_id = Column(String(50), unique=True)  
    collection_name = Column(String(255))  # Tên thường không quá dài
    space_id = Column(String(50))
    # Tokens thường có độ dài cố định, thường là 32-64 ký tự
    api_token = Column(String(100))  
    outline_api_token = Column(String(100))
    # URLs có thể dài nhưng hiếm khi quá 255 ký tự
    outline_api_url = Column(String(255))
    github_token = Column(String(100))
    created_at = Column(DateTime, default=datetime.now(vietnam_tz))
    repo = Column(String(255))  # Đường dẫn repo không nên quá dài
    
    """# -------------- Relationships --------------"""
    documents = relationship("GitbookDocument", back_populates="collection")



class GitbookDocument(Base):
    __tablename__ = 'gitbook_documents'
    
    id = Column(Integer, primary_key=True) 
    gitbook_id = Column(String(50))
    
    # metadata fields
    path = Column(String(500))  # Đường dẫn có thể dài
    git_path = Column(String(500))
    title = Column(String(255))
    # Description và text nên dùng Text thay vì String vì có thể rất dài
    description = Column(Text)  
    parent = Column(String(50))
    outline_id = Column(String(50))
    outline_parent_id = Column(String(50))
    
    # content
    text = Column(Text)  # Nội dung có thể rất dài
    child_links = Column(Text)  # Links có thể nhiều và dài
    created_at = Column(DateTime, default=datetime.now(vietnam_tz))
    
    collection_id = Column(String(50), ForeignKey('gitbook_collections.collection_id'), nullable=False)
    
    
    """# -------------- Relationships --------------"""
    collection = relationship("GitbookCollection", back_populates="documents")

    """# -------------- Indexes --------------"""
    __table_args__ = (
        Index('idx_gitbook_outline_id', outline_id),
        Index('idx_gitbook_collection_id', collection_id),
        Index('idx_gitbook_created_at', created_at),
    )

"""
### Tạo các bảng
"""
Base.metadata.create_all(bind=engine)
