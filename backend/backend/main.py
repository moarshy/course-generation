import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.core.config import settings
from backend.shared.database import init_database
from backend.routers import users, health, projects, course_generation

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

# Set specific loggers to INFO level for important operations
logging.getLogger("backend.services.user_service").setLevel(logging.INFO)
logging.getLogger("backend.services.course_service").setLevel(logging.INFO)
logging.getLogger("backend.services.repository_clone_service").setLevel(logging.INFO)
logging.getLogger("backend.services.document_analyser_service").setLevel(logging.INFO)
logging.getLogger("backend.services.learning_pathway_service").setLevel(logging.INFO)
logging.getLogger("backend.services.modules_generation_service").setLevel(logging.INFO)
logging.getLogger("backend.routers.course_generation").setLevel(logging.INFO)
logging.getLogger("backend.worker.tasks").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and other startup tasks"""
    logger.info("Initializing database...")
    init_database()
    logger.info("Database initialized successfully")

# Include routers
app.include_router(health.router)
app.include_router(users.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(course_generation.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to Naptha Course Creator Backend"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 