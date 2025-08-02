import re
import logging
from typing import List, Dict
import numpy as np
import os 

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

class TextProcessor:
    """Utility class for text processing and analysis"""
    
    def __init__(self):
        """Initializes the text processor with common patterns and keywords."""
        self.logger = logging.getLogger(__name__)
        
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
        
        model_path = '/app/models/all-MiniLM-L6-v2'
        
        if SentenceTransformer:
            try:
                if os.path.exists(model_path):
                    self.section_model = SentenceTransformer(model_path)
                else:
                    self.section_model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                self.section_model = None
                self.logger.error(f"Could not load SentenceTransformer model: {e}")
                raise ImportError(f"SentenceTransformer is required but failed to load: {e}")
        else:
            self.section_model = None
            raise ImportError("SentenceTransformer is not installed. Please install it via 'pip install sentence-transformers'.")
        
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
            raise ImportError("SentenceTransformer is required for semantic section extraction.")
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        if not text or len(text) <= chunk_size:
            return [text] if text else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            if end < len(text):
                sentence_end = text.rfind('.', start + chunk_size - 100, end)
                if sentence_end > start:
                    end = sentence_end + 1
                else:
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
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        words = text.split()
        keywords = set()
        
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'under', 'between', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
            'could', 'can', 'may', 'might', 'must', 'shall', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }
        
        for word in words:
            if len(word) > 2 and word not in stop_words:
                keywords.add(word)
        
        for i in range(len(words) - 1):
            phrase_2 = ' '.join(words[i:i+2])
            if len(phrase_2) > 5:
                keywords.add(phrase_2)
            
            if i < len(words) - 2:
                phrase_3 = ' '.join(words[i:i+3])
                if len(phrase_3) > 8:
                    keywords.add(phrase_3)
        
        filtered_keywords = [kw for kw in keywords if not kw.isdigit()]
        
        return filtered_keywords[:50]

    def extract_skills(self, text: str) -> List[str]:
        text_lower = text.lower()
        found_skills = set()
        
        all_predefined_skills = self.common_skills['technical'] + self.common_skills['soft_skills']
        for skill in all_predefined_skills:
            if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
                found_skills.add(skill)
        
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
        return self._extract_sections(resume_text, is_resume=True)
    
    def extract_job_sections(self, job_description: str) -> Dict[str, str]:
        return self._extract_sections(job_description, is_resume=False)
    
    def _extract_sections(self, text: str, is_resume: bool) -> Dict[str, str]:
        sections = {}
        lines = text.split('\n')
        current_section = 'header'
        current_content = []
        header_positions = {}
        
        potential_headers = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and len(stripped) < 60:
                potential_headers.append((i, stripped.lower()))
        
        detected_sections = {}
        if self.section_model and (is_resume and self.resume_prototype_embs or not is_resume and self.job_prototype_embs):
            header_texts = [h[1] for h in potential_headers]
            if header_texts:
                header_embs = self.section_model.encode(header_texts)
                prototype_embs = self.resume_prototype_embs if is_resume else self.job_prototype_embs
                
                for idx, header_emb in enumerate(header_embs):
                    similarities = {}
                    for sec_name, proto_emb in prototype_embs.items():
                        sim = np.dot(header_emb, proto_emb) / (np.linalg.norm(header_emb) * np.linalg.norm(proto_emb))
                        similarities[sec_name] = sim
                    
                    max_sec = max(similarities, key=similarities.get)
                    if similarities[max_sec] > 0.5:
                        line_num, header_text = potential_headers[idx]
                        detected_sections[line_num] = max_sec
        else:
            raise ImportError("SentenceTransformer is required for semantic section extraction.")
        
        sorted_sections = sorted(detected_sections.items())
        
        prev_line = 0
        for j, (line_num, sec_name) in enumerate(sorted_sections):
            section_content = '\n'.join(lines[prev_line:line_num]).strip()
            if section_content:
                sections[current_section] = section_content
            
            current_section = sec_name
            header_content = lines[line_num].strip()
            current_content = [header_content] if header_content else []
            prev_line = line_num + 1
        
        remaining_content = '\n'.join(lines[prev_line:]).strip()
        if remaining_content:
            sections[current_section] = remaining_content
        
        return sections