import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import re

from .models import ResumeAnalysis, UserSession, AnalysisHistory, get_db, init_database

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for handling database operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Initialize database on first use
        try:
            init_database()
        except Exception as e:
            self.logger.error(f"Database initialization failed: {str(e)}")
    
    def generate_session_id(self) -> str:
        """Generate a unique session ID"""
        return str(uuid.uuid4())
    
    def create_or_update_session(self, session_id: str, preferences: Dict[str, Any] = None) -> UserSession:
        """Create or update user session"""
        db = get_db()
        try:
            session = db.query(UserSession).filter(UserSession.session_id == session_id).first()
            
            if session:
                session.last_activity = datetime.utcnow()
                if preferences:
                    session.preferences = preferences
            else:
                session = UserSession(
                    session_id=session_id,
                    preferences=preferences or {},
                    analysis_count=0
                )
                db.add(session)
            
            db.commit()
            db.refresh(session)
            return session
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error creating/updating session: {str(e)}")
            raise
        finally:
            db.close()
    
    def save_analysis(self, session_id: str, resume_text: str, job_description: str,
                     analysis_results: Dict[str, Any], optimized_resume: str = "",
                     original_filename: str = "") -> ResumeAnalysis:
        """Save resume analysis to database"""
        db = get_db()
        try:
            # Extract key metrics from analysis results
            match_score = analysis_results.get('match_score', 0)
            overall_rating = analysis_results.get('overall_rating', 'Fair')
            missing_keywords_count = len(analysis_results.get('missing_keywords', []))
            improvements_count = len(analysis_results.get('improvements', []))
            
            analysis = ResumeAnalysis(
                session_id=session_id,
                original_filename=original_filename,
                resume_text=resume_text,
                job_description=job_description,
                analysis_results=analysis_results,
                optimized_resume=optimized_resume,
                match_score=match_score,
                overall_rating=overall_rating,
                missing_keywords_count=missing_keywords_count,
                improvements_count=improvements_count
            )
            
            db.add(analysis)
            
            # Update session analysis count
            session = db.query(UserSession).filter(UserSession.session_id == session_id).first()
            if session:
                session.analysis_count += 1
                session.last_activity = datetime.utcnow()
            
            # Add to analysis history
            job_info = self._extract_job_info(job_description)
            history = AnalysisHistory(
                session_id=session_id,
                job_title=job_info.get('title', ''),
                company_name=job_info.get('company', ''),
                match_score=match_score
            )
            db.add(history)
            
            db.commit()
            db.refresh(analysis)
            return analysis
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error saving analysis: {str(e)}")
            raise
        finally:
            db.close()
    
    def get_analysis_history(self, session_id: str, limit: int = 10) -> List[AnalysisHistory]:
        """Get analysis history for a session"""
        db = get_db()
        try:
            history = db.query(AnalysisHistory)\
                        .filter(AnalysisHistory.session_id == session_id)\
                        .order_by(desc(AnalysisHistory.created_at))\
                        .limit(limit)\
                        .all()
            return history
        except Exception as e:
            self.logger.error(f"Error getting analysis history: {str(e)}")
            return []
        finally:
            db.close()
    
    def get_latest_analysis(self, session_id: str) -> Optional[ResumeAnalysis]:
        """Get the most recent analysis for a session"""
        db = get_db()
        try:
            analysis = db.query(ResumeAnalysis)\
                        .filter(ResumeAnalysis.session_id == session_id)\
                        .filter(ResumeAnalysis.is_active == True)\
                        .order_by(desc(ResumeAnalysis.created_at))\
                        .first()
            return analysis
        except Exception as e:
            self.logger.error(f"Error getting latest analysis: {str(e)}")
            return None
        finally:
            db.close()
    
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
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session"""
        db = get_db()
        try:
            session = db.query(UserSession).filter(UserSession.session_id == session_id).first()
            
            if not session:
                return {}
            
            # Get analysis statistics
            analyses = db.query(ResumeAnalysis)\
                        .filter(ResumeAnalysis.session_id == session_id)\
                        .filter(ResumeAnalysis.is_active == True)\
                        .all()
            
            avg_match_score = 0
            if analyses:
                avg_match_score = sum(a.match_score for a in analyses if a.match_score) / len(analyses)
            
            return {
                'total_analyses': len(analyses),
                'average_match_score': round(avg_match_score, 1),
                'session_created': session.created_at,
                'last_activity': session.last_activity,
                'improvements_generated': sum(a.improvements_count for a in analyses if a.improvements_count)
            }
        except Exception as e:
            self.logger.error(f"Error getting session stats: {str(e)}")
            return {}
        finally:
            db.close()
    
    def delete_analysis(self, analysis_id: int, session_id: str) -> bool:
        """Soft delete an analysis"""
        db = get_db()
        try:
            analysis = db.query(ResumeAnalysis)\
                        .filter(ResumeAnalysis.id == analysis_id)\
                        .filter(ResumeAnalysis.session_id == session_id)\
                        .first()
            
            if analysis:
                analysis.is_active = False
                analysis.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error deleting analysis: {str(e)}")
            return False
        finally:
            db.close()
    
    def _extract_job_info(self, job_description: str) -> Dict[str, str]:
        """Extract job title and company from job description"""
        job_info = {'title': '', 'company': ''}
        
        try:
            lines = job_description.split('\n')[:10]  # Check first 10 lines
            
            # Common patterns for job titles
            title_patterns = [
                r'(?i)position:\s*(.+)',
                r'(?i)job\s+title:\s*(.+)',
                r'(?i)role:\s*(.+)',
                r'(?i)we\s+are\s+looking\s+for\s+a?\s*(.+)',
                r'(?i)hiring\s+a?\s*(.+)',
            ]
            
            # Common patterns for company names
            company_patterns = [
                r'(?i)company:\s*(.+)',
                r'(?i)at\s+([A-Z][a-zA-Z\s&]+)(?:\s+we|\s+is|\s+has)',
                r'(?i)join\s+([A-Z][a-zA-Z\s&]+)',
            ]
            
            for line in lines:
                # Extract job title
                for pattern in title_patterns:
                    match = re.search(pattern, line)
                    if match and not job_info['title']:
                        job_info['title'] = match.group(1).strip()[:100]  # Limit length
                
                # Extract company name
                for pattern in company_patterns:
                    match = re.search(pattern, line)
                    if match and not job_info['company']:
                        job_info['company'] = match.group(1).strip()[:100]  # Limit length
                
                if job_info['title'] and job_info['company']:
                    break
            
        except Exception as e:
            self.logger.warning(f"Error extracting job info: {str(e)}")
        
        return job_info