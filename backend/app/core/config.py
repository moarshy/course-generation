import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Project info
    PROJECT_NAME: str = "Naptha Course Creator"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "AI-powered course creation platform"
    
    # Redis configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}"
    
    # Auth0 configuration
    AUTH0_DOMAIN: str = os.getenv("AUTH0_DOMAIN", "")
    AUTH0_CLIENT_ID: str = os.getenv("AUTH0_CLIENT_ID", "")
    AUTH0_API_AUDIENCE: str = os.getenv("AUTH0_API_AUDIENCE", "")
    AUTH0_ALGORITHMS: List[str] = ["RS256"]
    AUTH0_ISSUER: str = f"https://{AUTH0_DOMAIN}/"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ]
    
    # API
    API_V1_STR: str = "/api/v1"
    
    # Course Data Configuration
    ROOT_DATA_DIR: str = os.getenv("ROOT_DATA_DIR", "../data")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Update Redis URL if host/port are set
if settings.REDIS_HOST and settings.REDIS_PORT:
    settings.REDIS_URL = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}" 