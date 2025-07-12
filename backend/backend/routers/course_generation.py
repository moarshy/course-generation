import logging
from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Optional
import redis
import json
from backend.shared.models import (
    CourseGenerationRequest, GenerationTaskStatus,
    Stage1Response, Stage1Input, Stage2Response, Stage2Input, Stage3Input, Stage3Response,
    Stage4Input, Stage4Response, UpdateDocumentRequest,
    UpdateModuleRequest, CreateModuleRequest, UpdatePathwayRequest, ModuleReorderRequest,
    CourseUpdate, CourseStatus
)
from backend.services.repository_clone_service import RepositoryCloneService
from backend.services.document_analyser_service import DocumentAnalyserService
from backend.services.learning_pathway_service import LearningPathwayService
from backend.services.modules_generation_service import ModulesGenerationService
from backend.services.course_service import CourseService
from backend.core.security import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/course-generation", tags=["course-generation"])

# Initialize the 4 lean services instead of the bloated one
repo_service = RepositoryCloneService()
doc_service = DocumentAnalyserService()
pathway_service = LearningPathwayService()
modules_service = ModulesGenerationService()
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
        
        # Start generation using lean RepositoryCloneService
        task_id = repo_service.start_repository_analysis(
            course_id, current_user_id, request.repo_url
        )
        
        # Update course status
        course_service.update_course(course_id, current_user_id, CourseUpdate(status=CourseStatus.STAGE1_RUNNING))
        
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
        # Verify course ownership and get course record
        course = course_service.get_course_by_id(course_id, current_user_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Get the actual course status from database
        course_status = course.status
        
        # Map database status to stage information
        stage_mapping = {
            'draft': {'current_stage': 'stage1', 'progress': 0},
            'stage1_running': {'current_stage': 'stage1', 'progress': 10},
            'stage1_complete': {'current_stage': 'stage1', 'progress': 25},
            'stage2_running': {'current_stage': 'stage2', 'progress': 35},
            'stage2_complete': {'current_stage': 'stage2', 'progress': 50},
            'stage3_running': {'current_stage': 'stage3', 'progress': 60},
            'stage3_complete': {'current_stage': 'stage3', 'progress': 75},
            'stage4_running': {'current_stage': 'stage4', 'progress': 85},
            'stage4_complete': {'current_stage': 'stage4', 'progress': 100},
            'stage1_failed': {'current_stage': 'stage1', 'progress': 0},
            'stage2_failed': {'current_stage': 'stage2', 'progress': 25},
            'stage3_failed': {'current_stage': 'stage3', 'progress': 50},
            'stage4_failed': {'current_stage': 'stage4', 'progress': 75},
            'failed': {'current_stage': 'unknown', 'progress': 0}
        }
        
        stage_info = stage_mapping.get(course_status, {'current_stage': 'unknown', 'progress': 0})
        
        # Determine overall status
        if 'complete' in course_status:
            overall_status = 'completed'
        elif 'running' in course_status:
            overall_status = 'running'
        elif 'failed' in course_status:
            overall_status = 'failed'
        else:
            overall_status = 'pending'
        
        # Build stage statuses
        stage_statuses = {
            'CLONE_REPO': 'completed' if course_status in ['stage1_complete', 'stage2_running', 'stage2_complete', 'stage3_running', 'stage3_complete', 'stage4_running', 'stage4_complete'] else 'running' if course_status == 'stage1_running' else 'pending',
            'DOCUMENT_ANALYSIS': 'completed' if course_status in ['stage2_complete', 'stage3_running', 'stage3_complete', 'stage4_running', 'stage4_complete'] else 'running' if course_status == 'stage2_running' else 'pending',
            'PATHWAY_BUILDING': 'completed' if course_status in ['stage3_complete', 'stage4_running', 'stage4_complete'] else 'running' if course_status == 'stage3_running' else 'pending',
            'COURSE_GENERATION': 'completed' if course_status == 'stage4_complete' else 'running' if course_status == 'stage4_running' else 'pending'
        }
        
        return {
            'course_id': course_id,
            'current_stage': stage_info['current_stage'],
            'status': overall_status,
            'progress_percentage': stage_info['progress'],
            'stage_statuses': stage_statuses,
            'database_status': course_status  # Include the raw database status for debugging
        }
        
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
        
        # Check status first using lean service
        status_info = repo_service.get_task_status(course_id)
        
        if status_info['status'] in ['STARTED', 'PENDING']:
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Stage 1 is still in progress"
            )
        elif status_info['status'] == 'FAILURE':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=status_info.get('error_message', 'Repository analysis failed')
            )
        
        # Get results using lean service
        result = repo_service.get_repository_files(course_id)
        
        if 'error' in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['error']
            )
        
        return Stage1Response(**result)
        
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
        
        # Save Stage 1 selections using lean service
        success = repo_service.save_stage1_selections(
            course_id, 
            stage1_input.include_folders,
            stage1_input.overview_doc
        )
        
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
        
        # Check status first using lean service
        status_info = repo_service.get_task_status(course_id)
        
        if status_info['status'] in ['STARTED', 'PENDING']:
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Stage 1 is still in progress. Selections not available yet."
            )
        elif status_info['status'] == 'FAILURE':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stage 1 failed. Cannot retrieve selections."
            )
        
        # Get selections using lean service
        selections = repo_service.get_stage1_selections(course_id)
        
        if not selections:
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
    """Start Stage 2 - Document Analysis"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Start Stage 2 using lean service
        task_id = doc_service.start_document_analysis(
            course_id, 
            current_user_id, 
            stage2_input.complexity_level,
            stage2_input.additional_info or ""
        )
        
        return {
            "message": "Stage 2 document analysis started",
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
        
        # Get results using lean service
        result = doc_service.get_analyzed_documents(course_id)
        
        if 'error' in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['error']
            )
        
        return Stage2Response(
            processed_files_count=result['total_documents'],
            failed_files_count=0,  # We don't track this separately now
            include_folders=[],  # Could be retrieved from Stage1 selections if needed
            overview_doc=None,  # Could be retrieved from Stage1 selections if needed
            analysis_timestamp=None,  # Could add this to database
            analyzed_documents=result['analyzed_documents']
        )
        
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
    """Update document metadata"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # For now, just return success as document metadata updates 
        # would need to be implemented in the DocumentAnalyserService
        return {"message": "Document metadata update not yet implemented in lean service"}
        
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
        
        # Update pathway using lean service
        success = pathway_service.update_pathway(
            course_id,
            update_request.pathway_id,
            title=update_request.title,
            description=update_request.description,
            complexity_level=getattr(update_request, 'complexity_level', None),
            estimated_duration=getattr(update_request, 'estimated_duration', None)
        )
        
        if success:
            return {"message": "Pathway updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update pathway"
            )
        
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
    """Update module details"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Update module using lean service
        success = pathway_service.update_module(
            course_id,
            update_request.pathway_id,
            update_request.module_id,
            title=update_request.title,
            description=update_request.description,
            learning_objectives=getattr(update_request, 'learning_objectives', None)
        )
        
        if success:
            return {"message": "Module updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update module"
            )
        
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
        
        # Create module using lean service
        success = pathway_service.add_module(
            course_id,
            create_request.pathway_id,
            create_request.title,
            create_request.description,
            getattr(create_request, 'learning_objectives', [])
        )
        
        if success:
            return {"message": "Module created successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create module"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create module for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create module: {str(e)}"
        )

@router.delete("/{course_id}/stage3/pathway/{pathway_id}/module/{module_id}")
async def delete_module(
    course_id: str,
    pathway_id: str,
    module_id: str,
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
        
        # Delete module using lean service
        success = pathway_service.delete_module(course_id, pathway_id, module_id)
        
        if success:
            return {"message": "Module deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete module"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete module for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete module: {str(e)}"
        )

@router.put("/{course_id}/stage3/pathway/{pathway_id}/modules/reorder")
async def reorder_modules(
    course_id: str,
    pathway_id: str,
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
        
        # Reorder modules using lean service
        success = pathway_service.rearrange_modules(
            course_id, 
            pathway_id, 
            reorder_request.module_order
        )
        
        if success:
            return {"message": "Modules reordered successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reorder modules"
            )
        
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
    stage3_input: Optional[Stage3Input] = None,
    current_user_id: str = Depends(get_current_user_id)
):
    """Start Stage 3 - Learning Pathway Generation"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Start Stage 3 using lean service
        complexity_level = stage3_input.complexity_level if stage3_input else "intermediate"
        additional_info = stage3_input.additional_instructions if stage3_input else ""
        
        task_id = pathway_service.start_pathway_generation(
            course_id, 
            current_user_id, 
            complexity_level,
            additional_info
        )
        
        complexity_msg = ""
        if stage3_input and stage3_input.complexity_level:
            complexity_msg = f" with complexity level: {stage3_input.complexity_level}"
        
        return {
            "message": f"Stage 3 - Learning pathway generation started{complexity_msg}",
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
        
        # Get results using lean service
        result = pathway_service.get_pathways(course_id)
        
        if 'error' in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['error']
            )
        
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
        
        # Start Stage 4 using lean service
        task_id = modules_service.start_course_generation(
            course_id, 
            current_user_id, 
            getattr(stage4_input, 'selected_pathway_id', None)
        )
        
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
        
        # Get results using lean service
        result = modules_service.get_generated_course(course_id)
        
        if 'error' in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['error']
            )
        
        # Convert to expected response format
        from backend.shared.models import CourseSummary
        course_summary = CourseSummary(
            title=result['title'],
            description=result['description'],
            module_count=result['module_count'],
            export_path=str(result['export_path'])
        )
        
        # Update course status to completed if generation is successful
        if result.get('generation_complete'):
            course_service.update_course(course_id, current_user_id, CourseUpdate(status=CourseStatus.STAGE4_COMPLETE))
        
        return Stage4Response(course_summary=course_summary)
        
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
        
        # Cancel generation across all services
        success = modules_service.cancel_generation(course_id)
        
        if success:
            # Update course status
            from backend.shared.models import CourseUpdate, CourseStatus
            course_service.update_course(course_id, current_user_id, CourseUpdate(status=CourseStatus.FAILED))
            
            return {"message": "Course generation cancelled successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel course generation"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel generation for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel course generation: {str(e)}"
        )

@router.get("/stage2/progress")
async def get_stage2_progress(course_id: str = Query(..., description="Course ID")):
    """Get detailed progress for Stage 2 document analysis"""
    try:
        # Use lean service to get task status
        task_status = doc_service.get_task_status(course_id)
        
        if task_status['status'] == 'not_started':
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stage 2 task not found"
            )
        
        # Return simplified progress info from database
        return {
            'status': task_status['status'],
            'progress': task_status['progress'],
            'current_step': task_status.get('current_step', ''),
            'error': task_status.get('error_message'),
            'started_at': task_status.get('started_at'),
            'completed_at': task_status.get('completed_at')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Stage 2 progress for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Stage 2 progress: {str(e)}"
        )

@router.get("/stage3/progress")
async def get_stage3_progress(course_id: str = Query(..., description="Course ID")):
    """Get progress for Stage 3 pathway generation"""
    try:
        # Use lean service to get task status
        task_status = pathway_service.get_task_status(course_id)
        
        if task_status['status'] == 'not_started':
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stage 3 task not found"
            )
        
        # Return simplified progress info from database
        return {
            'status': task_status['status'],
            'progress': task_status['progress'],
            'current_step': task_status.get('current_step', ''),
            'error': task_status.get('error_message'),
            'started_at': task_status.get('started_at'),
            'completed_at': task_status.get('completed_at')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Stage 3 progress for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Stage 3 progress: {str(e)}"
        )

@router.get("/stage4/progress")
async def get_stage4_progress(course_id: str = Query(..., description="Course ID")):
    """Get progress for Stage 4 course generation"""
    try:
        # Use lean service to get task status
        task_status = modules_service.get_task_status(course_id)
        
        if task_status['status'] == 'not_started':
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stage 4 task not found"
            )
        
        # Return simplified progress info from database
        return {
            'status': task_status['status'],
            'progress': task_status['progress'],
            'current_step': task_status.get('current_step', ''),
            'error': task_status.get('error_message'),
            'started_at': task_status.get('started_at'),
            'completed_at': task_status.get('completed_at')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Stage 4 progress for course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Stage 4 progress: {str(e)}"
        )

@router.get("/{course_id}/course-content")
async def get_course_content(
    course_id: str, 
    user_id: str = Depends(get_current_user_id)
):
    """Get course content structure"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, user_id):
            raise HTTPException(status_code=404, detail="Course not found")
        
        # Get course export path using lean service
        export_path = modules_service.get_course_export_path(course_id)
        
        if not export_path:
            raise HTTPException(status_code=404, detail="Course content not found")
        
        from pathlib import Path
        course_path = Path(export_path)
        course_info_path = course_path / "course_info.json"
        
        if not course_info_path.exists():
            raise HTTPException(status_code=404, detail="Course content not available")
        
        # Read course info
        with open(course_info_path, 'r') as f:
            course_info = json.load(f)
        
        return course_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get course content for {course_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get course content: {str(e)}"
        )

@router.get("/{course_id}/course-content/{module_id}/{file_name}")
async def get_course_file_content(
    course_id: str,
    module_id: str, 
    file_name: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get specific course file content"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, user_id):
            raise HTTPException(status_code=404, detail="Course not found")
        
        # Get course export path using lean service
        export_path = modules_service.get_course_export_path(course_id)
        
        if not export_path:
            raise HTTPException(status_code=404, detail="Course content not found")
        
        from pathlib import Path
        course_path = Path(export_path)
        file_path = course_path / module_id / file_name
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {"content": content}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file content for {course_id}/{module_id}/{file_name}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get file content: {str(e)}"
        )

@router.get("/{course_id}/download")
async def download_course(
    course_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Download course as ZIP file"""
    try:
        # Verify course ownership
        if not course_service.verify_course_ownership(course_id, user_id):
            raise HTTPException(status_code=404, detail="Course not found")
        
        # Get course export path using lean service
        export_path = modules_service.get_course_export_path(course_id)
        
        if not export_path:
            raise HTTPException(status_code=404, detail="Course content not found")
        
        from pathlib import Path
        course_path = Path(export_path)
        
        if not course_path.exists():
            raise HTTPException(status_code=404, detail="Course files not found")
        
        # For now, return the path info
        # In a full implementation, you'd create and return a ZIP file
        return {
            "message": "Course download functionality needs ZIP creation implementation",
            "course_path": str(course_path),
            "available_files": [f.name for f in course_path.rglob("*") if f.is_file()]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download course {course_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to download course: {str(e)}"
        ) 