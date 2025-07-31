import os
import json
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

# --- ADD THIS NEW TASK ---
@shared_task(name='run_optimization')
def run_optimization_task(analysis_id: str):
    """
    Celery task to generate the optimized resume.
    """
    try:
        logger.info(f"Starting optimization for analysis_id: {analysis_id}")
        db_service.update_analysis_status(analysis_id, "OPTIMIZING")

        # Fetch the required data from the database
        analysis_record = db_service.get_full_analysis_by_id(analysis_id)
        if not analysis_record:
            raise ValueError("Analysis record not found.")

        parsed_resume_dict = analysis_record.analysis_results.get('parsed_resume')
        job_description = analysis_record.job_description
        sections_to_optimize = parsed_resume_dict.get('optimizable_sections', [])

        if not parsed_resume_dict or not sections_to_optimize:
            logger.warning(f"No optimizable sections for analysis_id: {analysis_id}. Marking as complete.")
            db_service.update_optimized_resume(analysis_id, json.dumps(parsed_resume_dict))
            db_service.update_analysis_status(analysis_id, "COMPLETED")
            return

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        analyzer = ResumeAnalyzer(client=client)

        optimized_structure = analyzer.generate_optimized_resume(
            parsed_resume_dict,
            job_description,
            sections_to_optimize
        )

        db_service.update_optimized_resume(analysis_id, json.dumps(optimized_structure))
        db_service.update_analysis_status(analysis_id, "COMPLETED") # Mark as completed after optimization
        logger.info(f"Successfully completed optimization for analysis_id: {analysis_id}")

    except Exception as e:
        sentry_sdk.capture_exception(e)
        db_service.update_analysis_status(analysis_id, "FAILED")
        logger.error(f"Optimization {analysis_id} failed: {e}")