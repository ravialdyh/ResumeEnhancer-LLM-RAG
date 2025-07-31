from loguru import logger
import sentry_sdk
from celery import shared_task
from google import genai
from utils.resume_analyzer import ResumeAnalyzer
from database.service import DatabaseService

db_service = DatabaseService()

@shared_task(name='run_analysis')
def run_analysis_task(analysis_id: str, resume_bytes: bytes, mime_type: str, job_desc: str):
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        analyzer = ResumeAnalyzer(client=client)
        results = analyzer.analyze_resume(resume_bytes, mime_type, job_desc)
        db_service.update_analysis_with_results(analysis_id, results, status="COMPLETED")
    except Exception as e:
        sentry_sdk.capture_exception(e)
        db_service.update_analysis_status(analysis_id, "FAILED")
        logger.error(f"Analysis {analysis_id} failed: {e}")