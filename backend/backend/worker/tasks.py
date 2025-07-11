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
    CourseGenerationStage, 
    Stage2Result, Stage3Result, Stage4Result, Stage3UserInput, Stage4UserInput,
    ComplexityLevel, DocumentTree, LearningPath, GeneratedCourse,
    DocumentMetadata, DocumentNode, DocumentAnalysis
)
from backend.shared.utils import StageDataManager
from backend.worker.course_content_agent.modules import LearningPathGenerator, CourseGenerator, CourseExporter
from backend.worker.agents.s1_repo_cloner import process_stage1
from backend.worker.agents.s2_document_analyzer import process_stage2
from backend.worker.agents.s3_learning_pathway_generator import process_stage3
from backend.core.config import settings

# Load environment variables
load_dotenv()

# Configure DSPy
dspy.configure(lm=dspy.LM("gemini/gemini-2.5-flash", cache=False, max_tokens=20000, temperature=0.))

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

def get_n_words(text: str, max_words: int) -> int:
    """Truncate text to max_words words."""
    return " ".join(text.split()[:max_words])

def get_stage_manager(user_id: str, course_id: str) -> StageDataManager:
    """Get a stage data manager for a specific user and course."""
    base_dir = Path(settings.ROOT_DATA_DIR) / user_id.replace('|', '_').replace('/', '_')
    return StageDataManager(base_dir, course_id)



@app.task(bind=True)
def stage1_clone_repository(self, user_id: str, course_id: str, repo_url: str) -> Dict[str, Any]:
    """Stage 1: Clone repository and analyze structure"""
    try:
        logger.info(f"Starting Stage 1 for course {course_id}: cloning {repo_url}")
        
        stage1_result = process_stage1(
            repo_url, 
            user_id=user_id, 
            course_id=course_id, 
            task_id=self.request.id, 
            redis_client=redis_client
        )
        
        logger.info(f"Stage 1 completed for course {course_id}")

        stage_manager = get_stage_manager(user_id, course_id)
        stage_manager.save_stage_data(
            CourseGenerationStage.CLONE_REPO, 
            stage1_result,
        )

        return {
            'success': True,
            'stage': CourseGenerationStage.CLONE_REPO.value,
            'result': stage1_result.model_dump(),
            'next_stage': CourseGenerationStage.DOCUMENT_ANALYSIS.value
        }
        
    except Exception as e:
        logger.error(f"Stage 1 failed for course {course_id}: {str(e)}")
        return {
            'success': False,
            'stage': CourseGenerationStage.CLONE_REPO.value,
            'error': str(e)
        }



def convert_stage2_to_document_tree(stage2_result: Stage2Result, stage1_result) -> DocumentTree:
    """Convert Stage2Result to DocumentTree format expected by frontend"""
    try:        
        # Create document nodes from document analyses
        nodes = {}
        repo_path = Path(stage1_result.repo_path)
        
        for doc_analysis in stage2_result.document_analyses:
            # Read the document content
            try:
                with open(doc_analysis.file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                logger.warning(f"Could not read content for {doc_analysis.file_path}: {e}")
                content = f"Content unavailable: {e}"
            
            # Convert absolute path to relative path from repo directory
            try:
                doc_path = Path(doc_analysis.file_path).resolve()
                repo_path_resolved = Path(repo_path).resolve()
                
                # Try to make it relative to repo_path
                relative_path = doc_path.relative_to(repo_path_resolved)
                relative_path_str = str(relative_path)
                
                logger.debug(f"Converted {doc_analysis.file_path} -> {relative_path_str}")
                
            except ValueError as e:
                # If we can't make it relative, use just the filename
                relative_path_str = Path(doc_analysis.file_path).name
                logger.warning(f"Could not make path relative: {doc_analysis.file_path}, using filename: {relative_path_str}. Error: {e}")
            
            # Create document metadata
            metadata = DocumentMetadata(
                title=doc_analysis.title,
                doc_type=doc_analysis.doc_type,
                key_concepts=doc_analysis.key_concepts,
                learning_objectives=doc_analysis.learning_objectives,
                semantic_summary=doc_analysis.semantic_summary,
                headings=doc_analysis.headings,
                code_blocks=[],  # Could extract from code_languages if needed
                frontmatter=getattr(doc_analysis, 'frontmatter', {}),
                primary_language=doc_analysis.code_languages[0] if doc_analysis.code_languages else None
            )
            
            # Create document node with relative path
            node = DocumentNode(
                id=relative_path_str,  
                path=relative_path_str,
                filename=Path(relative_path_str).name,
                content=content,
                metadata=metadata,
                parent_path=None  # Could set this if needed
            )
            
            # Use relative path as the key
            nodes[relative_path_str] = node
        
        # Create document tree
        document_tree = DocumentTree(
            repo_url=getattr(stage1_result, 'repo_url', ''),
            repo_name=stage1_result.repo_name,
            root_path=stage1_result.repo_path,
            nodes=nodes,
            tree_structure={},  # Could build this if needed
            cross_references={},  # Could analyze cross-references if needed
            last_updated=datetime.utcnow(),
            document_categories={},  # Could categorize by doc_type if needed
            complexity_distribution={},  # Could build from complexity_level if needed
            learning_paths=[]  # Will be populated in Stage 3
        )
        
        logger.info(f"Created DocumentTree with {len(nodes)} nodes using relative paths")
        return document_tree
        
    except Exception as e:
        logger.error(f"Failed to convert Stage2Result to DocumentTree: {e}")
        raise

@app.task(bind=True)
def stage2_document_analysis(self, user_id: str, course_id: str, user_input: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 2 - Document analysis"""
    try:
        logger.info(f"Starting Stage 2 document analysis for course {course_id}")
        
        # Load Stage 1 result from stage manager
        stage_manager = get_stage_manager(user_id, course_id)
        stage1_result = stage_manager.load_stage_data(CourseGenerationStage.CLONE_REPO)
        
        if not stage1_result:
            raise ValueError(f"Stage 1 result not found for course {course_id}")
        
        # Call the stage processor
        stage2_result = process_stage2(
            stage1_result=stage1_result,
            user_input=user_input,
            task_id=self.request.id,
            redis_client=redis_client,
            course_id=course_id
        )
        
        # Save Stage2Result using stage manager
        stage_manager.save_stage_data(CourseGenerationStage.DOCUMENT_ANALYSIS, stage2_result)
        
        # Convert to DocumentTree format and save separately
        document_tree = convert_stage2_to_document_tree(stage2_result, stage1_result)
        stage_manager.save_stage_data(CourseGenerationStage.DOCUMENT_ANALYSIS, document_tree, suffix="tree")
        
        logger.info(f"Stage 2 completed for course {course_id}")
        return {
            'success': True,
            'stage': CourseGenerationStage.DOCUMENT_ANALYSIS.value,
            'result': stage2_result.model_dump()
        }
        
    except Exception as e:
        logger.error(f"Stage 2 failed for course {course_id}: {str(e)}")
        return {
            'success': False,
            'stage': CourseGenerationStage.DOCUMENT_ANALYSIS.value,
            'error': str(e)
        }

@app.task(bind=True)
def stage3_pathway_building(self, user_id: str, course_id: str, user_input: Dict[str, Any] = None) -> Dict[str, Any]:
    """Stage 3: Generate learning pathways using debate agent"""
    try:
        logger.info(f"Starting Stage 3 pathway building for course {course_id}")
        
        # Parse user input
        if user_input:
            stage3_input = Stage3UserInput(**user_input)
        else:
            stage3_input = Stage3UserInput()
        
        logger.info(f"Stage 3 input: complexity_level={stage3_input.complexity_level}, additional_instructions={stage3_input.additional_instructions}")
        
        # Get stage manager
        stage_manager = get_stage_manager(user_id, course_id)
        
        # Load Stage 2 result from stage manager
        stage2_result = stage_manager.load_stage_data(CourseGenerationStage.DOCUMENT_ANALYSIS)
        
        if not stage2_result:
            raise ValueError(f"Stage 2 result not found for course {course_id}")
        
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
        
        # Save stage result
        stage_manager.save_stage_data(CourseGenerationStage.PATHWAY_BUILDING, stage3_result)
        
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
        try:
            progress_key = f"stage3_progress:{course_id}"
            progress_data = {
                'stage': 'failed',
                'stage_description': f'Pathway generation failed: {str(e)}',
                'error': str(e),
                'updated_at': datetime.now().isoformat()
            }
            redis_client.set(progress_key, json.dumps(progress_data))
        except:
            pass  # Don't let Redis errors mask the original error
        
        return {
            'success': False,
            'stage': CourseGenerationStage.PATHWAY_BUILDING.value,
            'error': str(e)
        }

def generate_course_with_progress(course_generator, pathway, document_tree, overview_context, 
                                 progress_key, redis_client, progress_data):
    """Generate course content with detailed progress tracking"""
    
    logger.info(f"Generating course content for {pathway.title}")
    
    # Update total modules count
    total_modules = len(pathway.modules)
    progress_data.update({
        'total_modules': total_modules,
        'current_step': 'generating_modules',
        'step_progress': 55,
        'updated_at': datetime.now().isoformat()
    })
    redis_client.set(progress_key, json.dumps(progress_data))
    
    # Generate modules with progress tracking
    module_contents = []
    
    for i, module in enumerate(pathway.modules):
        # Update current module being processed
        progress_data.update({
            'current_module': module.title,
            'generated_modules': i,
            'step_progress': 55 + int((i / total_modules) * 25),  # 55-80% for module generation
            'updated_at': datetime.now().isoformat()
        })
        redis_client.set(progress_key, json.dumps(progress_data))
        
        logger.info(f"-> Generating content for module: {module.title}")
        
        # Generate module content (this calls the original method)
        module_content = course_generator._generate_module_content(
            module, pathway, document_tree, overview_context, i
        )
        module_contents.append(module_content)
        
        # Mark module as completed
        progress_data['completed_modules'].append(module.title)
        progress_data.update({
            'generated_modules': i + 1,
            'step_progress': 55 + int(((i + 1) / total_modules) * 25),
            'updated_at': datetime.now().isoformat()
        })
        redis_client.set(progress_key, json.dumps(progress_data))
        
        logger.info(f"✓ Completed module: {module.title}")
    
    # Update progress: generating course conclusion
    progress_data.update({
        'current_module': '',
        'current_step': 'generating_conclusion',
        'step_progress': 80,
        'updated_at': datetime.now().isoformat()
    })
    redis_client.set(progress_key, json.dumps(progress_data))
    
    # Generate course conclusion
    course_conclusion = course_generator._generate_course_conclusion(pathway)
    
    # Create complete course
    course = GeneratedCourse(
        course_id=pathway.pathway_id,
        title=pathway.title,
        description=pathway.description,
        welcome_message=pathway.welcome_message,
        modules=module_contents,
        course_conclusion=course_conclusion
    )
    
    logger.info(f"Generated complete course with {len(module_contents)} modules")
    return course

@app.task(bind=True)
def stage4_course_generation(self, user_id: str, course_id: str, user_input: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 4: Generate final course content"""
    try:
        logger.info(f"Starting Stage 4 for course {course_id}: course generation")
        logger.info(f"Stage 4 user_input: {user_input}")
        
        # Initialize Redis progress tracking
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        progress_key = f"stage4_progress:{course_id}"
        
        # Initialize progress data
        progress_data = {
            'stage': 'initializing',
            'stage_description': 'Setting up course generation...',
            'total_modules': 0,
            'generated_modules': 0,
            'current_module': '',
            'completed_modules': [],
            'current_step': 'loading_data',
            'step_progress': 0,
            'updated_at': datetime.now().isoformat()
        }
        redis_client.set(progress_key, json.dumps(progress_data))
        
        # Parse user input
        stage4_input = Stage4UserInput(**user_input)
        logger.info(f"Stage 4 parsed input: {stage4_input}")
        
        # Get stage manager
        stage_manager = get_stage_manager(user_id, course_id)
        logger.info(f"Stage manager created for user {user_id}, course {course_id}")
        
        # Update progress: loading data
        progress_data.update({
            'stage': 'loading_data',
            'stage_description': 'Loading previous stage data...',
            'step_progress': 10,
            'updated_at': datetime.now().isoformat()
        })
        redis_client.set(progress_key, json.dumps(progress_data))
        
        # Load previous stage data
        logger.info("Loading Stage 3 data...")
        stage3_result = stage_manager.load_stage_data(CourseGenerationStage.PATHWAY_BUILDING)
        logger.info(f"Stage 3 data loaded: {stage3_result is not None}")
        if stage3_result is None:
                raise ValueError("Stage 3 data is None - pathway building data not found")
        
        # Update progress: stage 3 data loaded
        progress_data.update({
            'step_progress': 20,
            'updated_at': datetime.now().isoformat()
        })
        redis_client.set(progress_key, json.dumps(progress_data))
        
        logger.info("Loading Document Tree...")
        document_tree: DocumentTree = stage_manager.load_stage_data(CourseGenerationStage.DOCUMENT_ANALYSIS, suffix="tree")
        logger.info(f"Document tree loaded: {document_tree is not None}")
        if document_tree is None:
            raise ValueError("Document tree is None - document analysis data not found")
        
        # Update progress: document tree loaded
        progress_data.update({
            'step_progress': 30,
            'updated_at': datetime.now().isoformat()
        })
        redis_client.set(progress_key, json.dumps(progress_data))
        
        # Get selected pathway
        logger.info("Getting learning paths...")
        if not stage3_result.learning_paths:
            raise ValueError("No learning paths found in Stage 3 result")
        
        if stage4_input.custom_pathway:
            logger.info("Using custom pathway from input")
            selected_pathway = stage4_input.custom_pathway
        else:
            logger.info("Using first pathway from generated paths")
            selected_pathway = stage3_result.learning_paths[0]
        
        logger.info(f"Selected pathway: {selected_pathway.title}")
        
        # Update progress: pathway selected
        progress_data.update({
            'step_progress': 40,
            'updated_at': datetime.now().isoformat()
        })
        redis_client.set(progress_key, json.dumps(progress_data))
        
        # Get overview context
        logger.info("Getting overview context...")
        overview_context = ""
        if stage3_result.stage2_result and stage3_result.stage2_result.overview_context:
            overview_context = stage3_result.stage2_result.overview_context
            logger.info(f"Overview context loaded: {len(overview_context)} chars")
        else:
            logger.info("No overview context available")
        
        # Update progress: preparing for course generation
        progress_data.update({
            'stage': 'generating_course',
            'stage_description': 'Generating course content with AI...',
            'total_modules': len(selected_pathway.modules) if hasattr(selected_pathway, 'modules') else 0,
            'current_step': 'preparing_generation',
            'step_progress': 50,
            'updated_at': datetime.now().isoformat()
        })
        redis_client.set(progress_key, json.dumps(progress_data))
        
        # Generate course
        logger.info("Generating course...")
        course_generator = CourseGenerator()
        logger.info(f"Course generator created: {course_generator is not None}")
        
        logger.info(f"Calling generate_course with pathway: {selected_pathway.title if hasattr(selected_pathway, 'title') else 'No title'}")
        
        # Create a custom course generator that can track progress
        generated_course = generate_course_with_progress(
            course_generator, selected_pathway, document_tree, overview_context, 
            progress_key, redis_client, progress_data
        )
        
        logger.info(f"Course generated: {generated_course is not None}")
        if generated_course is None:
            raise ValueError("Course generation failed - generated_course is None")
        
        # Update progress: exporting course
        progress_data.update({
            'stage': 'exporting',
            'stage_description': 'Exporting course to markdown files...',
            'current_step': 'exporting',
            'step_progress': 85,
            'updated_at': datetime.now().isoformat()
        })
        redis_client.set(progress_key, json.dumps(progress_data))
        
        # Export course to markdown
        logger.info("Exporting course to markdown...")
        exporter = CourseExporter()
        logger.info(f"Course exporter created: {exporter is not None}")
        
        # Create export directory
        user_dir = Path(settings.ROOT_DATA_DIR) / user_id.replace('|', '_').replace('/', '_') / course_id
        export_dir = user_dir / "generated"
        logger.info(f"Export directory: {export_dir}")
        
        export_success = exporter.export_to_markdown(generated_course, export_dir)
        logger.info(f"Export success: {export_success}")
        
        if not export_success:
            raise ValueError("Failed to export course to markdown")
        
        # Create stage 4 result
        logger.info("Creating Stage 4 result...")
        stage4_result = Stage4Result(
            generated_course_path="",  # Will be set after saving
            export_path=export_dir
        )
        
        # Save generated course
        logger.info("Saving generated course...")
        course_path = stage_manager.save_stage_data(
            CourseGenerationStage.COURSE_GENERATION, generated_course
        )
        stage4_result.generated_course_path = course_path
        logger.info(f"Course saved to: {course_path}")
        
        # Save stage result
        logger.info("Saving stage result...")
        stage_manager.save_stage_data(
            CourseGenerationStage.COURSE_GENERATION, stage4_result
        )
        
        # Final progress update
        progress_data.update({
            'stage': 'completed',
            'stage_description': 'Course generation completed successfully',
            'current_step': 'completed',
            'step_progress': 100,
            'updated_at': datetime.now().isoformat()
        })
        redis_client.set(progress_key, json.dumps(progress_data))
        
        logger.info(f"Stage 4 completed for course {course_id}")
        
        # Clean up progress data after completion
        redis_client.delete(progress_key)
        
        return {
            'success': True,
            'stage': CourseGenerationStage.COURSE_GENERATION.value,
            'result': stage4_result.model_dump(),
            'course_summary': {
                'title': generated_course.title,
                'description': generated_course.description,
                'module_count': len(generated_course.modules),
                'export_path': export_dir
            }
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Stage 4 failed for course {course_id}: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        
        # Update progress with error
        try:
            redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
            progress_key = f"stage4_progress:{course_id}"
            progress_data = {
                'stage': 'failed',
                'stage_description': f'Course generation failed: {str(e)}',
                'error': str(e),
                'updated_at': datetime.now().isoformat()
            }
            redis_client.set(progress_key, json.dumps(progress_data))
        except:
            pass  # Don't let Redis errors mask the original error
        
        return {
            'success': False,
            'stage': CourseGenerationStage.COURSE_GENERATION.value,
            'error': str(e),
            'traceback': traceback.format_exc()
        }

# Helper task for getting stage status
@app.task
def get_stage_status(user_id: str, course_id: str, stage: str) -> Dict[str, Any]:
    """Get the status and data for a specific stage"""
    try:
        stage_enum = CourseGenerationStage(stage)
        stage_manager = get_stage_manager(user_id, course_id)
        
        if not stage_manager.stage_data_exists(stage_enum):
            return {
                'exists': False,
                'stage': stage
            }
        
        # Load stage data based on stage type
        if stage_enum == CourseGenerationStage.CLONE_REPO:
            data = stage_manager.load_stage_data(stage_enum)
            return {
                'exists': True,
                'stage': stage,
                'data': data.model_dump() if hasattr(data, 'model_dump') else data
            }
        # Add other stage types as needed
        
        return {
            'exists': True,
            'stage': stage,
            'data': 'Stage data exists but detailed loading not implemented for this stage'
        }
        
    except Exception as e:
        return {
            'exists': False,
            'stage': stage,
            'error': str(e)
        } 