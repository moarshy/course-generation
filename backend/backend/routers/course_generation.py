import logging
from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Optional
import redis
import json
from backend.shared.models import (
    CourseGenerationRequest, GenerationTaskStatus,
    Stage1Response, Stage1Input, Stage2Response, Stage2Input, Stage3Input, Stage3Response,
    Stage4Input, Stage4Response, UpdateDocumentRequest,
    UpdateModuleRequest, CreateModuleRequest, UpdatePathwayRequest, ModuleReorderRequest
)
from backend.services.course_generation_service import CourseGenerationService
from backend.services.course_service import CourseService
from backend.core.security import get_current_user_id

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
        from shared.models import CourseUpdate, CourseStatus
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

@router.get("/{course_id}/status")
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
        
        # Check generation status first
        generation_status = generation_service.get_task_status(course_id)
        
        if generation_status:
            stage_statuses = generation_status.get('stage_statuses', {})
            clone_repo_status = stage_statuses.get('CLONE_REPO') or stage_statuses.get('clone_repo')
            
            # If Stage 1 is running or pending, return appropriate status
            if clone_repo_status in ['running', 'pending']:
                raise HTTPException(
                    status_code=status.HTTP_202_ACCEPTED,
                    detail="Stage 1 is still in progress"
                )
            elif clone_repo_status == 'failed':
                error_message = generation_status.get('error_message', 'Repository analysis failed')
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_message
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

@router.post("/{course_id}/stage1/selections")
async def save_stage1_selections(
    course_id: str,
    stage1_input: Stage1Input,
    current_user_id: str = Depends(get_current_user_id)
):
    """Save Stage 1 user selections"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Save Stage 1 selections
        success = generation_service.save_stage1_selections(course_id, stage1_input)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save Stage 1 selections"
            )
        
        return {
            "message": "Stage 1 selections saved successfully",
            "selections": stage1_input.model_dump()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save Stage 1 selections for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save Stage 1 selections: {str(e)}"
        )

@router.get("/{course_id}/stage1/selections")
async def get_stage1_selections(
    course_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get Stage 1 user selections"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # First check the generation status to see if Stage 1 is still running
        generation_status = generation_service.get_task_status(course_id)
        
        if generation_status:
            stage_statuses = generation_status.get('stage_statuses', {})
            clone_repo_status = stage_statuses.get('CLONE_REPO') or stage_statuses.get('clone_repo')
            
            # If Stage 1 is running or pending, return a specific response
            if clone_repo_status in ['running', 'pending']:
                raise HTTPException(
                    status_code=status.HTTP_202_ACCEPTED,
                    detail="Stage 1 is still in progress. Selections not available yet."
                )
            elif clone_repo_status == 'failed':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Stage 1 failed. Cannot retrieve selections."
                )
        
        # Try to get selections
        selections = generation_service.get_stage1_selections(course_id)
        
        if not selections:
            # Check again if there's any task running
            if generation_status and generation_status.get('status') == 'running':
                raise HTTPException(
                    status_code=status.HTTP_202_ACCEPTED,
                    detail="Stage 1 is still in progress. Selections not available yet."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Stage 1 selections not found"
                )
        
        return selections
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Stage 1 selections for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Stage 1 selections: {str(e)}"
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

@router.get("/{course_id}/stage2", response_model=Optional[Stage2Response])
async def get_stage2_result(
    course_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get Stage 2 results - Document analysis"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        result = generation_service.get_stage2_result(course_id)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Stage 2 result for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Stage 2 result: {str(e)}"
        )

@router.put("/{course_id}/stage2/document")
async def update_document_metadata(
    course_id: str,
    update_request: UpdateDocumentRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update metadata for a specific document in Stage 2"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Update document metadata
        success = generation_service.update_document_metadata(
            course_id, 
            update_request.document_id, 
            update_request.metadata_updates
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update document metadata"
            )
        
        return {"message": "Document metadata updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update document metadata for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document metadata: {str(e)}"
        )

@router.put("/{course_id}/stage3/pathway")
async def update_pathway(
    course_id: str,
    update_request: UpdatePathwayRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update pathway details"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Update pathway
        success = generation_service.update_pathway(
            course_id, 
            update_request.pathway_index, 
            update_request.pathway_updates
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update pathway"
            )
        
        return {"message": "Pathway updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update pathway for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update pathway: {str(e)}"
        )

@router.put("/{course_id}/stage3/module")
async def update_module(
    course_id: str,
    update_request: UpdateModuleRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update a specific module in a pathway"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Update module
        success = generation_service.update_module(
            course_id, 
            update_request.pathway_index,
            update_request.module_index,
            update_request.module_updates
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update module"
            )
        
        return {"message": "Module updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update module for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update module: {str(e)}"
        )

@router.post("/{course_id}/stage3/module")
async def create_module(
    course_id: str,
    create_request: CreateModuleRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """Create a new module in a pathway"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Create module
        success = generation_service.create_module(
            course_id, 
            create_request.pathway_index,
            create_request.module_data
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create module"
            )
        
        return {"message": "Module created successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create module for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create module: {str(e)}"
        )

@router.delete("/{course_id}/stage3/pathway/{pathway_index}/module/{module_index}")
async def delete_module(
    course_id: str,
    pathway_index: int,
    module_index: int,
    current_user_id: str = Depends(get_current_user_id)
):
    """Delete a module from a pathway"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Delete module
        success = generation_service.delete_module(
            course_id, 
            pathway_index,
            module_index
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete module"
            )
        
        return {"message": "Module deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete module for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete module: {str(e)}"
        )

@router.put("/{course_id}/stage3/pathway/{pathway_index}/modules/reorder")
async def reorder_modules(
    course_id: str,
    pathway_index: int,
    reorder_request: ModuleReorderRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """Reorder modules in a pathway"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Reorder modules
        success = generation_service.reorder_modules(
            course_id, 
            pathway_index,
            reorder_request.module_order
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to reorder modules"
            )
        
        return {"message": "Modules reordered successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reorder modules for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reorder modules: {str(e)}"
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

@router.get("/{course_id}/stage3")
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
            from shared.models import CourseUpdate, CourseStatus
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
            from shared.models import CourseUpdate, CourseStatus
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

@router.get("/stage2/progress")
async def get_stage2_progress(course_id: str = Query(..., description="Course ID")):
    """Get detailed progress for Stage 2 document analysis"""
    try:
        detailed_progress = generation_service.get_stage2_detailed_progress(course_id)
        
        if detailed_progress is None:
            # No detailed progress found - check if task is running
            task_status = generation_service.get_task_status(course_id)
            if task_status and task_status.get('current_stage') == 'DOCUMENT_ANALYSIS':
                # Task is running but no detailed progress yet
                return {
                    "stage": "initializing",
                    "stage_description": "Initializing document analysis...",
                    "percentage": 0,
                    "total_files": 0,
                    "processed_files": 0,
                    "current_file": "",
                    "completed_files": [],
                    "failed_files_list": []
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No progress information available"
                )
        
        return detailed_progress
        
    except Exception as e:
        logger.error(f"Failed to get Stage 2 progress for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve progress: {str(e)}"
        )

@router.get("/stage3/progress")
async def get_stage3_progress(course_id: str = Query(..., description="Course ID")):
    """Get detailed progress for Stage 3 pathway building"""
    try:
        # Get progress data through service layer (more robust)
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        progress_key = f"stage3_progress:{course_id}"
        
        logger.info(f"Fetching Stage 3 progress for course: {course_id}")
        
        progress_data_str = redis_client.get(progress_key)
        if not progress_data_str:
            logger.info(f"No Redis progress data found for course {course_id}, checking task status")
            # No detailed progress found - check if task is running
            task_status = generation_service.get_task_status(course_id)
            if task_status and (task_status.get('current_stage') == 'PATHWAY_BUILDING' or 
                               task_status.get('stage_statuses', {}).get('PATHWAY_BUILDING') == 'running'):
                logger.info(f"Stage 3 is running for course {course_id}, returning initializing state")
                # Task is running but no detailed progress yet
                return {
                    "stage": "initializing", 
                    "stage_description": "Initializing pathway generation...",
                    "total_pathways": 3,
                    "generated_pathways": 0,
                    "current_complexity": "",
                    "completed_complexities": []
                }
            else:
                logger.warning(f"No progress information available for course {course_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No progress information available"
                )
        
        # Parse JSON with better error handling
        try:
            progress_data = json.loads(progress_data_str)
            logger.info(f"Successfully parsed progress data for course {course_id}: {progress_data}")
            return progress_data
        except json.JSONDecodeError as json_err:
            logger.error(f"Failed to parse JSON progress data for course {course_id}: {json_err}")
            logger.error(f"Raw data: {progress_data_str}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid progress data format"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Stage 3 progress for course {course_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve progress: {str(e)}"
        )

@router.get("/stage4/progress")
async def get_stage4_progress(course_id: str = Query(..., description="Course ID")):
    """Get detailed progress for Stage 4 course generation"""
    try:
        # Get progress data through Redis directly (like stage3)
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        progress_key = f"stage4_progress:{course_id}"
        
        logger.info(f"Fetching Stage 4 progress for course: {course_id}")
        
        progress_data_str = redis_client.get(progress_key)
        if not progress_data_str:
            logger.info(f"No Redis progress data found for course {course_id}, checking task status")
            # No detailed progress found - check if task is running
            task_status = generation_service.get_task_status(course_id)
            if task_status and (task_status.get('current_stage') == 'COURSE_GENERATION' or 
                               task_status.get('stage_statuses', {}).get('COURSE_GENERATION') == 'running'):
                logger.info(f"Stage 4 is running for course {course_id}, returning initializing state")
                # Task is running but no detailed progress yet
                return {
                    "stage": "initializing",
                    "stage_description": "Initializing course generation...",
                    "total_modules": 0,
                    "generated_modules": 0,
                    "current_module": "",
                    "completed_modules": [],
                    "current_step": "loading_data",
                    "step_progress": 0
                }
            else:
                logger.warning(f"No progress information available for course {course_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No progress information available"
                )
        
        # Parse JSON with better error handling
        try:
            progress_data = json.loads(progress_data_str)
            logger.info(f"Successfully parsed progress data for course {course_id}: {progress_data}")
            return progress_data
        except json.JSONDecodeError as json_err:
            logger.error(f"Failed to parse JSON progress data for course {course_id}: {json_err}")
            logger.error(f"Raw data: {progress_data_str}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid progress data format"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Stage 4 progress for course {course_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve progress: {str(e)}"
        )

@router.get("/{course_id}/course-content")
async def get_course_content(
    course_id: str, 
    user_id: str = Depends(get_current_user_id)
):
    """Get the complete course structure and metadata"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, user_id):
            raise HTTPException(status_code=404, detail="Course not found")
        
        course_path = generation_service.get_course_export_path(user_id, course_id)
        course_info_path = course_path / "course_info.json"
        
        if not course_info_path.exists():
            raise HTTPException(status_code=404, detail="Course content not found")
        
        with open(course_info_path, 'r', encoding='utf-8') as f:
            course_info = json.load(f)
        
        return course_info
        
    except Exception as e:
        logger.error(f"Error getting course content for {course_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get course content")


@router.get("/{course_id}/course-content/{module_id}/{file_name}")
async def get_course_file_content(
    course_id: str,
    module_id: str, 
    file_name: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get the content of a specific course file"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, user_id):
            raise HTTPException(status_code=404, detail="Course not found")
        
        course_path = generation_service.get_course_export_path(user_id, course_id)
        file_path = course_path / module_id / file_name
        
        if not file_path.exists():
            # Also check in root directory for welcome/conclusion files
            file_path = course_path / file_name
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="File not found")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {"content": content}
        
    except Exception as e:
        logger.error(f"Error getting file content for {course_id}/{module_id}/{file_name}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get file content")


@router.get("/{course_id}/download")
async def download_course(
    course_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Download the complete course as a zip file"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, user_id):
            raise HTTPException(status_code=404, detail="Course not found")
        
        course_path = generation_service.get_course_export_path(user_id, course_id)
        
        if not course_path.exists():
            raise HTTPException(status_code=404, detail="Course content not found")
        
        # Create a zip file in memory
        import zipfile
        from io import BytesIO
        
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add all files from the course directory
            for file_path in course_path.rglob('*'):
                if file_path.is_file():
                    # Create relative path for the zip file
                    relative_path = file_path.relative_to(course_path)
                    zip_file.write(file_path, relative_path)
        
        zip_buffer.seek(0)
        
        from fastapi.responses import StreamingResponse
        
        return StreamingResponse(
            iter([zip_buffer.read()]),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=course_{course_id}.zip"}
        )
        
    except Exception as e:
        logger.error(f"Error downloading course {course_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download course") 