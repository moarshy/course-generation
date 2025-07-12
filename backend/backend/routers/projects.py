import logging
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from backend.shared.models import Course, CourseCreate, CourseUpdate
from backend.services.course_service import CourseService
from backend.core.security import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])
course_service = CourseService()

@router.post("/", response_model=Course)
async def create_course(
    course_data: CourseCreate,
    current_user_id: str = Depends(get_current_user_id)
):
    """Create a new course"""
    try:
        course = course_service.create_course(course_data, current_user_id)
        return course
        
    except Exception as e:
        logger.error(f"Failed to create course for user {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create course: {str(e)}"
        )

@router.get("/", response_model=List[Course])
async def get_user_courses(
    current_user_id: str = Depends(get_current_user_id)
):
    """Get all courses for the current user"""
    try:
        courses = course_service.get_user_courses(current_user_id)
        # Convert to Course model (without internal fields)
        return [
            Course(
                course_id=course.course_id,
                title=course.title,
                description=course.description,
                repo_url=course.repo_url,
                status=course.status,
                created_at=course.created_at,
                updated_at=course.updated_at
            )
            for course in courses
        ]
        
    except Exception as e:
        logger.error(f"Failed to get courses for user {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get courses: {str(e)}"
        )

@router.get("/{course_id}", response_model=Course)
async def get_course(
    course_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get a specific course"""
    try:
        # Verify ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        course = course_service.get_course_by_id(course_id, current_user_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Convert to Course model
        return Course(
            course_id=course.course_id,
            title=course.title,
            description=course.description,
            repo_url=course.repo_url,
            status=course.status,
            created_at=course.created_at,
            updated_at=course.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get course: {str(e)}"
        )

@router.put("/{course_id}", response_model=Course)
async def update_course(
    course_id: str,
    course_data: CourseUpdate,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update a course"""
    try:
        # Verify ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        course = course_service.update_course(course_id, current_user_id, course_data)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Convert to Course model
        return Course(
            course_id=course.course_id,
            title=course.title,
            description=course.description,
            repo_url=course.repo_url,
            status=course.status,
            created_at=course.created_at,
            updated_at=course.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update course: {str(e)}"
        )

@router.delete("/{course_id}")
async def delete_course(
    course_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Delete a course"""
    try:
        # Verify ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        success = course_service.delete_course(course_id, current_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        return {"message": "Course deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete course: {str(e)}"
        ) 