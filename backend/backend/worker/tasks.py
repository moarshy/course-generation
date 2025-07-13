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
    CourseGenerationStage, Stage3Input as Stage3InputModel, Stage4Input,
    ComplexityLevel, DocumentAnalysis, Stage1Response
)
from backend.shared.utils import get_n_words
# Database operations for the 4-service architecture
from backend.shared.database import (
    init_database, get_db_session, update_task_progress, update_course_status,
    save_repository_files, Course, RepositoryFile, Stage1Selection, Stage2Input,
    AnalyzedDocument, Stage3Input as Stage3InputDB, Pathway, Module, Stage3Selection, 
    GeneratedCourse as DBGeneratedCourse, ModuleContent
)
# All stage processors from agents directory
from backend.worker.agents.s1_repo_cloner import process_stage1
from backend.worker.agents.s2_document_analyzer import process_stage2
from backend.worker.agents.s3_learning_pathway_generator import process_stage3, LearningPath, Stage2Result, LearningModule
from backend.worker.agents.s4_course_generator import process_stage4, Stage3Result
from backend.core.config import settings
from backend.services.repository_clone_service import RepositoryCloneService

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
        # Update existing course record
        course = db.query(Course).filter(Course.course_id == course_id).first()
        if course:
            course.repo_name = stage1_result.get('repo_name', '')
            course.repo_path = stage1_result.get('repo_path', '') 
            course.status = 'stage1_complete'
            course.updated_at = datetime.utcnow()
        else:
            logger.error(f"Course {course_id} not found in database - cannot save Stage 1 data")
            return
        
        # Save repository files
        available_files = stage1_result.get('available_files', [])
        available_folders = stage1_result.get('available_folders', [])
        
        if available_files or available_folders:
            # Clear existing files
            db.query(RepositoryFile).filter(RepositoryFile.course_id == course_id).delete()
            
            # Add files
            for file_path in available_files:
                repo_file = RepositoryFile(
                    course_id=course_id,
                    file_path=file_path,
                    file_type='file',
                    is_documentation=file_path.endswith(('.md', '.mdx', '.txt', '.rst')),
                    is_overview_candidate=any(keyword in file_path.lower() for keyword in ['readme', 'overview', 'intro', 'getting-started'])
                )
                db.add(repo_file)
            
            # Add folders
            for folder_path in available_folders:
                repo_file = RepositoryFile(
                    course_id=course_id,
                    file_path=folder_path,
                    file_type='folder',
                    is_documentation=False,
                    is_overview_candidate=False
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

def load_stage1_data(course_id: str) -> Optional[dict]:
    """Load Stage 1 data from database"""
    db = get_db_session()
    try:
        course = db.query(Course).filter(Course.course_id == course_id).first()
        if not course:
            return None
        
        # Load repository files
        repo_files = db.query(RepositoryFile).filter(RepositoryFile.course_id == course_id).all()
        
        # Separate files and folders
        available_files = [f.file_path for f in repo_files if f.file_type == 'file']
        available_folders = [f.file_path for f in repo_files if f.file_type == 'folder']
        
        # Find overview documents
        overview_candidates = [f.file_path for f in repo_files if f.is_overview_candidate and f.file_type == 'file']
        
        # Create dict result that matches what process_stage2 expects
        result = {
            "repo_name": course.repo_name or '',
            "repo_url": course.repo_url,
            "repo_path": course.repo_path or '',
            "available_folders": available_folders,
            "available_files": available_files,
            "suggested_overview_docs": overview_candidates,
            "all_overview_candidates": available_files,  # All available files
            "total_files": len(available_files)
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to load Stage 1 data: {e}")
        return None
    finally:
        db.close()

def save_stage2_data(course_id: str, stage2_result):
    """Save Stage 2 analyzed documents to database with improved transaction handling"""
    db = get_db_session()
    try:
        # Update existing documents instead of deleting them to preserve IDs
        if 'document_analyses' in stage2_result:
            for doc_analysis in stage2_result['document_analyses']:
                file_path = doc_analysis.get('file_path', '')
                
                # Find existing document by file path
                existing_doc = db.query(AnalyzedDocument).filter(
                    AnalyzedDocument.course_id == course_id,
                    AnalyzedDocument.file_path == file_path
                ).first()
                
                # Robust data validation with defaults
                doc_type = doc_analysis.get('doc_type')
                if doc_type is None or doc_type == '' or doc_type == 'None':
                    doc_type = 'guide'  # Default fallback
                    logger.warning(f"Document {file_path} had invalid doc_type, setting to 'guide'")
                
                complexity_level = doc_analysis.get('complexity_level')
                if complexity_level is None or complexity_level == '' or complexity_level == 'None':
                    complexity_level = 'intermediate'  # Default fallback
                    logger.warning(f"Document {file_path} had invalid complexity_level, setting to 'intermediate'")
                
                title = doc_analysis.get('title')
                if title is None or title == '' or title == 'None':
                    # Extract filename as fallback title
                    title = Path(file_path).stem if file_path else 'Untitled Document'
                    logger.warning(f"Document {file_path} had invalid title, setting to '{title}'")
                
                if existing_doc:
                    # Update existing document (preserve ID and any user edits)
                    existing_doc.title = title
                    existing_doc.doc_type = doc_type
                    existing_doc.complexity_level = complexity_level
                    # Only update AI-generated fields, preserve user edits
                    if not existing_doc.key_concepts or existing_doc.key_concepts == '[]':
                        existing_doc.key_concepts = json.dumps(doc_analysis.get('key_concepts', []))
                    if not existing_doc.learning_objectives or existing_doc.learning_objectives == '[]':
                        existing_doc.learning_objectives = json.dumps(doc_analysis.get('learning_objectives', []))
                    if not existing_doc.summary:
                        existing_doc.summary = doc_analysis.get('semantic_summary', '')
                    existing_doc.prerequisites = json.dumps(doc_analysis.get('prerequisites', []))
                    existing_doc.related_topics = json.dumps(doc_analysis.get('related_topics', []))
                    existing_doc.headings = json.dumps(doc_analysis.get('headings', []))
                    existing_doc.code_languages = json.dumps(doc_analysis.get('code_languages', []))
                    existing_doc.frontmatter = json.dumps(doc_analysis.get('frontmatter', {}))
                    existing_doc.doc_metadata = json.dumps(doc_analysis.get('metadata', {}))
                    existing_doc.word_count = doc_analysis.get('word_count', 0)
                    existing_doc.analyzed_at = datetime.utcnow()
                else:
                    # Create new document
                    analyzed_doc = AnalyzedDocument(
                        course_id=course_id,
                        file_path=file_path,
                        title=title,
                        doc_type=doc_type,
                        complexity_level=complexity_level,
                        key_concepts=json.dumps(doc_analysis.get('key_concepts', [])),
                        learning_objectives=json.dumps(doc_analysis.get('learning_objectives', [])),
                        summary=doc_analysis.get('semantic_summary', ''),
                        prerequisites=json.dumps(doc_analysis.get('prerequisites', [])),
                        related_topics=json.dumps(doc_analysis.get('related_topics', [])),
                        headings=json.dumps(doc_analysis.get('headings', [])),
                        code_languages=json.dumps(doc_analysis.get('code_languages', [])),
                        frontmatter=json.dumps(doc_analysis.get('frontmatter', {})),
                        doc_metadata=json.dumps(doc_analysis.get('metadata', {})),
                        word_count=doc_analysis.get('word_count', 0)
                    )
                    db.add(analyzed_doc)
        
        # Commit all documents first
        db.commit()
        logger.info(f"Saved {len(stage2_result.get('document_analyses', []))} analyzed documents to database for course {course_id}")
        
        # Update course status in a separate transaction to ensure documents are fully committed
        course = db.query(Course).filter(Course.course_id == course_id).first()
        if course:
            course.status = 'stage2_complete'
            course.updated_at = datetime.utcnow()
            db.commit()
            logger.info(f"Updated course {course_id} status to stage2_complete")
        
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
        
        if not analyzed_docs:
            logger.error(f"No analyzed documents found for course {course_id}")
            return None
        
        # Convert to document analyses list for agents
        document_analyses = []
        for doc in analyzed_docs:
            # Robust data validation with defaults during loading
            doc_type = doc.doc_type
            if doc_type is None or doc_type == '' or doc_type == 'None':
                doc_type = 'guide'  # Default fallback
                logger.warning(f"Document {doc.file_path} had invalid doc_type in database, using 'guide'")
            
            complexity_level = doc.complexity_level
            if complexity_level is None or complexity_level == '' or complexity_level == 'None':
                complexity_level = 'intermediate'  # Default fallback
                logger.warning(f"Document {doc.file_path} had invalid complexity_level in database, using 'intermediate'")
            
            title = doc.title
            if title is None or title == '' or title == 'None':
                title = Path(doc.file_path).stem if doc.file_path else 'Untitled Document'
                logger.warning(f"Document {doc.file_path} had invalid title in database, using '{title}'")
            
            try:
                doc_analysis = DocumentAnalysis(
                    file_path=doc.file_path or '',
                    title=title,
                    doc_type=doc_type,
                    complexity_level=complexity_level,
                    key_concepts=json.loads(doc.key_concepts) if doc.key_concepts else [],
                    learning_objectives=json.loads(doc.learning_objectives) if doc.learning_objectives else [],
                    semantic_summary=doc.summary or '',
                    prerequisites=json.loads(doc.prerequisites) if doc.prerequisites else [],
                    related_topics=json.loads(doc.related_topics) if doc.related_topics else [],
                    headings=json.loads(doc.headings) if doc.headings else [],
                    code_languages=json.loads(doc.code_languages) if doc.code_languages else [],
                    frontmatter=json.loads(doc.frontmatter) if doc.frontmatter else {},
                    word_count=doc.word_count or 0,
                    metadata=json.loads(doc.doc_metadata) if doc.doc_metadata else {}
                )
                document_analyses.append(doc_analysis)
            except Exception as e:
                logger.error(f"Failed to create DocumentAnalysis for {doc.file_path}: {e}")
                # Skip this document but continue with others
                continue
        
        if not document_analyses:
            logger.error(f"Failed to load any valid documents for course {course_id}")
            return None
        
        return Stage2Result(
            document_analyses=document_analyses,
            overview_context=""  # We can add this if stored separately
        )
        
    except Exception as e:
        logger.error(f"Failed to load Stage 2 data: {e}")
        return None
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
                            learning_objectives=json.dumps(getattr(module, 'learning_objectives', [])),
                            documents=json.dumps(getattr(module, 'documents', []))
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

def load_stage3_data(course_id: str):
    """Load Stage 3 data from database and reconstruct Stage3Result object"""
    db = get_db_session()
    try:
        # Load pathways and modules
        pathways = db.query(Pathway).filter(Pathway.course_id == course_id).all()
        
        if not pathways:
            logger.warning(f"No pathways found for course {course_id}")
            return None
            
        # Reconstruct learning paths
        learning_paths = []
        for pathway in pathways:
            # Load modules for this pathway
            modules = db.query(Module).filter(Module.pathway_id == pathway.id).order_by(Module.sequence_order).all()
            
            # Convert modules to LearningModule objects
            learning_modules = []
            for module in modules:
                learning_objectives = json.loads(module.learning_objectives) if module.learning_objectives else []
                documents = json.loads(module.documents) if module.documents else []
                
                learning_module = LearningModule(
                    module_id=module.id,
                    title=module.title,
                    description=module.description,
                    documents=documents,  # Now properly restored from database
                    learning_objectives=learning_objectives
                )
                learning_modules.append(learning_module)
            
            # Convert to LearningPath object
            learning_path = LearningPath(
                path_id=pathway.id,
                title=pathway.title,
                description=pathway.description,
                target_complexity=ComplexityLevel(pathway.complexity_level) if pathway.complexity_level else ComplexityLevel.INTERMEDIATE,
                modules=learning_modules
            )
            learning_paths.append(learning_path)
        
        # Load Stage 2 data (document analyses)
        stage2_result = load_stage2_data(course_id)
        
        if not stage2_result:
            logger.warning(f"No Stage 2 data found for course {course_id}")
            stage2_result = Stage2Result(document_analyses=[], overview_context="")
        
        # Create Stage2Result object
        stage2_result_obj = stage2_result
        
        # Determine target complexity from the first pathway
        target_complexity = learning_paths[0].target_complexity if learning_paths else ComplexityLevel.INTERMEDIATE
        
        # Create Stage3Result object
        stage3_result = Stage3Result(
            learning_paths=learning_paths,
            target_complexity=target_complexity,
            stage2_result=stage2_result_obj
        )
        
        logger.info(f"Loaded Stage 3 data: {len(learning_paths)} pathways with {sum(len(path.modules) for path in learning_paths)} total modules")
        return stage3_result
        
    except Exception as e:
        logger.error(f"Failed to load Stage 3 data: {e}")
        return None
    finally:
        db.close()

def save_stage4_data(course_id: str, stage4_result):
    """Save Stage 4 results to database"""
    db = get_db_session()
    try:
        # Save generated course record
        generated_course = DBGeneratedCourse(
            course_id=course_id,
            pathway_id=stage4_result.stage3_result.learning_paths[0].path_id if stage4_result.stage3_result.learning_paths else None,
            export_path="",  # Will be set when exported
            status='completed' if stage4_result.successful_generations > 0 else 'failed'
        )
        db.merge(generated_course)
        
        # Save module content for each generated module
        for module_content in stage4_result.generated_content:
            db_module_content = ModuleContent(
                module_id=module_content.module_id,
                introduction=module_content.introduction,
                main_content=module_content.main_content,
                conclusion=module_content.conclusion,
                assessment=module_content.assessment,
                summary=module_content.summary
            )
            db.merge(db_module_content)
        
        # Update course status
        course = db.query(Course).filter(Course.course_id == course_id).first()
        if course:
            course.status = 'stage4_complete' if stage4_result.successful_generations > 0 else 'stage4_failed'
            course.updated_at = datetime.utcnow()
        
        db.commit()
        logger.info(f"Saved Stage 4 data: {len(stage4_result.generated_content)} modules generated")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save Stage 4 data: {e}")
        raise
    finally:
        db.close()

@app.task(bind=True)
def stage1_clone_repository(self, user_id: str, course_id: str, repo_url: str) -> Dict[str, Any]:
    """Stage 1: Clone repository and analyze structure - Updated to use database"""
    try:
        logger.info(f"Starting Stage 1 for course {course_id}: cloning {repo_url}")
        
        # Initialize database and update course record
        init_database()
        db = get_db_session()
        try:
            # Update existing course record (should already exist from project creation)
            course = db.query(Course).filter(Course.course_id == course_id).first()
            if course:
                course.repo_url = repo_url
                course.status = 'stage1_running'
                course.updated_at = datetime.utcnow()
                db.commit()
            else:
                logger.warning(f"Course {course_id} not found in database - task may have been triggered incorrectly")
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
        
        # Load Stage 1 selections from database
        repo_service = RepositoryCloneService()
        stage1_selections = repo_service.get_stage1_selections(course_id)
        
        if not stage1_selections:
            raise ValueError(f"Stage 1 selections not found for course {course_id}. Please complete Stage 1 selections first.")
        
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
        
        # Combine Stage 1 selections with Stage 2 input for process_stage2
        combined_user_input = {
            'include_folders': stage1_selections['selected_folders'],
            'overview_doc': stage1_selections['overview_document'],
            'complexity_level': user_input.get('complexity_level', 'intermediate'),
            'additional_info': user_input.get('additional_info', '')
        }
        
        # Update task progress
        update_task_progress(course_id, 'stage2', self.request.id, 'STARTED', 20, "Processing documents")
        
        # Call the stage processor
        stage2_result = process_stage2(
            stage1_result=stage1_result,
            user_input=combined_user_input,
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
            stage3_input = Stage3InputModel(**user_input)
        else:
            stage3_input = Stage3InputModel()
        
        # Save user input to database
        db = get_db_session()
        try:
            stage3_db_input = Stage3InputDB(
                course_id=course_id,
                complexity_level=stage3_input.complexity_level,
                additional_instructions=stage3_input.additional_instructions or ''
            )
            db.merge(stage3_db_input)
            db.commit()
        finally:
            db.close()
        
        logger.info(f"Stage 3 input: complexity_level={stage3_input.complexity_level}, additional_instructions={stage3_input.additional_instructions}")
        
        # Load Stage 2 result from database instead of pickle
        stage2_result = load_stage2_data(course_id)
        
        if not stage2_result or not stage2_result.document_analyses:
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
            redis_client=redis_client,
            course_id=course_id
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
        
        # Load Stage 3 result from database
        update_task_progress(course_id, 'stage4', self.request.id, 'STARTED', 10, "Loading Stage 3 data")
        stage3_result = load_stage3_data(course_id)
        
        if not stage3_result:
            raise ValueError(f"Stage 3 result not found for course {course_id}")
        
        # Call the real Stage 4 agent
        update_task_progress(course_id, 'stage4', self.request.id, 'STARTED', 20, "Starting course content generation")
        
        stage4_result = process_stage4(
            stage3_result=stage3_result,
            additional_instructions=getattr(stage4_input, 'additional_instructions', ''),
            task_id=self.request.id,
            redis_client=redis_client
        )
        
        if not stage4_result or stage4_result.successful_generations == 0:
            raise ValueError("No course content generated")
        
        # Save stage result to database
        update_task_progress(course_id, 'stage4', self.request.id, 'STARTED', 90, "Saving generated content")
        save_stage4_data(course_id, stage4_result)
        
        # Update task progress
        update_task_progress(course_id, 'stage4', self.request.id, 'SUCCESS', 100, "Course generation complete")
        update_course_status(course_id, 'stage4_complete')
        
        logger.info(f"Stage 4 completed for course {course_id}: {stage4_result.successful_generations} modules generated")
        
        return {
            'success': True,
            'stage': CourseGenerationStage.COURSE_GENERATION.value,
            'result': stage4_result.model_dump(),
            'course_summary': {
                'title': 'Generated Course',
                'description': 'Course content generated successfully',
                'module_count': stage4_result.successful_generations,
                'export_path': ''  # Will be set when exported
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