from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: str
    name: str
    picture: Optional[str] = None
    email_verified: bool = False

class UserCreate(UserBase):
    auth0_id: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: Optional[bool] = None

class UserSync(UserBase):
    auth0_id: str

class User(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    auth0_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class UserInDB(User):
    """User model as stored in database/Redis"""
    pass 