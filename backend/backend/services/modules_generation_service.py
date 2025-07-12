"""
ModulesGenerationService - Service 4 of 4

Responsibility: Course content generation
- Triggers Celery task for final course generation
- Manages Stage 4 results and course exports
- Database-driven, no pickle files
"""

import logging
from typing import List, Dict, Any, Optional

from backend.shared.database import (
    get_db_session, Course, GeneratedCourse, ModuleContent, Module, Pathway
)
from backend.shared.models import Stage4Input
from backend.services.base_service import BaseService

logger = logging.getLogger(__name__)


class ModulesGenerationService(BaseService):
    """Lean service for course content generation"""
    
    def start_course_generation(self, course_id: str, user_id: str, 
                              stage4_input: Stage4Input) -> str:
        """Start course generation (Stage 4) - Triggers Celery task"""
        try:
            # Convert Stage4Input to dictionary for Celery task
            user_input = stage4_input.model_dump() if hasattr(stage4_input, 'model_dump') else stage4_input
            
            # Trigger Celery task using base class method
            task_id = self.trigger_celery_task(
                'backend.worker.tasks.stage4_course_generation',
                [user_id, course_id, user_input]
            )
            
            logger.info(f"Started course generation for course {course_id}, task {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to start course generation: {e}")
            raise
    
    def get_generated_course(self, course_id: str) -> Dict[str, Any]:
        """Get generated course information from database"""
        db = get_db_session()
        try:
            # Get generated course info
            generated_course = db.query(GeneratedCourse).filter(
                GeneratedCourse.course_id == course_id
            ).first()
            
            if not generated_course:
                return {"error": "No generated course found"}
            
            # Get course basic info
            course = db.query(Course).filter(Course.course_id == course_id).first()
            
            # Get module content for this course by joining through Module and Pathway
            module_contents = db.query(ModuleContent).join(Module).join(Pathway).filter(
                Pathway.course_id == course_id
            ).all() if generated_course.pathway_id else []
            
            module_list = []
            for content in module_contents:
                module_list.append({
                    "module_id": content.module_id,
                    "introduction": content.introduction,
                    "main_content": content.main_content[:500] + "..." if content.main_content and len(content.main_content) > 500 else content.main_content,
                    "conclusion": content.conclusion,
                    "assessment": content.assessment,
                    "summary": content.summary,
                    "generated_at": content.generated_at.isoformat() if content.generated_at else None
                })
            
            return {
                "course_id": course_id,
                "title": course.title if course else "Generated Course",
                "description": course.description if course else "",
                "export_path": generated_course.export_path,
                "status": generated_course.status,
                "pathway_id": generated_course.pathway_id,
                "modules": module_list,
                "module_count": len(module_list),
                "generated_at": generated_course.generated_at.isoformat() if generated_course.generated_at else None,
                "generation_complete": generated_course.status == 'completed'
            }
            
        except Exception as e:
            logger.error(f"Failed to get generated course: {e}")
            return {"error": str(e)}
        finally:
            db.close()
    
    def get_course_export_path(self, course_id: str) -> Optional[str]:
        """Get the export path for a generated course"""
        db = get_db_session()
        try:
            generated_course = db.query(GeneratedCourse).filter(
                GeneratedCourse.course_id == course_id
            ).first()
            
            return generated_course.export_path if generated_course else None
            
        except Exception as e:
            logger.error(f"Failed to get export path: {e}")
            return None
        finally:
            db.close()
    
    def update_course_status(self, course_id: str, status: str) -> bool:
        """Update the status of a generated course"""
        db = get_db_session()
        try:
            generated_course = db.query(GeneratedCourse).filter(
                GeneratedCourse.course_id == course_id
            ).first()
            
            if generated_course:
                generated_course.status = status
                db.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update course status: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def get_task_status(self, course_id: str) -> Dict[str, Any]:
        """Get task status from database"""
        return super().get_task_status(course_id, 'stage4')
    
    def cancel_generation(self, course_id: str) -> bool:
        """Cancel course generation"""
        return self.cancel_task(course_id, 'stage4')