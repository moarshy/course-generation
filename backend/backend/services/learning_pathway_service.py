"""
LearningPathwayService - Service 3 of 4

Responsibility: Learning pathway generation
- Triggers Celery task for pathway generation
- Manages Stage 3 user inputs and pathway selections
- Database-driven, no pickle files
"""

import logging
from typing import List, Dict, Any, Optional

from backend.shared.database import (
    get_db_session, Pathway, Module, Stage3Input, Stage3Selection
)
from backend.services.base_service import BaseService

logger = logging.getLogger(__name__)


class LearningPathwayService(BaseService):
    """Lean service for learning pathway generation"""
    
    def start_pathway_generation(self, course_id: str, user_id: str, 
                               complexity_level: str = "intermediate", 
                               additional_info: str = "") -> str:
        """Start pathway generation (Stage 3) - Triggers Celery task"""
        try:
            # Save user input to database
            db = get_db_session()
            try:
                stage3_input = Stage3Input(
                    course_id=course_id,
                    complexity_level=complexity_level,
                    additional_instructions=additional_info
                )
                db.merge(stage3_input)
                db.commit()
                
                # Trigger Celery task using base class method
                task_id = self.trigger_celery_task(
                    'backend.worker.tasks.stage3_pathway_building',
                    [user_id, course_id, {
                        "complexity_level": complexity_level,
                        "additional_instructions": additional_info
                    }]
                )
                
                logger.info(f"Started pathway generation for course {course_id}, task {task_id}")
                return task_id
                
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to start pathway generation: {e}")
            raise
    
    def get_pathways(self, course_id: str) -> Dict[str, Any]:
        """Get generated pathways from database"""
        db = get_db_session()
        try:
            # Get pathways for this course
            pathways = db.query(Pathway).filter(Pathway.course_id == course_id).all()
            
            pathway_list = []
            for i, pathway in enumerate(pathways):
                # Get modules for this pathway
                modules = db.query(Module).filter(
                    Module.pathway_id == pathway.id
                ).order_by(Module.sequence_order).all()
                
                module_list = []
                for module in modules:
                    import json
                    module_list.append({
                        "id": module.id,
                        "title": module.title,
                        "description": module.description,
                        "sequence_order": module.sequence_order,
                        "learning_objectives": json.loads(module.learning_objectives) if module.learning_objectives else [],
                        "documents": json.loads(module.documents) if module.documents else [],  # Add document paths
                        "estimated_time": module.estimated_time,
                        "theme": "General"  # Add theme field that frontend expects
                    })
                
                pathway_list.append({
                    "id": pathway.id,
                    "index": i,
                    "title": pathway.title,
                    "description": pathway.description,
                    "complexity_level": pathway.complexity_level,  # Keep original field
                    "complexity": pathway.complexity_level,  # Add mapped field for frontend
                    "estimated_duration": pathway.estimated_duration,
                    "prerequisites": pathway.prerequisites,
                    "module_count": len(module_list),
                    "modules": module_list,
                    "created_at": pathway.created_at.isoformat() if pathway.created_at else None
                })
            
            return {
                "pathways": pathway_list,
                "total_pathways": len(pathway_list),
                "total_documents": sum(len(module.get("documents", [])) for pathway in pathway_list for module in pathway.get("modules", [])),
                "repo_name": "Documentation"  # You might want to get this from course metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to get pathways: {e}")
            return {"error": str(e)}
        finally:
            db.close()
    
    def update_pathway(self, course_id: str, pathway_id: str, title: str = None, 
                      description: str = None, complexity_level: str = None, 
                      estimated_duration: str = None) -> bool:
        """Update pathway details"""
        db = get_db_session()
        try:
            pathway = db.query(Pathway).filter(
                Pathway.id == pathway_id,
                Pathway.course_id == course_id
            ).first()
            
            if not pathway:
                return False
            
            if title:
                pathway.title = title
            if description:
                pathway.description = description
            if complexity_level:
                pathway.complexity_level = complexity_level
            if estimated_duration:
                pathway.estimated_duration = estimated_duration
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update pathway: {e}")
            return False
        finally:
            db.close()
    
    def get_pathway_selection(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Get user's pathway selection from database"""
        db = get_db_session()
        try:
            selection = db.query(Stage3Selection).filter(Stage3Selection.course_id == course_id).first()
            if not selection:
                return None
            
            # Get the selected pathway details
            pathway = db.query(Pathway).filter(Pathway.id == selection.selected_pathway_id).first()
            
            return {
                "selected_pathway_id": selection.selected_pathway_id,
                "pathway_title": pathway.title if pathway else "Unknown",
                "selected_at": selection.selected_at.isoformat() if selection.selected_at else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get pathway selection: {e}")
            return None
        finally:
            db.close()
    
    def get_stage3_input(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Get Stage 3 user input from database"""
        db = get_db_session()
        try:
            input_data = db.query(Stage3Input).filter(Stage3Input.course_id == course_id).first()
            if not input_data:
                return None
            
            return {
                "complexity_level": input_data.complexity_level,
                "additional_instructions": input_data.additional_instructions,
                "created_at": input_data.created_at.isoformat() if input_data.created_at else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get Stage 3 input: {e}")
            return None
        finally:
            db.close()
    
    def get_task_status(self, course_id: str) -> Dict[str, Any]:
        """Get task status from database"""
        return super().get_task_status(course_id, 'stage3')

    def update_module(self, course_id: str, pathway_id: str, module_id: str, 
                     title: str = None, description: str = None, 
                     learning_objectives: List[str] = None,
                     linked_documents: List[str] = None,
                     theme: str = None,
                     target_complexity: str = None) -> bool:
        """Update module details"""
        db = get_db_session()
        try:
            # Verify the pathway belongs to the course
            pathway = db.query(Pathway).filter(
                Pathway.id == pathway_id,
                Pathway.course_id == course_id
            ).first()
            
            if not pathway:
                return False
            
            # Find the module
            module = db.query(Module).filter(
                Module.id == module_id,
                Module.pathway_id == pathway_id
            ).first()
            
            if not module:
                return False
            
            # Update fields
            if title:
                module.title = title
            if description:
                module.description = description
            if learning_objectives is not None:
                import json
                module.learning_objectives = json.dumps(learning_objectives)
            if linked_documents is not None:
                import json
                module.documents = json.dumps(linked_documents)
            # Note: theme and target_complexity are not stored in the current Module model
            # They would need to be added as columns if needed
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update module: {e}")
            return False
        finally:
            db.close()
    
    def add_module(self, course_id: str, pathway_id: str, title: str, 
                  description: str, learning_objectives: List[str] = None, 
                  linked_documents: List[str] = None, theme: str = None, 
                  target_complexity: str = None) -> bool:
        """Add new module to pathway"""
        db = get_db_session()
        try:
            # Verify the pathway belongs to the course
            pathway = db.query(Pathway).filter(
                Pathway.id == pathway_id,
                Pathway.course_id == course_id
            ).first()
            
            if not pathway:
                return False
            
            # Get next sequence order
            max_order = db.query(Module.sequence_order).filter(
                Module.pathway_id == pathway_id
            ).order_by(Module.sequence_order.desc()).first()
            
            next_order = (max_order[0] + 1) if max_order else 0
            
            # Create new module
            import json
            new_module = Module(
                pathway_id=pathway_id,
                title=title,
                description=description,
                sequence_order=next_order,
                learning_objectives=json.dumps(learning_objectives or []),
                documents=json.dumps(linked_documents or [])  # Use linked_documents if provided
            )
            
            db.add(new_module)
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to add module: {e}")
            return False
        finally:
            db.close()
    
    def delete_module(self, course_id: str, pathway_id: str, module_id: str) -> bool:
        """Delete module from pathway"""
        db = get_db_session()
        try:
            # Verify the pathway belongs to the course
            pathway = db.query(Pathway).filter(
                Pathway.id == pathway_id,
                Pathway.course_id == course_id
            ).first()
            
            if not pathway:
                return False
            
            # Find and delete the module
            module = db.query(Module).filter(
                Module.id == module_id,
                Module.pathway_id == pathway_id
            ).first()
            
            if not module:
                return False
            
            db.delete(module)
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete module: {e}")
            return False
        finally:
            db.close()
    
    def rearrange_modules(self, course_id: str, pathway_id: str, module_order: List[int]) -> bool:
        """Rearrange modules in a pathway according to new order"""
        db = get_db_session()
        try:
            # Verify the pathway belongs to the course
            pathway = db.query(Pathway).filter(
                Pathway.id == pathway_id,
                Pathway.course_id == course_id
            ).first()
            
            if not pathway:
                return False
            
            # Get all modules for this pathway
            modules = db.query(Module).filter(
                Module.pathway_id == pathway_id
            ).order_by(Module.sequence_order).all()
            
            if len(module_order) != len(modules):
                logger.error(f"Module order length ({len(module_order)}) doesn't match modules count ({len(modules)})")
                return False
            
            # Validate that module_order contains valid indices
            if not all(0 <= idx < len(modules) for idx in module_order):
                logger.error(f"Invalid module order indices: {module_order}")
                return False
            
            # Update sequence_order for each module according to new order
            for new_position, old_position in enumerate(module_order):
                module = modules[old_position]
                module.sequence_order = new_position
            
            db.commit()
            logger.info(f"Successfully reordered modules for pathway {pathway_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to rearrange modules: {e}")
            return False
        finally:
            db.close() 