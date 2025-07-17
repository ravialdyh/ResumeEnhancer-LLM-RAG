# utils/text_processor.py (updated - removed old parse method)
import re
import logging
from typing import List, Dict, Any

class TextProcessor:
    """Utility class for text processing and analysis"""
    
    def __init__(self):
        """Initializes the text processor with common patterns and keywords."""
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
        
        # Regex patterns for identifying section headers
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
        Split text into overlapping chunks for RAG processing.
        
        Args:
            text (str): Input text.
            chunk_size (int): Maximum size of each chunk.
            overlap (int): Overlap between chunks.
            
        Returns:
            List[str]: List of text chunks.
        """
        if not text or len(text) <= chunk_size:
            return [text] if text else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to end at a sentence boundary for cleaner chunks
            if end < len(text):
                # Look for sentence endings within the last part of the chunk
                sentence_end = text.rfind('.', start + chunk_size - 100, end)
                if sentence_end > start:
                    end = sentence_end + 1
                else:
                    # If no sentence end, look for word boundaries
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
        Extract important keywords from text.
        
        Args:
            text (str): Input text.
            
        Returns:
            List[str]: List of keywords.
        """
        # Clean and normalize text
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        words = text.split()
        keywords = set()
        
        # Define common English stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'under', 'between', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
            'could', 'can', 'may', 'might', 'must', 'shall', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }
        
        # Extract single words (if not stop words)
        for word in words:
            if len(word) > 2 and word not in stop_words:
                keywords.add(word)
        
        # Extract multi-word phrases (bigrams and trigrams)
        for i in range(len(words) - 1):
            phrase_2 = ' '.join(words[i:i+2])
            if len(phrase_2) > 5:
                keywords.add(phrase_2)
            
            if i < len(words) - 2:
                phrase_3 = ' '.join(words[i:i+3])
                if len(phrase_3) > 8:
                    keywords.add(phrase_3)
        
        # Filter out purely numeric keywords
        filtered_keywords = [kw for kw in keywords if not kw.isdigit()]
        
        return filtered_keywords[:50]  # Return top 50 keywords for brevity

    def extract_skills(self, text: str) -> List[str]:
        """
        Extract technical and soft skills from text.
        
        Args:
            text (str): Input text.
            
        Returns:
            List[str]: List of identified skills.
        """
        text_lower = text.lower()
        found_skills = set()
        
        # Check for pre-defined technical and soft skills
        all_predefined_skills = self.common_skills['technical'] + self.common_skills['soft_skills']
        for skill in all_predefined_skills:
            # Use word boundaries to avoid matching substrings (e.g., 'art' in 'artificial')
            if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
                found_skills.add(skill)
        
        # Extract other potential technologies with regex
        tech_patterns = [
            r'\b(?:python|java|javascript|typescript|c\+\+|c#|php|ruby|go|rust|swift|kotlin)\b',
            r'\b(?:react|angular|vue|node\.?js|express|django|flask|spring|laravel)\b',
            r'\b(?:aws|azure|gcp|docker|kubernetes|jenkins|terraform|ansible)\b',
            r'\b(?:sql|mysql|postgresql|mongodb|redis|elasticsearch|cassandra)\b'
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, text_lower)
            found_skills.update(matches)
        
        return list(found_skills)
    
    def extract_resume_sections(self, resume_text: str) -> Dict[str, str]:
        """
        Extract different sections from resume text using regex patterns.
        
        Args:
            resume_text (str): Resume content.
            
        Returns:
            Dict[str, str]: Dictionary mapping section names to their content.
        """
        sections = {}
        lines = resume_text.split('\n')
        current_section = 'header' # Default section for content at the top
        current_content = []
        
        for line in lines:
            stripped_line = line.strip()
            if not stripped_line:
                continue
            
            # Check if the line matches a section header pattern
            section_found = None
            # A line is considered a header if it's short and matches a pattern
            if len(stripped_line) < 50: 
                for section_name, pattern in self.section_patterns.items():
                    if re.match(pattern, stripped_line):
                        section_found = section_name
                        break
            
            if section_found:
                # Save the content of the previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # Start a new section
                current_section = section_found
                # Include the header line in the section content if it's descriptive
                header_content = stripped_line.replace(re.match(pattern, stripped_line).group(0), "").strip()
                current_content = [header_content] if header_content else []
            else:
                current_content.append(line)
        
        # Save the last section's content
        if current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections