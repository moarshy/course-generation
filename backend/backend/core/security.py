from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.services.auth_service import AuthService
from backend.core.config import settings
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()
auth_service = AuthService()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency to get current user from JWT token
    Returns the JWT payload which contains user info
    """
    token = credentials.credentials
    
    # Development mode bypass
    if settings.DEV_MODE and token == settings.DEV_TOKEN:
        logger.info("🔧 DEV MODE: Using development token bypass")
        return {
            "sub": settings.DEV_USER_ID,
            "email": "dev@example.com",
            "name": "Development User",
            "iat": 1000000000,
            "exp": 2000000000
        }
    
    return auth_service.verify_token(token)

def get_current_user_id(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> str:
    """
    Dependency to get current user's Auth0 ID
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: no user ID found"
        )
    return user_id 