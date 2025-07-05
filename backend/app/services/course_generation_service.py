import redis
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from celery import Celery
from app.core.config import settings
from app.models.course_generation import (
    CourseGenerationStage, GenerationStatus, GenerationTaskStatus,
    Stage1Response, Stage3Response, Stage4Response,
    Stage2Input, Stage3Input, Stage4Input, PathwaySummary, CourseSummary
)

logger = logging.getLogger(__name__)

class CourseGenerationService:
    """Service for managing course generation tasks"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )
        
        # Initialize Celery client for task management
        self.celery_app = Celery('course_generator')
        self.celery_app.config_from_object({
            'broker_url': f'redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0',
            'result_backend': f'redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0',
        })
    
    def start_course_generation(self, user_id: str, course_id: str, repo_url: str) -> str:
        """Start course generation process - Stage 1"""
        try:
            # Generate task ID
            task_id = str(uuid.uuid4())
            
            # Send task to worker
            task = self.celery_app.send_task(
                'app.tasks.stage1_clone_repository',
                args=[user_id, course_id, repo_url],
                task_id=task_id
            )
            
            # Store task info in Redis
            task_info = {
                'task_id': task_id,
                'course_id': course_id,
                'user_id': user_id,
                'repo_url': repo_url,
                'current_stage': CourseGenerationStage.CLONE_REPO.value,
                'status': GenerationStatus.RUNNING.value,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            task_key = f"generation_task:{course_id}"
            self.redis_client.set(task_key, json.dumps(task_info))
            
            logger.info(f"Started course generation for course {course_id}, task {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to start course generation: {e}")
            raise
    
    def get_task_status(self, course_id: str) -> Optional[GenerationTaskStatus]:
        """Get current status of a generation task"""
        try:
            task_key = f"generation_task:{course_id}"
            task_data = self.redis_client.get(task_key)
            
            if not task_data:
                return None
            
            task_info = json.loads(task_data)
            
            # Get Celery task status
            celery_result = self.celery_app.AsyncResult(task_info['task_id'])
            
            # Update status based on Celery result
            if celery_result.state == 'PENDING':
                status = GenerationStatus.PENDING
            elif celery_result.state == 'STARTED':
                status = GenerationStatus.RUNNING
            elif celery_result.state == 'SUCCESS':
                status = GenerationStatus.COMPLETED
            elif celery_result.state == 'FAILURE':
                status = GenerationStatus.FAILED
            else:
                status = GenerationStatus.RUNNING
            
            # Calculate progress based on stage
            progress = self._calculate_progress(CourseGenerationStage(task_info['current_stage']))
            
            return GenerationTaskStatus(
                task_id=task_info['task_id'],
                course_id=task_info['course_id'],
                current_stage=CourseGenerationStage(task_info['current_stage']),
                status=status,
                progress_percentage=progress,
                created_at=datetime.fromisoformat(task_info['created_at']),
                updated_at=datetime.fromisoformat(task_info['updated_at']),
                error_message=str(celery_result.info) if celery_result.state == 'FAILURE' else None
            )
            
        except Exception as e:
            logger.error(f"Failed to get task status for course {course_id}: {e}")
            return None
    
    def get_stage1_result(self, course_id: str) -> Optional[Stage1Response]:
        """Get Stage 1 results"""
        try:
            task_info = self._get_task_info(course_id)
            if not task_info:
                return None
            
            celery_result = self.celery_app.AsyncResult(task_info['task_id'])
            
            if celery_result.state != 'SUCCESS':
                return None
            
            result = celery_result.result
            if not result.get('success'):
                return None
            
            stage1_data = result['result']
            return Stage1Response(
                repo_name=stage1_data['repo_name'],
                available_folders=stage1_data['available_folders'],
                available_files=stage1_data['available_files'],
                suggested_overview_docs=stage1_data['suggested_overview_docs'],
                total_files=len(stage1_data['available_files'])
            )
            
        except Exception as e:
            logger.error(f"Failed to get Stage 1 result for course {course_id}: {e}")
            return None
    
    def start_stage2(self, user_id: str, course_id: str, stage2_input: Stage2Input) -> str:
        """Start Stage 2 - Document Analysis"""
        try:
            # Generate new task ID
            task_id = str(uuid.uuid4())
            
            # Send task to worker
            task = self.celery_app.send_task(
                'app.tasks.stage2_document_analysis',
                args=[user_id, course_id, stage2_input.model_dump()],
                task_id=task_id
            )
            
            # Update task info
            self._update_task_stage(course_id, task_id, CourseGenerationStage.DOCUMENT_ANALYSIS)
            
            logger.info(f"Started Stage 2 for course {course_id}, task {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to start Stage 2: {e}")
            raise
    
    def start_stage3(self, user_id: str, course_id: str) -> str:
        """Start Stage 3 - Pathway Building"""
        try:
            # Generate new task ID
            task_id = str(uuid.uuid4())
            
            # Send task to worker
            task = self.celery_app.send_task(
                'app.tasks.stage3_pathway_building',
                args=[user_id, course_id],
                task_id=task_id
            )
            
            # Update task info
            self._update_task_stage(course_id, task_id, CourseGenerationStage.PATHWAY_BUILDING)
            
            logger.info(f"Started Stage 3 for course {course_id}, task {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to start Stage 3: {e}")
            raise
    
    def get_stage3_result(self, course_id: str) -> Optional[Stage3Response]:
        """Get Stage 3 results"""
        try:
            task_info = self._get_task_info(course_id)
            if not task_info:
                return None
            
            celery_result = self.celery_app.AsyncResult(task_info['task_id'])
            
            if celery_result.state != 'SUCCESS':
                return None
            
            result = celery_result.result
            if not result.get('success'):
                return None
            
            pathways_data = result['pathways']
            pathways = [
                PathwaySummary(**pathway_data) for pathway_data in pathways_data
            ]
            
            return Stage3Response(
                pathways=pathways,
                total_documents=result.get('total_documents', 0),
                repo_name=result.get('repo_name', 'Unknown')
            )
            
        except Exception as e:
            logger.error(f"Failed to get Stage 3 result for course {course_id}: {e}")
            return None
    
    def start_stage4(self, user_id: str, course_id: str, stage4_input: Stage4Input) -> str:
        """Start Stage 4 - Course Generation"""
        try:
            # Generate new task ID
            task_id = str(uuid.uuid4())
            
            # Send task to worker
            task = self.celery_app.send_task(
                'app.tasks.stage4_course_generation',
                args=[user_id, course_id, stage4_input.model_dump()],
                task_id=task_id
            )
            
            # Update task info
            self._update_task_stage(course_id, task_id, CourseGenerationStage.COURSE_GENERATION)
            
            logger.info(f"Started Stage 4 for course {course_id}, task {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to start Stage 4: {e}")
            raise
    
    def get_stage4_result(self, course_id: str) -> Optional[Stage4Response]:
        """Get Stage 4 results"""
        try:
            task_info = self._get_task_info(course_id)
            if not task_info:
                return None
            
            celery_result = self.celery_app.AsyncResult(task_info['task_id'])
            
            if celery_result.state != 'SUCCESS':
                return None
            
            result = celery_result.result
            if not result.get('success'):
                return None
            
            course_data = result['course_summary']
            return Stage4Response(
                course_summary=CourseSummary(**course_data)
            )
            
        except Exception as e:
            logger.error(f"Failed to get Stage 4 result for course {course_id}: {e}")
            return None
    
    def cancel_generation(self, course_id: str) -> bool:
        """Cancel course generation"""
        try:
            task_info = self._get_task_info(course_id)
            if not task_info:
                return False
            
            # Revoke Celery task
            self.celery_app.control.revoke(task_info['task_id'], terminate=True)
            
            # Update task status
            task_info['status'] = GenerationStatus.FAILED.value
            task_info['updated_at'] = datetime.utcnow().isoformat()
            
            task_key = f"generation_task:{course_id}"
            self.redis_client.set(task_key, json.dumps(task_info))
            
            logger.info(f"Cancelled generation for course {course_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel generation for course {course_id}: {e}")
            return False
    
    def cleanup_generation_data(self, course_id: str):
        """Clean up generation data for a course"""
        try:
            task_key = f"generation_task:{course_id}"
            self.redis_client.delete(task_key)
            
            # Note: Stage data cleanup happens in the worker
            logger.info(f"Cleaned up generation data for course {course_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup generation data for course {course_id}: {e}")
    
    def _get_task_info(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Get task info from Redis"""
        task_key = f"generation_task:{course_id}"
        task_data = self.redis_client.get(task_key)
        
        if not task_data:
            return None
        
        return json.loads(task_data)
    
    def _update_task_stage(self, course_id: str, task_id: str, stage: CourseGenerationStage):
        """Update task stage and ID"""
        task_info = self._get_task_info(course_id)
        if task_info:
            task_info['task_id'] = task_id
            task_info['current_stage'] = stage.value
            task_info['status'] = GenerationStatus.RUNNING.value
            task_info['updated_at'] = datetime.utcnow().isoformat()
            
            task_key = f"generation_task:{course_id}"
            self.redis_client.set(task_key, json.dumps(task_info))
    
    def _calculate_progress(self, stage: CourseGenerationStage) -> int:
        """Calculate progress percentage based on current stage"""
        stage_progress = {
            CourseGenerationStage.CLONE_REPO: 25,
            CourseGenerationStage.DOCUMENT_ANALYSIS: 50,
            CourseGenerationStage.PATHWAY_BUILDING: 75,
            CourseGenerationStage.COURSE_GENERATION: 90,
            CourseGenerationStage.COMPLETED: 100,
            CourseGenerationStage.FAILED: 0
        }
        return stage_progress.get(stage, 0) 