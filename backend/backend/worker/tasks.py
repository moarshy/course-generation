import os
import logging
from celery import Celery
from typing import List, Optional, Dict, Any
from pathlib import Path
import dspy
from dotenv import load_dotenv
import redis
import json
from datetime import datetime

from backend.shared.models import (
    CourseGenerationStage, Stage3Input, Stage4Input,
    ComplexityLevel, DocumentAnalysis
)
from backend.shared.utils import get_n_words
# Database operations for the 4-service architecture
from backend.shared.database import (
    init_database, get_db_session, update_task_progress, update_course_status,
    save_repository_files, Course, RepositoryFile, Stage1Selection, Stage2Input,
    AnalyzedDocument, Stage3Input, Pathway, Module, Stage3Selection, 
    GeneratedCourse as DBGeneratedCourse, ModuleContent
)
# All stage processors from agents directory
from backend.worker.agents.s1_repo_cloner import process_stage1
from backend.worker.agents.s2_document_analyzer import process_stage2
from backend.worker.agents.s3_learning_pathway_generator import process_stage3
from backend.worker.agents.s4_course_generator import process_stage4
from backend.core.config import settings

# Load environment variables
load_dotenv()

# Configure DSPy using centralized settings
dspy.configure(lm=dspy.LM(
    settings.MODEL_NAME, 
    cache=settings.MODEL_CACHE_ENABLED, 
    max_tokens=settings.MODEL_MAX_TOKENS, 
    temperature=settings.MODEL_TEMPERATURE
))

# Configure Celery
app = Celery('course_generator')
app.config_from_object({
    'broker_url': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    'result_backend': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'UTC',
    'enable_utc': True,
})

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Filter out noisy LiteLLM logs
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("litellm").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

##### Clients #####
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

##### ALL CONFIGURATION IS HERE #####
OVERVIEW_DOC_MAX_WORDS = 10000

# Replace StageDataManager with database operations
def save_stage1_data(course_id: str, stage1_result):
    """Save Stage 1 data to database"""
    db = get_db_session()
    try:
        # Create course record if it doesn't exist
        course = db.query(Course).filter(Course.course_id == course_id).first()
        if not course:
            # This shouldn't happen, but create if missing
            course = Course(
                course_id=course_id,
                user_id="unknown",  # Should be passed properly
                repo_url=getattr(stage1_result, 'repo_url', ''),
                repo_name=getattr(stage1_result, 'repo_name', ''),
                status='stage1_complete'
            )
            db.add(course)
        else:
            course.repo_name = getattr(stage1_result, 'repo_name', '')
            course.status = 'stage1_complete'
        
        # Save repository files
        if hasattr(stage1_result, 'files') and stage1_result.files:
            # Clear existing files
            db.query(RepositoryFile).filter(RepositoryFile.course_id == course_id).delete()
            
            # Add new files
            for file_info in stage1_result.files:
                repo_file = RepositoryFile(
                    course_id=course_id,
                    file_path=getattr(file_info, 'path', str(file_info)),
                    file_type='file',  # Assume file for now
                    is_documentation=getattr(file_info, 'is_documentation', False),
                    is_overview_candidate=getattr(file_info, 'is_overview_candidate', False)
                )
                db.add(repo_file)
        
        db.commit()
        logger.info(f"Saved Stage 1 data to database for course {course_id}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save Stage 1 data: {e}")
        raise
    finally:
        db.close()

def load_stage1_data(course_id: str):
    """Load Stage 1 data from database"""
    db = get_db_session()
    try:
        course = db.query(Course).filter(Course.course_id == course_id).first()
        if not course:
            return None
        
        # For now, return a simple object that the existing code can use
        # You may need to adjust this based on what process_stage2 expects
        class Stage1Result:
            def __init__(self):
                self.repo_url = course.repo_url
                self.repo_name = course.repo_name
                self.repo_path = ""  # May need to be set properly
                self.files = []
        
        result = Stage1Result()
        return result
        
    except Exception as e:
        logger.error(f"Failed to load Stage 1 data: {e}")
        return None
    finally:
        db.close()

def save_stage2_data(course_id: str, stage2_result):
    """Save Stage 2 analyzed documents to database"""
    db = get_db_session()
    try:
        # Clear existing analyzed documents
        db.query(AnalyzedDocument).filter(AnalyzedDocument.course_id == course_id).delete()
        
        # Save analyzed documents
        if hasattr(stage2_result, 'document_analyses'):
            for doc_analysis in stage2_result.document_analyses:
                analyzed_doc = AnalyzedDocument(
                    course_id=course_id,
                    file_path=doc_analysis.file_path,
                    title=doc_analysis.title,
                    doc_type=doc_analysis.doc_type,
                    key_concepts=json.dumps(doc_analysis.key_concepts) if hasattr(doc_analysis, 'key_concepts') else None,
                    learning_objectives=json.dumps(doc_analysis.learning_objectives) if hasattr(doc_analysis, 'learning_objectives') else None,
                    summary=doc_analysis.semantic_summary if hasattr(doc_analysis, 'semantic_summary') else None,
                    word_count=getattr(doc_analysis, 'word_count', 0)
                )
                db.add(analyzed_doc)
        
        # Update course status
        course = db.query(Course).filter(Course.course_id == course_id).first()
        if course:
            course.status = 'stage2_complete'
            course.updated_at = datetime.utcnow()
        
        db.commit()
        logger.info(f"Saved Stage 2 data to database for course {course_id}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save Stage 2 data: {e}")
        raise
    finally:
        db.close()

def load_stage2_data(course_id: str):
    """Load Stage 2 data from database"""
    db = get_db_session()
    try:
        analyzed_docs = db.query(AnalyzedDocument).filter(AnalyzedDocument.course_id == course_id).all()
        
        # Convert to document analyses list for agents
        document_analyses = []
        for doc in analyzed_docs:
            doc_analysis = DocumentAnalysis(
                file_path=doc.file_path,
                title=doc.title,
                doc_type=doc.doc_type,
                complexity_level=doc.complexity_level or 'intermediate',
                key_concepts=json.loads(doc.key_concepts) if doc.key_concepts else [],
                learning_objectives=json.loads(doc.learning_objectives) if doc.learning_objectives else [],
                semantic_summary=doc.summary or '',
                prerequisites=[],
                related_topics=[]
            )
            document_analyses.append(doc_analysis)
        
        return document_analyses
        
    except Exception as e:
        logger.error(f"Failed to load Stage 2 data: {e}")
        return []
    finally:
        db.close()

def save_stage3_data(course_id: str, stage3_result):
    """Save Stage 3 pathways to database"""
    db = get_db_session()
    try:
        # Clear existing pathways for this course
        db.query(Pathway).filter(Pathway.course_id == course_id).delete()
        
        # Save pathways and modules
        if hasattr(stage3_result, 'learning_paths'):
            for learning_path in stage3_result.learning_paths:
                pathway = Pathway(
                    course_id=course_id,
                    title=learning_path.title,
                    description=learning_path.description,
                    complexity_level=getattr(learning_path, 'target_complexity', 'intermediate'),
                    estimated_duration=getattr(learning_path, 'estimated_duration', '')
                )
                db.add(pathway)
                db.flush()  # To get the pathway ID
                
                # Save modules
                if hasattr(learning_path, 'modules'):
                    for i, module in enumerate(learning_path.modules):
                        db_module = Module(
                            pathway_id=pathway.id,
                            title=module.title,
                            description=module.description,
                            sequence_order=i,
                            learning_objectives=json.dumps(getattr(module, 'learning_objectives', []))
                        )
                        db.add(db_module)
        
        # Update course status
        course = db.query(Course).filter(Course.course_id == course_id).first()
        if course:
            course.status = 'stage3_complete'
            course.updated_at = datetime.utcnow()
        
        db.commit()
        logger.info(f"Saved Stage 3 data to database for course {course_id}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save Stage 3 data: {e}")
        raise
    finally:
        db.close()

@app.task(bind=True)
def stage1_clone_repository(self, user_id: str, course_id: str, repo_url: str) -> Dict[str, Any]:
    """Stage 1: Clone repository and analyze structure - Updated to use database"""
    try:
        logger.info(f"Starting Stage 1 for course {course_id}: cloning {repo_url}")
        
        # Initialize database and create course record
        init_database()
        db = get_db_session()
        try:
            # Create course record
            course = Course(
                course_id=course_id,
                user_id=user_id,
                repo_url=repo_url,
                status='stage1_running'
            )
            db.merge(course)  # Use merge to handle existing records
            db.commit()
        finally:
            db.close()
        
        # Update task progress
        update_task_progress(course_id, 'stage1', self.request.id, 'STARTED', 0, "Starting repository analysis")
        
        stage1_result = process_stage1(
            repo_url, 
            user_id=user_id, 
            course_id=course_id, 
            task_id=self.request.id, 
            redis_client=redis_client
        )
        
        # Save to database instead of pickle file
        save_stage1_data(course_id, stage1_result)
        
        # Update task progress
        update_task_progress(course_id, 'stage1', self.request.id, 'SUCCESS', 100, "Repository analysis complete")
        update_course_status(course_id, 'stage1_complete')
        
        logger.info(f"Stage 1 completed for course {course_id}")

        return {
            'success': True,
            'stage': CourseGenerationStage.CLONE_REPO.value,
            'result': stage1_result,
            'next_stage': CourseGenerationStage.DOCUMENT_ANALYSIS.value
        }
        
    except Exception as e:
        logger.error(f"Stage 1 failed for course {course_id}: {str(e)}")
        update_task_progress(course_id, 'stage1', self.request.id, 'FAILURE', 0, error_msg=str(e))
        update_course_status(course_id, 'stage1_failed')
        return {
            'success': False,
            'stage': CourseGenerationStage.CLONE_REPO.value,
            'error': str(e)
        }



# convert_stage2_to_document_tree function removed - DocumentTree model no longer exists

@app.task(bind=True)
def stage2_document_analysis(self, user_id: str, course_id: str, user_input: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 2 - Document analysis - Updated to use database"""
    try:
        logger.info(f"Starting Stage 2 document analysis for course {course_id}")
        
        # Update task progress
        update_task_progress(course_id, 'stage2', self.request.id, 'STARTED', 0, "Loading Stage 1 data")
        
        # Load Stage 1 result from database instead of pickle
        stage1_result = load_stage1_data(course_id)
        
        if not stage1_result:
            raise ValueError(f"Stage 1 result not found for course {course_id}")
        
        # Save user input to database
        db = get_db_session()
        try:
            stage2_input = Stage2Input(
                course_id=course_id,
                complexity_level=user_input.get('complexity_level', 'intermediate'),
                additional_info=user_input.get('additional_info', '')
            )
            db.merge(stage2_input)
            db.commit()
        finally:
            db.close()
        
        # Update task progress
        update_task_progress(course_id, 'stage2', self.request.id, 'STARTED', 20, "Processing documents")
        
        # Call the stage processor
        stage2_result = process_stage2(
            stage1_result=stage1_result,
            user_input=user_input,
            task_id=self.request.id,
            redis_client=redis_client,
            course_id=course_id
        )
        
        # Save Stage2Result to database instead of pickle
        save_stage2_data(course_id, stage2_result)
        
        # Update task progress
        update_task_progress(course_id, 'stage2', self.request.id, 'SUCCESS', 100, "Document analysis complete")
        update_course_status(course_id, 'stage2_complete')
        
        logger.info(f"Stage 2 completed for course {course_id}")
        return {
            'success': True,
            'stage': CourseGenerationStage.DOCUMENT_ANALYSIS.value,
            'result': stage2_result
        }
        
    except Exception as e:
        logger.error(f"Stage 2 failed for course {course_id}: {str(e)}")
        update_task_progress(course_id, 'stage2', self.request.id, 'FAILURE', 0, error_msg=str(e))
        update_course_status(course_id, 'stage2_failed')
        return {
            'success': False,
            'stage': CourseGenerationStage.DOCUMENT_ANALYSIS.value,
            'error': str(e)
        }

@app.task(bind=True)
def stage3_pathway_building(self, user_id: str, course_id: str, user_input: Dict[str, Any] = None) -> Dict[str, Any]:
    """Stage 3: Generate learning pathways - Updated to use database"""
    try:
        logger.info(f"Starting Stage 3 pathway building for course {course_id}")
        
        # Update task progress
        update_task_progress(course_id, 'stage3', self.request.id, 'STARTED', 0, "Loading previous stage data")
        
        # Parse user input
        if user_input:
            stage3_input = Stage3Input(**user_input)
        else:
            stage3_input = Stage3Input()
        
        # Save user input to database
        db = get_db_session()
        try:
            stage3_db_input = Stage3Input(
                course_id=course_id,
                additional_info=stage3_input.additional_instructions or ''
            )
            db.merge(stage3_db_input)
            db.commit()
        finally:
            db.close()
        
        logger.info(f"Stage 3 input: complexity_level={stage3_input.complexity_level}, additional_instructions={stage3_input.additional_instructions}")
        
        # Load Stage 2 result from database instead of pickle
        stage2_result = load_stage2_data(course_id)
        
        if not stage2_result:
            raise ValueError(f"Stage 2 result not found for course {course_id}")
        
        # Update task progress
        update_task_progress(course_id, 'stage3', self.request.id, 'STARTED', 30, "Generating learning pathways")
        
        # Determine target complexity
        try:
            target_complexity = ComplexityLevel(stage3_input.complexity_level.lower())
        except ValueError:
            logger.warning(f"Invalid complexity level: {stage3_input.complexity_level}, defaulting to intermediate")
            target_complexity = ComplexityLevel.INTERMEDIATE
        
        # Call the new Stage 3 agent
        stage3_result = process_stage3(
            stage2_result=stage2_result,
            target_complexity=target_complexity,
            additional_instructions=stage3_input.additional_instructions,
            task_id=self.request.id,
            redis_client=redis_client
        )
        
        if not stage3_result or not stage3_result.learning_paths:
            raise ValueError("No learning paths generated")
        
        # Save stage result to database instead of pickle
        save_stage3_data(course_id, stage3_result)
        
        # Update task progress
        update_task_progress(course_id, 'stage3', self.request.id, 'SUCCESS', 100, "Pathway generation complete")
        update_course_status(course_id, 'stage3_complete')
        
        # Prepare response with pathway summaries
        pathway_summaries = []
        for i, path in enumerate(stage3_result.learning_paths):
            pathway_summaries.append({
                'index': i,
                'title': path.title,
                'description': path.description,
                'complexity': path.target_complexity.value,
                'module_count': len(path.modules),
                'modules': [{'title': m.title, 'theme': getattr(m, 'theme', 'General'), 'description': m.description} for m in path.modules]
            })
        
        logger.info(f"Stage 3 completed for course {course_id}: {len(stage3_result.learning_paths)} pathways generated")
        return {
            'success': True,
            'stage': CourseGenerationStage.PATHWAY_BUILDING.value,
            'result': stage3_result.model_dump(),
            'pathways': pathway_summaries,
            'next_stage': CourseGenerationStage.COURSE_GENERATION.value
        }
        
    except Exception as e:
        logger.error(f"Stage 3 failed for course {course_id}: {str(e)}")
        
        # Update progress with error
        update_task_progress(course_id, 'stage3', self.request.id, 'FAILURE', 0, error_msg=str(e))
        update_course_status(course_id, 'stage3_failed')
        
        return {
            'success': False,
            'stage': CourseGenerationStage.PATHWAY_BUILDING.value,
            'error': str(e)
        }

# generate_course_with_progress function removed - using process_stage4 from agents instead

@app.task(bind=True)
def stage4_course_generation(self, user_id: str, course_id: str, user_input: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 4: Generate final course content using agents/process_stage4"""
    try:
        logger.info(f"Starting Stage 4 for course {course_id}: course generation")
        
        # Update task progress
        update_task_progress(course_id, 'stage4', self.request.id, 'STARTED', 0, "Initializing course generation")
        
        # Parse user input
        stage4_input = Stage4Input(**user_input)
        logger.info(f"Stage 4 input: {stage4_input}")
        
        # For now, return success with minimal data since stage4 is not fully implemented in the agents
        # TODO: Implement proper stage4 with process_stage4 when needed
        
        update_task_progress(course_id, 'stage4', self.request.id, 'SUCCESS', 100, "Stage 4 placeholder completed")
        update_course_status(course_id, 'stage4_complete')
        
        logger.info(f"Stage 4 completed for course {course_id} (placeholder)")
        
        return {
            'success': True,
            'stage': CourseGenerationStage.COURSE_GENERATION.value,
            'result': {'placeholder': True},
            'course_summary': {
                'title': 'Generated Course',
                'description': 'Course content generated successfully',
                'module_count': 0,
                'export_path': ''
            }
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Stage 4 failed for course {course_id}: {str(e)}")
        
        # Update progress with error
        update_task_progress(course_id, 'stage4', self.request.id, 'FAILURE', 0, error_msg=str(e))
        update_course_status(course_id, 'stage4_failed')
        
        return {
            'success': False,
            'stage': CourseGenerationStage.COURSE_GENERATION.value,
            'error': str(e),
            'traceback': traceback.format_exc()
        }

# Helper task for getting stage status - Updated to use database
@app.task
def get_stage_status(user_id: str, course_id: str, stage: str) -> Dict[str, Any]:
    """Get the status and data for a specific stage from database"""
    try:
        db = get_db_session()
        try:
            # Get task status from database
            from backend.shared.database import CourseTask
            task = db.query(CourseTask).filter(
                CourseTask.course_id == course_id,
                CourseTask.stage == stage
            ).first()
            
            if not task:
                return {
                    'exists': False,
                    'stage': stage,
                    'status': 'not_started'
                }
            
            return {
                'exists': True,
                'stage': stage,
                'status': task.status,
                'progress': task.progress_percentage,
                'current_step': task.current_step,
                'error_message': task.error_message
            }
            
        finally:
            db.close()
        
    except Exception as e:
        return {
            'exists': False,
            'stage': stage,
            'error': str(e)
        } 