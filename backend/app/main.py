import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.core.config import settings
from app.routers import users, health, projects, course_generation

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

# Set specific loggers to INFO level for important operations
logging.getLogger("app.services.user_service").setLevel(logging.INFO)
logging.getLogger("app.services.course_service").setLevel(logging.INFO)
logging.getLogger("app.services.course_generation_service").setLevel(logging.INFO)
logging.getLogger("app.routers.users").setLevel(logging.WARNING)
logging.getLogger("app.routers.projects").setLevel(logging.WARNING)
logging.getLogger("app.routers.course_generation").setLevel(logging.INFO)

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