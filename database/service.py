import json
import logging
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session 
from .models import ResumeAnalysis, AppUser 
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for handling database operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_user_by_username(self, db: Session, username: str) -> Optional[AppUser]:
        return db.query(AppUser).filter(AppUser.username == username).first()

    def authenticate_user(self, db: Session, username: str, password: str) -> Optional[AppUser]:
        user = self.get_user_by_username(db, username)
        if user and pwd_context.verify(password, user.hashed_password):
            return user
        return None

    def create_user(self, db: Session, username: str, hashed_password: str) -> AppUser:
        user = AppUser(username=username, hashed_password=hashed_password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def create_initial_analysis(self, db: Session, session_id: str, user_id: int, original_filename: str, job_description: str) -> ResumeAnalysis:
        analysis = ResumeAnalysis(
            session_id=session_id,
            user_id=user_id,
            original_filename=original_filename,
            job_description=job_description,
            status="PENDING"
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis
    
    def get_analysis_by_id(self, db: Session, analysis_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        analysis = db.query(ResumeAnalysis).filter(ResumeAnalysis.id == analysis_id, ResumeAnalysis.user_id == user_id).first()
        if analysis:
            optimized_resume_data = None
            if analysis.optimized_resume:
                try:
                    optimized_resume_data = json.loads(analysis.optimized_resume)
                except json.JSONDecodeError:
                    optimized_resume_data = analysis.optimized_resume
            return {
                "status": analysis.status,
                "results": analysis.analysis_results if analysis.status in ["COMPLETED", "OPTIMIZING"] else None,
                "optimized_resume": optimized_resume_data if analysis.status == "COMPLETED" and analysis.optimized_resume else None
            }
        return None