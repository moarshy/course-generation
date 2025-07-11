from typing import List
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Project info
    PROJECT_NAME: str = "Naptha Course Creator"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "AI-powered course creation platform"
    
    # Redis configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379"
    
    # Auth0 configuration
    AUTH0_DOMAIN: str = ""
    AUTH0_CLIENT_ID: str = ""
    AUTH0_API_AUDIENCE: str = ""
    AUTH0_ALGORITHMS: List[str] = ["RS256"]
    AUTH0_ISSUER: str = ""
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ]
    
    # API
    API_V1_STR: str = "/api/v1"
    
    # Course Data Configuration
    ROOT_DATA_DIR: str = "/Users/arshath/play/naptha/course-generation/data"
    logger.info(f"ROOT_DATA_DIR: {ROOT_DATA_DIR}")
    
    # AI/LLM Configuration
    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    
    # Celery Configuration
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )

# Create settings instance
settings = Settings()

# Update derived fields
if settings.AUTH0_DOMAIN:
    settings.AUTH0_ISSUER = f"https://{settings.AUTH0_DOMAIN}/"

if settings.REDIS_HOST and settings.REDIS_PORT:
    settings.REDIS_URL = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}" 