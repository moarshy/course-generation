import logging
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional
from app.models.course_generation import (
    CourseGenerationRequest, GenerationTaskStatus,
    Stage1Response, Stage2Input, Stage3Input, Stage3Response,
    Stage4Input, Stage4Response
)
from app.services.course_generation_service import CourseGenerationService
from app.services.course_service import CourseService
from app.core.security import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/course-generation", tags=["course-generation"])
generation_service = CourseGenerationService()
course_service = CourseService()

@router.post("/{course_id}/start")
async def start_course_generation(
    course_id: str,
    request: CourseGenerationRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """Start the course generation process - Stage 1: Clone Repository"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Start generation
        task_id = generation_service.start_course_generation(
            current_user_id, course_id, request.repo_url
        )
        
        # Update course status
        from app.models.course import CourseUpdate, CourseStatus
        course_service.update_course(course_id, CourseUpdate(status=CourseStatus.GENERATING))
        
        return {
            "message": "Course generation started",
            "task_id": task_id,
            "stage": "clone_repo"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start course generation for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start course generation: {str(e)}"
        )

@router.get("/{course_id}/status", response_model=Optional[GenerationTaskStatus])
async def get_generation_status(
    course_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get the current status of course generation"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        status = generation_service.get_task_status(course_id)
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get generation status for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get generation status: {str(e)}"
        )

@router.get("/{course_id}/stage1", response_model=Optional[Stage1Response])
async def get_stage1_result(
    course_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get Stage 1 results - Repository analysis"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        result = generation_service.get_stage1_result(course_id)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Stage 1 result for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Stage 1 result: {str(e)}"
        )

@router.post("/{course_id}/stage2")
async def start_stage2(
    course_id: str,
    stage2_input: Stage2Input,
    current_user_id: str = Depends(get_current_user_id)
):
    """Start Stage 2 - Document Analysis with user selections"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Start Stage 2
        task_id = generation_service.start_stage2(current_user_id, course_id, stage2_input)
        
        return {
            "message": "Stage 2 - Document analysis started",
            "task_id": task_id,
            "stage": "document_analysis"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start Stage 2 for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start Stage 2: {str(e)}"
        )

@router.post("/{course_id}/stage3")
async def start_stage3(
    course_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Start Stage 3 - Learning Pathway Building"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Start Stage 3
        task_id = generation_service.start_stage3(current_user_id, course_id)
        
        return {
            "message": "Stage 3 - Learning pathway building started",
            "task_id": task_id,
            "stage": "pathway_building"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start Stage 3 for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start Stage 3: {str(e)}"
        )

@router.get("/{course_id}/stage3", response_model=Optional[Stage3Response])
async def get_stage3_result(
    course_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get Stage 3 results - Learning pathways"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        result = generation_service.get_stage3_result(course_id)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Stage 3 result for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Stage 3 result: {str(e)}"
        )

@router.post("/{course_id}/stage4")
async def start_stage4(
    course_id: str,
    stage4_input: Stage4Input,
    current_user_id: str = Depends(get_current_user_id)
):
    """Start Stage 4 - Course Generation"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Start Stage 4
        task_id = generation_service.start_stage4(current_user_id, course_id, stage4_input)
        
        return {
            "message": "Stage 4 - Course generation started",
            "task_id": task_id,
            "stage": "course_generation"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start Stage 4 for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start Stage 4: {str(e)}"
        )

@router.get("/{course_id}/stage4", response_model=Optional[Stage4Response])
async def get_stage4_result(
    course_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get Stage 4 results - Generated course"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        result = generation_service.get_stage4_result(course_id)
        
        # Update course status to completed if generation is successful
        if result:
            from app.models.course import CourseUpdate, CourseStatus
            course_service.update_course(course_id, CourseUpdate(status=CourseStatus.COMPLETED))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Stage 4 result for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Stage 4 result: {str(e)}"
        )

@router.delete("/{course_id}/cancel")
async def cancel_generation(
    course_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Cancel course generation"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Cancel generation
        success = generation_service.cancel_generation(course_id)
        
        if success:
            # Update course status
            from app.models.course import CourseUpdate, CourseStatus
            course_service.update_course(course_id, CourseUpdate(status=CourseStatus.FAILED))
            
            return {"message": "Course generation cancelled"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to cancel generation"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel generation for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel generation: {str(e)}"
        ) 