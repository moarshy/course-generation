import logging
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any
from app.models.user import User, UserSync, UserInDB
from app.services.user_service import UserService
from app.core.security import get_current_user, get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])
user_service = UserService()

@router.post("/sync", response_model=UserInDB)
async def sync_user(
    user_data: UserSync, 
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Sync user data from Auth0 to Redis"""
    try:
        # Verify the user owns this auth0_id
        if current_user.get("sub") != user_data.auth0_id:
            logger.warning(f"Token mismatch: {current_user.get('sub')} != {user_data.auth0_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token doesn't match user ID"
            )
        
        # Sync user data
        user = user_service.sync_user(user_data)
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync user {user_data.auth0_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync user: {str(e)}"
        )

@router.get("/me", response_model=UserInDB)
async def get_current_user_profile(
    current_user_id: str = Depends(get_current_user_id)
):
    """Get current user information"""
    try:
        user = user_service.get_user_by_auth0_id(current_user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user profile {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}"
        )

@router.get("/{auth0_id}", response_model=UserInDB)
async def get_user_by_id(
    auth0_id: str, 
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user by Auth0 ID (admin only or self)"""
    try:
        # For now, only allow users to get their own data
        if current_user_id != auth0_id:
            logger.warning(f"Access denied: {current_user_id} tried to access {auth0_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        user = user_service.get_user_by_auth0_id(auth0_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user {auth0_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}"
        )

@router.delete("/me")
async def delete_current_user(
    current_user_id: str = Depends(get_current_user_id)
):
    """Delete current user account"""
    try:
        success = user_service.delete_user(current_user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {"message": "User account deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        ) 