from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings"""
    
    # General
    ENVIRONMENT: str = "development"
    
    # Security
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    
    # Service URLs
    LLM_SERVICE_URL: str
    VECTOR_STORE_URL: str
    EMBEDDING_SERVICE_URL: str
    MAPPING_SERVICE_URL: str
    SPEECH_SERVICE_URL: str
    INGESTION_SERVICE_URL: str
    GEOCODING_SERVICE_URL: str
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
