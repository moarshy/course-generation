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
            
            # Auto-export course if not already exported
            if not generated_course.export_path and module_list:
                export_path = self.export_course_content(course_id)
                if export_path:
                    generated_course.export_path = export_path
                    db.commit()
            
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
    
    def export_course_content(self, course_id: str) -> Optional[str]:
        """Export course content to files and return the export path"""
        try:
            from pathlib import Path
            import json
            from backend.core.config import settings
            
            # Create export directory
            export_dir = Path(settings.ROOT_DATA_DIR) / "exports" / course_id
            export_dir.mkdir(parents=True, exist_ok=True)
            
            db = get_db_session()
            try:
                # Get course info
                course = db.query(Course).filter(Course.course_id == course_id).first()
                if not course:
                    return None
                
                # Get generated course
                generated_course = db.query(GeneratedCourse).filter(
                    GeneratedCourse.course_id == course_id
                ).first()
                if not generated_course:
                    return None
                
                # Get pathways and modules
                pathways = db.query(Pathway).filter(Pathway.course_id == course_id).all()
                
                # Collect all modules and their content
                course_modules = {}
                total_modules = 0
                
                for pathway in pathways:
                    modules = db.query(Module).filter(Module.pathway_id == pathway.id).order_by(Module.sequence_order).all()
                    
                    for module in modules:
                        # Get module content
                        content = db.query(ModuleContent).filter(ModuleContent.module_id == module.id).first()
                        
                        if content:
                            course_modules[f"module_{module.id}"] = {
                                "title": module.title,
                                "content": f"{content.introduction}\n\n{content.main_content}\n\n{content.conclusion}",  # Keep combined for backward compatibility
                                "introduction": content.introduction,
                                "main_content": content.main_content,
                                "conclusion": content.conclusion,
                                "learning_objectives": json.loads(module.learning_objectives) if module.learning_objectives else [],
                                "theme": "General",  # Default theme
                                "sequence_order": module.sequence_order,
                                "assessment": content.assessment,
                                "summary": content.summary
                            }
                            total_modules += 1
                
                # Create course_info.json
                course_info = {
                    "course_overview": {
                        "title": course.title,
                        "description": course.description or "Generated Course Content",
                        "total_modules": total_modules,
                        "complexity_level": pathways[0].complexity_level if pathways else "intermediate",
                        "estimated_duration": pathways[0].estimated_duration if pathways else "4-6 hours"
                    },
                    "modules": course_modules
                }
                
                # Write course_info.json
                course_info_path = export_dir / "course_info.json"
                with open(course_info_path, 'w', encoding='utf-8') as f:
                    json.dump(course_info, f, indent=2, ensure_ascii=False)
                
                # Create individual module files
                for module_id, module_data in course_modules.items():
                    module_file = export_dir / f"{module_id}.md"
                    with open(module_file, 'w', encoding='utf-8') as f:
                        f.write(f"# {module_data['title']}\n\n")
                        f.write(module_data['content'])
                        if module_data.get('assessment'):
                            f.write(f"\n\n## Assessment\n\n{module_data['assessment']}")
                
                logger.info(f"Exported course content to {export_dir}")
                return str(export_dir)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to export course content: {e}")
            return None
    
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