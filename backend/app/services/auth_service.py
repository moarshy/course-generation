import os
import requests
import logging
from fastapi import HTTPException, status
from jose import jwt, JWTError
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.AUTH0_DOMAIN = settings.AUTH0_DOMAIN
        self.AUTH0_API_AUDIENCE = settings.AUTH0_API_AUDIENCE
        self.AUTH0_ALGORITHMS = ["RS256"]
        self.AUTH0_ISSUER = f"https://{self.AUTH0_DOMAIN}/"
        self._jwks_cache = None
    
    def get_auth0_public_key(self) -> Dict[str, Any]:
        """Get Auth0 public key for JWT verification with caching"""
        if self._jwks_cache is None:
            try:
                response = requests.get(f"https://{self.AUTH0_DOMAIN}/.well-known/jwks.json")
                response.raise_for_status()
                self._jwks_cache = response.json()
            except Exception as e:
                logger.error(f"Failed to fetch Auth0 public key: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Unable to fetch Auth0 public key: {str(e)}"
                )
        return self._jwks_cache
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify Auth0 JWT token"""
        try:
            # Debug: Log token format
            token_parts = token.split('.')
            logger.info(f"Token has {len(token_parts)} parts")
            
            # JWT should have exactly 3 parts
            if len(token_parts) != 3:
                logger.error(f"Invalid token format: {len(token_parts)} parts. Expected JWT with 3 parts.")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token format"
                )
            
            # Get the public key
            jwks = self.get_auth0_public_key()
            
            # Decode the token header to get kid
            unverified_header = jwt.get_unverified_header(token)
            
            # Find the key
            key = None
            for jwk in jwks["keys"]:
                if jwk["kid"] == unverified_header["kid"]:
                    key = jwk
                    break
            
            if not key:
                logger.error(f"No matching key found for kid: {unverified_header.get('kid')}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to find appropriate key"
                )
            
            # Verify the token
            payload = jwt.decode(
                token,
                key,
                algorithms=self.AUTH0_ALGORITHMS,
                audience=self.AUTH0_API_AUDIENCE,
                issuer=self.AUTH0_ISSUER
            )
            
            return payload
        
        except JWTError as e:
            logger.error(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Token verification failed: {str(e)}"
            )
    
    def get_user_from_token(self, token: str) -> str:
        """Get user's Auth0 ID from JWT token"""
        payload = self.verify_token(token)
        return payload.get("sub") 