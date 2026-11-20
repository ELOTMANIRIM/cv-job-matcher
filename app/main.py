from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
import logging
from app.models.cv_parser import CVParser
from app.models.linkedin_parser import LinkedInParser
from app.models.matcher import JobMatcher
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

# Initialize components with error handling
try:
    cv_parser = CVParser()
    job_matcher = JobMatcher()
    logger.info("Components initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize components: {e}")
    # Create fallback components
    cv_parser = None
    job_matcher = None

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    status = {
        'cv_parser': cv_parser is not None,
        'job_matcher': job_matcher is not None,
        'status': 'healthy' if cv_parser and job_matcher else 'degraded'
    }
    return jsonify(status)

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        # Check if components are available
        if not cv_parser or not job_matcher:
            return jsonify({'error': 'System components not available. Please check server health.'}), 500
        
        # Get CV file
        cv_file = request.files.get('cv')
        linkedin_url = request.form.get('linkedin_url', '').strip()
        
        if not cv_file:
            return jsonify({'error': 'No CV file provided'}), 400
        
        if cv_file and allowed_file(cv_file.filename):
            # Save CV file
            filename = secure_filename(cv_file.filename)
            os.makedirs('data/raw', exist_ok=True)
            cv_path = os.path.join('data/raw', filename)
            cv_file.save(cv_path)
            
            # Parse CV
            logger.info(f"Processing CV: {filename}")
            cv_text = cv_parser.extract_text(cv_path)
            
            if not cv_text or len(cv_text.strip()) < 50:
                return jsonify({'error': 'Could not extract sufficient text from the CV. Please ensure the file is not empty and in a supported format.'}), 400
            
            cv_data = cv_parser.parse_cv(cv_text)
            
            # Parse LinkedIn (if provided)
            linkedin_skills = []
            linkedin_data = {}
            if linkedin_url:
                logger.info(f"Processing LinkedIn profile: {linkedin_url}")
                try:
                    linkedin_parser = LinkedInParser()
                    linkedin_data = linkedin_parser.get_profile_data(linkedin_url)
                    linkedin_skills = linkedin_parser.extract_skills_from_linkedin(linkedin_data)
                except Exception as e:
                    logger.warning(f"LinkedIn parsing failed: {e}")
                    # Continue without LinkedIn data
            
            # Match jobs
            logger.info("Matching jobs...")
            matching_results = job_matcher.match_cv_to_jobs(cv_data, linkedin_data)
            
            # Clean up uploaded file
            try:
                os.remove(cv_path)
            except:
                pass
            
            return render_template('results.html', 
                                 results=matching_results,
                                 cv_data=cv_data,
                                 linkedin_skills=linkedin_skills)
        
        return jsonify({'error': 'Invalid file type. Please upload PDF, DOCX, or TXT files.'}), 400
        
    except Exception as e:
        logger.error(f"Upload processing failed: {e}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error. Please try again later.'}), 500

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('data/raw', exist_ok=True)
    os.makedirs('data/processed', exist_ok=True)
    
    logger.info("Starting CV Job Matcher...")
    app.run(debug=True, host='0.0.0.0', port=5000)