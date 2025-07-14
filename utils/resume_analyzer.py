import os
import json
import logging
from typing import Dict, List, Any
import re

from google import genai
from google.genai import types

from utils.rag_system import RAGSystem
from utils.text_processor import TextProcessor

class ResumeAnalyzer:
    """AI-powered resume analyzer using Gemini 2.5 Flash and RAG"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize Gemini client
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        self.client = genai.Client(api_key=api_key)
        self.rag_system = RAGSystem()
        self.text_processor = TextProcessor()
    
    def analyze_resume(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """
        Analyze resume against job requirements using AI and RAG
        
        Args:
            resume_text (str): Resume content
            job_description (str): Job description/requirements
            
        Returns:
            Dict: Analysis results with scores, improvements, and recommendations
        """
        try:
            # Build RAG index with job requirements
            self.rag_system.clear_index()
            self.rag_system.build_job_requirements_index(job_description)
            
            # Get relevant context for analysis
            context = self.rag_system.get_context_for_query(resume_text, max_context_length=1500)
            
            # Prepare analysis prompt
            analysis_prompt = self._build_analysis_prompt(resume_text, job_description, context)
            
            # Get analysis from Gemini
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=analysis_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )
            
            if not response.text:
                raise ValueError("Empty response from Gemini API")
            
            # Parse JSON response
            analysis_results = json.loads(response.text)
            
            # Enhance results with additional processing
            analysis_results = self._enhance_analysis_results(
                analysis_results, resume_text, job_description
            )
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Error analyzing resume: {str(e)}")
            raise
    
    def generate_optimized_resume(self, resume_text: str, job_description: str, analysis_results: Dict[str, Any]) -> str:
        """
        Generate an optimized version of the resume
        
        Args:
            resume_text (str): Original resume content
            job_description (str): Job description/requirements
            analysis_results (Dict): Previous analysis results
            
        Returns:
            str: Optimized resume content
        """
        try:
            # Get relevant context for optimization
            context = self.rag_system.get_context_for_query(resume_text, max_context_length=1000)
            
            # Prepare optimization prompt
            optimization_prompt = self._build_optimization_prompt(
                resume_text, job_description, analysis_results, context
            )
            
            # Get optimized resume from Gemini
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=optimization_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4
                )
            )
            
            if not response.text:
                raise ValueError("Empty response from Gemini API")
            
            return response.text.strip()
            
        except Exception as e:
            self.logger.error(f"Error generating optimized resume: {str(e)}")
            raise
    
    def _build_analysis_prompt(self, resume_text: str, job_description: str, context: str) -> str:
        """Build the analysis prompt for Gemini"""
        return f"""
You are an expert resume analyst and career coach. Analyze the following resume against the job requirements and provide a comprehensive assessment.

**Job Requirements Context:**
{context}

**Full Job Description:**
{job_description}

**Resume to Analyze:**
{resume_text}

Please provide a detailed analysis in JSON format with the following structure:
{{
    "match_score": <percentage 0-100>,
    "overall_rating": "<Excellent/Good/Fair/Poor>",
    "missing_keywords": [
        "<important keyword 1>",
        "<important keyword 2>"
    ],
    "missing_keywords_count": <number>,
    "strengths": [
        "<strength 1>",
        "<strength 2>"
    ],
    "improvements": [
        {{
            "category": "<Skills/Experience/Education/Format>",
            "issue": "<specific issue>",
            "suggestion": "<detailed suggestion>",
            "priority": "<High/Medium/Low>",
            "section": "<which resume section>"
        }}
    ],
    "recommendations": [
        "<recommendation 1>",
        "<recommendation 2>"
    ],
    "keyword_analysis": {{
        "present_keywords": ["<keyword1>", "<keyword2>"],
        "missing_critical_keywords": ["<keyword1>", "<keyword2>"],
        "skill_gaps": ["<skill1>", "<skill2>"]
    }}
}}

Focus on:
1. Keyword matching and ATS optimization
2. Relevant experience alignment
3. Skills gap analysis
4. Format and presentation improvements
5. Quantifiable achievements
6. Industry-specific requirements
"""
    
    def _build_optimization_prompt(self, resume_text: str, job_description: str, analysis_results: Dict[str, Any], context: str) -> str:
        """Build the optimization prompt for Gemini"""
        improvements_text = ""
        if analysis_results.get('improvements'):
            improvements_text = "\n".join([
                f"- {imp.get('issue', '')}: {imp.get('suggestion', '')}"
                for imp in analysis_results['improvements'][:5]
            ])
        
        missing_keywords = ", ".join(analysis_results.get('missing_keywords', [])[:10])
        
        return f"""
You are an expert resume writer. Create an optimized version of the resume based on the analysis results and job requirements.

**Job Requirements Context:**
{context}

**Original Resume:**
{resume_text}

**Key Issues to Address:**
{improvements_text}

**Missing Keywords to Include:** {missing_keywords}

**Optimization Guidelines:**
1. Maintain the original structure and personal information
2. Incorporate missing keywords naturally
3. Enhance experience descriptions with quantifiable achievements
4. Align skills and experience with job requirements
5. Improve action verbs and impact statements
6. Ensure ATS-friendly formatting
7. Keep the same general length and sections

**Important:**
- Do not fabricate experience or skills
- Enhance and reframe existing content more effectively
- Use stronger action verbs and metrics where possible
- Maintain professional tone and accuracy
- Focus on relevance to the target role

Please provide the complete optimized resume text:
"""
    
    def _enhance_analysis_results(self, results: Dict[str, Any], resume_text: str, job_description: str) -> Dict[str, Any]:
        """Enhance analysis results with additional processing"""
        try:
            # Add text statistics
            results['resume_stats'] = {
                'word_count': len(resume_text.split()),
                'character_count': len(resume_text),
                'section_count': len(self.text_processor.extract_resume_sections(resume_text))
            }
            
            # Add keyword density analysis
            job_keywords = self.text_processor.extract_keywords(job_description)
            resume_keywords = self.text_processor.extract_keywords(resume_text)
            
            # Calculate keyword overlap
            overlap = set(job_keywords) & set(resume_keywords)
            results['keyword_overlap'] = {
                'total_job_keywords': len(job_keywords),
                'matching_keywords': len(overlap),
                'overlap_percentage': (len(overlap) / len(job_keywords) * 100) if job_keywords else 0
            }
            
            # Ensure required fields exist
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
    
    def extract_skills_gap(self, resume_text: str, job_description: str) -> Dict[str, List[str]]:
        """Extract skills gap between resume and job requirements"""
        try:
            job_skills = self.text_processor.extract_skills(job_description)
            resume_skills = self.text_processor.extract_skills(resume_text)
            
            return {
                'missing_skills': list(set(job_skills) - set(resume_skills)),
                'matching_skills': list(set(job_skills) & set(resume_skills)),
                'additional_skills': list(set(resume_skills) - set(job_skills))
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting skills gap: {str(e)}")
            return {'missing_skills': [], 'matching_skills': [], 'additional_skills': []}
    
    def get_ats_score(self, resume_text: str) -> Dict[str, Any]:
        """Calculate ATS (Applicant Tracking System) friendliness score"""
        try:
            score = 100
            issues = []
            
            # Check for common ATS issues
            if len(re.findall(r'[^\w\s-]', resume_text)) > len(resume_text) * 0.05:
                score -= 15
                issues.append("Too many special characters")
            
            if len(resume_text.split()) < 200:
                score -= 10
                issues.append("Resume too short")
            
            if len(resume_text.split()) > 800:
                score -= 5
                issues.append("Resume might be too long")
            
            # Check for standard sections
            sections = self.text_processor.extract_resume_sections(resume_text)
            required_sections = ['experience', 'skills', 'education']
            missing_sections = [s for s in required_sections if s not in [sec.lower() for sec in sections.keys()]]
            
            if missing_sections:
                score -= len(missing_sections) * 10
                issues.extend([f"Missing {section} section" for section in missing_sections])
            
            score = max(0, min(100, score))
            
            return {
                'ats_score': score,
                'issues': issues,
                'recommendations': self._get_ats_recommendations(issues)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating ATS score: {str(e)}")
            return {'ats_score': 75, 'issues': [], 'recommendations': []}
    
    def _get_ats_recommendations(self, issues: List[str]) -> List[str]:
        """Get ATS improvement recommendations based on issues"""
        recommendations = []
        
        for issue in issues:
            if "special characters" in issue:
                recommendations.append("Use simple formatting and avoid excessive special characters")
            elif "too short" in issue:
                recommendations.append("Add more detail to your experience and achievements")
            elif "too long" in issue:
                recommendations.append("Condense content to focus on most relevant information")
            elif "Missing" in issue:
                recommendations.append(f"Add a {issue.split('Missing ')[1]} section to your resume")
        
        return recommendations
