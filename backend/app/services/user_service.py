import redis
import json
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from app.models.user import User, UserSync, UserInDB
from app.core.config import settings

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )
    
    def get_user_by_auth0_id(self, auth0_id: str) -> Optional[UserInDB]:
        """Get user by Auth0 ID"""
        try:
            user_key = f"user:{auth0_id}"
            user_data = self.redis_client.get(user_key)
            
            if not user_data:
                return None
            
            user_dict = json.loads(user_data)
            return UserInDB(**user_dict)
        except Exception as e:
            logger.error(f"Error getting user by auth0_id {auth0_id}: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email"""
        try:
            # Get auth0_id from email index
            auth0_id = self.redis_client.get(f"user_email:{email}")
            if not auth0_id:
                return None
            
            return self.get_user_by_auth0_id(auth0_id)
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None
    
    def create_user(self, user_data: UserSync) -> UserInDB:
        """Create a new user"""
        try:
            now = datetime.utcnow()
            user_dict = {
                "auth0_id": user_data.auth0_id,
                "email": user_data.email,
                "name": user_data.name,
                "picture": user_data.picture,
                "email_verified": user_data.email_verified,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            
            # Save to Redis
            user_key = f"user:{user_data.auth0_id}"
            self.redis_client.set(user_key, json.dumps(user_dict))
            
            # Maintain email index
            self.redis_client.set(f"user_email:{user_data.email}", user_data.auth0_id)
            
            logger.info(f"Created new user: {user_data.email}")
            return UserInDB(**user_dict)
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise
    
    def update_user(self, auth0_id: str, user_data: UserSync) -> UserInDB:
        """Update existing user"""
        try:
            # Get existing user
            existing_user = self.get_user_by_auth0_id(auth0_id)
            if not existing_user:
                raise ValueError(f"User with auth0_id {auth0_id} not found")
            
            # Update user data
            now = datetime.utcnow()
            user_dict = {
                "auth0_id": auth0_id,
                "email": user_data.email,
                "name": user_data.name,
                "picture": user_data.picture,
                "email_verified": user_data.email_verified,
                "created_at": existing_user.created_at.isoformat() if existing_user.created_at else now.isoformat(),
                "updated_at": now.isoformat()
            }
            
            # Save to Redis
            user_key = f"user:{auth0_id}"
            self.redis_client.set(user_key, json.dumps(user_dict))
            
            # Update email index if email changed
            if existing_user.email != user_data.email:
                # Remove old email index
                self.redis_client.delete(f"user_email:{existing_user.email}")
                # Add new email index
                self.redis_client.set(f"user_email:{user_data.email}", auth0_id)
            
            return UserInDB(**user_dict)
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            raise
    
    def sync_user(self, user_data: UserSync) -> UserInDB:
        """Sync user data from Auth0 - create if doesn't exist, update if exists"""
        try:
            existing_user = self.get_user_by_auth0_id(user_data.auth0_id)
            
            if existing_user:
                return self.update_user(user_data.auth0_id, user_data)
            else:
                return self.create_user(user_data)
        except Exception as e:
            logger.error(f"Error syncing user: {e}")
            raise
    
    def delete_user(self, auth0_id: str) -> bool:
        """Delete user and associated data"""
        try:
            user = self.get_user_by_auth0_id(auth0_id)
            if not user:
                return False
            
            # Delete user data
            user_key = f"user:{auth0_id}"
            self.redis_client.delete(user_key)
            
            # Delete email index
            self.redis_client.delete(f"user_email:{user.email}")
            
            logger.info(f"Deleted user: {user.email}")
            return True
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False
    
    def ping_redis(self) -> bool:
        """Check if Redis is connected"""
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis connection error: {e}")
            return False 