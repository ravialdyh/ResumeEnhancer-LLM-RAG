import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .models import ResumeAnalysis, get_db, init_database, AppUser

from passlib.context import CryptContext
from .models import AppUser
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for handling database operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        try:
            init_database()
        except Exception as e:
            self.logger.error(f"Database initialization failed: {str(e)}")
    
    def update_optimized_resume(self, analysis_id: int, optimized_resume: str) -> bool:
        """Update the optimized resume for an analysis"""
        db = get_db()
        try:
            analysis = db.query(ResumeAnalysis).filter(ResumeAnalysis.id == analysis_id).first()
            if analysis:
                analysis.optimized_resume = optimized_resume
                analysis.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error updating optimized resume: {str(e)}")
            return False
        finally:
            db.close()
    
    def create_user(self, username: str, hashed_password: str) -> AppUser:
        db = get_db()
        try:
            user = AppUser(username=username, hashed_password=hashed_password)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()

    def authenticate_user(self, username: str, password: str) -> Optional[AppUser]:
        db = get_db()
        try:
            user = db.query(AppUser).filter(AppUser.username == username).first()
            if user and pwd_context.verify(password, user.hashed_password):
                return user
            return None
        finally:
            db.close()

    def get_user_by_username(self, username: str) -> Optional[AppUser]:
        db = get_db()
        try:
            return db.query(AppUser).filter(AppUser.username == username).first()
        finally:
            db.close()

    def create_initial_analysis(self, session_id: str, user_id: int, original_filename: str, job_description: str) -> ResumeAnalysis:
        db = get_db()
        try:
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
        finally:
            db.close()

    def update_analysis_status(self, analysis_id: str, status: str):
        db = get_db()
        try:
            analysis = db.query(ResumeAnalysis).filter(ResumeAnalysis.id == analysis_id).first()
            if analysis:
                analysis.status = status
                analysis.updated_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    def update_analysis_with_results(self, analysis_id: str, results: Dict[str, Any], status: str = "COMPLETED"):
        db = get_db()
        try:
            analysis = db.query(ResumeAnalysis).filter(ResumeAnalysis.id == analysis_id).first()
            if analysis:
                analysis.analysis_results = results
                analysis.status = status
                analysis.updated_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    def get_analysis_by_id(self, analysis_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        db = get_db()
        try:
            analysis = db.query(ResumeAnalysis).filter(ResumeAnalysis.id == analysis_id, ResumeAnalysis.user_id == user_id).first()
            if analysis:
                optimized_resume_data = None
                if analysis.optimized_resume:
                    try:
                        optimized_resume_data = json.loads(analysis.optimized_resume)
                    except json.JSONDecodeError:
                        optimized_resume_data = analysis.optimized_resume # Fallback for non-JSON

                return {
                    "status": analysis.status,
                    "results": analysis.analysis_results if analysis.status in ["COMPLETED", "OPTIMIZING"] else None,
                    "optimized_resume": optimized_resume_data if analysis.status == "COMPLETED" and analysis.optimized_resume else None
                }
            return None
        finally:
            db.close()

    def get_full_analysis_by_id(self, analysis_id: str) -> Optional[ResumeAnalysis]:
        """Gets the full SQLAlchemy ResumeAnalysis object."""
        db = get_db()
        try:
            return db.query(ResumeAnalysis).filter(ResumeAnalysis.id == analysis_id).first()
        finally:
            db.close()