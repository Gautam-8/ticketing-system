from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./ticketing_system.db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # OpenAI/LLM Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    
    # Vector Database (Chroma/Pinecone)
    VECTOR_DB_PATH: str = "./vector_db"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # RAG Configuration
    MAX_CONTEXT_LENGTH: int = 4000
    SIMILARITY_THRESHOLD: float = 0.7
    MAX_RETRIEVED_DOCS: int = 5
    
    # Ticket Configuration
    AUTO_CATEGORIZATION_ENABLED: bool = True
    CONFIDENCE_THRESHOLD: float = 0.8
    ESCALATION_THRESHOLD: float = 0.5
    
    class Config:
        env_file = ".env"

settings = Settings() 