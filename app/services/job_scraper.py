import requests
from bs4 import BeautifulSoup
import json
import time
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlencode
import re

logger = logging.getLogger(__name__)

class JobScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def scrape_jobs_from_web(self, skills: List[str], location: str = "") -> List[Dict]:
        """
        Scrape real jobs from multiple job boards based on skills
        """
        all_jobs = []
        
        # Scrape from multiple sources
        try:
            logger.info(f"Scraping jobs for skills: {skills}")
            
            # Indeed
            indeed_jobs = self._scrape_indeed(skills, location)
            all_jobs.extend(indeed_jobs)
            
            # LinkedIn (simplified - requires proper API for full access)
            linkedin_jobs = self._scrape_linkedin_simple(skills, location)
            all_jobs.extend(linkedin_jobs)
            
            # RemoteOK (remote jobs)
            remoteok_jobs = self._scrape_remoteok(skills)
            all_jobs.extend(remoteok_jobs)
            
            # Stack Overflow Jobs
            stackoverflow_jobs = self._scrape_stack_overflow(skills)
            all_jobs.extend(stackoverflow_jobs)
            
            # Remove duplicates based on title and company
            unique_jobs = self._remove_duplicates(all_jobs)
            
            logger.info(f"Found {len(unique_jobs)} unique jobs")
            return unique_jobs[:20]  # Limit to 20 jobs
            
        except Exception as e:
            logger.error(f"Error scraping jobs: {e}")
            return self._get_fallback_jobs(skills)

    def _scrape_indeed(self, skills: List[str], location: str = "") -> List[Dict]:
        """Scrape jobs from Indeed"""
        jobs = []
        try:
            search_term = "+".join(skills[:3])  # Use top 3 skills
            base_url = "https://www.indeed.com/jobs"
            params = {
                'q': search_term,
                'l': location,
                'sort': 'date'
            }
            
            url = f"{base_url}?{urlencode(params)}"
            logger.info(f"Scraping Indeed: {url}")
            
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                job_cards = soup.find_all('div', class_='job_seen_beacon')
                
                for card in job_cards[:10]:  # Limit to 10 jobs from Indeed
                    try:
                        title_elem = card.find('h2', class_='jobTitle')
                        company_elem = card.find('span', class_='companyName')
                        location_elem = card.find('div', class_='companyLocation')
                        
                        if title_elem and company_elem:
                            # Extract job URL
                            link_elem = title_elem.find('a')
                            if link_elem and link_elem.get('href'):
                                job_url = urljoin('https://www.indeed.com', link_elem['href'])
                            else:
                                job_url = "#"
                            
                            job = {
                                'id': f"indeed_{len(jobs)}",
                                'title': title_elem.text.strip(),
                                'company': company_elem.text.strip(),
                                'location': location_elem.text.strip() if location_elem else 'Remote',
                                'description': self._extract_indeed_description(card),
                                'required_skills': skills,
                                'experience_level': 'Not specified',
                                'salary_range': {},
                                'job_type': 'Full-time',
                                'posted_date': 'Recent',
                                'url': job_url,
                                'source': 'Indeed'
                            }
                            jobs.append(job)
                    except Exception as e:
                        logger.debug(f"Error parsing Indeed job card: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error scraping Indeed: {e}")
            
        return jobs

    def _extract_indeed_description(self, card) -> str:
        """Extract job description from Indeed card"""
        try:
            # Try multiple description selectors
            desc_selectors = [
                'div[class*="job-snippet"]',
                'div[class*="description"]',
                'span[class*="summary"]'
            ]
            
            for selector in desc_selectors:
                desc_elem = card.select_one(selector)
                if desc_elem:
                    return desc_elem.text.strip()[:200] + "..."
                    
        except:
            pass
        
        return "Job description not available"

    def _scrape_linkedin_simple(self, skills: List[str], location: str = "") -> List[Dict]:
        """Simple LinkedIn job scraping (limited without API)"""
        jobs = []
        try:
            # This is a simplified version - LinkedIn requires proper API for full access
            search_term = "%20".join(skills[:2])
            url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={search_term}&location={location}"
            
            logger.info(f"Scraping LinkedIn: {url}")
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                job_cards = soup.find_all('div', class_='base-card')
                
                for card in job_cards[:8]:  # Limit to 8 jobs from LinkedIn
                    try:
                        title_elem = card.find('h3', class_='base-search-card__title')
                        company_elem = card.find('h4', class_='base-search-card__subtitle')
                        location_elem = card.find('span', class_='job-search-card__location')
                        
                        if title_elem and company_elem:
                            # Extract job URL
                            link_elem = card.find('a', class_='base-card__full-link')
                            job_url = link_elem['href'] if link_elem and link_elem.get('href') else "#"
                            
                            job = {
                                'id': f"linkedin_{len(jobs)}",
                                'title': title_elem.text.strip(),
                                'company': company_elem.text.strip(),
                                'location': location_elem.text.strip() if location_elem else 'Remote',
                                'description': 'View on LinkedIn for full details',
                                'required_skills': skills,
                                'experience_level': 'Not specified',
                                'salary_range': {},
                                'job_type': 'Full-time',
                                'posted_date': 'Recent',
                                'url': job_url,
                                'source': 'LinkedIn'
                            }
                            jobs.append(job)
                    except Exception as e:
                        logger.debug(f"Error parsing LinkedIn job card: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error scraping LinkedIn: {e}")
            
        return jobs

    def _scrape_remoteok(self, skills: List[str]) -> List[Dict]:
        """Scrape remote jobs from RemoteOK"""
        jobs = []
        try:
            search_term = "-".join(skills[:2])
            url = f"https://remoteok.com/remote-{search_term}-jobs"
            
            logger.info(f"Scraping RemoteOK: {url}")
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                job_cards = soup.find_all('tr', class_='job')
                
                for card in job_cards[:6]:  # Limit to 6 jobs from RemoteOK
                    try:
                        title_elem = card.find('h2', itemprop='title')
                        company_elem = card.find('h3', itemprop='name')
                        
                        if title_elem and company_elem:
                            # Extract job URL
                            link_elem = card.find('a', class_='preventLink')
                            if link_elem and link_elem.get('href'):
                                job_url = urljoin('https://remoteok.com', link_elem['href'])
                            else:
                                job_url = "#"
                            
                            # Extract tags (skills)
                            tag_elems = card.find_all('div', class_='tag')
                            job_skills = [tag.text.strip() for tag in tag_elems[:3]]
                            
                            job = {
                                'id': f"remoteok_{len(jobs)}",
                                'title': title_elem.text.strip(),
                                'company': company_elem.text.strip(),
                                'location': 'Remote',
                                'description': f"Remote position requiring {', '.join(job_skills) if job_skills else 'various skills'}",
                                'required_skills': job_skills + skills[:2],
                                'experience_level': 'Not specified',
                                'salary_range': {},
                                'job_type': 'Full-time',
                                'posted_date': 'Recent',
                                'url': job_url,
                                'source': 'RemoteOK'
                            }
                            jobs.append(job)
                    except Exception as e:
                        logger.debug(f"Error parsing RemoteOK job card: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error scraping RemoteOK: {e}")
            
        return jobs

    def _scrape_stack_overflow(self, skills: List[str]) -> List[Dict]:
        """Scrape jobs from Stack Overflow"""
        jobs = []
        try:
            search_term = "+".join(skills[:2])
            url = f"https://stackoverflow.com/jobs?q={search_term}"
            
            logger.info(f"Scraping Stack Overflow: {url}")
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                job_cards = soup.find_all('div', class_='-job')
                
                for card in job_cards[:6]:  # Limit to 6 jobs from Stack Overflow
                    try:
                        title_elem = card.find('h2', class_='mb4')
                        company_elem = card.find('h3', class_='mb4')
                        location_elem = card.find('span', class_='fc-black-500')
                        
                        if title_elem:
                            # Extract job URL
                            link_elem = title_elem.find('a')
                            if link_elem and link_elem.get('href'):
                                job_url = urljoin('https://stackoverflow.com', link_elem['href'])
                            else:
                                job_url = "#"
                            
                            # Extract tags
                            tag_elems = card.find_all('a', class_='s-tag')
                            job_skills = [tag.text.strip() for tag in tag_elems[:4]]
                            
                            job = {
                                'id': f"stackoverflow_{len(jobs)}",
                                'title': title_elem.text.strip(),
                                'company': company_elem.text.strip() if company_elem else 'Not specified',
                                'location': location_elem.text.strip() if location_elem else 'Remote',
                                'description': f"Developer position requiring {', '.join(job_skills) if job_skills else 'programming skills'}",
                                'required_skills': job_skills + skills[:2],
                                'experience_level': 'Not specified',
                                'salary_range': {},
                                'job_type': 'Full-time',
                                'posted_date': 'Recent',
                                'url': job_url,
                                'source': 'Stack Overflow'
                            }
                            jobs.append(job)
                    except Exception as e:
                        logger.debug(f"Error parsing Stack Overflow job card: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error scraping Stack Overflow: {e}")
            
        return jobs

    def _remove_duplicates(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicate jobs based on title and company"""
        seen = set()
        unique_jobs = []
        
        for job in jobs:
            # Create a unique identifier
            identifier = f"{job['title'].lower()}_{job['company'].lower()}"
            
            if identifier not in seen:
                seen.add(identifier)
                unique_jobs.append(job)
        
        return unique_jobs

    def _get_fallback_jobs(self, skills: List[str]) -> List[Dict]:
        """Provide fallback jobs if scraping fails"""
        logger.info("Using fallback job data")
        
        fallback_jobs = [
            {
                'id': 'fallback_1',
                'title': f'Python Developer ({skills[0] if skills else "Tech"})',
                'company': 'Tech Company',
                'location': 'Remote',
                'description': f'Looking for developer with experience in {", ".join(skills[:3]) if skills else "programming"}.',
                'required_skills': skills,
                'experience_level': 'Mid-level',
                'salary_range': {'min': 80000, 'max': 120000},
                'job_type': 'Full-time',
                'posted_date': '2024-01-15',
                'url': 'https://example.com/jobs/fallback1',
                'source': 'System'
            },
            {
                'id': 'fallback_2',
                'title': f'Software Engineer',
                'company': 'Startup Inc.',
                'location': 'Various Locations',
                'description': f'Software engineering position requiring {skills[0] if skills else "programming"} skills.',
                'required_skills': skills[:2],
                'experience_level': 'Mid-level',
                'salary_range': {'min': 70000, 'max': 110000},
                'job_type': 'Full-time',
                'posted_date': '2024-01-10',
                'url': 'https://example.com/jobs/fallback2',
                'source': 'System'
            }
        ]
        
        return fallback_jobs

    def get_jobs_from_apis(self, skills: List[str]) -> List[Dict]:
        """Main method to get jobs - uses web scraping"""
        return self.scrape_jobs_from_web(skills)