from typing import List, Dict, Tuple
import logging
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from app.services.job_scraper import JobScraper

logger = logging.getLogger(__name__)

class JobMatcher:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.embedding_model = SentenceTransformer(model_name)
        self.job_scraper = JobScraper()
        self.similarity_threshold = 0.2  # Much lower threshold to show more jobs
        
        # Industry-standard job categories and keywords
        self.job_categories = {
            'software_development': [
                'software engineer', 'developer', 'full stack', 'backend', 'frontend',
                'web developer', 'mobile developer', 'devops engineer'
            ],
            'data_science': [
                'data scientist', 'machine learning engineer', 'data analyst',
                'business intelligence', 'data engineer'
            ],
            'cloud_engineering': [
                'cloud engineer', 'aws engineer', 'azure engineer', 'devops',
                'site reliability engineer'
            ]
        }

    def match_cv_to_jobs(self, cv_data: Dict, linkedin_data: Dict = None) -> Dict:
        """
        Match CV with real jobs from the web - MORE LENIENT MATCHING
        """
        try:
            # Combine CV and LinkedIn data
            combined_profile = self._combine_profile_data(cv_data, linkedin_data)
            
            # Get real jobs from the web
            job_listings = self.job_scraper.get_jobs_from_apis(combined_profile['skills'])
            
            logger.info(f"Found {len(job_listings)} jobs to match against")
            logger.info(f"Profile skills: {combined_profile['skills']}")
            
            if not job_listings:
                return self._get_fallback_with_jobs(combined_profile)
            
            # Use simpler matching that shows more results
            matches = self._simple_skill_matching(combined_profile, job_listings)
            
            # If no matches with simple method, use semantic matching
            if not matches:
                matches = self._lenient_semantic_matching(combined_profile, job_listings)
            
            # If still no matches, show top jobs based on skills
            if not matches:
                matches = self._get_top_jobs_by_skills(combined_profile, job_listings)
            
            # Always return at least some jobs
            if not matches:
                matches = self._get_all_jobs_with_scores(job_listings, combined_profile)
            
            # Rank matches
            ranked_matches = self._rank_matches(matches, combined_profile)
            
            return {
                'profile_summary': self._generate_profile_summary(combined_profile),
                'matches': ranked_matches,
                'match_statistics': self._calculate_match_stats(ranked_matches),
                'recommendations': self._generate_recommendations(combined_profile, ranked_matches)
            }
            
        except Exception as e:
            logger.error(f"Job matching failed: {e}")
            return self._get_empty_results_with_fallback()

    def _simple_skill_matching(self, profile: Dict, job_listings: List[Dict]) -> List[Dict]:
        """Simple skill-based matching that shows more results"""
        matches = []
        profile_skills_lower = [skill.lower() for skill in profile['skills']]
        
        for job in job_listings:
            score = 0
            matched_skills = []
            
            # Check job title against profile skills
            job_title = job.get('title', '').lower()
            for skill in profile_skills_lower:
                if skill in job_title:
                    score += 3  # Higher weight for title matches
                    matched_skills.append(skill.title())
                    break
            
            # Check required skills
            required_skills = job.get('required_skills', [])
            for req_skill in required_skills:
                req_skill_lower = req_skill.lower()
                for profile_skill in profile_skills_lower:
                    if (req_skill_lower in profile_skill or 
                        profile_skill in req_skill_lower or
                        self._are_skills_related(req_skill_lower, profile_skill)):
                        score += 2
                        matched_skills.append(req_skill)
                        break
            
            # Check job description for skills
            job_desc = job.get('description', '').lower()
            for skill in profile_skills_lower:
                if skill in job_desc:
                    score += 1
                    if skill.title() not in matched_skills:
                        matched_skills.append(skill.title())
            
            # Even if score is low, include the job with a basic score
            if score > 0 or len(matches) < 5:  # Always include at least 5 jobs
                final_score = min(score / 10, 1.0)  # Normalize
                if final_score < 0.3:
                    final_score = 0.3  # Minimum score to show job
                
                matches.append({
                    'job': job,
                    'keyword_score': final_score,
                    'semantic_score': 0.3,  # Base semantic score
                    'matched_skills': list(set(matched_skills)),
                    'hybrid_score': final_score,
                    'final_score': final_score
                })
        
        return matches

    def _lenient_semantic_matching(self, profile: Dict, job_listings: List[Dict]) -> List[Dict]:
        """Very lenient semantic matching"""
        matches = []
        
        # Create profile embedding
        profile_text = self._create_profile_text(profile)
        profile_embedding = self.embedding_model.encode(profile_text)
        
        for job in job_listings:
            # Create job embedding
            job_text = self._create_job_text(job)
            job_embedding = self.embedding_model.encode(job_text)
            
            # Calculate similarity with very low threshold
            similarity = cosine_similarity([profile_embedding], [job_embedding])[0][0]
            
            # Include even low similarity matches
            semantic_score = max(similarity, 0.1)  # Minimum score
            
            matches.append({
                'job': job,
                'keyword_score': 0.3,  # Base keyword score
                'semantic_score': semantic_score,
                'matched_skills': [],
                'hybrid_score': semantic_score,
                'final_score': semantic_score
            })
        
        return matches

    def _get_top_jobs_by_skills(self, profile: Dict, job_listings: List[Dict]) -> List[Dict]:
        """Get top jobs based on skill relevance"""
        profile_skills_lower = [skill.lower() for skill in profile['skills']]
        scored_jobs = []
        
        for job in job_listings:
            relevance_score = 0
            
            # Score based on title
            job_title = job.get('title', '').lower()
            for skill in profile_skills_lower:
                if skill in job_title:
                    relevance_score += 2
            
            # Score based on description
            job_desc = job.get('description', '').lower()
            for skill in profile_skills_lower:
                if skill in job_desc:
                    relevance_score += 1
            
            scored_jobs.append((job, relevance_score))
        
        # Sort by relevance and take top ones
        scored_jobs.sort(key=lambda x: x[1], reverse=True)
        
        matches = []
        for job, score in scored_jobs[:10]:  # Top 10 most relevant
            final_score = max(0.3, min(score / 10, 0.8))  # Score between 0.3 and 0.8
            
            matches.append({
                'job': job,
                'keyword_score': final_score,
                'semantic_score': 0.4,
                'matched_skills': [],
                'hybrid_score': final_score,
                'final_score': final_score
            })
        
        return matches

    def _get_all_jobs_with_scores(self, job_listings: List[Dict], profile: Dict) -> List[Dict]:
        """Return all jobs with basic scores"""
        matches = []
        
        for i, job in enumerate(job_listings[:15]):  # Limit to 15 jobs
            # Give slightly different scores to create ranking
            base_score = 0.4 + (i * 0.02)  # Scores from 0.4 to 0.7
            
            matches.append({
                'job': job,
                'keyword_score': base_score,
                'semantic_score': 0.4,
                'matched_skills': [],
                'hybrid_score': base_score,
                'final_score': base_score
            })
        
        return matches

    def _are_skills_related(self, skill1: str, skill2: str) -> bool:
        """Check if skills are related"""
        related_skills = {
            'python': ['django', 'flask', 'pandas', 'numpy', 'machine learning'],
            'javascript': ['react', 'node', 'vue', 'angular', 'typescript'],
            'java': ['spring', 'hibernate', 'android'],
            'aws': ['cloud', 'devops', 'docker', 'kubernetes'],
            'react': ['javascript', 'frontend', 'ui', 'redux'],
            'node': ['javascript', 'backend', 'express'],
            'docker': ['kubernetes', 'devops', 'aws', 'azure'],
            'machine learning': ['python', 'ai', 'data science', 'tensorflow']
        }
        
        for main_skill, related_list in related_skills.items():
            if skill1 == main_skill and skill2 in related_list:
                return True
            if skill2 == main_skill and skill1 in related_list:
                return True
        
        return False

    def _combine_profile_data(self, cv_data: Dict, linkedin_data: Dict = None) -> Dict:
        """Combine CV and LinkedIn data into a unified profile"""
        profile = {
            'skills': set(),
            'experience': cv_data.get('experience', {}),
            'education': cv_data.get('education', []),
            'summary': cv_data.get('summary', ''),
            'personal_info': cv_data.get('personal_info', {})
        }
        
        # Add CV skills
        cv_skills = cv_data.get('skills', {})
        if isinstance(cv_skills, dict) and 'all' in cv_skills:
            profile['skills'].update(cv_skills['all'])
        else:
            profile['skills'].update(cv_skills)
        
        # Add LinkedIn skills if available
        if linkedin_data:
            linkedin_skills = linkedin_data.get('skills', [])
            profile['skills'].update(linkedin_skills)
            
            # Enhance with LinkedIn data
            if not profile['summary'] and linkedin_data.get('headline'):
                profile['summary'] = linkedin_data['headline']
        
        profile['skills'] = list(profile['skills'])
        
        return profile

    def _rank_matches(self, matches: List[Dict], profile: Dict) -> List[Dict]:
        """Rank matches - always return all matches"""
        # Just sort by final score, don't filter
        return sorted(matches, key=lambda x: x['final_score'], reverse=True)

    def _create_profile_text(self, profile: Dict) -> str:
        """Create text for embedding from profile data"""
        parts = []
        
        if profile.get('summary'):
            parts.append(profile['summary'])
        
        parts.append("Skills: " + ", ".join(profile['skills']))
        
        experience = profile.get('experience', {})
        if experience.get('total_experience'):
            parts.append(f"Experience: {experience['total_experience']}")
        
        if experience.get('job_titles'):
            parts.append("Previous roles: " + ", ".join(experience['job_titles']))
        
        return " ".join(parts)

    def _create_job_text(self, job: Dict) -> str:
        """Create text for embedding from job data"""
        parts = [
            job.get('title', ''),
            job.get('description', ''),
            "Company: " + job.get('company', '')
        ]
        
        required_skills = job.get('required_skills', [])
        if required_skills:
            parts.append("Required skills: " + ", ".join(required_skills))
        
        return " ".join(parts)

    def _generate_profile_summary(self, profile: Dict) -> Dict:
        """Generate a comprehensive profile summary"""
        return {
            'skill_count': len(profile['skills']),
            'experience_level': profile.get('experience', {}).get('level', 'Not specified'),
            'total_experience': profile.get('experience', {}).get('total_experience', 'Not specified'),
            'top_skills': profile['skills'][:8]
        }

    def _calculate_match_stats(self, matches: List[Dict]) -> Dict:
        """Calculate matching statistics"""
        if not matches:
            return {'total_matches': 0, 'average_score': 0, 'match_quality': 'Exploring Opportunities'}
        
        scores = [match['final_score'] for match in matches]
        avg_score = sum(scores) / len(scores)
        
        quality = 'Excellent' if avg_score > 0.7 else 'Good' if avg_score > 0.5 else 'Fair' if avg_score > 0.3 else 'Exploring Opportunities'
        
        return {
            'total_matches': len(matches),
            'average_score': round(avg_score, 3),
            'match_quality': quality
        }

    def _generate_recommendations(self, profile: Dict, matches: List[Dict]) -> List[str]:
        """Generate career recommendations"""
        recommendations = []
        
        if matches:
            if len(matches) > 10:
                recommendations.append("Great! You have many matching opportunities")
            else:
                recommendations.append("Consider these roles that align with your skills")
        
        # Skill development recommendations
        profile_skills = [s.lower() for s in profile['skills']]
        high_demand_skills = ['python', 'javascript', 'aws', 'react', 'docker', 'machine learning']
        
        missing_skills = [skill for skill in high_demand_skills if skill not in profile_skills]
        if missing_skills:
            recommendations.append(f"Consider learning: {missing_skills[0]}")
        
        return recommendations[:2]

    def _get_fallback_with_jobs(self, profile: Dict) -> Dict:
        """Return results with fallback jobs"""
        fallback_jobs = self.job_scraper._get_recent_fallback_jobs(profile['skills'])
        
        matches = []
        for i, job in enumerate(fallback_jobs):
            matches.append({
                'job': job,
                'keyword_score': 0.5,
                'semantic_score': 0.5,
                'matched_skills': profile['skills'][:3],
                'hybrid_score': 0.5,
                'final_score': 0.5
            })
        
        return {
            'profile_summary': self._generate_profile_summary(profile),
            'matches': matches,
            'match_statistics': {
                'total_matches': len(matches),
                'average_score': 0.5,
                'match_quality': 'Good Opportunities'
            },
            'recommendations': ['Showing relevant job opportunities based on your profile']
        }

    def _get_empty_results_with_fallback(self) -> Dict:
        """Return empty results with fallback message"""
        return {
            'profile_summary': {},
            'matches': [],
            'match_statistics': {
                'total_matches': 0, 
                'average_score': 0, 
                'match_quality': 'No matches found'
            },
            'recommendations': [
                'Try uploading a more detailed CV',
                'Add your LinkedIn profile for better matching',
                'Check if your skills are clearly listed in the CV'
            ]
        }