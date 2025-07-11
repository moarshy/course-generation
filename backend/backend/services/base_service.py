"""
Base service class for Course Creator backend services.

Provides common functionality for the 4-service architecture:
- Celery client initialization
- Task status management
- Database session handling
"""

import uuid
import logging
from typing import Dict, Any
from celery import Celery

from backend.shared.database import get_db_session, CourseTask
from backend.core.config import settings

logger = logging.getLogger(__name__)


class BaseService:
    """Base class for all course generation services"""
    
    def __init__(self):
        """Initialize common service components"""
        # Initialize Celery client with common configuration
        self.celery_app = Celery('course_generator')
        self.celery_app.config_from_object({
            'broker_url': f'redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0',
            'result_backend': f'redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0',
        })
    
    def get_task_status(self, course_id: str, stage: str) -> Dict[str, Any]:
        """Get task status from database (common implementation for all services)"""
        db = get_db_session()
        try:
            task = db.query(CourseTask).filter(
                CourseTask.course_id == course_id,
                CourseTask.stage == stage
            ).first()
            
            if not task:
                return {"status": "not_started", "progress": 0}
            
            return {
                "status": task.status,
                "progress": task.progress_percentage,
                "current_step": task.current_step,
                "error_message": task.error_message,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get task status for {stage}: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            db.close()
    
    def trigger_celery_task(self, task_name: str, args: list, task_id: str = None) -> str:
        """Trigger a Celery task and return the task ID"""
        if not task_id:
            task_id = str(uuid.uuid4())
            
        task = self.celery_app.send_task(task_name, args=args, task_id=task_id)
        return task_id
    
    def cancel_task(self, course_id: str, stage: str) -> bool:
        """Cancel a running task"""
        try:
            db = get_db_session()
            try:
                # Get current task
                task = db.query(CourseTask).filter(
                    CourseTask.course_id == course_id,
                    CourseTask.stage == stage
                ).first()
                
                if task and task.task_id:
                    # Revoke Celery task
                    self.celery_app.control.revoke(task.task_id, terminate=True)
                    
                    # Update task status
                    task.status = 'FAILURE'
                    task.error_message = 'Cancelled by user'
                    db.commit()
                    
                    logger.info(f"Cancelled {stage} task for course {course_id}")
                    return True
                
                return False
                
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to cancel {stage} task: {e}")
            return False 