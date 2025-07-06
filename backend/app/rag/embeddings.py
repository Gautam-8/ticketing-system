from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for generating and managing text embeddings"""
    
    def __init__(self):
        self.model = None
        self.model_name = settings.EMBEDDING_MODEL
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model"""
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded embedding model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        if not self.model:
            raise ValueError("Embedding model not loaded")
        
        try:
            embedding = self.model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if not self.model:
            raise ValueError("Embedding model not loaded")
        
        try:
            embeddings = self.model.encode(texts, convert_to_tensor=False)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
            
            if norm_product == 0:
                return 0.0
            
            similarity = dot_product / norm_product
            return float(similarity)
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0
    
    def find_most_similar(self, query_embedding: List[float], 
                         candidate_embeddings: List[List[float]], 
                         threshold: float = None) -> List[Dict[str, Any]]:
        """Find most similar embeddings to query"""
        if threshold is None:
            threshold = settings.SIMILARITY_THRESHOLD
        
        similarities = []
        for i, candidate in enumerate(candidate_embeddings):
            similarity = self.calculate_similarity(query_embedding, candidate)
            if similarity >= threshold:
                similarities.append({
                    'index': i,
                    'similarity': similarity
                })
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Limit results
        return similarities[:settings.MAX_RETRIEVED_DOCS]

# Global embedding service instance
embedding_service = EmbeddingService() 