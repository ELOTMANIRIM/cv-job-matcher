import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    LINKEDIN_EMAIL = os.getenv('LINKEDIN_EMAIL')
    LINKEDIN_PASSWORD = os.getenv('LINKEDIN_PASSWORD')
    
    # Model Settings
    EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
    SIMILARITY_THRESHOLD = 0.7
    
    # Job Platforms
    JOB_PLATFORMS = {
        'linkedin': 'https://www.linkedin.com/jobs/search/',
        'indeed': 'https://www.indeed.com/jobs',
        'glassdoor': 'https://www.glassdoor.com/Job/jobs.htm'
    }
    
    # File Upload
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'txt'}
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB