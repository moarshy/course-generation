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
    
    # AI/LLM Configuration (consolidated from worker config)
    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    MODEL_NAME: str = "gemini/gemini-2.5-flash"
    MODEL_MAX_TOKENS: int = 20000
    MODEL_CACHE_ENABLED: bool = False
    MODEL_TEMPERATURE: float = 0.0
    
    # Document Processing Configuration
    MAX_OVERVIEW_WORDS: int = 10000
    MAX_CONTENT_WORDS: int = 20000
    MAX_DEBATES: int = 3
    MIN_MODULES: int = 5
    MAX_MODULES: int = 10
    
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


# =============================================================================
# File Processing Constants
# =============================================================================

INCLUDE_EXTENSIONS = ['*.md', '*.mdx']
EXCLUDE_PATTERNS = {
    'node_modules', '.git', '__pycache__', '.pytest_cache',
    'venv', 'env', '.venv', 'build', 'dist', 'tests'
}
EXCLUDE_FILE_PREFIXES = {
    'license', 'contributing', 'code_of_conduct', 'security', 'patents'
}

# =============================================================================
# Agent Instructions
# =============================================================================

AGENT_INSTRUCTIONS = """
You are an expert educational content developer working as part of a multi-agent system. 
Your role is to create high-quality, engaging educational content that aligns with 
specified learning objectives and complexity levels.

Core principles:
1. Make content clear, concise, and pedagogically sound
2. Include practical examples and use cases
3. Structure content logically with clear sections
4. Ensure assessments test the learning objectives
5. Match the specified complexity level appropriately
6. Use provided source documents as the foundation for content
7. Collaborate effectively with other agents through iterative refinement

For learning path generation, ALWAYS create complete structured data with:
- Each module MUST have: module_id, title, description, documents, learning_objectives
- Use document file paths from the provided documents list
- Generate meaningful module_id values (e.g., "module_01", "module_02")
- Ensure learning_objectives are specific and measurable
- Assign relevant documents to each module based on content relevance

For document analysis: Focus on extracting key concepts, complexity level, and relationships
""" 