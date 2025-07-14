import os
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import logging

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

logger = logging.getLogger(__name__)

class ResumeAnalysis(Base):
    """Store resume analysis results"""
    __tablename__ = "resume_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True)  # For tracking user sessions
    original_filename = Column(String(255))
    resume_text = Column(Text)
    job_description = Column(Text)
    analysis_results = Column(JSON)  # Store the full analysis JSON
    optimized_resume = Column(Text)
    match_score = Column(Float)
    overall_rating = Column(String(50))
    missing_keywords_count = Column(Integer)
    improvements_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class UserSession(Base):
    """Track user sessions and preferences"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True)
    last_activity = Column(DateTime, default=datetime.utcnow)
    preferences = Column(JSON)  # Store user preferences
    analysis_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class AnalysisHistory(Base):
    """Store condensed analysis history for quick access"""
    __tablename__ = "analysis_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True)
    job_title = Column(String(255))  # Extracted from job description
    company_name = Column(String(255))  # Extracted from job description
    match_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

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
        return db
    except Exception as e:
        db.close()
        raise

def init_database():
    """Initialize database"""
    try:
        create_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise