import os
import logging
from celery import Celery
from typing import List, Optional, Dict, Any
from pathlib import Path
import dspy
from dotenv import load_dotenv

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
# TODO: Add a way to configure the course generation process

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
            'stage': CourseGenerationStage.CLONE_REPO,
            'result': stage1_result.model_dump(),
            'next_stage': CourseGenerationStage.DOCUMENT_ANALYSIS
        }
        
    except Exception as e:
        logger.error(f"Stage 1 failed for course {course_id}: {str(e)}")
        return {
            'success': False,
            'stage': CourseGenerationStage.CLONE_REPO,
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
        
        # Create document tree
        tree = DocumentTree(
            repo_url=str(repo_path),
            repo_name=stage1_result.repo_name,
            root_path=str(repo_path),
            nodes={},
            tree_structure={},
            cross_references={}
        )
        
        # Process documents (basic extraction)
        processed_results = builder._process_raw_documents(md_files, tree)
        
        # Find overview document if specified
        overview_context = ""
        if stage2_input.overview_doc:
            overview_path = repo_path / stage2_input.overview_doc
            if overview_path.exists():
                with open(overview_path, 'r', encoding='utf-8') as f:
                    overview_context = f.read()[:2000]  # First 2000 chars
        
        # Apply LLM analysis
        successfully_processed_count = builder._apply_llm_analysis(processed_results, tree, overview_context)
        
        # Calculate counts
        total_raw_files = len(processed_results)
        successful_raw_files = len([r for r in processed_results if r['success']])
        failed_raw_files = total_raw_files - successful_raw_files
        
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
        
        logger.info(f"Stage 2 completed for course {course_id}")
        return {
            'success': True,
            'stage': CourseGenerationStage.DOCUMENT_ANALYSIS,
            'result': stage2_result.model_dump(),
            'next_stage': CourseGenerationStage.PATHWAY_BUILDING
        }
        
    except Exception as e:
        logger.error(f"Stage 2 failed for course {course_id}: {str(e)}")
        return {
            'success': False,
            'stage': CourseGenerationStage.DOCUMENT_ANALYSIS,
            'error': str(e)
        }

@app.task(bind=True)
def stage3_pathway_building(self, user_id: str, course_id: str) -> Dict[str, Any]:
    """Stage 3: Generate learning pathways for user selection"""
    try:
        logger.info(f"Starting Stage 3 for course {course_id}: pathway building")
        
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
                    overview_context = f.read()[:2000]
        
        # Generate learning pathways
        path_generator = LearningPathGenerator()
        learning_paths = path_generator.generate_grouped_paths(document_tree, overview_context)
        
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
                'complexity': path.target_complexity,
                'module_count': len(path.modules),
                'modules': [{'title': m.title, 'theme': m.theme, 'description': m.description} for m in path.modules]
            })
        
        logger.info(f"Stage 3 completed for course {course_id}")
        return {
            'success': True,
            'stage': CourseGenerationStage.PATHWAY_BUILDING,
            'result': stage3_result.model_dump(),
            'pathways': pathway_summaries,
            'next_stage': CourseGenerationStage.COURSE_GENERATION
        }
        
    except Exception as e:
        logger.error(f"Stage 3 failed for course {course_id}: {str(e)}")
        return {
            'success': False,
            'stage': CourseGenerationStage.PATHWAY_BUILDING,
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
                    overview_context = f.read()[:2000]
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
            'stage': CourseGenerationStage.COURSE_GENERATION,
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
            'stage': CourseGenerationStage.COURSE_GENERATION,
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