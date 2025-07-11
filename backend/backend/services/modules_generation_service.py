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
    get_db_session, Course, GeneratedCourse, ModuleContent
)
from backend.services.base_service import BaseService

logger = logging.getLogger(__name__)


class ModulesGenerationService(BaseService):
    """Lean service for course content generation"""
    
    def start_course_generation(self, course_id: str, user_id: str, 
                              selected_pathway_id: str = None) -> str:
        """Start course generation (Stage 4) - Triggers Celery task"""
        try:
            # Trigger Celery task using base class method
            task_id = self.trigger_celery_task(
                'backend.worker.tasks.stage4_course_generation',
                [user_id, course_id, {
                    "selected_pathway_id": selected_pathway_id,
                    "custom_pathway": None  # For now, use selected pathway
                }]
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
            
            # Get module content if available
            module_contents = db.query(ModuleContent).join(
                # This would need proper join logic based on pathway/module relationships
                # For now, return basic info
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