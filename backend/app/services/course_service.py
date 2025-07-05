import redis
import json
import os
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
from app.models.course import Course, CourseCreate, CourseUpdate, CourseInDB, CourseStatus
from app.core.config import settings

logger = logging.getLogger(__name__)

class CourseService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )
        self.root_data_dir = Path(getattr(settings, 'ROOT_DATA_DIR', './data'))
        self.root_data_dir.mkdir(exist_ok=True)
    
    def _get_user_dir(self, user_id: str) -> Path:
        """Get user's data directory"""
        # Sanitize user_id for filesystem
        safe_user_id = user_id.replace('|', '_').replace('/', '_')
        return self.root_data_dir / safe_user_id
    
    def _get_course_dir(self, user_id: str, course_id: str) -> Path:
        """Get course directory"""
        user_dir = self._get_user_dir(user_id)
        return user_dir / course_id
    
    def _ensure_course_directories(self, user_id: str, course_id: str) -> Dict[str, str]:
        """Create course directories and return paths"""
        course_dir = self._get_course_dir(user_id, course_id)
        cache_dir = course_dir / "cache"
        generated_dir = course_dir / "generated"
        
        # Create directories
        course_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(exist_ok=True)
        generated_dir.mkdir(exist_ok=True)
        
        return {
            "cache_dir": str(cache_dir),
            "generated_course_dir": str(generated_dir)
        }
    
    def create_course(self, user_id: str, course_data: CourseCreate) -> CourseInDB:
        """Create a new course"""
        try:
            course_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            # Create course directories
            dirs = self._ensure_course_directories(user_id, course_id)
            
            # Create course record
            course_dict = {
                "course_id": course_id,
                "title": course_data.title,
                "description": course_data.description,
                "status": CourseStatus.DRAFT.value,
                "user_id": user_id,
                "cache_dir": dirs["cache_dir"],
                "generated_course_dir": dirs["generated_course_dir"],
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            
            # Save to Redis
            course_key = f"course:{course_id}"
            self.redis_client.set(course_key, json.dumps(course_dict))
            
            # Add to user's course list
            user_courses_key = f"user_courses:{user_id}"
            self.redis_client.sadd(user_courses_key, course_id)
            
            logger.info(f"Created course {course_id} for user {user_id}")
            return CourseInDB(**course_dict)
            
        except Exception as e:
            logger.error(f"Error creating course: {e}")
            raise
    
    def get_course_by_id(self, course_id: str) -> Optional[CourseInDB]:
        """Get course by ID"""
        try:
            course_key = f"course:{course_id}"
            course_data = self.redis_client.get(course_key)
            
            if not course_data:
                return None
            
            course_dict = json.loads(course_data)
            return CourseInDB(**course_dict)
            
        except Exception as e:
            logger.error(f"Error getting course {course_id}: {e}")
            return None
    
    def get_user_courses(self, user_id: str) -> List[CourseInDB]:
        """Get all courses for a user"""
        try:
            user_courses_key = f"user_courses:{user_id}"
            course_ids = self.redis_client.smembers(user_courses_key)
            
            courses = []
            for course_id in course_ids:
                course = self.get_course_by_id(course_id)
                if course:
                    courses.append(course)
            
            # Sort by created_at descending
            courses.sort(key=lambda x: x.created_at, reverse=True)
            return courses
            
        except Exception as e:
            logger.error(f"Error getting courses for user {user_id}: {e}")
            return []
    
    def update_course(self, course_id: str, course_data: CourseUpdate) -> Optional[CourseInDB]:
        """Update an existing course"""
        try:
            existing_course = self.get_course_by_id(course_id)
            if not existing_course:
                return None
            
            # Update fields
            now = datetime.utcnow()
            course_dict = {
                "course_id": existing_course.course_id,
                "title": course_data.title if course_data.title else existing_course.title,
                "description": course_data.description if course_data.description is not None else existing_course.description,
                "status": course_data.status.value if course_data.status else existing_course.status.value,
                "user_id": existing_course.user_id,
                "cache_dir": existing_course.cache_dir,
                "generated_course_dir": existing_course.generated_course_dir,
                "created_at": existing_course.created_at.isoformat(),
                "updated_at": now.isoformat()
            }
            
            # Save to Redis
            course_key = f"course:{course_id}"
            self.redis_client.set(course_key, json.dumps(course_dict))
            
            return CourseInDB(**course_dict)
            
        except Exception as e:
            logger.error(f"Error updating course {course_id}: {e}")
            raise
    
    def delete_course(self, course_id: str, user_id: str) -> bool:
        """Delete a course and its directories"""
        try:
            course = self.get_course_by_id(course_id)
            if not course or course.user_id != user_id:
                return False
            
            # Delete from Redis
            course_key = f"course:{course_id}"
            self.redis_client.delete(course_key)
            
            # Remove from user's course list
            user_courses_key = f"user_courses:{user_id}"
            self.redis_client.srem(user_courses_key, course_id)
            
            # Delete course directories
            course_dir = self._get_course_dir(user_id, course_id)
            if course_dir.exists():
                import shutil
                shutil.rmtree(course_dir)
            
            logger.info(f"Deleted course {course_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting course {course_id}: {e}")
            return False
    
    def verify_course_ownership(self, course_id: str, user_id: str) -> bool:
        """Verify that a course belongs to a user"""
        try:
            course = self.get_course_by_id(course_id)
            return course is not None and course.user_id == user_id
        except Exception as e:
            logger.error(f"Error verifying course ownership: {e}")
            return False 