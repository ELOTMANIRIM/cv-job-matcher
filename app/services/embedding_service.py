from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict

class EmbeddingService:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text"""
        return self.model.encode(text)
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        embedding1 = self.get_embedding(text1)
        embedding2 = self.get_embedding(text2)
        similarity = cosine_similarity([embedding1], [embedding2])[0][0]
        return float(similarity)
    
    def match_jobs(self, cv_embedding: np.ndarray, job_descriptions: List[Dict]) -> List[Dict]:
        """Match CV with job descriptions"""
        matched_jobs = []
        
        for job in job_descriptions:
            job_embedding = self.get_embedding(job['description'])
            similarity = cosine_similarity([cv_embedding], [job_embedding])[0][0]
            
            if similarity > 0.7:  # threshold
                job['similarity_score'] = round(similarity, 3)
                matched_jobs.append(job)
        
        # Sort by similarity score
        matched_jobs.sort(key=lambda x: x['similarity_score'], reverse=True)
        return matched_jobs