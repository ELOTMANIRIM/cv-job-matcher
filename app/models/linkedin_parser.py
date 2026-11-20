import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)

class LinkedInParser:
    def __init__(self, email: str = None, password: str = None):
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_profile_data(self, profile_url: str) -> Dict:
        """
        Extract data from LinkedIn profile
        Note: This uses public profile data. For full access, use LinkedIn API
        """
        try:
            # Clean profile URL
            profile_url = self._clean_linkedin_url(profile_url)
            
            if not profile_url:
                return self._get_mock_profile_data()
            
            # Try to get public profile data
            public_data = self._get_public_profile_data(profile_url)
            
            if public_data:
                return public_data
            else:
                logger.warning("Using mock data - implement proper LinkedIn API integration for production")
                return self._get_mock_profile_data()
                
        except Exception as e:
            logger.error(f"Error parsing LinkedIn profile {profile_url}: {e}")
            return self._get_mock_profile_data()

    def _clean_linkedin_url(self, profile_url: str) -> Optional[str]:
        """Clean and validate LinkedIn URL"""
        if not profile_url or 'linkedin.com' not in profile_url:
            return None
        
        # Ensure proper format
        if '/in/' not in profile_url:
            return None
        
        # Remove tracking parameters
        clean_url = profile_url.split('?')[0]
        return clean_url

    def _get_public_profile_data(self, profile_url: str) -> Optional[Dict]:
        """
        Attempt to get public profile data
        Note: LinkedIn restricts scraping. This is for educational purposes.
        """
        try:
            response = self.session.get(profile_url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract basic info from public profile
                profile_data = {
                    'name': self._extract_name(soup),
                    'headline': self._extract_headline(soup),
                    'location': self._extract_location(soup),
                    'about': self._extract_about(soup),
                    'skills': self._extract_skills_public(soup),
                    'experience': self._extract_experience_public(soup),
                    'education': self._extract_education_public(soup)
                }
                
                # Only return if we got meaningful data
                if any(profile_data.values()):
                    return profile_data
                    
        except Exception as e:
            logger.debug(f"Public profile extraction failed: {e}")
        
        return None

    def _extract_name(self, soup: BeautifulSoup) -> str:
        """Extract name from public profile"""
        try:
            name_element = soup.find('h1', class_='top-card-layout__title')
            if name_element:
                return name_element.get_text().strip()
        except:
            pass
        return ""

    def _extract_headline(self, soup: BeautifulSoup) -> str:
        """Extract headline from public profile"""
        try:
            headline_element = soup.find('h2', class_='top-card-layout__headline')
            if headline_element:
                return headline_element.get_text().strip()
        except:
            pass
        return ""

    def _extract_location(self, soup: BeautifulSoup) -> str:
        """Extract location from public profile"""
        try:
            location_element = soup.find('span', class_='top-card__subline-item')
            if location_element:
                return location_element.get_text().strip()
        except:
            pass
        return ""

    def _extract_about(self, soup: BeautifulSoup) -> str:
        """Extract about section from public profile"""
        try:
            about_element = soup.find('section', class_='summary')
            if about_element:
                return about_element.get_text().strip()
        except:
            pass
        return ""

    def _extract_skills_public(self, soup: BeautifulSoup) -> List[str]:
        """Extract skills from public profile"""
        skills = []
        try:
            skill_elements = soup.find_all('span', class_='skill-pill__label')
            for element in skill_elements:
                skill = element.get_text().strip()
                if skill:
                    skills.append(skill)
        except:
            pass
        return skills[:20]  # Limit to top 20 skills

    def _extract_experience_public(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract experience from public profile"""
        experience = []
        try:
            exp_elements = soup.find_all('li', class_='experience-item')
            for exp in exp_elements[:5]:  # Limit to 5 most recent
                try:
                    title_elem = exp.find('h3', class_='profile-section-card__title')
                    company_elem = exp.find('h4', class_='profile-section-card__subtitle')
                    duration_elem = exp.find('time')
                    
                    if title_elem and company_elem:
                        exp_entry = {
                            'title': title_elem.get_text().strip(),
                            'company': company_elem.get_text().strip(),
                            'duration': duration_elem.get_text().strip() if duration_elem else ""
                        }
                        experience.append(exp_entry)
                except:
                    continue
        except:
            pass
        return experience

    def _extract_education_public(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract education from public profile"""
        education = []
        try:
            edu_elements = soup.find_all('li', class_='education-item')
            for edu in edu_elements[:3]:  # Limit to 3 most recent
                try:
                    school_elem = edu.find('h3', class_='profile-section-card__title')
                    degree_elem = edu.find('h4', class_='profile-section-card__subtitle')
                    
                    if school_elem:
                        edu_entry = {
                            'school': school_elem.get_text().strip(),
                            'degree': degree_elem.get_text().strip() if degree_elem else ""
                        }
                        education.append(edu_entry)
                except:
                    continue
        except:
            pass
        return education

    def _get_mock_profile_data(self) -> Dict:
        """Return realistic mock data for demonstration"""
        return {
            'name': 'John Doe',
            'headline': 'Senior Software Engineer at Tech Company',
            'location': 'San Francisco, California',
            'about': 'Experienced software engineer with 8+ years in full-stack development...',
            'skills': [
                'Python', 'JavaScript', 'React', 'Node.js', 'AWS', 'Docker', 
                'Kubernetes', 'Machine Learning', 'Data Analysis', 'Agile Methodologies'
            ],
            'experience': [
                {
                    'title': 'Senior Software Engineer',
                    'company': 'Tech Innovations Inc.',
                    'duration': '2020 - Present'
                },
                {
                    'title': 'Software Engineer',
                    'company': 'Startup Solutions',
                    'duration': '2018 - 2020'
                }
            ],
            'education': [
                {
                    'school': 'Stanford University',
                    'degree': 'M.S. Computer Science'
                },
                {
                    'school': 'UC Berkeley',
                    'degree': 'B.S. Computer Engineering'
                }
            ]
        }

    def extract_skills_from_linkedin(self, profile_data: Dict) -> List[str]:
        """Extract and normalize skills from LinkedIn profile data"""
        skills = profile_data.get('skills', [])
        
        # Normalize skills (remove duplicates, standardize capitalization)
        normalized_skills = list(set([skill.strip().title() for skill in skills if skill.strip()]))
        
        return sorted(normalized_skills)

    def get_profile_summary(self, profile_data: Dict) -> str:
        """Generate a professional summary from LinkedIn data"""
        name = profile_data.get('name', '')
        headline = profile_data.get('headline', '')
        location = profile_data.get('location', '')
        about = profile_data.get('about', '')
        
        summary_parts = []
        
        if name and headline:
            summary_parts.append(f"{name} - {headline}")
        elif headline:
            summary_parts.append(headline)
        
        if location:
            summary_parts.append(f"Located in {location}")
        
        if about:
            # Truncate about section if too long
            about_summary = about[:200] + "..." if len(about) > 200 else about
            summary_parts.append(about_summary)
        
        return "\n".join(summary_parts)