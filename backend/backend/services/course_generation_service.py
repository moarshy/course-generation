import redis
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from celery import Celery
from backend.core.config import settings
from shared.models import (
    CourseGenerationStage, GenerationStatus, GenerationTaskStatus,
    Stage1Response, Stage2Response, Stage3Response, Stage4Response,
    Stage2Input, Stage3Input, Stage4Input, PathwaySummary, CourseSummary, DocumentSummary,
    DocumentMetadataUpdate, ModuleUpdate, ModuleCreate, PathwayUpdate, ModuleSummary
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
                'worker.tasks.stage1_clone_repository',
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
                all_overview_candidates=stage1_data.get('all_overview_candidates', stage1_data['suggested_overview_docs']),  # Fallback for backward compatibility
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
                'worker.tasks.stage2_document_analysis',
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
    
    def get_stage2_result(self, course_id: str) -> Optional['Stage2Response']:
        """Get Stage 2 results - Document analysis"""
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
            
            stage2_data = result['result']
            
            # Load the actual document tree to get analyzed documents
            analyzed_documents = []
            try:
                import pickle
                import sys
                import os
                from pathlib import Path
                
                user_id = task_info['user_id']
                
                # Add worker path to sys.path so pickle can import the required modules
                file_path = Path(__file__).resolve()
                root_path = file_path.parent.parent.parent.parent
                worker_path = root_path / "worker"
                original_path = sys.path.copy()

                logger.info(f"Worker path: {worker_path}")
                
                # if worker_path not in sys.path:
                #     sys.path.insert(0, worker_path)
                sys.path.append(worker_path)

                # Construct the path to stage files
                safe_user_id = user_id.replace('|', '_').replace('/', '_')
                base_data_dir = Path("../data")
                course_dir = base_data_dir / safe_user_id / course_id
                
                document_tree_file = course_dir / "document_analysis.pkl"
                
                if document_tree_file.exists():
                    logger.info(f"Loading DocumentTree from {document_tree_file}")
                    
                    # Load the document tree
                    with open(document_tree_file, 'rb') as f:
                        document_tree = pickle.load(f)
                    
                    logger.info(f"Successfully loaded document tree with {len(document_tree.nodes)} nodes")
                    
                    # Convert document nodes to frontend format
                    for path, node in document_tree.nodes.items():
                        doc_summary = DocumentSummary(
                            id=node.id,
                            filename=node.filename,
                            path=node.path,
                            content=node.content[:500] + '...' if len(node.content) > 500 else node.content,
                            metadata={
                                'title': node.metadata.title,
                                'doc_type': node.metadata.doc_type.value if hasattr(node.metadata.doc_type, 'value') else str(node.metadata.doc_type),
                                'key_concepts': node.metadata.key_concepts,
                                'learning_objectives': node.metadata.learning_objectives,
                                'semantic_summary': node.metadata.semantic_summary,
                                'headings': node.metadata.headings,
                                'code_blocks': len(node.metadata.code_blocks) if node.metadata.code_blocks else 0,
                                'primary_language': node.metadata.primary_language
                            }
                        )
                        analyzed_documents.append(doc_summary)
                        
                    logger.info(f"Successfully loaded {len(analyzed_documents)} analyzed documents for course {course_id}")
                else:
                    logger.warning(f"Document tree file not found: {document_tree_file}")
                
                # Restore original sys.path
                sys.path = original_path
                
            except Exception as e:
                # Restore original sys.path on error
                if 'original_path' in locals():
                    sys.path = original_path
                logger.error(f"Failed to load document tree for course {course_id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Return basic info without documents if loading fails
                pass
            
            # Return document analysis data for the frontend with safe field access
            return Stage2Response(
                processed_files_count=stage2_data.get('processed_files_count', len(analyzed_documents)),
                failed_files_count=stage2_data.get('failed_files_count', 0),
                include_folders=stage2_data.get('include_folders', []),
                overview_doc=stage2_data.get('overview_doc'),
                analysis_timestamp=stage2_data.get('analysis_timestamp', datetime.utcnow().isoformat()),
                analyzed_documents=analyzed_documents
            )
            
        except Exception as e:
            logger.error(f"Failed to get Stage 2 result for course {course_id}: {e}")
            return None
    
    def start_stage3(self, user_id: str, course_id: str) -> str:
        """Start Stage 3 - Pathway Building"""
        try:
            # Generate new task ID
            task_id = str(uuid.uuid4())
            
            # Send task to worker
            task = self.celery_app.send_task(
                'worker.tasks.stage3_pathway_building',
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
    
    def get_stage3_result(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Get Stage 3 results"""
        try:
            task_info = self._get_task_info(course_id)
            if not task_info:
                return None
            
            user_id = task_info['user_id']
            
            # Try to load from saved paths file first
            try:
                import pickle
                import sys
                from pathlib import Path
                
                # Add worker path to sys.path
                file_path = Path(__file__).resolve()
                root_path = file_path.parent.parent.parent.parent
                worker_path = root_path / "worker"
                original_path = sys.path.copy()
                sys.path.append(str(worker_path))
                
                try:
                    # Construct path to learning paths file
                    safe_user_id = user_id.replace('|', '_').replace('/', '_')
                    base_data_dir = Path("../data")
                    course_dir = base_data_dir / safe_user_id / course_id
                    learning_paths_file = course_dir / "pathway_building_paths.pkl"
                    
                    if learning_paths_file.exists():
                        # Load learning paths from file
                        with open(learning_paths_file, 'rb') as f:
                            paths_data = pickle.load(f)
                            learning_paths = paths_data['paths']
                        
                        # Convert to PathwaySummary objects
                        pathways = []
                        for i, path in enumerate(learning_paths):
                            # For each pathway, include full module data with learning objectives and linked documents
                            full_modules = []
                            for m in path.modules:
                                # Create a dictionary with full module data (not just summary)
                                module_data = {
                                    'module_id': getattr(m, 'module_id', f'module-{i}-{len(full_modules)}'),
                                    'title': m.title,
                                    'description': m.description,
                                    'theme': m.theme,
                                    'target_complexity': m.target_complexity.value if hasattr(m.target_complexity, 'value') else str(m.target_complexity),
                                    'learning_objectives': getattr(m, 'learning_objectives', []),
                                    'linked_documents': getattr(m, 'linked_documents', [])
                                }
                                full_modules.append(module_data)
                            
                            pathways.append({
                                'index': i,
                                'title': path.title,
                                'description': path.description,
                                'complexity': path.target_complexity.value if hasattr(path.target_complexity, 'value') else str(path.target_complexity),
                                'module_count': len(path.modules),
                                'modules': full_modules  # Use full module data instead of ModuleSummary
                            })
                        
                        return {
                            'pathways': pathways,
                            'total_documents': paths_data['document_tree_summary'].get('total_documents', 0),
                            'repo_name': paths_data['document_tree_summary'].get('repo_name', 'Unknown')
                        }
                finally:
                    # Restore original sys.path
                    sys.path = original_path
                    
            except Exception as e:
                logger.warning(f"Could not load from paths file, falling back to Celery result: {e}")
            
            # Fall back to loading from Celery result
            celery_result = self.celery_app.AsyncResult(task_info['task_id'])
            
            if celery_result.state != 'SUCCESS':
                return None
            
            result = celery_result.result
            if not result.get('success'):
                return None
            
            pathways_data = result['pathways']
            
            return {
                'pathways': pathways_data,
                'total_documents': result.get('total_documents', 0),
                'repo_name': result.get('repo_name', 'Unknown')
            }
            
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
                'worker.tasks.stage4_course_generation',
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
    
    def update_document_metadata(self, course_id: str, document_id: str, metadata_updates: DocumentMetadataUpdate) -> bool:
        """Update metadata for a specific document in the document tree"""
        try:
            task_info = self._get_task_info(course_id)
            if not task_info:
                logger.error(f"No task info found for course {course_id}")
                return False
            
            user_id = task_info['user_id']
            
            # Load the document tree
            import pickle
            import sys
            from pathlib import Path
            
            # Add worker path to sys.path
            file_path = Path(__file__).resolve()
            root_path = file_path.parent.parent.parent.parent
            worker_path = root_path / "worker"
            original_path = sys.path.copy()
            sys.path.append(worker_path)
            
            try:
                # Construct path to document tree file
                safe_user_id = user_id.replace('|', '_').replace('/', '_')
                base_data_dir = Path("../data")
                course_dir = base_data_dir / safe_user_id / course_id
                document_tree_file = course_dir / "document_analysis.pkl"
                
                if not document_tree_file.exists():
                    logger.error(f"Document tree file not found: {document_tree_file}")
                    return False
                
                # Load document tree
                with open(document_tree_file, 'rb') as f:
                    document_tree = pickle.load(f)
                
                # Find and update the document
                document_found = False
                for path, node in document_tree.nodes.items():
                    if node.id == document_id:
                        # Update metadata fields that were provided
                        if metadata_updates.doc_type is not None:
                            node.metadata.doc_type = metadata_updates.doc_type
                        if metadata_updates.semantic_summary is not None:
                            node.metadata.semantic_summary = metadata_updates.semantic_summary
                        if metadata_updates.key_concepts is not None:
                            node.metadata.key_concepts = metadata_updates.key_concepts
                        if metadata_updates.learning_objectives is not None:
                            node.metadata.learning_objectives = metadata_updates.learning_objectives
                        
                        document_found = True
                        logger.info(f"Updated metadata for document {document_id}")
                        break
                
                if not document_found:
                    logger.error(f"Document with ID {document_id} not found in document tree")
                    return False
                
                # Save updated document tree back to file
                with open(document_tree_file, 'wb') as f:
                    pickle.dump(document_tree, f)
                
                logger.info(f"Successfully updated document tree for course {course_id}")
                return True
                
            finally:
                # Restore original sys.path
                sys.path = original_path
                
        except Exception as e:
            logger.error(f"Failed to update document metadata for course {course_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def update_pathway(self, course_id: str, pathway_index: int, pathway_updates: PathwayUpdate) -> bool:
        """Update pathway details"""
        try:
            task_info = self._get_task_info(course_id)
            if not task_info:
                logger.error(f"No task info found for course {course_id}")
                return False
            
            user_id = task_info['user_id']
            
            # Load the learning paths
            import pickle
            import sys
            from pathlib import Path
            
            # Add worker path to sys.path
            file_path = Path(__file__).resolve()
            root_path = file_path.parent.parent.parent.parent
            worker_path = root_path / "worker"
            original_path = sys.path.copy()
            sys.path.append(str(worker_path))
            
            try:
                # Construct path to learning paths file
                safe_user_id = user_id.replace('|', '_').replace('/', '_')
                base_data_dir = Path("../data")
                course_dir = base_data_dir / safe_user_id / course_id
                learning_paths_file = course_dir / "pathway_building_paths.pkl"
                
                if not learning_paths_file.exists():
                    logger.error(f"Learning paths file not found: {learning_paths_file}")
                    return False
                
                # Load learning paths
                with open(learning_paths_file, 'rb') as f:
                    paths_data = pickle.load(f)
                    learning_paths = paths_data['paths']
                
                # Validate pathway index
                if pathway_index < 0 or pathway_index >= len(learning_paths):
                    logger.error(f"Invalid pathway index {pathway_index}")
                    return False
                
                # Update pathway fields
                pathway = learning_paths[pathway_index]
                if pathway_updates.title is not None:
                    pathway.title = pathway_updates.title
                if pathway_updates.description is not None:
                    pathway.description = pathway_updates.description
                if pathway_updates.target_complexity is not None:
                    pathway.target_complexity = pathway_updates.target_complexity
                if pathway_updates.estimated_duration is not None:
                    pathway.estimated_duration = pathway_updates.estimated_duration
                if pathway_updates.prerequisites is not None:
                    pathway.prerequisites = pathway_updates.prerequisites
                
                # Save updated learning paths back to file
                paths_data['paths'] = learning_paths
                with open(learning_paths_file, 'wb') as f:
                    pickle.dump(paths_data, f)
                
                logger.info(f"Successfully updated pathway {pathway_index} for course {course_id}")
                return True
                
            finally:
                # Restore original sys.path
                sys.path = original_path
                
        except Exception as e:
            logger.error(f"Failed to update pathway for course {course_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def update_module(self, course_id: str, pathway_index: int, module_index: int, module_updates: ModuleUpdate) -> bool:
        """Update a specific module in a pathway"""
        try:
            task_info = self._get_task_info(course_id)
            if not task_info:
                logger.error(f"No task info found for course {course_id}")
                return False
            
            user_id = task_info['user_id']
            
            # Load the learning paths
            import pickle
            import sys
            from pathlib import Path
            
            # Add worker path to sys.path
            file_path = Path(__file__).resolve()
            root_path = file_path.parent.parent.parent.parent
            worker_path = root_path / "worker"
            original_path = sys.path.copy()
            sys.path.append(str(worker_path))
            
            try:
                # Construct path to learning paths file
                safe_user_id = user_id.replace('|', '_').replace('/', '_')
                base_data_dir = Path("../data")
                course_dir = base_data_dir / safe_user_id / course_id
                learning_paths_file = course_dir / "learning_pathways.pkl"
                
                if not learning_paths_file.exists():
                    logger.error(f"Learning paths file not found: {learning_paths_file}")
                    return False
                
                # Load learning paths
                with open(learning_paths_file, 'rb') as f:
                    learning_paths = pickle.load(f)
                
                # Validate indices
                if pathway_index < 0 or pathway_index >= len(learning_paths):
                    logger.error(f"Invalid pathway index {pathway_index}")
                    return False
                
                pathway = learning_paths[pathway_index]
                if module_index < 0 or module_index >= len(pathway.modules):
                    logger.error(f"Invalid module index {module_index}")
                    return False
                
                # Update module fields
                module = pathway.modules[module_index]
                if module_updates.title is not None:
                    module.title = module_updates.title
                if module_updates.description is not None:
                    module.description = module_updates.description
                if module_updates.learning_objectives is not None:
                    module.learning_objectives = module_updates.learning_objectives
                if module_updates.linked_documents is not None:
                    module.linked_documents = module_updates.linked_documents
                if module_updates.theme is not None:
                    module.theme = module_updates.theme
                if module_updates.target_complexity is not None:
                    module.target_complexity = module_updates.target_complexity
                
                # Save updated learning paths back to file
                paths_data['paths'] = learning_paths
                with open(learning_paths_file, 'wb') as f:
                    pickle.dump(paths_data, f)
                
                logger.info(f"Successfully updated module {module_index} in pathway {pathway_index} for course {course_id}")
                return True
                
            finally:
                # Restore original sys.path
                sys.path = original_path
                
        except Exception as e:
            logger.error(f"Failed to update module for course {course_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def create_module(self, course_id: str, pathway_index: int, module_data: ModuleCreate) -> bool:
        """Create a new module in a pathway"""
        try:
            task_info = self._get_task_info(course_id)
            if not task_info:
                logger.error(f"No task info found for course {course_id}")
                return False
            
            user_id = task_info['user_id']
            
            # Load the learning paths
            import pickle
            import sys
            from pathlib import Path
            
            # Add worker path to sys.path
            file_path = Path(__file__).resolve()
            root_path = file_path.parent.parent.parent.parent
            worker_path = root_path / "worker"
            original_path = sys.path.copy()
            sys.path.append(str(worker_path))
            
            try:
                # Import required classes
                from worker.course_content_agent.models import LearningModule, AssessmentPoint
                
                # Construct path to learning paths file
                safe_user_id = user_id.replace('|', '_').replace('/', '_')
                base_data_dir = Path("../data")
                course_dir = base_data_dir / safe_user_id / course_id
                learning_paths_file = course_dir / "learning_pathways.pkl"
                
                if not learning_paths_file.exists():
                    logger.error(f"Learning paths file not found: {learning_paths_file}")
                    return False
                
                # Load learning paths
                with open(learning_paths_file, 'rb') as f:
                    learning_paths = pickle.load(f)
                
                # Validate pathway index
                if pathway_index < 0 or pathway_index >= len(learning_paths):
                    logger.error(f"Invalid pathway index {pathway_index}")
                    return False
                
                pathway = learning_paths[pathway_index]
                
                # Create new module ID
                existing_ids = [m.module_id for m in pathway.modules]
                new_id = f"module_{len(pathway.modules) + 1:02d}"
                while new_id in existing_ids:
                    new_id = f"module_{len(existing_ids) + 1:02d}"
                
                # Create assessment for new module
                assessment = AssessmentPoint(
                    assessment_id=f"{new_id}_assessment",
                    title=f"{module_data.title} Assessment",
                    concepts_to_assess=[module_data.theme.lower()]
                )
                
                # Create new module
                new_module = LearningModule(
                    module_id=new_id,
                    title=module_data.title,
                    description=module_data.description,
                    learning_objectives=module_data.learning_objectives,
                    linked_documents=module_data.linked_documents,
                    theme=module_data.theme,
                    target_complexity=module_data.target_complexity,
                    assessment=assessment
                )
                
                # Add module to pathway
                pathway.modules.append(new_module)
                
                # Save updated learning paths back to file
                paths_data['paths'] = learning_paths
                with open(learning_paths_file, 'wb') as f:
                    pickle.dump(paths_data, f)
                
                logger.info(f"Successfully created new module in pathway {pathway_index} for course {course_id}")
                return True
                
            finally:
                # Restore original sys.path
                sys.path = original_path
                
        except Exception as e:
            logger.error(f"Failed to create module for course {course_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def delete_module(self, course_id: str, pathway_index: int, module_index: int) -> bool:
        """Delete a module from a pathway"""
        try:
            task_info = self._get_task_info(course_id)
            if not task_info:
                logger.error(f"No task info found for course {course_id}")
                return False
            
            user_id = task_info['user_id']
            
            # Load the learning paths
            import pickle
            import sys
            from pathlib import Path
            
            # Add worker path to sys.path
            file_path = Path(__file__).resolve()
            root_path = file_path.parent.parent.parent.parent
            worker_path = root_path / "worker"
            original_path = sys.path.copy()
            sys.path.append(str(worker_path))
            
            try:
                # Construct path to learning paths file
                safe_user_id = user_id.replace('|', '_').replace('/', '_')
                base_data_dir = Path("../data")
                course_dir = base_data_dir / safe_user_id / course_id
                learning_paths_file = course_dir / "learning_pathways.pkl"
                
                if not learning_paths_file.exists():
                    logger.error(f"Learning paths file not found: {learning_paths_file}")
                    return False
                
                # Load learning paths
                with open(learning_paths_file, 'rb') as f:
                    learning_paths = pickle.load(f)
                
                # Validate indices
                if pathway_index < 0 or pathway_index >= len(learning_paths):
                    logger.error(f"Invalid pathway index {pathway_index}")
                    return False
                
                pathway = learning_paths[pathway_index]
                if module_index < 0 or module_index >= len(pathway.modules):
                    logger.error(f"Invalid module index {module_index}")
                    return False
                
                # Remove module from pathway
                removed_module = pathway.modules.pop(module_index)
                
                # Save updated learning paths back to file
                paths_data['paths'] = learning_paths
                with open(learning_paths_file, 'wb') as f:
                    pickle.dump(paths_data, f)
                
                logger.info(f"Successfully deleted module '{removed_module.title}' from pathway {pathway_index} for course {course_id}")
                return True
                
            finally:
                # Restore original sys.path
                sys.path = original_path
                
        except Exception as e:
            logger.error(f"Failed to delete module for course {course_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def reorder_modules(self, course_id: str, pathway_index: int, module_order: list[int]) -> bool:
        """Reorder modules in a pathway"""
        try:
            task_info = self._get_task_info(course_id)
            if not task_info:
                logger.error(f"No task info found for course {course_id}")
                return False
            
            user_id = task_info['user_id']
            
            # Load the learning paths
            import pickle
            import sys
            from pathlib import Path
            
            # Add worker path to sys.path
            file_path = Path(__file__).resolve()
            root_path = file_path.parent.parent.parent.parent
            worker_path = root_path / "worker"
            original_path = sys.path.copy()
            sys.path.append(str(worker_path))
            
            try:
                # Construct path to learning paths file
                safe_user_id = user_id.replace('|', '_').replace('/', '_')
                base_data_dir = Path("../data")
                course_dir = base_data_dir / safe_user_id / course_id
                learning_paths_file = course_dir / "learning_pathways.pkl"
                
                if not learning_paths_file.exists():
                    logger.error(f"Learning paths file not found: {learning_paths_file}")
                    return False
                
                # Load learning paths
                with open(learning_paths_file, 'rb') as f:
                    learning_paths = pickle.load(f)
                
                # Validate pathway index
                if pathway_index < 0 or pathway_index >= len(learning_paths):
                    logger.error(f"Invalid pathway index {pathway_index}")
                    return False
                
                pathway = learning_paths[pathway_index]
                
                # Validate module order
                if len(module_order) != len(pathway.modules):
                    logger.error(f"Module order length ({len(module_order)}) doesn't match modules count ({len(pathway.modules)})")
                    return False
                
                if sorted(module_order) != list(range(len(pathway.modules))):
                    logger.error(f"Invalid module order: {module_order}")
                    return False
                
                # Reorder modules
                original_modules = pathway.modules.copy()
                pathway.modules = [original_modules[i] for i in module_order]
                
                # Save updated learning paths back to file
                paths_data['paths'] = learning_paths
                with open(learning_paths_file, 'wb') as f:
                    pickle.dump(paths_data, f)
                
                logger.info(f"Successfully reordered modules in pathway {pathway_index} for course {course_id}")
                return True
                
            finally:
                # Restore original sys.path
                sys.path = original_path
                
        except Exception as e:
            logger.error(f"Failed to reorder modules for course {course_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False 