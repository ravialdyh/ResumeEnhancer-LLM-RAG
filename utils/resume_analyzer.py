import os
import json
import logging
from typing import Dict, List, Any, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field, create_model

from utils.rag_system import RAGSystem
from utils.text_processor import TextProcessor

class ContactInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    other_links: Optional[str] = None

class ExperienceTask(BaseModel):
    bullets: List[str] = Field(default_factory=list)
    tools: Optional[str] = None

class ExperienceEntry(BaseModel):
    company: Optional[str] = None
    location: Optional[str] = None
    position: Optional[str] = None
    dates: Optional[str] = None
    tasks: List[ExperienceTask] = Field(default_factory=list)
    additional: Optional[str] = None

class Achievement(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class Project(BaseModel):
    name: Optional[str] = None
    link: Optional[str] = None
    bullets: List[str] = Field(default_factory=list)
    tools: Optional[str] = None
    
class Education(BaseModel):
    institution: Optional[str] = None
    dates: Optional[str] = None
    details: Optional[str] = None

class Volunteering(BaseModel):
    organization: Optional[str] = None
    position: Optional[str] = None
    dates: Optional[str] = None
    bullets: List[str] = Field(default_factory=list)

class Skills(BaseModel):
    technical: Optional[str] = None
    interests: Optional[str] = None

class ParsedResume(BaseModel):
    contact_info: Optional[ContactInfo] = None
    summary: Optional[str] = None
    experience: List[ExperienceEntry] = Field(default_factory=list)
    achievements: List[Achievement] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    volunteering: List[Volunteering] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    skills: Optional[Skills] = None
    optimizable_sections: List[str] = Field(
        default_factory=list,
        description="A list of section names that contain descriptive text suitable for rewriting."
    )
    extracted_text: Optional[str] = Field(
        default=None,
        description="The full text content of the resume as extracted from the document."
    )

class ResumeAnalysisResult(BaseModel):
    match_score: int = Field(description="Percentage match score from 0-100.")
    overall_rating: str = Field(description="Overall rating: Excellent, Good, Fair, or Poor.")
    missing_keywords: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    improvements: List[Dict[str, Any]] = Field(default_factory=list)

class ResumeAnalyzer:
    def __init__(self, client: genai.Client):
        self.logger = logging.getLogger(__name__)
        if not client:
            raise ValueError("A valid genai.Client object is required.")
        self.client = client
        self.rag_system = RAGSystem()
        self.text_processor = TextProcessor()

    def analyze_resume(self, resume_bytes: bytes, resume_mime_type: str, job_description: str) -> Dict[str, Any]:
        """
        Orchestrates the hybrid analysis:
        1. Natively parses the resume document.
        2. Builds a RAG index for the job description.
        3. Performs a RAG-powered analysis.
        """
        try:
            # Step 1: Parse the resume from its byte content into a structured object
            parsed_resume_obj = self._parse_resume_from_bytes(resume_bytes, resume_mime_type)
            if not parsed_resume_obj or not parsed_resume_obj.extracted_text:
                raise ValueError("Failed to parse resume or extract its text content.")
            
            resume_text = parsed_resume_obj.extracted_text

            # Step 2: Build RAG index for the job description
            self.rag_system.clear_index()
            self.rag_system.build_job_requirements_index(job_description)

            # Step 3: Get the most relevant context from the JD using the resume as a query
            context = self.rag_system.get_context_for_query(resume_text, max_context_length=10000)

            # Step 4: Perform the final analysis using the extracted text and RAG context
            analysis_dict = self._perform_analysis_with_rag(resume_text, job_description, context)

            # Step 5: Combine everything into a single result for the Streamlit app
            final_result = analysis_dict
            final_result['parsed_resume'] = parsed_resume_obj.model_dump()
            final_result['extracted_resume_text'] = resume_text
            final_result['missing_keywords_count'] = len(final_result.get('missing_keywords', []))
            final_result['improvements_count'] = len(final_result.get('improvements', []))
            
            return final_result

        except Exception as e:
            self.logger.error(f"Error during hybrid resume analysis: {str(e)}")
            raise

    def _parse_resume_from_bytes(self, resume_bytes: bytes, resume_mime_type: str) -> Optional[ParsedResume]:
        """[Call 1] Sends the resume bytes to Gemini to be parsed into a Pydantic object."""
        prompt = """
        You are a world-class resume parsing engine. 
        Use your great vision capabilities to extract structured information from the provided resume document.
        1. Extract all text from the provided document and place it into the `extracted_text` field.
        2. Parse the document's content into the required structured format.
        3. Identify sections with free-form text (summary, experience bullets, etc.) and list them in `optimizable_sections`.
        """
        resume_part = types.Part(
            inline_data=types.Blob(mime_type=resume_mime_type, data=resume_bytes)
        )
        response = self.client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=[resume_part, prompt],
            config={
                "response_mime_type": "application/json",
                "response_schema": ParsedResume,
                "temperature": 0.1
            }
        )
        return response.parsed

    def _perform_analysis_with_rag(self, resume_text: str, job_description: str, rag_context: str) -> Dict[str, Any]:
        """[Call 2] Performs the resume analysis, grounded by the RAG context."""
        prompt = self._build_analysis_prompt(resume_text, job_description, rag_context)
        response = self.client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": ResumeAnalysisResult,
                "temperature": 0.3
            }
        )
        return response.parsed.model_dump()

    def _build_analysis_prompt(self, resume_text: str, job_description: str, context: str) -> str:
        """Builds the prompt for the RAG-powered analysis."""
        return f"""
        You are an expert resume analyst and career coach.
        Analyze the following resume against the job requirements, paying close attention to the provided "Key Job Requirements Context".

        **Key Job Requirements Context (from RAG system):**
        {context}
        
        **Full Job Description:**
        {job_description}
        
        **Full Resume to Analyze:**
        {resume_text}
        
        Please provide a detailed analysis in the required JSON format.
        """

    def generate_optimized_resume(self, resume_structure: Dict[str, Any], job_description: str, sections_to_optimize: List[str]) -> Dict[str, Any]:
        """
        Generates an optimized resume using a single, dynamically-structured batch API call.
        """
        optimized_structure = json.loads(json.dumps(resume_structure))

        if not sections_to_optimize:
            self.logger.info("No sections identified for optimization.")
            return optimized_structure

        master_schema_definitions = {
            "summary": str,
            "experience": List[ExperienceEntry],
            "projects": List[Project],
            "achievements": List[Achievement],
            "volunteering": List[Volunteering]
        }

        dynamic_schema_fields = {}
        data_to_optimize = {}
        for section in sections_to_optimize:
            if section in resume_structure and section in master_schema_definitions:
                data_to_optimize[section] = resume_structure[section]
                dynamic_schema_fields[section] = (master_schema_definitions[section], ...)

        if not data_to_optimize:
            return optimized_structure
        
        DynamicBatchModel = create_model('DynamicBatchModel', **dynamic_schema_fields)

        batch_prompt = f"""
        You are an expert resume writer. Rewrite the content in the following JSON object to be more impactful and aligned with the provided job description.
        Use strong action verbs and quantify results where possible.

        **Job Description:**
        {job_description}

        **Original Resume Sections to Optimize:**
        ```json
        {json.dumps(data_to_optimize, indent=2)}
        ```
        """
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=batch_prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": DynamicBatchModel,
                },
            )

            optimized_sections_model = response.parsed
            if optimized_sections_model:
                optimized_sections = optimized_sections_model.model_dump()
                for section_name, optimized_content in optimized_sections.items():
                    optimized_structure[section_name] = optimized_content
                self.logger.info(f"Successfully optimized sections via batch: {list(optimized_sections.keys())}")

        except Exception as e:
            self.logger.error(f"Batch optimization with schema failed: {e}. Keeping original content.")

        return optimized_structure