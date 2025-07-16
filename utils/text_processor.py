import re
import logging
from typing import List, Dict, Set
from collections import Counter

class TextProcessor:
    """Utility class for text processing and analysis"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common job-related keywords and skills
        self.common_skills = {
            'technical': [
                'python', 'java', 'javascript', 'sql', 'html', 'css', 'react', 'angular', 'vue',
                'node.js', 'express', 'django', 'flask', 'spring', 'mongodb', 'postgresql',
                'mysql', 'redis', 'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'git',
                'jenkins', 'terraform', 'ansible', 'linux', 'windows', 'api', 'rest',
                'graphql', 'microservices', 'devops', 'ci/cd', 'agile', 'scrum', 'machine learning',
                'artificial intelligence', 'data science', 'tensorflow', 'pytorch', 'pandas',
                'numpy', 'scikit-learn', 'tableau', 'power bi', 'excel', 'r', 'matlab'
            ],
            'soft_skills': [
                'communication', 'leadership', 'teamwork', 'problem solving', 'analytical',
                'creative', 'adaptable', 'detail-oriented', 'organized', 'time management',
                'project management', 'customer service', 'presentation', 'negotiation',
                'strategic thinking', 'innovation', 'collaboration', 'mentoring', 'coaching'
            ]
        }
        
        # Section headers patterns
        self.section_patterns = {
            'experience': r'(?i)(work\s+)?experience|employment|professional\s+experience|career\s+history',
            'education': r'(?i)education|academic|qualifications|degrees?',
            'skills': r'(?i)skills|competencies|technical\s+skills|core\s+competencies',
            'summary': r'(?i)summary|profile|objective|about|overview',
            'projects': r'(?i)projects?|portfolio|work\s+samples',
            'certifications': r'(?i)certifications?|certificates?|licenses?',
            'achievements': r'(?i)achievements?|accomplishments?|awards?|honors?',
            'contact': r'(?i)contact|personal\s+information|details'
        }
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks for RAG processing
        
        Args:
            text (str): Input text
            chunk_size (int): Maximum size of each chunk
            overlap (int): Overlap between chunks
            
        Returns:
            List[str]: List of text chunks
        """
        if not text or len(text) <= chunk_size:
            return [text] if text else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to end at a sentence boundary
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                sentence_end = text.rfind('.', start + chunk_size - 100, end)
                if sentence_end > start:
                    end = sentence_end + 1
                else:
                    # Look for word boundaries
                    word_end = text.rfind(' ', start + chunk_size - 50, end)
                    if word_end > start:
                        end = word_end
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            
            if start >= len(text):
                break
        
        return chunks
    
    def extract_keywords(self, text: str) -> List[str]:
        """
        Extract important keywords from text
        
        Args:
            text (str): Input text
            
        Returns:
            List[str]: List of keywords
        """
        # Clean and normalize text
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Extract potential keywords (2-4 word phrases and single words)
        words = text.split()
        keywords = set()
        
        # Single words (filter common words)
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'under', 'between', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
            'could', 'can', 'may', 'might', 'must', 'shall', 'this', 'that', 'these', 'those'
        }
        
        for word in words:
            if len(word) > 2 and word not in stop_words:
                keywords.add(word)
        
        # Multi-word phrases (2-3 words)
        for i in range(len(words) - 1):
            phrase = ' '.join(words[i:i+2])
            if len(phrase) > 5:
                keywords.add(phrase)
            
            if i < len(words) - 2:
                phrase = ' '.join(words[i:i+3])
                if len(phrase) > 8:
                    keywords.add(phrase)
        
        # Filter and rank keywords
        filtered_keywords = []
        for keyword in keywords:
            if len(keyword) > 2 and not keyword.isdigit():
                filtered_keywords.append(keyword)
        
        return filtered_keywords[:50]  # Return top 50 keywords
    
    def extract_skills(self, text: str) -> List[str]:
        """
        Extract technical and soft skills from text
        
        Args:
            text (str): Input text
            
        Returns:
            List[str]: List of identified skills
        """
        text_lower = text.lower()
        found_skills = []
        
        # Check for technical skills
        for skill in self.common_skills['technical']:
            if skill in text_lower:
                found_skills.append(skill)
        
        # Check for soft skills
        for skill in self.common_skills['soft_skills']:
            if skill in text_lower:
                found_skills.append(skill)
        
        # Extract programming languages and technologies
        tech_patterns = [
            r'\b(?:python|java|javascript|typescript|c\+\+|c#|php|ruby|go|rust|swift|kotlin)\b',
            r'\b(?:react|angular|vue|node\.?js|express|django|flask|spring|laravel)\b',
            r'\b(?:aws|azure|gcp|docker|kubernetes|jenkins|terraform|ansible)\b',
            r'\b(?:sql|mysql|postgresql|mongodb|redis|elasticsearch|cassandra)\b'
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, text_lower)
            found_skills.extend(matches)
        
        return list(set(found_skills))
    
    def extract_resume_sections(self, resume_text: str) -> Dict[str, str]:
        """
        Extract different sections from resume text
        
        Args:
            resume_text (str): Resume content
            
        Returns:
            Dict[str, str]: Dictionary mapping section names to content
        """
        sections = {}
        lines = resume_text.split('\n')
        current_section = 'header'
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line is a section header
            section_found = None
            for section_name, pattern in self.section_patterns.items():
                if re.match(pattern, line):
                    section_found = section_name
                    break
            
            if section_found:
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                
                # Start new section
                current_section = section_found
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def extract_job_sections(self, job_description: str) -> Dict[str, str]:
        """
        Extract different sections from job description
        
        Args:
            job_description (str): Job description text
            
        Returns:
            Dict[str, str]: Dictionary mapping section names to content
        """
        sections = {}
        
        # Common job description section patterns
        job_patterns = {
            'requirements': r'(?i)requirements?|qualifications?|what\s+we\s+need|must\s+have',
            'responsibilities': r'(?i)responsibilities?|duties|what\s+you\s+will\s+do|role|tasks?',
            'skills': r'(?i)skills?|competencies|technical\s+skills|abilities',
            'experience': r'(?i)experience|background|years?\s+of\s+experience',
            'education': r'(?i)education|degree|academic|university|college',
            'benefits': r'(?i)benefits?|perks?|what\s+we\s+offer|compensation',
            'company': r'(?i)about\s+(us|the\s+company)|company\s+overview|who\s+we\s+are'
        }
        
        lines = job_description.split('\n')
        current_section = 'overview'
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line is a section header
            section_found = None
            for section_name, pattern in job_patterns.items():
                if re.match(pattern, line) or (len(line) < 50 and re.search(pattern, line)):
                    section_found = section_name
                    break
            
            if section_found:
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                
                # Start new section
                current_section = section_found
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts using simple keyword overlap
        
        Args:
            text1 (str): First text
            text2 (str): Second text
            
        Returns:
            float: Similarity score between 0 and 1
        """
        keywords1 = set(self.extract_keywords(text1))
        keywords2 = set(self.extract_keywords(text2))
        
        if not keywords1 or not keywords2:
            return 0.0
        
        intersection = keywords1 & keywords2
        union = keywords1 | keywords2
        
        return len(intersection) / len(union) if union else 0.0
    
    def highlight_missing_keywords(self, text: str, keywords: List[str]) -> str:
        """
        Highlight missing keywords in text (for display purposes)
        
        Args:
            text (str): Original text
            keywords (List[str]): Keywords to highlight
            
        Returns:
            str: Text with highlighted keywords
        """
        highlighted_text = text
        
        for keyword in keywords:
            # Case-insensitive replacement with highlighting
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            highlighted_text = pattern.sub(f"**{keyword}**", highlighted_text)
        
        return highlighted_text
    
    def extract_quantifiable_achievements(self, text: str) -> List[str]:
        """
        Extract quantifiable achievements from text
        
        Args:
            text (str): Input text
            
        Returns:
            List[str]: List of achievements with numbers/percentages
        """
        # Patterns for quantifiable achievements
        patterns = [
            r'[^\.\n]*\d+%[^\.\n]*',  # Percentages
            r'[^\.\n]*\$[\d,]+[^\.\n]*',  # Dollar amounts
            r'[^\.\n]*\d+[\s\-]*(?:years?|months?|weeks?|days?)[^\.\n]*',  # Time periods
            r'[^\.\n]*\d+[\s\-]*(?:people|employees|team members?|users?|customers?)[^\.\n]*',  # People
            r'[^\.\n]*(?:increased|improved|reduced|decreased|saved|generated)[^\.\n]*\d+[^\.\n]*',  # Impact verbs with numbers
        ]
        
        achievements = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            achievements.extend([match.strip() for match in matches])
        
        return list(set(achievements))
    
    def parse_resume_to_structured_dict(self, resume_text: str) -> Dict[str, Any]:
            """
            Parses resume text into a structured dictionary.
            This is a simplified example; a more robust implementation might use more advanced regex.
            """
            sections = self.extract_resume_sections(resume_text)
            structured_resume = {}

            # Parse Summary
            if 'summary' in sections:
                structured_resume['summary'] = sections['summary']
            
            # Parse Contact Info (usually in the header)
            if 'header' in sections:
                header_text = sections['header']
                structured_resume['contact_info'] = {
                    'name': header_text.split('\n')[0],
                    'details': '\n'.join(header_text.split('\n')[1:])
                }

            # Parse Experience
            if 'experience' in sections:
                structured_resume['experience'] = []
                # This regex is an example; it might need refinement for different resume formats
                jobs = re.split(r'\n(?=[A-Z\s&]+\s*\|)', sections['experience']) # Split by "COMPANY | Location"
                for job in jobs:
                    if not job.strip(): continue
                    lines = job.strip().split('\n')
                    job_title_line = lines[1] if len(lines) > 1 else ''
                    date_line = re.search(r'(\w+\s\d{4}\s*–\s*\w+)', job_title_line)
                    
                    job_entry = {
                        "company_location": lines[0].strip(),
                        "title": job_title_line.split(' | ')[0].replace('**', '').strip(),
                        "dates": date_line.group(0) if date_line else "",
                        "bullets": [l.replace('*','').strip() for l in lines[2:] if l.strip().startswith('*')]
                    }
                    structured_resume['experience'].append(job_entry)

            # Add stubs for other sections to be parsed
            structured_resume['education'] = sections.get('education', '')
            structured_resume['skills'] = sections.get('skills', '')

            return structured_resume


    def generate_optimized_resume(self, resume_structure: Dict[str, Any], job_description: str, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
            """
            Generate an optimized version of the resume from a structured dictionary.
            
            Args:
                resume_structure (Dict): Structured dictionary of the original resume.
                job_description (str): Job description/requirements.
                analysis_results (Dict): Previous analysis results.
            
            Returns:
                Dict: A new structured dictionary with optimized content.
            """
            try:
                optimization_prompt = self._build_structured_optimization_prompt(
                    resume_structure, job_description, analysis_results
                )
                
                response = self.model.generate_content(
                    optimization_prompt,
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.4
                    )
                )
                
                if not response.text:
                    raise ValueError("Empty response from Gemini API for optimization")
                
                # The model now returns a JSON object that matches our structured format
                optimized_structure = json.loads(response.text)
                return optimized_structure
                
            except Exception as e:
                self.logger.error(f"Error generating optimized resume structure: {str(e)}")
                raise

        # You also need a new prompt-building function for this structured approach.
        # Add this method to the ResumeAnalyzer class.
    def _build_structured_optimization_prompt(self, resume_structure: Dict[str, Any], job_description: str, analysis_results: Dict[str, Any]) -> str:
            """Build the structured optimization prompt for Gemini."""
            
            improvements_text = "\n".join([
                f"- {imp.get('issue', '')}: {imp.get('suggestion', '')}"
                for imp in analysis_results.get('improvements', [])[:5]
            ])

            # The f-string starts here with f"""
            return f"""
                You are an expert resume writer. Rewrite the content of the following JSON resume structure to be more impactful and better aligned with the provided job description.

                **Job Description:**
                {job_description}

                **Key Issues from Initial Analysis:**
                {improvements_text}

                **Original Resume Content (in JSON format):**
                ```json
                {json.dumps(resume_structure, indent=2)}```
            """