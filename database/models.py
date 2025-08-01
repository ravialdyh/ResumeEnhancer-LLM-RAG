import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, Float, JSON, Boolean,
    Index, PrimaryKeyConstraint, ForeignKeyConstraint
)
from sqlalchemy.orm import sessionmaker, Session, declarative_base
import logging

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

logger = logging.getLogger(__name__)

class AppUser(Base):
    __tablename__ = "app_users"
    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        PrimaryKeyConstraint('id', name='pk_app_users'),
        Index('ix_app_users_username', 'username', unique=True),
    )


class ResumeAnalysis(Base):
    """Store resume analysis results"""
    __tablename__ = "resume_analyses"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), index=True)
    user_id = Column(Integer, nullable=False) # Foreign key is defined in __table_args__
    original_filename = Column(String(255))
    resume_text = Column(Text)
    job_description = Column(Text)
    analysis_results = Column(JSON)
    optimized_resume = Column(Text)
    match_score = Column(Float)
    overall_rating = Column(String(50))
    missing_keywords_count = Column(Integer)
    improvements_count = Column(Integer)
    status = Column(String(50), default='PENDING', nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        PrimaryKeyConstraint('id', name='pk_resume_analyses'),
        ForeignKeyConstraint(['user_id'], ['app_users.id'], name='fk_resume_analyses_user_id'),
        Index('ix_resume_analyses_user_id', 'user_id'),
        Index('ix_resume_analyses_session_id', 'session_id'),
    )


def create_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise

def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_database():
    """Initialize database"""
    try:
        create_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise