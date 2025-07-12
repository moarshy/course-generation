import uuid
import logging
from datetime import datetime, timezone 
from typing import List, Optional, Dict, Any
from pathlib import Path
from backend.shared.models import Course, CourseCreate, CourseUpdate, CourseInDB, CourseStatus
from backend.shared.database import get_db_session, Course as DBCourse
from backend.core.config import settings

logger = logging.getLogger(__name__)

class CourseService:
    def __init__(self):
        self.root_data_dir = Path(getattr(settings, 'ROOT_DATA_DIR', './data'))
        self.root_data_dir.mkdir(exist_ok=True)
    
    def create_course(self, course_data: CourseCreate, user_id: str) -> Course:
        """Create a new course for the user"""
        course_id = str(uuid.uuid4())
        
        # Create database entry
        db = get_db_session()
        try:
            db_course = DBCourse(
                course_id=course_id,
                user_id=user_id,
                title=course_data.title,
                description=course_data.description,
                status=CourseStatus.DRAFT.value,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(db_course)
            db.commit()
            
            # Return Course model
            return Course(
                course_id=course_id,
                title=course_data.title,
                description=course_data.description,
                repo_url=None,  # Will be set later when generation starts
                status=CourseStatus.DRAFT,
                created_at=db_course.created_at,
                updated_at=db_course.updated_at
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create course: {e}")
            raise
        finally:
            db.close()
    
    def get_course_by_id(self, course_id: str, user_id: str) -> Optional[Course]:
        """Get course by ID for the user"""
        db = get_db_session()
        try:
            db_course = db.query(DBCourse).filter(
                DBCourse.course_id == course_id,
                DBCourse.user_id == user_id
            ).first()
            
            if not db_course:
                return None
            
            return Course(
                course_id=db_course.course_id,
                title=db_course.title,
                description=db_course.description,
                repo_url=db_course.repo_url,
                status=CourseStatus(db_course.status),
                created_at=db_course.created_at,
                updated_at=db_course.updated_at
            )
            
        except Exception as e:
            logger.error(f"Failed to get course {course_id}: {e}")
            return None
        finally:
            db.close()
    
    def get_user_courses(self, user_id: str) -> List[Course]:
        """Get all courses for the user"""
        db = get_db_session()
        try:
            db_courses = db.query(DBCourse).filter(
                DBCourse.user_id == user_id
            ).order_by(DBCourse.updated_at.desc()).all()
            
            return [
                Course(
                    course_id=db_course.course_id,
                    title=db_course.title,
                    description=db_course.description,
                    repo_url=db_course.repo_url,
                    status=CourseStatus(db_course.status),
                    created_at=db_course.created_at,
                    updated_at=db_course.updated_at
                ) for db_course in db_courses
            ]
            
        except Exception as e:
            logger.error(f"Failed to get courses for user {user_id}: {e}")
            return []
        finally:
            db.close()
    
    def update_course(self, course_id: str, user_id: str, updates: CourseUpdate) -> Optional[Course]:
        """Update course information"""
        db = get_db_session()
        try:
            db_course = db.query(DBCourse).filter(
                DBCourse.course_id == course_id,
                DBCourse.user_id == user_id
            ).first()
            
            if not db_course:
                return None
            
            # Update fields
            if updates.title is not None:
                db_course.title = updates.title
            if updates.description is not None:
                db_course.description = updates.description
            if updates.repo_url is not None:
                db_course.repo_url = updates.repo_url
            if updates.status is not None:
                db_course.status = updates.status.value
            
            db_course.updated_at = datetime.now(timezone.utc)
            db.commit()
            
            return Course(
                course_id=db_course.course_id,
                title=db_course.title,
                description=db_course.description,
                repo_url=db_course.repo_url,
                status=CourseStatus(db_course.status),
                created_at=db_course.created_at,
                updated_at=db_course.updated_at
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update course {course_id}: {e}")
            return None
        finally:
            db.close()
    
    def delete_course(self, course_id: str, user_id: str) -> bool:
        """Delete a course and all its data"""
        db = get_db_session()
        try:
            db_course = db.query(DBCourse).filter(
                DBCourse.course_id == course_id,
                DBCourse.user_id == user_id
            ).first()
            
            if not db_course:
                return False
            
            # Delete database record (cascades to related tables)
            db.delete(db_course)
            db.commit()
            
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete course {course_id}: {e}")
            return False
        finally:
            db.close()
    
    def verify_course_ownership(self, course_id: str, user_id: str) -> bool:
        """Verify that the user owns the course"""
        db = get_db_session()
        try:
            course = db.query(DBCourse).filter(
                DBCourse.course_id == course_id,
                DBCourse.user_id == user_id
            ).first()
            return course is not None
        finally:
            db.close() 