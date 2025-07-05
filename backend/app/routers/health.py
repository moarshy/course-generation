from fastapi import APIRouter
from app.services.user_service import UserService
from app.core.config import settings

router = APIRouter(tags=["health"])
user_service = UserService()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    # Check Redis connection
    redis_healthy = user_service.ping_redis()
    
    return {
        "status": "healthy",
        "redis": "healthy" if redis_healthy else "unhealthy",
        "auth0_domain": settings.AUTH0_DOMAIN,
        "version": settings.VERSION
    } 