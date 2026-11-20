import PyPDF2
from docx import Document
import re
import nltk
import logging
from typing import Dict, List, Tuple
import os

logger = logging.getLogger(__name__)

class CVParser:
    def __init__(self):
        # Download required NLTK data with proper error handling
        self._download_nltk_data()
        
        self.stop_words = set()
        
        # Comprehensive skill database
        self.skill_categories = {
            'programming_languages': [
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust', 
                'swift', 'kotlin', 'ruby', 'php', 'scala', 'r', 'matlab'
            ],
            'web_frameworks': [
                'react', 'angular', 'vue', 'django', 'flask', 'fastapi', 'spring', 
                'express', 'laravel', 'ruby on rails', 'asp.net', 'node.js'
            ],
            'databases': [
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'cassandra',
                'oracle', 'sql server', 'sqlite', 'dynamodb', 'cosmosdb'
            ],
            'cloud_platforms': [
                'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'ansible',
                'jenkins', 'gitlab', 'github actions', 'ci/cd'
            ],
            'data_science': [
                'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn',
                'pandas', 'numpy', 'matplotlib', 'seaborn', 'data analysis', 'data visualization',
                'natural language processing', 'computer vision', 'big data', 'spark', 'hadoop'
            ],
            'soft_skills': [
                'leadership', 'communication', 'teamwork', 'problem solving', 'project management',
                'agile', 'scrum', 'kanban', 'critical thinking', 'time management'
            ]
        }
        
        # Flatten all skills
        self.all_skills = []
        for category_skills in self.skill_categories.values():
            self.all_skills.extend(category_skills)

    def _download_nltk_data(self):
        """Download required NLTK data with fallbacks"""
        required_packages = ['punkt_tab', 'stopwords']
        
        for package in required_packages:
            try:
                nltk.data.find(f'tokenizers/{package}' if package == 'punkt_tab' else f'corpora/{package}')
                logger.info(f"NLTK {package} already installed")
            except LookupError:
                try:
                    logger.info(f"Downloading NLTK {package}...")
                    nltk.download(package, quiet=True)
                    logger.info(f"Successfully downloaded {package}")
                except Exception as e:
                    logger.warning(f"Failed to download {package}: {e}")
                    # Try alternative package for punkt
                    if package == 'punkt_tab':
                        try:
                            nltk.download('punkt', quiet=True)
                            logger.info("Fallback: downloaded punkt instead of punkt_tab")
                        except:
                            logger.error("Failed to download any punkt tokenizer")
        
        # Initialize stopwords after download attempt
        try:
            self.stop_words = set(nltk.corpus.stopwords.words('english'))
        except:
            logger.warning("Using minimal stopwords set")
            self.stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}

    def extract_text(self, file_path: str) -> str:
        """Extract text from various file formats with robust error handling"""
        try:
            if file_path.endswith('.pdf'):
                return self._extract_from_pdf(file_path)
            elif file_path.endswith('.docx'):
                return self._extract_from_docx(file_path)
            elif file_path.endswith('.doc'):
                return self._extract_from_doc(file_path)
            else:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            return ""

    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF with multiple fallback methods"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
        return text.strip()

    def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX files"""
        try:
            doc = Document(file_path)
            full_text = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    full_text.append(paragraph.text)
            
            # Extract from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            full_text.append(cell.text)
            
            return '\n'.join(full_text)
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            return ""

    def _extract_from_doc(self, file_path: str) -> str:
        """Placeholder for DOC file extraction"""
        logger.warning("DOC file parsing not implemented. Please convert to DOCX or PDF.")
        return ""

    def parse_cv(self, cv_text: str) -> Dict:
        """Comprehensive CV parsing with multiple extraction methods"""
        if not cv_text or len(cv_text.strip()) < 50:
            return self._get_empty_profile()
        
        cv_text_lower = cv_text.lower()
        
        # Extract various components
        skills = self._extract_skills_advanced(cv_text_lower)
        experience = self._extract_experience_detailed(cv_text_lower)
        education = self._extract_education_advanced(cv_text)
        personal_info = self._extract_personal_info_advanced(cv_text)
        certifications = self._extract_certifications(cv_text_lower)
        
        # Categorize skills
        categorized_skills = self._categorize_skills(skills)
        
        return {
            'personal_info': personal_info,
            'skills': {
                'all': skills,
                'categorized': categorized_skills,
                'certifications': certifications
            },
            'experience': experience,
            'education': education,
            'summary': self._generate_summary(cv_text, skills, experience),
            'full_text': cv_text
        }

    def _extract_skills_advanced(self, text_lower: str) -> List[str]:
        """Advanced skill extraction using multiple techniques"""
        found_skills = set()
        
        # Direct keyword matching
        for skill in self.all_skills:
            if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
                found_skills.add(skill.title())
        
        # Pattern-based extraction for technologies
        technology_patterns = [
            r'(?:proficient in|experienced with|skills? in|expertise in)[\s\w,]+?([a-z]+(?:\s+[a-z]+)*)',
            r'(?:technologies?|tools):[\s\w,]+?([a-z]+(?:\s+[a-z]+)*)'
        ]
        
        for pattern in technology_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                potential_skills = [s.strip() for s in match.split(',')]
                for skill in potential_skills:
                    if len(skill) > 2 and skill not in self.stop_words:
                        found_skills.add(skill.title())
        
        return sorted(list(found_skills))

    def _extract_experience_detailed(self, text_lower: str) -> Dict:
        """Extract detailed experience information"""
        # Extract years of experience
        years_exp = self._extract_years_experience(text_lower)
        
        # Extract job titles
        job_titles = self._extract_job_titles(text_lower)
        
        # Extract companies (simplified)
        companies = self._extract_companies(text_lower)
        
        return {
            'total_experience': years_exp,
            'job_titles': job_titles[:5],  # Top 5 most recent
            'companies': companies[:3],     # Recent companies
            'level': self._determine_seniority(years_exp, job_titles)
        }

    def _extract_years_experience(self, text_lower: str) -> str:
        """Extract years of experience with multiple patterns"""
        patterns = [
            r'(\d+)\+?\s*years?[\s\w]*experience',
            r'experience.*?(\d+)\+?\s*years?',
            r'(\d+)\s*-\s*(\d+)\s*years?',
            r'(\d+)\s*years?.*?professional'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                if isinstance(matches[0], tuple):  # Range like "3-5 years"
                    return f"{matches[0][0]}-{matches[0][1]} years"
                else:
                    return f"{matches[0]} years"
        
        return "Not specified"

    def _extract_job_titles(self, text_lower: str) -> List[str]:
        """Extract potential job titles"""
        common_titles = [
            'software engineer', 'developer', 'data scientist', 'analyst',
            'manager', 'director', 'architect', 'consultant', 'specialist',
            'lead', 'senior', 'junior', 'full stack', 'frontend', 'backend'
        ]
        
        # Use simple sentence splitting if NLTK fails
        try:
            sentences = nltk.sent_tokenize(text_lower)
        except:
            sentences = re.split(r'[.!?]+', text_lower)
        
        titles = []
        
        for sentence in sentences:
            for title in common_titles:
                if title in sentence:
                    # Extract the full title phrase
                    title_match = re.search(r'([\w\s]*(?:{})[\w\s]*)'.format(title), sentence)
                    if title_match:
                        titles.append(title_match.group(0).strip().title())
        
        return list(set(titles))

    def _extract_companies(self, text_lower: str) -> List[str]:
        """Extract company names (simplified)"""
        # This is a simplified version - in production, use a company database
        company_indicators = ['at ', 'company:', 'firm:', 'corporation:']
        companies = []
        
        for indicator in company_indicators:
            if indicator in text_lower:
                # Extract text after indicator
                pattern = r'{}([\w\s]+)'.format(indicator)
                matches = re.findall(pattern, text_lower)
                companies.extend([match.strip().title() for match in matches])
        
        return companies

    def _extract_education_advanced(self, text: str) -> List[Dict]:
        """Extract structured education information"""
        education_entries = []
        
        # Degree patterns
        degree_patterns = [
            r'(bachelor|bsc|bs|ba)\s*(?:\w+)?\s*(?:in|of)\s*([\w\s]+)',
            r'(master|msc|ms|ma|mba)\s*(?:\w+)?\s*(?:in|of)\s*([\w\s]+)',
            r'(phd|ph\.d|doctorate)\s*(?:in|of)?\s*([\w\s]+)'
        ]
        
        # University patterns
        university_patterns = [
            r'(?:at|from)\s+([\w\s]+university)',
            r'(?:at|from)\s+([\w\s]+college)',
            r'(?:at|from)\s+([\w\s]+institute)'
        ]
        
        # Use simple sentence splitting if NLTK fails
        try:
            sentences = nltk.sent_tokenize(text)
        except:
            sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            education_entry = {}
            
            # Extract degree
            for pattern in degree_patterns:
                match = re.search(pattern, sentence.lower())
                if match:
                    education_entry['degree'] = match.group(1).title()
                    education_entry['field'] = match.group(2).title() if match.group(2) else "Not specified"
                    break
            
            # Extract university
            for pattern in university_patterns:
                match = re.search(pattern, sentence.lower())
                if match:
                    education_entry['institution'] = match.group(1).title()
                    break
            
            if education_entry:
                education_entries.append(education_entry)
        
        return education_entries

    def _extract_personal_info_advanced(self, text: str) -> Dict:
        """Extract comprehensive personal information"""
        # Email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, text)
        email = email_match.group(0) if email_match else None
        
        # Phone (international format)
        phone_patterns = [
            r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}',
            r'\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b'
        ]
        
        phone = None
        for pattern in phone_patterns:
            phone_match = re.search(pattern, text)
            if phone_match:
                phone = phone_match.group(0)
                break
        
        # Location (simplified)
        location_pattern = r'(\w+[\s\w]*,\s*\w+[\s\w]*)'
        location_match = re.search(location_pattern, text)
        location = location_match.group(0) if location_match else None
        
        return {
            'email': email,
            'phone': phone,
            'location': location
        }

    def _extract_certifications(self, text_lower: str) -> List[str]:
        """Extract professional certifications"""
        common_certifications = [
            'aws certified', 'azure certified', 'gcp certified', 'pmp',
            'scrum master', 'six sigma', 'cisp', 'ceh', 'comptia'
        ]
        
        certifications = []
        for cert in common_certifications:
            if cert in text_lower:
                certifications.append(cert.title())
        
        return certifications

    def _categorize_skills(self, skills: List[str]) -> Dict[str, List[str]]:
        """Categorize skills into predefined categories"""
        categorized = {category: [] for category in self.skill_categories.keys()}
        
        for skill in skills:
            skill_lower = skill.lower()
            for category, category_skills in self.skill_categories.items():
                if any(cat_skill in skill_lower for cat_skill in category_skills):
                    categorized[category].append(skill)
        
        return categorized

    def _determine_seniority(self, years_exp: str, job_titles: List[str]) -> str:
        """Determine seniority level based on experience and titles"""
        # Extract numeric years
        years_match = re.search(r'(\d+)', years_exp)
        if years_match:
            years = int(years_match.group(1))
            if years >= 8:
                return "Senior/Lead"
            elif years >= 3:
                return "Mid-level"
            else:
                return "Junior/Entry"
        
        # Fallback to title analysis
        senior_keywords = ['senior', 'lead', 'principal', 'manager', 'director', 'head']
        if any(keyword in ' '.join(job_titles).lower() for keyword in senior_keywords):
            return "Senior/Lead"
        
        return "Mid-level"

    def _generate_summary(self, cv_text: str, skills: List[str], experience: Dict) -> str:
        """Generate a professional summary"""
        experience_level = experience.get('level', 'Professional')
        top_skills = skills[:5] if skills else []
        
        summary_parts = []
        
        if experience_level:
            summary_parts.append(f"{experience_level} professional")
        
        if top_skills:
            summary_parts.append(f"skilled in {', '.join(top_skills)}")
        
        if experience.get('total_experience') != "Not specified":
            summary_parts.append(f"with {experience['total_experience']} of experience")
        
        return ". ".join(summary_parts) + "."

    def _get_empty_profile(self) -> Dict:
        """Return empty profile structure"""
        return {
            'personal_info': {},
            'skills': {
                'all': [],
                'categorized': {category: [] for category in self.skill_categories.keys()},
                'certifications': []
            },
            'experience': {
                'total_experience': "Not specified",
                'job_titles': [],
                'companies': [],
                'level': "Not specified"
            },
            'education': [],
            'summary': "No sufficient information extracted",
            'full_text': ''
        }