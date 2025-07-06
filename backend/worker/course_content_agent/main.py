import os
import logging
import sys
import multiprocessing as mp
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from dotenv import load_dotenv
import dspy
from typing import Optional, List
import pickle

from .models import DocumentTree, ComplexityLevel, DocumentType
from .modules import (
    RepoManager, LearningPathGenerator, CourseGenerator, CourseExporter,
    process_single_document, process_llm_analysis
)

load_dotenv()

# =============================================================================
# Constants
# =============================================================================

CACHE_DIR = ".cache"

# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler('output.log', mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Suppress litellm logs below WARNING
logging.getLogger("litellm").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# =============================================================================
# Configuration
# =============================================================================
# dspy.configure(lm=dspy.LM("anthropic/claude-3-5-haiku-latest", cache=False))
dspy.configure(lm=dspy.LM("gemini/gemini-2.5-flash", cache=False, max_tokens=20000, temperature=0.))

# =============================================================================
# Course Builder
# =============================================================================

class CourseBuilder:
    """Build courses from documentation repositories with multiprocessing"""
    
    def __init__(self, cache_dir: str = CACHE_DIR, max_workers: int = None):
        self.repo_manager = RepoManager(cache_dir)
        self.learning_path_generator = LearningPathGenerator()
        self.course_generator = CourseGenerator()
        self.course_exporter = CourseExporter()
        
        # Set max workers (default to CPU count - 1)
        self.max_workers = max_workers or max(1, mp.cpu_count() - 1)
        logger.info(f"Using {self.max_workers} worker processes")
    
    def _process_documents_parallel(self, md_files, repo_path):
        """Process documents in parallel using multiprocessing"""
        logger.info(f"Starting parallel processing of {len(md_files)} files...")
        
        # Prepare arguments for multiprocessing
        args = [(file_path, repo_path, True) for file_path in md_files]
        
        # Process with multiprocessing
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(process_single_document, args))
        
        # Log results
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        logger.info(f"Parallel processing complete: {successful} successful, {failed} failed")
        
        if failed > 0:
            for r in results:
                if not r['success']:
                    logger.error(f"✗ Failed to process: {r['relative_path']} - {r['error']}")
        
        return results
    
    def _process_raw_documents(self, md_files, tree):
        """Process documents to extract basic content without LLM analysis"""
        logger.info(f"Processing raw content from {len(md_files)} files...")
        
        # Prepare arguments for multiprocessing
        args = [(file_path, tree.root_path, False) for file_path in md_files]
        
        # Process with multiprocessing
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(process_single_document, args))
        
        # Log results
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        logger.info(f"Raw document processing complete: {successful} successful, {failed} failed")
        
        if failed > 0:
            for r in results:
                if not r['success']:
                    logger.error(f"✗ Failed to process: {r['relative_path']} - {r['error']}")
        
        return results
    
    def _apply_llm_analysis(self, processed_results, tree, overview_context: str = ""):
        """Apply LLM analysis to processed documents using parallel processing"""
        
        successful_results = [r for r in processed_results if r['success']]
        
        if not successful_results:
            logger.warning("No successful results to process with LLM")
            return 0
        
        logger.info(f"Starting parallel LLM analysis of {len(successful_results)} documents...")
        if overview_context:
            logger.info("Using overview context for better document understanding")
        
        # Prepare arguments for multiprocessing
        llm_args = [(result, tree.root_path, overview_context) for result in successful_results]
        
        # Process with multiprocessing
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            llm_results = list(executor.map(process_llm_analysis, llm_args))
        
        # Process results and create nodes
        error_count = 0
        llm_error_count = 0
        
        for llm_result in llm_results:
            if not llm_result['success']:
                logger.error(f"✗ LLM processing failed: {llm_result['relative_path']} - {llm_result['error']}")
                error_count += 1
                continue
            
            if not llm_result['llm_success']:
                logger.warning(f"⚠ LLM analysis failed for {llm_result['relative_path']}, using basic metadata: {llm_result['error_msg']}")
                llm_error_count += 1
            
            try:
                # Create DocumentNode from the processed data
                from course_content_agent.models import DocumentNode
                node_data = llm_result['node_data']
                node = DocumentNode(**node_data)
                tree.nodes[llm_result['relative_path']] = node
                
            except Exception as e:
                logger.error(f"Failed to create node for {llm_result['relative_path']}: {e}")
                error_count += 1
        
        logger.info(f"LLM analysis complete: {len(tree.nodes)} nodes created")
        if llm_error_count > 0:
            logger.warning(f"⚠ {llm_error_count} documents used basic metadata due to LLM failures")
        
        return error_count
    
    def _apply_llm_analysis_batch(self, processed_results, tree, batch_size: int = 50, overview_context: str = ""):
        """Apply LLM analysis in batches to manage memory usage"""
        
        successful_results = [r for r in processed_results if r['success']]
        total_docs = len(successful_results)
        
        if not successful_results:
            logger.warning("No successful results to process with LLM")
            return 0
        
        logger.info(f"Starting batched LLM analysis of {total_docs} documents (batch size: {batch_size})...")
        if overview_context:
            logger.info("Using overview context for better document understanding")
        
        total_error_count = 0
        total_llm_error_count = 0
        
        # Process in batches
        for i in range(0, total_docs, batch_size):
            batch_end = min(i + batch_size, total_docs)
            batch_results = successful_results[i:batch_end]
            
            logger.info(f"Processing batch {i//batch_size + 1}/{(total_docs + batch_size - 1)//batch_size} ({len(batch_results)} documents)")
            
            # Prepare arguments for this batch
            llm_args = [(result, tree.root_path, overview_context) for result in batch_results]
            
            # Process batch with multiprocessing
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                llm_results = list(executor.map(process_llm_analysis, llm_args))
            
            # Process batch results
            error_count = 0
            llm_error_count = 0
            
            for llm_result in llm_results:
                if not llm_result['success']:
                    logger.error(f"✗ LLM processing failed: {llm_result['relative_path']} - {llm_result['error']}")
                    error_count += 1
                    continue
                
                if not llm_result['llm_success']:
                    llm_error_count += 1
                
                try:
                    # Create DocumentNode from the processed data
                    from course_content_agent.models import DocumentNode
                    node_data = llm_result['node_data']
                    node = DocumentNode(**node_data)
                    tree.nodes[llm_result['relative_path']] = node
                    
                except Exception as e:
                    logger.error(f"Failed to create node for {llm_result['relative_path']}: {e}")
                    error_count += 1
            
            total_error_count += error_count
            total_llm_error_count += llm_error_count
            
            logger.info(f"Batch complete: {len(batch_results) - error_count} nodes created")
        
        logger.info(f"All batches complete: {len(tree.nodes)} total nodes created")
        if total_llm_error_count > 0:
            logger.warning(f"⚠ {total_llm_error_count} documents used basic metadata due to LLM failures")
        
        return total_error_count
    
    def _find_overview_document(self, doc_files, overview_filename):
        """
        Find and extract overview document content for context
        
        Args:
            doc_files: List of documentation file paths
            overview_filename: Filename to look for (e.g., "architecture.mdx")
            
        Returns:
            str: Overview document content, empty string if not found
        """
        if not overview_filename:
            return ""
            
        for file_path in doc_files:
            if file_path.name.lower() == overview_filename.lower():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    logger.info(f"Using overview document: {file_path.name}")
                    return content
                except Exception as e:
                    logger.warning(f"Failed to read overview file {file_path}: {e}")
                    return ""
        
        logger.warning(f"Overview file '{overview_filename}' not found in documentation files")
        return ""

    def build_course(self, 
                     repo_path: str, 
                     output_dir: str = "course_output",
                     cache_dir: str = "doc_cache",
                     batch_size: int = 50,
                     skip_llm: bool = False,
                     include_folders: Optional[List[str]] = None,
                     overview_doc: Optional[str] = None) -> bool:
        """
        Build a course from a documentation repository
        
        Args:
            repo_path: Path to the documentation repository
            output_dir: Directory to save the generated course
            cache_dir: Directory to cache processed document trees
            batch_size: Number of documents to process in each batch
            skip_llm: If True, skip LLM processing and use only basic metadata
            include_folders: Optional list of folder paths to include (relative to repo root).
                           If provided, only files in these folders will be processed.
                           Use forward slashes, e.g., ["docs", "guides", "api-reference"]
            overview_doc: Optional filename of overview document to provide context for
                         better document classification (e.g., "architecture.mdx", "overview.md")
        
        Returns:
            bool: True if course generation was successful
        """
        try:
            # Convert to Path object if it's a local path, otherwise keep as URL string
            if not repo_path.startswith(('http://', 'https://')):
                repo_path_obj = Path(repo_path).resolve()
                # Check if repo exists locally
                if not repo_path_obj.exists():
                    logger.error(f"Repository path does not exist: {repo_path}")
                    return False
            
            # Create output directory
            output_path = Path(output_dir).resolve()
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Create cache directory
            cache_path = Path(cache_dir).resolve()
            cache_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Starting course generation from: {repo_path}")
            logger.info(f"Output directory: {output_path}")
            logger.info(f"Cache directory: {cache_path}")
            if include_folders:
                logger.info(f"Including folders: {include_folders}")

            # Clone the repo
            cloned_repo_path = self.repo_manager.clone_or_update_repo(repo_path)
            
            # Find documentation files using existing repo manager
            doc_files = self.repo_manager.find_documentation_files(cloned_repo_path, include_folders=include_folders)
            
            if not doc_files:
                logger.error("No documentation files found in repository")
                return False
            
            logger.info(f"Found {len(doc_files)} documentation files")
            
            # Find overview document content for context
            overview_content = self._find_overview_document(doc_files, overview_doc)
            
            # Check cache for processed document tree
            repo_name = cloned_repo_path.name
            cache_file = cache_path / f"{repo_name}_document_tree.pkl"
            
            tree = None
            if cache_file.exists():
                try:
                    with open(cache_file, 'rb') as f:
                        tree = pickle.load(f)
                    logger.info(f"Loaded cached document tree with {len(tree.nodes)} nodes")
                except Exception as e:
                    logger.warning(f"Failed to load cached tree: {e}")
                    tree = None
            
            # Process documents if no valid cache
            if tree is None:
                logger.info("Processing documents...")
                
                # Create document tree
                tree = DocumentTree(
                    repo_url=repo_path,
                    repo_name=repo_name,
                    root_path=str(cloned_repo_path),
                    nodes={},
                    tree_structure={},
                    cross_references={},
                    last_updated=datetime.now(),
                    document_categories={},
                    complexity_distribution={},
                    learning_paths=[]
                )
                
                # Process raw documents
                raw_results = self._process_raw_documents(doc_files, tree)
                
                # Apply LLM analysis if not skipped
                if not skip_llm:
                    if batch_size > 0:
                        self._apply_llm_analysis_batch(raw_results, tree, batch_size, overview_content)
                    else:
                        self._apply_llm_analysis(raw_results, tree, overview_content)
                
                # Cache the processed tree
                try:
                    with open(cache_file, 'wb') as f:
                        pickle.dump(tree, f)
                    logger.info(f"Cached document tree to {cache_file}")
                except Exception as e:
                    logger.warning(f"Failed to cache document tree: {e}")
            
            # Generate learning paths using the new LearningPathGenerator
            # Check if learning paths already exist in cached tree
            if hasattr(tree, 'learning_paths') and tree.learning_paths:
                logger.info(f"Using {len(tree.learning_paths)} cached learning paths")
                grouped_paths = tree.learning_paths
            else:
                logger.info("Generating learning paths...")
                
                # Set repo_name if not available
                if not hasattr(tree, 'repo_name') or not tree.repo_name:
                    tree.repo_name = repo_name
                
                grouped_paths = self.learning_path_generator.generate_grouped_paths(tree, overview_content)
                
                if not grouped_paths:
                    logger.error("No learning paths were generated")
                    return False
                    
                logger.info(f"Generated {len(grouped_paths)} learning paths")
                
                # Add learning paths to tree and re-cache
                tree.learning_paths = grouped_paths
                
                # Update cache with learning paths
                try:
                    with open(cache_file, 'wb') as f:
                        pickle.dump(tree, f)
                    logger.info(f"Updated cache with learning paths: {cache_file}")
                except Exception as e:
                    logger.warning(f"Failed to update cache with learning paths: {e}")
            
            # Generate course content for each learning path
            logger.info("Generating course content...")
            course_count = 0
            
            for grouped_path in grouped_paths:
                try:
                    # Generate complete course content
                    course = self.course_generator.generate_course(grouped_path, tree, overview_content)
                    
                    if course and course.modules:
                        course_count += 1
                        
                        # Export course
                        export_success = self.course_exporter.export_to_markdown(course, str(output_path))
                        
                        if export_success:
                            logger.info(f"✓ {grouped_path.target_complexity.value.title()} course exported successfully")
                        else:
                            logger.error(f"✗ Failed to export {grouped_path.target_complexity.value} course")
                    else:
                        logger.warning(f"No content generated for {grouped_path.target_complexity.value} course")
                        
                except Exception as e:
                    logger.error(f"Error generating course for {grouped_path.target_complexity.value}: {e}")
                    continue
                        
            if course_count == 0:
                logger.error("No courses were generated")
                return False
                
            logger.info(f"Course generation complete! Generated {course_count} courses in {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Course generation failed: {e}")
            return False

