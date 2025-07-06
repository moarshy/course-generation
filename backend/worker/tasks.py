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
        
        # Parse user input
        stage4_input = Stage4UserInput(**user_input)
        
        # Get stage manager
        stage_manager = get_stage_manager(user_id, course_id)
        
        # Load previous stage data
        stage3_data = stage_manager.load_stage_data(CourseGenerationStage.PATHWAY_BUILDING)
        document_tree: DocumentTree = stage_manager.load_stage_data(CourseGenerationStage.DOCUMENT_ANALYSIS)
        stage2_result = stage_manager.load_stage_data(CourseGenerationStage.DOCUMENT_ANALYSIS, suffix="result")
        
        # Get selected pathway
        learning_paths = stage3_data['paths']
        if stage4_input.custom_pathway:
            selected_pathway = stage4_input.custom_pathway
        else:
            # Use the first pathway by default if no custom pathway
            selected_pathway = learning_paths[0] if learning_paths else None
        
        if not selected_pathway:
            raise ValueError("No pathway available for course generation")
        
        # Get overview context
        overview_context = ""
        if stage2_result.overview_doc:
            stage1_result = stage_manager.load_stage_data(CourseGenerationStage.CLONE_REPO)
            overview_path = Path(stage1_result.repo_path) / stage2_result.overview_doc
            if overview_path.exists():
                with open(overview_path, 'r', encoding='utf-8') as f:
                    overview_context = f.read()[:2000]
        
        # Generate course
        course_generator = CourseGenerator()
        generated_course = course_generator.generate_course(selected_pathway, document_tree, overview_context)
        
        # Export course to markdown
        from worker.course_content_agent.modules import CourseExporter
        exporter = CourseExporter()
        
        # Create export directory
        user_dir = f"../data/{user_id.replace('|', '_').replace('/', '_')}/{course_id}"
        export_dir = f"{user_dir}/generated"
        
        export_success = exporter.export_to_markdown(generated_course, export_dir)
        
        if not export_success:
            raise ValueError("Failed to export course to markdown")
        
        # Create stage 4 result
        stage4_result = Stage4Result(
            generated_course_path="",  # Will be set after saving
            export_path=export_dir
        )
        
        # Save generated course
        course_path = stage_manager.save_stage_data(
            CourseGenerationStage.COURSE_GENERATION, generated_course
        )
        stage4_result.generated_course_path = course_path
        
        # Save stage result
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
        logger.error(f"Stage 4 failed for course {course_id}: {str(e)}")
        return {
            'success': False,
            'stage': CourseGenerationStage.COURSE_GENERATION,
            'error': str(e)
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