# utils/resume_analyzer.py (updated)
import os
import json
import logging
from typing import Dict, List, Any, Optional

import google.genai as genai
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
        description="A list of section names (e.g., 'summary', 'experience') that contain descriptive text suitable for rewriting."
    )

class ResumeAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        self.client = genai.Client(api_key=api_key)
        self.model_name = 'gemini-2.5-flash-lite'
        
        self.rag_system = RAGSystem()
        self.text_processor = TextProcessor()


    def analyze_resume(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """
        Performs the initial analysis of the resume against the job description using RAG.
        """
        try:
            self.rag_system.clear_index()
            self.rag_system.build_job_requirements_index(job_description)
            context = self.rag_system.get_context_for_query(resume_text, max_context_length=1500)
            analysis_prompt = self._build_analysis_prompt(resume_text, job_description, context)
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=analysis_prompt,
                config={
                    "response_mime_type": "application/json",
                    "temperature": 0.3
                }
            )
            
            if not response.text:
                raise ValueError("Empty response from Gemini API for initial analysis")
            
            analysis_results = json.loads(response.text)
            return self._enhance_analysis_results(analysis_results, resume_text, job_description)
            
        except Exception as e:
            self.logger.error(f"Error during initial resume analysis: {str(e)}")
            raise

    def _build_parsing_rag_index(self):
        """Builds a small RAG index with standard resume section examples for grounding parsing."""
        # Hardcoded diverse examples (snippets of sections with variations; add more as needed)
        standard_examples = [
            # Summary variations
            "SUMMARY: Experienced software engineer with 5 years in Python and AI.",
            "Professional Profile: Data scientist specializing in ML models.",
            # Experience
            "WORK EXPERIENCE: Google, Mountain View - Software Engineer, 2020-Present. * Developed apps * Led teams",
            "Career History: Amazon, Seattle - Developer, 2018-2020. Responsibilities: Coding, testing.",
            # Volunteering edges
            "VOLUNTEER EXPERIENCE: Red Cross - Helper, 2022. * Organized events",
            "Community Service: Local Shelter - Volunteer, 2021. Activities: Feeding animals.",
            "Freiwilligenarbeit: NGO - Ehrenamtlicher, 2023. * Hilfsprojekte",  # Multilingual example
            "Volunteer: Soup Kitchen - Server, 2020. Bullets: Served meals, cleaned.",
            # Projects/Portfolio
            "PROJECTS: AI Chatbot - Built with PyTorch. Link: github.com/project",
            "Portfolio: Web Apps - Various sites using React.",
            # Achievements/Awards
            "ACHIEVEMENTS: Best Employee 2024 - Issued by Company X.",
            "Awards and Honors: Hackathon Winner - 2023.",
            # Education
            "EDUCATION: Harvard University, 2015-2019. BS in CS. GPA 3.8.",
            "Academic Background: MIT - MS in AI, 2020-2022.",
            # Certifications
            "CERTIFICATIONS: AWS Certified Developer - 2024.",
            "Licenses: Google Cloud Professional - Expires 2026.",
            # Skills
            "SKILLS: Technical: Python, Java. Interests: AI, Data Science.",
            "Competencies: Soft: Leadership. Hard: SQL, Docker."
        ]
        metadata = [{"type": "standard_section_example", "section": ex.split(":")[0].lower()} for ex in standard_examples]
        
        self.rag_system.clear_index()
        self.rag_system.add_documents(standard_examples, metadata)
        self.parsing_index_built = True
        self.logger.info("Built RAG index for resume parsing with standard examples.")

    def parse_resume_to_structure(self, resume_text: str) -> Optional[ParsedResume]:
        """
        Parses resume text and identifies optimizable sections in a single API call
        using a Pydantic model for structured output.
        """
        prompt = f"""
        You are a resume parsing expert. Extract information from the following resume text.
        
        Also, identify which sections contain descriptive, free-form text (like summaries or bullet points)
        that would benefit from being rewritten and list their names in the 'optimizable_sections' field.
        
        - INCLUDE descriptive sections like: summary, experience, projects, achievements, volunteering.
        - EXCLUDE factual lists like: skills, certifications, contact_info.

        Resume Text:
        {resume_text}
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": ParsedResume,
                }
            )
            return response.parsed
        except Exception as e:
            self.logger.error(f"Failed to parse resume with structured output: {e}")
            return None

    def _identify_optimizable_sections(self, resume_structure: Dict[str, Any]) -> List[str]:
        """
        Makes one preliminary API call to ask the AI which sections are suitable for rewriting.
        This remains unchanged but is crucial for the new batching logic.
        """
        section_previews = {}
        for section, data in resume_structure.items():
            preview = ""
            if isinstance(data, str):
                preview = (data[:150] + "...") if len(data) > 150 else data
            elif isinstance(data, list) and data and isinstance(data[0], dict):
                preview = "List of entries like: " + json.dumps(data[0])
            elif isinstance(data, list) and data:
                 preview = "List of items: " + ", ".join(map(str, data[:3]))
            elif data:
                preview = str(data)[:150]
            section_previews[section] = preview.strip()

        prompt = f"""
            You are a system configuration API. 
            Your task is to analyze the structure of a resume and decide which sections should be sent for content optimization.
            Based on the following section names and content previews, identify which sections contain descriptive, free-form text (like summaries or bullet points) that would benefit from being rewritten.
            **Rules:**
            - **INCLUDE** sections with descriptive paragraphs or bullet points (e.g., Summary, Experience, Projects, Achievements, Volunteering).
            - **EXCLUDE** sections that are just lists of keywords (like a simple 'Skills' list), contact information, or raw data that should not be changed.
            **Resume Structure Preview:**
            ```json
            {json.dumps(section_previews, indent=2)}
            ```
            Your response MUST be a single, valid JSON list containing only the string names of the sections to be optimized.
            Example response: ["summary", "experience", "projects"]
            """
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(response_mime_type="application/json")
            )
            optimizable_sections = json.loads(response.text)
            self.logger.info(f"AI identified the following sections to optimize: {optimizable_sections}")
            return optimizable_sections
        except Exception as e:
            self.logger.error(f"Failed to identify optimizable sections: {e}. Returning empty list.")
            return []
        
    def _build_batch_optimization_prompt(self, data_to_optimize: Dict[str, Any], job_description: str) -> str:
        """
        Builds a single prompt to optimize a batch of resume sections.
        """
        return f"""You are an expert resume writer. Rewrite the content in the following JSON object to be more impactful and aligned with the provided job description.

            - Use strong action verbs and quantify results where possible.
            - Do not change factual information like company names or dates.
            - Your response MUST be a single, valid JSON object with the exact same structure as the input, containing all the rewritten sections.

            **Job Description:**
            ```
            {job_description}
            ```

            **Original Resume Sections to Optimize:**
            ```json
            {json.dumps(data_to_optimize, indent=2)}
            ```
            """


    def generate_optimized_resume(self, resume_structure: Dict[str, Any], job_description: str, sections_to_optimize: List[str]) -> Dict[str, Any]:
        """
        Generates an optimized resume using a single, dynamically-structured batch API call.
        """
        optimized_structure = json.loads(json.dumps(resume_structure))

        if not sections_to_optimize:
            self.logger.info("No sections identified for optimization.")
            return optimized_structure

        # 1. Define all possible Pydantic models for the schemas
        master_schema_definitions = {
            "summary": str,
            "experience": List[ExperienceEntry],
            "projects": List[Project],
            "achievements": List[Achievement],
            "volunteering": List[Volunteering]
        }

        # 2. Dynamically build the schema and data for the specific sections to optimize
        dynamic_schema_fields = {}
        data_to_optimize = {}
        for section in sections_to_optimize:
            if section in resume_structure and section in master_schema_definitions:
                data_to_optimize[section] = resume_structure[section]
                dynamic_schema_fields[section] = (master_schema_definitions[section], ...)

        if not data_to_optimize:
            return optimized_structure
        
        # 3. Create a dynamic Pydantic model for the batch response
        DynamicBatchModel = create_model('DynamicBatchModel', **dynamic_schema_fields)

        # 4. Build the simplified batch prompt
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
        
        # 5. Execute the single, reliable batch call
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=batch_prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": DynamicBatchModel,
                },
            )

            # 6. Update the main structure with the results
            optimized_sections_model = response.parsed
            if optimized_sections_model:
                optimized_sections = optimized_sections_model.model_dump()
                for section_name, optimized_content in optimized_sections.items():
                    optimized_structure[section_name] = optimized_content
                self.logger.info(f"Successfully optimized sections via batch: {list(optimized_sections.keys())}")

        except Exception as e:
            self.logger.error(f"Batch optimization with schema failed: {e}. Keeping original content.")

        return optimized_structure    

    def _build_analysis_prompt(self, resume_text: str, job_description: str, context: str) -> str:
        """Builds the prompt for the initial analysis. (Unchanged)"""
        return f"""
        You are an expert resume analyst and career coach. Analyze the following resume against the job requirements and provide a comprehensive assessment.
        
        Job Requirements Context (from relevant parts of the job description):
        {context}
        
        Full Job Description:
        {job_description}
        
        Resume to Analyze:
        {resume_text}
        
        Please provide a detailed analysis in JSON format with the following structure:
        {{
            "match_score": <percentage 0-100>,
            "overall_rating": "<Excellent/Good/Fair/Poor>",
            "missing_keywords": ["<keyword 1>", "<keyword 2>"],
            "missing_keywords_count": <number>,
            "strengths": ["<strength 1>", "<strength 2>"],
            "improvements": [
                {{
                    "category": "<Skills/Experience/Education/Format>",
                    "issue": "<specific issue>",
                    "suggestion": "<detailed suggestion>",
                    "priority": "<High/Medium/Low>",
                    "section": "<which resume section>"
                }}
            ]
        }}
        """

    def _enhance_analysis_results(self, results: Dict[str, Any], resume_text: str, job_description: str) -> Dict[str, Any]:
        """Enhance analysis results with additional processing. (Unchanged)"""
        try:
            results['resume_stats'] = {
                'word_count': len(resume_text.split()),
                'character_count': len(resume_text),
                'section_count': len(self.text_processor.extract_resume_sections(resume_text))
            }
            job_keywords = self.text_processor.extract_keywords(job_description)
            resume_keywords = self.text_processor.extract_keywords(resume_text)
            overlap = set(job_keywords) & set(resume_keywords)
            results['keyword_overlap'] = {
                'total_job_keywords': len(job_keywords),
                'matching_keywords': len(overlap),
                'overlap_percentage': (len(overlap) / len(job_keywords) * 100) if job_keywords else 0
            }
            results.setdefault('match_score', 0)
            results.setdefault('missing_keywords', [])
            results.setdefault('missing_keywords_count', len(results.get('missing_keywords', [])))
            results.setdefault('strengths', [])
            results.setdefault('improvements', [])
            results.setdefault('recommendations', [])
            results.setdefault('overall_rating', 'Fair')
            return results
        except Exception as e:
            self.logger.error(f"Error enhancing analysis results: {str(e)}")
            return results