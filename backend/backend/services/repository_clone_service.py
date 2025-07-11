"""
RepositoryCloneService - Service 1 of 4

Responsibility: Repository analysis and file discovery
- Triggers Celery task for repository cloning
- Manages Stage 1 user selections
- Database-driven, no pickle files
"""

import logging
from typing import List, Dict, Any, Optional

from backend.shared.database import (
    get_db_session, Course, RepositoryFile, Stage1Selection
)
from backend.services.base_service import BaseService

logger = logging.getLogger(__name__)


class RepositoryCloneService(BaseService):
    """Lean service for repository cloning and analysis"""
    
    def start_repository_analysis(self, course_id: str, user_id: str, repo_url: str) -> str:
        """Start repository analysis (Stage 1) - Triggers Celery task"""
        try:
            # Create course record in database
            db = get_db_session()
            try:
                course = Course(
                    course_id=course_id,
                    user_id=user_id,
                    repo_url=repo_url,
                    status='stage1_running'
                )
                db.merge(course)
                db.commit()
                
                # Trigger Celery task using base class method
                task_id = self.trigger_celery_task(
                    'backend.worker.tasks.stage1_clone_repository',
                    [user_id, course_id, repo_url]
                )
                
                logger.info(f"Started repository analysis for course {course_id}, task {task_id}")
                return task_id
                
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to start repository analysis: {e}")
            raise
    
    def get_repository_files(self, course_id: str) -> Dict[str, Any]:
        """Get repository files from database"""
        db = get_db_session()
        try:
            # Get course info
            course = db.query(Course).filter(Course.course_id == course_id).first()
            if not course:
                return {"error": "Course not found"}
            
            # Get repository files
            files = db.query(RepositoryFile).filter(RepositoryFile.course_id == course_id).all()
            
            # Organize into folders and files
            folders = []
            file_list = []
            overview_candidates = []
            
            for file in files:
                if file.file_type == 'folder':
                    folders.append(file.file_path)
                else:
                    file_list.append(file.file_path)
                    if file.is_overview_candidate:
                        overview_candidates.append(file.file_path)
            
            return {
                "repo_name": course.repo_name or "Unknown",
                "available_folders": folders,
                "available_files": file_list,
                "suggested_overview_docs": overview_candidates[:3],  # Top 3
                "all_overview_candidates": overview_candidates,
                "total_files": len(file_list)
            }
            
        except Exception as e:
            logger.error(f"Failed to get repository files: {e}")
            return {"error": str(e)}
        finally:
            db.close()
    
    def save_stage1_selections(self, course_id: str, selected_folders: List[str], 
                             overview_document: str = None) -> bool:
        """Save Stage 1 user selections to database"""
        db = get_db_session()
        try:
            import json
            
            selection = Stage1Selection(
                course_id=course_id,
                selected_folders=json.dumps(selected_folders),
                overview_document=overview_document
            )
            db.merge(selection)
            db.commit()
            
            logger.info(f"Saved Stage 1 selections for course {course_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save Stage 1 selections: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def get_stage1_selections(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Get Stage 1 user selections from database"""
        db = get_db_session()
        try:
            selection = db.query(Stage1Selection).filter(Stage1Selection.course_id == course_id).first()
            if not selection:
                return None
            
            import json
            return {
                "selected_folders": json.loads(selection.selected_folders),
                "overview_document": selection.overview_document,
                "selected_at": selection.selected_at.isoformat() if selection.selected_at else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get Stage 1 selections: {e}")
            return None
        finally:
            db.close()
    
    def get_task_status(self, course_id: str) -> Dict[str, Any]:
        """Get task status from database"""
        return super().get_task_status(course_id, 'stage1') 