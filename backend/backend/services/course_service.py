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
    
    def _get_course_dir(self, user_id: str, course_id: str) -> Path:
        """Get course directory for deletion purposes"""
        safe_user_id = user_id.replace('|', '_').replace('/', '_')
        return self.root_data_dir / safe_user_id / course_id
    
    def create_course(self, user_id: str, course_data: CourseCreate) -> CourseInDB:
        """Create a new course"""
        try:
            course_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            # Save to SQLite database
            db = get_db_session()
            try:
                db_course = DBCourse(
                    course_id=course_id,
                    user_id=user_id,
                    title=course_data.title,
                    description=course_data.description,
                    status=CourseStatus.DRAFT.value,
                    repo_url=None,  # Will be set when generation starts
                    repo_name=None,
                    created_at=now,
                    updated_at=now
                )
                db.add(db_course)
                db.commit()
                
                # Create CourseInDB response
                course_in_db = CourseInDB(
                    course_id=course_id,
                    title=course_data.title,
                    description=course_data.description,
                    status=CourseStatus.DRAFT,
                    user_id=user_id,
                    repo_url=None,
                    repo_name=None,
                    created_at=now,
                    updated_at=now
                )
                
                logger.info(f"Created course {course_id} for user {user_id}")
                return course_in_db
                
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error creating course: {e}")
            raise
    
    def get_course_by_id(self, course_id: str) -> Optional[CourseInDB]:
        """Get course by ID"""
        try:
            db = get_db_session()
            try:
                db_course = db.query(DBCourse).filter(DBCourse.course_id == course_id).first()
                
                if not db_course:
                    return None
                
                return CourseInDB(
                    course_id=db_course.course_id,
                    title=db_course.title,
                    description=db_course.description,
                    status=CourseStatus(db_course.status),
                    user_id=db_course.user_id,
                    repo_url=db_course.repo_url,
                    repo_name=db_course.repo_name,
                    created_at=db_course.created_at,
                    updated_at=db_course.updated_at
                )
                
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error getting course {course_id}: {e}")
            return None
    
    def get_user_courses(self, user_id: str) -> List[CourseInDB]:
        """Get all courses for a user"""
        try:
            db = get_db_session()
            try:
                db_courses = db.query(DBCourse).filter(
                    DBCourse.user_id == user_id
                ).order_by(DBCourse.created_at.desc()).all()
                
                courses = []
                for db_course in db_courses:
                    course_in_db = CourseInDB(
                        course_id=db_course.course_id,
                        title=db_course.title,
                        description=db_course.description,
                        status=CourseStatus(db_course.status),
                        user_id=db_course.user_id,
                        repo_url=db_course.repo_url,
                        repo_name=db_course.repo_name,
                        created_at=db_course.created_at,
                        updated_at=db_course.updated_at
                    )
                    courses.append(course_in_db)
                
                return courses
                
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error getting courses for user {user_id}: {e}")
            return []
    
    def update_course(self, course_id: str, course_data: CourseUpdate) -> Optional[CourseInDB]:
        """Update an existing course"""
        try:
            db = get_db_session()
            try:
                db_course = db.query(DBCourse).filter(DBCourse.course_id == course_id).first()
                if not db_course:
                    return None
                
                # Update fields
                now = datetime.now(timezone.utc)
                if course_data.title:
                    db_course.title = course_data.title
                if course_data.description is not None:
                    db_course.description = course_data.description
                if course_data.status:
                    db_course.status = course_data.status.value
                db_course.updated_at = now
                
                db.commit()
                
                return CourseInDB(
                    course_id=db_course.course_id,
                    title=db_course.title,
                    description=db_course.description,
                    status=CourseStatus(db_course.status),
                    user_id=db_course.user_id,
                    repo_url=db_course.repo_url,
                    repo_name=db_course.repo_name,
                    created_at=db_course.created_at,
                    updated_at=db_course.updated_at
                )
                
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error updating course {course_id}: {e}")
            raise
    
    def delete_course(self, course_id: str, user_id: str) -> bool:
        """Delete a course and its directories"""
        try:
            db = get_db_session()
            try:
                db_course = db.query(DBCourse).filter(
                    DBCourse.course_id == course_id,
                    DBCourse.user_id == user_id
                ).first()
                
                if not db_course:
                    return False
                
                # Delete from database (CASCADE will handle related records)
                db.delete(db_course)
                db.commit()
                
                # Delete course directories
                course_dir = self._get_course_dir(user_id, course_id)
                if course_dir.exists():
                    import shutil
                    shutil.rmtree(course_dir)
                
                logger.info(f"Deleted course {course_id} for user {user_id}")
                return True
                
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error deleting course {course_id}: {e}")
            return False
    
    def verify_course_ownership(self, course_id: str, user_id: str) -> bool:
        """Verify that a course belongs to a user"""
        try:
            db = get_db_session()
            try:
                db_course = db.query(DBCourse).filter(
                    DBCourse.course_id == course_id,
                    DBCourse.user_id == user_id
                ).first()
                return db_course is not None
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error verifying course ownership: {e}")
            return False 