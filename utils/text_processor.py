import re
import logging
from typing import List, Dict
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

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
        
        # Prototype phrases for semantic classification (examples per section; expand as needed for better coverage)
        self.resume_section_prototypes = {
            'experience': ['work experience', 'professional experience', 'employment history', 'career history', 'job experience'],
            'education': ['education', 'academic background', 'qualifications', 'degrees', 'schooling'],
            'skills': ['skills', 'technical skills', 'competencies', 'core skills', 'abilities'],
            'summary': ['summary', 'professional profile', 'objective', 'about me', 'overview'],
            'projects': ['projects', 'portfolio', 'work samples', 'notable projects', 'personal projects'],
            'certifications': ['certifications', 'certificates', 'licenses', 'professional certifications', 'credentials'],
            'achievements': ['achievements', 'accomplishments', 'awards', 'honors', 'recognitions'],
            'contact': ['contact information', 'personal details', 'contact', 'info', 'reach me']
        }
        
        self.job_section_prototypes = {
            'responsibilities': ['responsibilities', 'duties', 'role', 'key responsibilities', 'what you will do', 'job duties', 'tasks'],
            'requirements': ['requirements', 'qualifications', 'skills required', 'must have', 'essential skills', 'job requirements'],
            'preferred': ['preferred skills', 'nice to have', 'desired qualifications', 'additional skills', 'bonus'],
            'company': ['about us', 'company overview', 'our team', 'about the company', 'organization info'],
            'benefits': ['benefits', 'perks', 'what we offer', 'compensation', 'employee benefits'],
            'application': ['how to apply', 'application process', 'apply now', 'submission instructions']
        }
        
        # Load semantic model if available
        self.section_model = SentenceTransformer('all-MiniLM-L6-v2') if SentenceTransformer else None
        
        # Precompute prototype embeddings if model available
        if self.section_model:
            self.resume_prototype_embs = {
                k: np.mean(self.section_model.encode(v), axis=0)
                for k, v in self.resume_section_prototypes.items()
            }
            self.job_prototype_embs = {
                k: np.mean(self.section_model.encode(v), axis=0)
                for k, v in self.job_section_prototypes.items()
            }
        else:
            raise ImportError("SentenceTransformer is required for semantic section extraction. Please install it via 'pip install sentence-transformers'.")
    
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
        Extract different sections from resume text using semantic similarity (or fallback regex).
        
        Args:
            resume_text (str): Resume content.
            
        Returns:
            Dict[str, str]: Dictionary mapping section names to their content.
        """
        return self._extract_sections(resume_text, is_resume=True)
    
    def extract_job_sections(self, job_description: str) -> Dict[str, str]:
        """
        Extract different sections from job description text using semantic similarity (or fallback regex).
        
        Args:
            job_description (str): Job description content.
            
        Returns:
            Dict[str, str]: Dictionary mapping section names to their content.
        """
        return self._extract_sections(job_description, is_resume=False)
    
    def _extract_sections(self, text: str, is_resume: bool) -> Dict[str, str]:
        """
        Shared method for semantic section extraction.
        
        Args:
            text (str): Input text (resume or job description).
            is_resume (bool): True for resumes, False for job descriptions.
            
        Returns:
            Dict[str, str]: Extracted sections.
        """
        sections = {}
        lines = text.split('\n')
        current_section = 'header'  # Default for top content
        current_content = []
        header_positions = {}  # Track start lines of detected sections
        
        # Identify potential headers (short, non-empty lines)
        potential_headers = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and len(stripped) < 60:  # Typical header length
                potential_headers.append((i, stripped.lower()))
        
        detected_sections = {}
        if self.section_model and (is_resume and self.resume_prototype_embs or not is_resume and self.job_prototype_embs):
            # Semantic classification
            header_texts = [h[1] for h in potential_headers]
            if header_texts:
                header_embs = self.section_model.encode(header_texts)
                prototype_embs = self.resume_prototype_embs if is_resume else self.job_prototype_embs
                
                for idx, header_emb in enumerate(header_embs):
                    similarities = {}
                    for sec_name, proto_emb in prototype_embs.items():
                        # Cosine similarity
                        sim = np.dot(header_emb, proto_emb) / (np.linalg.norm(header_emb) * np.linalg.norm(proto_emb))
                        similarities[sec_name] = sim
                    
                    max_sec = max(similarities, key=similarities.get)
                    if similarities[max_sec] > 0.5:  # Threshold for match; tune if needed
                        line_num, header_text = potential_headers[idx]
                        detected_sections[line_num] = max_sec
        else:
            raise ImportError("SentenceTransformer is required for semantic section extraction. Please install it via 'pip install sentence-transformers'.")
        
        # Sort detected sections by line number
        sorted_sections = sorted(detected_sections.items())
        
        # Assign content between headers
        prev_line = 0
        for j, (line_num, sec_name) in enumerate(sorted_sections):
            # Content from previous header to current
            section_content = '\n'.join(lines[prev_line:line_num]).strip()
            if section_content:
                sections[current_section] = section_content
            
            # Start new section (include header if descriptive)
            current_section = sec_name
            header_content = lines[line_num].strip()
            current_content = [header_content] if header_content else []
            prev_line = line_num + 1  # Content starts after header
        
        # Add remaining content
        remaining_content = '\n'.join(lines[prev_line:]).strip()
        if remaining_content:
            sections[current_section] = remaining_content
        
        return sections