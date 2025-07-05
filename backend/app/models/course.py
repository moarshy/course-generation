from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class CourseStatus(str, Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

class CourseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Course title")
    description: Optional[str] = Field(None, max_length=1000, description="Course description")

class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Course title")
    description: Optional[str] = Field(None, max_length=1000, description="Course description")
    status: Optional[CourseStatus] = Field(None, description="Course status")

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