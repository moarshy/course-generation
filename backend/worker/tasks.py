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

from shared.models import (
    CourseGenerationStage, StageStatus, CourseGenerationTask,
    Stage1Result, Stage2Result, Stage3Result, Stage4Result,
    Stage2UserInput, Stage3UserInput, Stage4UserInput,
    ComplexityLevel, DocumentTree, GroupedLearningPath, GeneratedCourse
)
from shared.utils import StageDataManager
from worker.course_content_agent.modules import RepoManager, LearningPathGenerator, CourseGenerator

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


##### ALL CONFIGURATION IS HERE #####
OVERVIEW_DOC_MAX_WORDS = 3000

def get_n_words(text: str, max_words: int) -> int:
    """Truncate text to max_words words."""
    return " ".join(text.split()[:max_words])

def get_stage_manager(user_id: str, course_id: str) -> StageDataManager:
    """Get a stage data manager for a specific user and course."""
    base_dir = f"../data/{user_id.replace('|', '_').replace('/', '_')}"
    return StageDataManager(base_dir, course_id)

@app.task(bind=True)
def stage1_clone_repository(self, user_id: str, course_id: str, repo_url: str) -> Dict[str, Any]:
    """Stage 1: Clone repository and analyze structure"""
    try:
        logger.info(f"Starting Stage 1 for course {course_id}: cloning {repo_url}")
        
        # Initialize repo manager
        cache_dir = f"../data/{user_id.replace('|', '_').replace('/', '_')}/{course_id}/cache"
        repo_manager = RepoManager(cache_dir)
        
        # Clone repository
        repo_path = repo_manager.clone_or_update_repo(repo_url)
        repo_name = Path(repo_url).name.replace('.git', '')
        
        # Discover available folders and files
        md_files = repo_manager.find_documentation_files(repo_path)
        
        # Get folder structure
        folders = set()
        all_files = []
        for file_path in md_files:
            relative_path = file_path.relative_to(repo_path)
            all_files.append(str(relative_path))
            
            # Add all parent directories
            for parent in relative_path.parents:
                if parent != Path('.'):
                    folders.add(str(parent))
        
        available_folders = sorted(list(folders))
        
        # Suggest overview documents (show all available files, not just keyword matches)
        overview_candidates = []
        suggested_overview_docs = []
        
        for file_path in md_files:
            relative_path = str(file_path.relative_to(repo_path))
            overview_candidates.append(relative_path)
            
            # Mark files with common overview keywords as suggested
            filename = file_path.name.lower()
            if any(keyword in filename for keyword in ['readme', 'overview', 'introduction', 'getting-started', 'index']):
                suggested_overview_docs.append(relative_path)
        
        # Create stage 1 result
        stage1_result = Stage1Result(
            repo_path=str(repo_path),
            repo_name=repo_name,
            available_folders=available_folders,
            available_files=all_files,
            suggested_overview_docs=suggested_overview_docs[:5],  # Top 5 suggested
            all_overview_candidates=overview_candidates  # All available files
        )
        
        # Save stage data
        stage_manager = get_stage_manager(user_id, course_id)
        stage_data_path = stage_manager.save_stage_data(
            CourseGenerationStage.CLONE_REPO, stage1_result
        )
        
        logger.info(f"Stage 1 completed for course {course_id}")
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

@app.task(bind=True)
def stage2_document_analysis(self, user_id: str, course_id: str, user_input: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 2: Process documents with user-selected folders and overview"""
    try:
        logger.info(f"Starting Stage 2 for course {course_id}: document analysis")
        
        # Parse user input
        stage2_input = Stage2UserInput(**user_input)
        
        # Get stage manager
        stage_manager = get_stage_manager(user_id, course_id)
        
        # Load Stage 1 data
        stage1_result = stage_manager.load_stage_data(CourseGenerationStage.CLONE_REPO)
        repo_path = Path(stage1_result.repo_path)
        
        # Import CourseBuilder for document processing
        from worker.course_content_agent.main import CourseBuilder
        
        # Initialize course builder
        cache_dir = f"../data/{user_id.replace('|', '_').replace('/', '_')}/{course_id}/cache"
        builder = CourseBuilder(cache_dir=cache_dir)
        
        # Find documentation files with folder filtering
        repo_manager = RepoManager(cache_dir)
        md_files = repo_manager.find_documentation_files(repo_path, stage2_input.include_folders)
        
        # Initialize detailed progress tracking in Redis
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        progress_key = f"stage2_progress:{course_id}"
        
        # Create list of files to process
        files_to_process = []
        for file_path in md_files:
            relative_path = str(file_path.relative_to(repo_path))
            files_to_process.append(relative_path)
        
        # Initialize progress data
        progress_data = {
            'total_files': len(files_to_process),
            'processed_files': 0,
            'failed_files': 0,
            'current_file': '',
            'files_to_process': files_to_process,
            'completed_files': [],
            'failed_files_list': [],
            'stage': 'raw_processing',
            'stage_description': 'Extracting content from markdown files',
            'updated_at': datetime.now().isoformat()
        }
        redis_client.set(progress_key, json.dumps(progress_data))
        
        # Create document tree
        tree = DocumentTree(
            repo_url=str(repo_path),
            repo_name=stage1_result.repo_name,
            root_path=str(repo_path),
            nodes={},
            tree_structure={},
            cross_references={}
        )
        
        # Process documents with progress tracking
        processed_results = builder._process_raw_documents_with_progress(
            md_files, tree, progress_key, redis_client, user_id, course_id
        )
        
        # Update progress for LLM analysis stage
        progress_data['stage'] = 'llm_analysis'
        progress_data['stage_description'] = 'Analyzing content with AI for key concepts and structure'
        progress_data['processed_files'] = 0  # Reset for LLM stage
        progress_data['completed_files'] = []
        progress_data['current_file'] = ''
        progress_data['updated_at'] = datetime.now().isoformat()
        redis_client.set(progress_key, json.dumps(progress_data))
        
        # Find overview document if specified
        overview_context = ""
        if stage2_input.overview_doc:
            overview_path = repo_path / stage2_input.overview_doc
            if overview_path.exists():
                with open(overview_path, 'r', encoding='utf-8') as f:
                    overview_context = get_n_words(f.read(), OVERVIEW_DOC_MAX_WORDS)
        
        # Apply LLM analysis with progress tracking
        successfully_processed_count = builder._apply_llm_analysis_with_progress(
            processed_results, tree, overview_context, progress_key, redis_client, user_id, course_id
        )
        
        # Calculate counts
        total_raw_files = len(processed_results)
        successful_raw_files = len([r for r in processed_results if r['success']])
        failed_raw_files = total_raw_files - successful_raw_files
        
        # Final progress update
        progress_data['stage'] = 'completed'
        progress_data['stage_description'] = 'Document analysis completed'
        progress_data['current_file'] = ''
        progress_data['updated_at'] = datetime.now().isoformat()
        redis_client.set(progress_key, json.dumps(progress_data))
        
        # Create stage 2 result
        stage2_result = Stage2Result(
            document_tree_path="",  # Will be set after saving
            processed_files_count=successfully_processed_count,  # Files successfully processed by LLM
            failed_files_count=failed_raw_files,  # Files that failed during raw processing
            include_folders=stage2_input.include_folders,
            overview_doc=stage2_input.overview_doc
        )
        
        # Save document tree separately
        tree_path = stage_manager.save_stage_data(
            CourseGenerationStage.DOCUMENT_ANALYSIS, tree
        )
        stage2_result.document_tree_path = tree_path
        
        # Save stage result to a different key to avoid overwriting the tree
        stage_manager.save_stage_data(
            CourseGenerationStage.DOCUMENT_ANALYSIS, stage2_result, suffix="result"
        )
        
        # Clean up progress data after completion
        redis_client.delete(progress_key)
        
        logger.info(f"Stage 2 completed for course {course_id}")
        return {
            'success': True,
            'stage': CourseGenerationStage.DOCUMENT_ANALYSIS.value,
            'result': stage2_result.model_dump(),
            'next_stage': CourseGenerationStage.PATHWAY_BUILDING.value
        }
        
    except Exception as e:
        logger.error(f"Stage 2 failed for course {course_id}: {str(e)}")
        
        # Update progress with error
        try:
            redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
            progress_key = f"stage2_progress:{course_id}"
            progress_data = {
                'stage': 'failed',
                'stage_description': f'Document analysis failed: {str(e)}',
                'error': str(e),
                'updated_at': datetime.now().isoformat()
            }
            redis_client.set(progress_key, json.dumps(progress_data))
        except:
            pass  # Don't let Redis errors mask the original error
        
        return {
            'success': False,
            'stage': CourseGenerationStage.DOCUMENT_ANALYSIS.value,
            'error': str(e)
        }

@app.task(bind=True)
def stage3_pathway_building(self, user_id: str, course_id: str) -> Dict[str, Any]:
    """Stage 3: Generate learning pathways for user selection"""
    try:
        logger.info(f"Starting Stage 3 for course {course_id}: pathway building")
        
        # Initialize Redis progress tracking
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        progress_key = f"stage3_progress:{course_id}"
        
        # Get stage manager
        stage_manager = get_stage_manager(user_id, course_id)
        
        # Load previous stage data
        stage2_result = stage_manager.load_stage_data(CourseGenerationStage.DOCUMENT_ANALYSIS, suffix="result")
        document_tree: DocumentTree = stage_manager.load_stage_data(CourseGenerationStage.DOCUMENT_ANALYSIS)
        
        # Get overview context if available
        overview_context = ""
        if stage2_result.overview_doc:
            stage1_result = stage_manager.load_stage_data(CourseGenerationStage.CLONE_REPO)
            overview_path = Path(stage1_result.repo_path) / stage2_result.overview_doc
            if overview_path.exists():
                with open(overview_path, 'r', encoding='utf-8') as f:
                    overview_context = get_n_words(f.read(), OVERVIEW_DOC_MAX_WORDS)
        
        # Initialize progress data
        complexities = [ComplexityLevel.BEGINNER, ComplexityLevel.INTERMEDIATE, ComplexityLevel.ADVANCED]
        complexity_names = [c.value.upper() for c in complexities]
        
        progress_data = {
            'stage': 'initializing',
            'stage_description': 'Preparing to generate learning pathways',
            'total_pathways': len(complexities),
            'generated_pathways': 0,
            'current_complexity': '',
            'completed_complexities': [],
            'updated_at': datetime.now().isoformat()
        }
        redis_client.set(progress_key, json.dumps(progress_data))
        
        # Update progress: starting pathway generation
        progress_data.update({
            'stage': 'generating_pathways',
            'stage_description': 'Generating learning pathways for different complexity levels',
            'updated_at': datetime.now().isoformat()
        })
        redis_client.set(progress_key, json.dumps(progress_data))
        
        # Generate learning pathways with progress updates
        path_generator = LearningPathGenerator()
        learning_paths = []
        
        # Get all documents (no complexity filtering - let LLM decide)
        all_documents = list(document_tree.nodes.values())
        
        if not all_documents:
            logger.warning("No documents found for learning path generation")
            # Update progress with error
            progress_data.update({
                'stage': 'failed',
                'stage_description': 'No documents found for pathway generation',
                'error': 'No documents available',
                'updated_at': datetime.now().isoformat()
            })
            redis_client.set(progress_key, json.dumps(progress_data))
            return {
                'success': False,
                'stage': CourseGenerationStage.PATHWAY_BUILDING.value,
                'error': 'No documents found for learning path generation'
            }
        
        logger.info(f"Generating learning paths for {len(all_documents)} documents")
        
        for i, complexity in enumerate(complexities):
            complexity_name = complexity.value.upper()
            
            # Update current complexity being processed
            progress_data.update({
                'current_complexity': complexity_name,
                'generated_pathways': i,
                'updated_at': datetime.now().isoformat()
            })
            redis_client.set(progress_key, json.dumps(progress_data))
            
            try:
                logger.info(f"Generating {complexity_name} complexity pathway...")
                
                # Generate learning path for this complexity level using the forward method directly
                grouped_path = path_generator.forward(
                    documents=all_documents,
                    complexity=complexity,
                    repo_name=document_tree.repo_name or "Documentation",
                    overview_context=overview_context
                )
                
                if grouped_path:
                    learning_paths.append(grouped_path)
                    logger.info(f"Generated {complexity_name} pathway with {len(grouped_path.modules)} modules")
                else:
                    logger.warning(f"No pathway generated for {complexity_name} level")
                
                # Mark as completed
                progress_data['completed_complexities'].append(complexity_name)
                progress_data.update({
                    'generated_pathways': i + 1,
                    'updated_at': datetime.now().isoformat()
                })
                redis_client.set(progress_key, json.dumps(progress_data))
                
            except Exception as e:
                logger.error(f"Error generating learning path for {complexity_name}: {e}")
                # Continue with other complexity levels
                continue
        
        # Mark as completed
        progress_data.update({
            'stage': 'completed',
            'stage_description': 'Learning pathways generated successfully',
            'current_complexity': '',
            'updated_at': datetime.now().isoformat()
        })
        redis_client.set(progress_key, json.dumps(progress_data))
        
        # Create stage 3 result
        stage3_result = Stage3Result(
            learning_paths_path="",  # Will be set after saving
        )
        
        # Save learning paths with suffix to avoid overwriting
        paths_data = {
            'paths': learning_paths,
            'document_tree_summary': {
                'total_documents': len(document_tree.nodes),
                'repo_name': document_tree.repo_name
            }
        }
        
        paths_path = stage_manager.save_stage_data(
            CourseGenerationStage.PATHWAY_BUILDING, paths_data, suffix="paths"
        )
        stage3_result.learning_paths_path = paths_path
        
        # Save stage result
        stage_manager.save_stage_data(
            CourseGenerationStage.PATHWAY_BUILDING, stage3_result, suffix="result"
        )
        
        # Prepare response with pathway summaries
        pathway_summaries = []
        for i, path in enumerate(learning_paths):
            pathway_summaries.append({
                'index': i,
                'title': path.title,
                'description': path.description,
                'complexity': path.target_complexity.value if hasattr(path.target_complexity, 'value') else str(path.target_complexity),
                'module_count': len(path.modules),
                'modules': [{'title': m.title, 'theme': m.theme, 'description': m.description} for m in path.modules]
            })
        
        # Clean up progress data after completion
        redis_client.delete(progress_key)
        
        logger.info(f"Stage 3 completed for course {course_id}")
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
            redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
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

@app.task(bind=True)
def stage4_course_generation(self, user_id: str, course_id: str, user_input: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 4: Generate final course content"""
    try:
        logger.info(f"Starting Stage 4 for course {course_id}: course generation")
        logger.info(f"Stage 4 user_input: {user_input}")
        
        # Parse user input
        stage4_input = Stage4UserInput(**user_input)
        logger.info(f"Stage 4 parsed input: {stage4_input}")
        
        # Get stage manager
        stage_manager = get_stage_manager(user_id, course_id)
        logger.info(f"Stage manager created for user {user_id}, course {course_id}")
        
        # Load previous stage data with debugging
        logger.info("Loading Stage 3 data...")
        # Load the paths data with the correct suffix
        stage3_data = stage_manager.load_stage_data(CourseGenerationStage.PATHWAY_BUILDING, suffix="paths")
        logger.info(f"Stage 3 data loaded: {stage3_data is not None}")
        if stage3_data is None:
            # Try without suffix for backward compatibility
            logger.info("Trying to load Stage 3 data without suffix...")
            stage3_data = stage_manager.load_stage_data(CourseGenerationStage.PATHWAY_BUILDING)
            logger.info(f"Stage 3 data loaded (no suffix): {stage3_data is not None}")
            if stage3_data is None:
                raise ValueError("Stage 3 data is None - pathway building data not found")
        logger.info(f"Stage 3 data keys: {list(stage3_data.keys()) if isinstance(stage3_data, dict) else type(stage3_data)}")
        
        logger.info("Loading Document Tree...")
        document_tree: DocumentTree = stage_manager.load_stage_data(CourseGenerationStage.DOCUMENT_ANALYSIS)
        logger.info(f"Document tree loaded: {document_tree is not None}")
        if document_tree is None:
            raise ValueError("Document tree is None - document analysis data not found")
        
        logger.info("Loading Stage 2 result...")
        stage2_result = stage_manager.load_stage_data(CourseGenerationStage.DOCUMENT_ANALYSIS, suffix="result")
        logger.info(f"Stage 2 result loaded: {stage2_result is not None}")
        if stage2_result is None:
            raise ValueError("Stage 2 result is None - document analysis result not found")
        
        # Get selected pathway
        logger.info("Getting learning paths...")
        if 'paths' not in stage3_data:
            raise ValueError(f"'paths' key not found in stage3_data. Available keys: {list(stage3_data.keys())}")
        
        learning_paths = stage3_data['paths']
        logger.info(f"Learning paths found: {len(learning_paths) if learning_paths else 0}")
        
        if stage4_input.custom_pathway:
            logger.info("Using custom pathway from input")
            selected_pathway = stage4_input.custom_pathway
        else:
            logger.info("Using first pathway from generated paths")
            selected_pathway = learning_paths[0] if learning_paths else None
        
        logger.info(f"Selected pathway: {selected_pathway is not None}")
        if not selected_pathway:
            raise ValueError("No pathway available for course generation")
        
        # Debug the selected pathway
        logger.info(f"Selected pathway type: {type(selected_pathway)}")
        logger.info(f"Selected pathway is dict: {isinstance(selected_pathway, dict)}")
        if hasattr(selected_pathway, '__dict__'):
            logger.info(f"Selected pathway attributes: {list(selected_pathway.__dict__.keys())}")
        if hasattr(selected_pathway, 'pathway_id'):
            logger.info(f"Selected pathway HAS pathway_id: {selected_pathway.pathway_id}")
        else:
            logger.warning("Selected pathway MISSING pathway_id attribute")
            
        # Convert dictionary back to GroupedLearningPath if needed
        if isinstance(selected_pathway, dict):
            logger.info("Converting pathway dictionary to GroupedLearningPath object")
            logger.info(f"Pathway dictionary keys: {list(selected_pathway.keys())}")
            logger.info(f"Pathway dictionary has pathway_id: {'pathway_id' in selected_pathway}")
            
            # If pathway_id is missing, add it
            if 'pathway_id' not in selected_pathway:
                logger.warning("pathway_id missing from dictionary, generating one")
                selected_pathway['pathway_id'] = f"pathway_{selected_pathway.get('title', 'unknown').lower().replace(' ', '_')}"
            
            from worker.course_content_agent.models import GroupedLearningPath
            selected_pathway = GroupedLearningPath(**selected_pathway)
            logger.info(f"Converted pathway - ID: {selected_pathway.pathway_id}")
        elif not hasattr(selected_pathway, 'pathway_id'):
            # It's a shared.models.GroupedLearningPath, convert to worker.course_content_agent.models.GroupedLearningPath
            logger.warning("Converting shared.models.GroupedLearningPath to worker model")
            
            # Convert safely with proper field mapping
            pathway_dict = selected_pathway.model_dump() if hasattr(selected_pathway, 'model_dump') else selected_pathway.__dict__
            
            # Add missing required fields
            pathway_dict['pathway_id'] = f"pathway_{pathway_dict.get('title', 'unknown').lower().replace(' ', '_')}"
            pathway_dict['welcome_message'] = pathway_dict.get('welcome_message', f"Welcome to {pathway_dict.get('title', 'this course')}!")
            
            # Remove fields that don't exist in worker model
            pathway_dict.pop('estimated_duration', None)
            pathway_dict.pop('prerequisites', None)
            
            # Fix modules - handle assessment field differences
            if 'modules' in pathway_dict:
                for module in pathway_dict['modules']:
                    if isinstance(module, dict) and module.get('assessment') is None:
                        # Create a basic assessment if missing
                        module['assessment'] = {
                            'assessment_id': f"{module.get('module_id', 'unknown')}_assessment",
                            'title': f"{module.get('title', 'Module')} Assessment",
                            'concepts_to_assess': module.get('learning_objectives', [])[:3]
                        }
            
            from worker.course_content_agent.models import GroupedLearningPath
            selected_pathway = GroupedLearningPath(**pathway_dict)
            logger.info(f"Converted pathway with ID: {selected_pathway.pathway_id}")
        
        # Get overview context
        logger.info("Getting overview context...")
        overview_context = ""
        if hasattr(stage2_result, 'overview_doc') and stage2_result.overview_doc:
            logger.info("Loading Stage 1 result for overview...")
            stage1_result = stage_manager.load_stage_data(CourseGenerationStage.CLONE_REPO)
            logger.info(f"Stage 1 result loaded: {stage1_result is not None}")
            if stage1_result is None:
                raise ValueError("Stage 1 result is None - clone repo data not found")
            
            overview_path = Path(stage1_result.repo_path) / stage2_result.overview_doc
            logger.info(f"Overview path: {overview_path}")
            if overview_path.exists():
                with open(overview_path, 'r', encoding='utf-8') as f:
                    overview_context = get_n_words(f.read(), OVERVIEW_DOC_MAX_WORDS)
                logger.info(f"Overview context loaded: {len(overview_context)} chars")
        else:
            logger.info("No overview document specified")
        
        # Generate course
        logger.info("Generating course...")
        course_generator = CourseGenerator()
        logger.info(f"Course generator created: {course_generator is not None}")
        
        logger.info(f"Calling generate_course with pathway: {selected_pathway.title if hasattr(selected_pathway, 'title') else 'No title'}")
        generated_course = course_generator.generate_course(selected_pathway, document_tree, overview_context)
        logger.info(f"Course generated: {generated_course is not None}")
        if generated_course is None:
            raise ValueError("Course generation failed - generated_course is None")
        
        # Export course to markdown
        logger.info("Exporting course to markdown...")
        from worker.course_content_agent.modules import CourseExporter
        exporter = CourseExporter()
        logger.info(f"Course exporter created: {exporter is not None}")
        
        # Create export directory
        user_dir = f"../data/{user_id.replace('|', '_').replace('/', '_')}/{course_id}"
        export_dir = f"{user_dir}/generated"
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
        
        logger.info(f"Stage 4 completed for course {course_id}")
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