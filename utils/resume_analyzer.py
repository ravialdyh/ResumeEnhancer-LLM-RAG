# utils/resume_analyzer.py (updated)
import os
import json
import logging
from typing import Dict, List, Any

import google.generativeai as genai

from utils.rag_system import RAGSystem
from utils.text_processor import TextProcessor

class ResumeAnalyzer:
    """
    AI-powered resume analyzer that uses a dynamic, two-stage optimization process.
    """

    def __init__(self):
        """Initializes the analyzer, Gemini model, and other utilities."""
        self.logger = logging.getLogger(__name__)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=api_key)
        # Use the updated model as per 2025 availability
        self.model = genai.GenerativeModel('gemini-2.5-flash') 
        self.rag_system = RAGSystem()
        self.text_processor = TextProcessor()
        self.parsing_index_built = False  # Flag to build parsing index once

    def analyze_resume(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """
        Performs the initial analysis of the resume against the job description using RAG.
        This remains unchanged to preserve the original analysis functionality.
        """
        try:
            self.rag_system.clear_index()
            self.rag_system.build_job_requirements_index(job_description)
            context = self.rag_system.get_context_for_query(resume_text, max_context_length=1500)
            analysis_prompt = self._build_analysis_prompt(resume_text, job_description, context)
            
            response = self.model.generate_content(
                analysis_prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
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

    def parse_resume_to_structure(self, resume_text: str) -> Dict[str, Any]:
        """
        Uses AI to parse the resume text into a standardized structured dictionary.
        Now augmented with RAG for better accuracy on edge cases.
        """
        if not self.parsing_index_built:
            self._build_parsing_rag_index()
        
        # Retrieve relevant standard examples as context
        query = f"Standard resume sections matching this content: {resume_text[:500]}"  # Truncate query for efficiency
        context = self.rag_system.get_context_for_query(query, max_context_length=1500)
        
        prompt = f"""
        You are a resume parsing expert. Extract the information from the following resume text into the specified JSON structure.
        Use the provided context of standard resume section examples to guide mapping and normalization (e.g., map 'Volunteer' or 'Community Service' to 'volunteering').
        Do not add any information that is not present in the resume. If a section is missing, omit it or use empty list/string/object.
        For skills, group into technical (comma-separated tools/languages) and interests (comma-separated topics) if possible.
        For experience, group bullets into tasks if they have associated tools or seem grouped; otherwise, use one task with all bullets.

        **Standard Examples Context for Guidance:**
        {context}

        JSON Schema:
        {{
          "contact_info": {{"name": "str", "email": "str", "phone": "str", "linkedin": "str", "other_links": "str"}},
          "summary": "str",
          "experience": [
            {{"company": "str", "location": "str", "position": "str", "dates": "str",
              "tasks": [
                {{"bullets": ["str"], "tools": "str"}}
              ],
              "additional": "str"
            }}
          ],
          "achievements": [
            {{"title": "str", "description": "str"}}
          ],
          "projects": [
            {{"name": "str", "link": "str", "bullets": ["str"], "tools": "str"}}
          ],
          "education": [
            {{"institution": "str", "dates": "str", "details": "str"}}
          ],
          "volunteering": [
            {{"organization": "str", "position": "str", "dates": "str", "bullets": ["str"]}}
          ],
          "certifications": ["str"],
          "skills": {{"technical": "str", "interests": "str"}}
        }}

        Resume Text:
        {resume_text}

        Respond with ONLY the valid JSON object.
        """
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(response_mime_type="application/json")
            )
            parsed_structure = json.loads(response.text)
            self.logger.info("Successfully parsed resume to structured dict with RAG assistance")
            return parsed_structure
        except Exception as e:
            self.logger.error(f"Failed to parse resume structure: {e}")
            raise

    def _identify_optimizable_sections(self, resume_structure: Dict[str, Any]) -> List[str]:
        """
        Makes one preliminary API call to ask the AI which sections are suitable for rewriting.
        This is the core of the new intelligent approach.
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
            You are a system configuration API. Your task is to analyze the structure of a resume and decide which sections should be sent for content optimization.
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

    def generate_optimized_resume(self, resume_structure: Dict[str, Any], job_description: str) -> Dict[str, Any]:
        """
        Generates an optimized resume by dynamically identifying and then optimizing all
        relevant sections found in the resume.
        """
        optimized_structure = json.loads(json.dumps(resume_structure)) # Deep copy
        
        # --- Step 1: Ask the AI which sections to optimize ---
        sections_to_optimize = self._identify_optimizable_sections(resume_structure)

        # --- Step 2: Dynamically loop through the sections the AI chose ---
        for section_name in sections_to_optimize:
            section_data = resume_structure.get(section_name)
            if not section_data:
                continue
            
            self.logger.info(f"Optimizing section: {section_name}")
            prompt = self._build_section_optimization_prompt(section_data, job_description, section_name)
            
            try:
                # Structured sections expect a JSON response.
                if isinstance(section_data, (dict, list)):
                    response = self.model.generate_content(
                        prompt,
                        generation_config=genai.GenerationConfig(response_mime_type="application/json")
                    )
                    optimized_structure[section_name] = json.loads(response.text)
                # Simple text sections expect a plain text response.
                else:
                    response = self.model.generate_content(prompt)
                    optimized_structure[section_name] = response.text.strip()
            except Exception as e:
                self.logger.error(f"Could not optimize section '{section_name}': {e}. Keeping original content.")
                optimized_structure[section_name] = section_data # Keep original on error
                
        return optimized_structure

    def _build_section_optimization_prompt(self, section_data: Any, job_description: str, section_name: str) -> str:
        """Builds a prompt to optimize an entire section of the resume."""
        if isinstance(section_data, (dict, list)):
            data_format_instruction = f"Original JSON for the '{section_name}' section:\n```json\n{json.dumps(section_data, indent=2)}\n```\n\nCRITICAL: Your response MUST be ONLY the modified JSON object for this section, with the exact same structure. Do not add any other text."
        else:
            data_format_instruction = f"Original Text for the '{section_name}':\n{section_data}\n\nCRITICAL: Respond with ONLY the rewritten text, and nothing else."
        
        return f"""
        You are an expert resume writer. Rewrite the user-facing text within the following resume section to be more impactful and aligned with the provided job description.
        Use strong action verbs and quantify results where possible. Do not change factual information like company names or dates.
        
        Job Description:
        {job_description}
        
        {data_format_instruction}
        """

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