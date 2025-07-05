from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class CourseStatus(str, Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    FAILED = "failed"

class CourseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[CourseStatus] = None

class CourseInDB(BaseModel):
    course_id: str
    title: str
    description: Optional[str] = None
    status: CourseStatus = CourseStatus.DRAFT
    user_id: str  # Auth0 user ID
    cache_dir: str  # Path to cache directory
    generated_course_dir: str  # Path to generated course directory
    created_at: datetime
    updated_at: datetime

class Course(BaseModel):
    course_id: str
    title: str
    description: Optional[str] = None
    status: CourseStatus = CourseStatus.DRAFT
    created_at: datetime
    updated_at: datetime 