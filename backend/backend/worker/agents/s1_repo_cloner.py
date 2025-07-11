"""
Stage 1: Repository Cloner Agent
Handles repository cloning, caching, and file discovery
"""

import os
import logging
import hashlib
import shutil
import time
from typing import List, Optional
from pathlib import Path
from urllib.parse import urlparse

import git
import redis

from backend.shared.models import Stage1Result
from backend.core.config import settings


logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

class S1Config:
    """Stage 1 Configuration"""
    CACHE_DIR = Path(settings.ROOT_DATA_DIR) / ".cache"
    logger.info(f"CACHE_DIR: {CACHE_DIR}")
    # File patterns
    INCLUDE_EXTENSIONS = ['*.md', '*.mdx']
    EXCLUDE_PATTERNS = {
        'node_modules', '.git', '__pycache__', '.pytest_cache',
        'venv', 'env', '.venv', 'build', 'dist', 'tests'
    }
    EXCLUDE_FILE_PREFIXES = {
        'license', 'contributing', 'code_of_conduct', 'security', 'patents'
    }

# =============================================================================
# Utility Functions
# =============================================================================

def _is_file_in_folders(file_path: Path, repo_path: Path, include_folders: List[str]) -> bool:
    """Check if file is in any of the included folders"""
    rel_path = file_path.relative_to(repo_path)
    rel_path_str = str(rel_path)
    
    for include_folder in include_folders:
        include_folder = include_folder.strip('/')
        
        # Check various path patterns
        if (rel_path_str.startswith(include_folder + '/') or 
            rel_path_str.startswith(include_folder + '\\') or
            (include_folder == '.' and '/' not in rel_path_str and '\\' not in rel_path_str) or
            str(rel_path.parent) == include_folder or
            str(rel_path.parent).replace('\\', '/') == include_folder):
            return True
    
    return False

# =============================================================================
# Repository Manager
# =============================================================================

class RepoManager:
    """Handles repository operations, cloning, caching, and file discovery"""
    
    def __init__(self, cache_dir: str = S1Config.CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def _get_repo_cache_path(self, repo_url: str) -> Path:
        """Generate cache path for repository"""
        repo_hash = hashlib.md5(repo_url.encode()).hexdigest()
        repo_name = urlparse(repo_url).path.strip('/').replace('/', '_')
        return self.cache_dir / f"{repo_name}_{repo_hash}"
    
    def _update_existing_repo(self, repo_path: Path) -> None:
        """Update existing repository with latest changes"""
        try:
            repo = git.Repo(repo_path)
            repo.remotes.origin.pull()
            logger.info("Updated repository with latest changes")
        except Exception as e:
            logger.warning(f"Warning: Could not update repository: {e}")
    
    def clone_or_update_repo(self, repo_url: str, force_update: bool = False) -> Path:
        """Clone repository or update if it exists"""
        repo_path = self._get_repo_cache_path(repo_url)
        
        if repo_path.exists() and not force_update:
            logger.info(f"Repository already cached at {repo_path}")
            self._update_existing_repo(repo_path)
            return repo_path
        
        if repo_path.exists():
            shutil.rmtree(repo_path)
            
        logger.info(f"Cloning repository to {repo_path}")
        git.Repo.clone_from(repo_url, repo_path)
        return repo_path
    
    def get_repo_path(self, repo_input: str) -> Path:
        """Get repository path - either clone remote repo or use local path"""
        if repo_input.startswith(('http://', 'https://', 'git@')):
            return self.clone_or_update_repo(repo_input)
        else:
            local_path = Path(repo_input).resolve()
            if not local_path.exists():
                raise ValueError(f"Local repository path does not exist: {local_path}")
            return local_path
    
    def find_documentation_files(self, repo_path: Path, include_folders: Optional[List[str]] = None) -> List[Path]:
        """Find all markdown files in repository, optionally filtered by folders"""
        # Find all markdown files
        md_files = []
        for ext in S1Config.INCLUDE_EXTENSIONS:
            md_files.extend(repo_path.rglob(ext))
        
        # Filter out excluded directories
        filtered_files = [
            file_path for file_path in md_files
            if not any(excluded in file_path.parts for excluded in S1Config.EXCLUDE_PATTERNS)
        ]
        
        # Remove common non-content files
        filtered_files = [
            file for file in filtered_files 
            if not file.name.lower().startswith(tuple(S1Config.EXCLUDE_FILE_PREFIXES))
        ]
        
        # Filter by include_folders if specified
        if include_folders:
            filtered_files = [
                file_path for file_path in filtered_files
                if _is_file_in_folders(file_path, repo_path, include_folders)
            ]
            logger.info(f"Filtered to {len(filtered_files)} files from specified folders: {include_folders}")
        
        return sorted(filtered_files)

# =============================================================================
# Progress Tracker
# =============================================================================

class S1ProgressTracker:
    """Tracks and updates Stage 1 progress"""
    
    def __init__(self, redis_client: redis.Redis, task_id: str):
        self.redis = redis_client
        self.task_id = task_id
        self.progress_key = f"task:{task_id}:progress"
    
    def update_progress(self, stage: str, progress: int, message: str = ""):
        """Update progress in Redis"""
        try:
            progress_data = {
                'stage': stage,
                'progress': progress,
                'message': message,
                'timestamp': str(int(time.time()))
            }
            
            self.redis.hset(self.progress_key, mapping=progress_data)
            self.redis.expire(self.progress_key, 3600)  # Expire after 1 hour
            
            logger.info(f"Stage 1 Progress: {progress}% - {message}")
        except Exception as e:
            logger.error(f"Failed to update progress: {e}")

# =============================================================================
# Main Stage 1 Processor
# =============================================================================

def process_stage1(repo_input: str, user_id: str = None, course_id: str = None,
                  include_folders: Optional[List[str]] = None, 
                  task_id: str = None, redis_client: redis.Redis = None) -> Stage1Result:
    """
    Process Stage 1: Repository setup and file discovery
    
    Args:
        repo_input: Repository URL or local path
        user_id: User ID for cache directory
        course_id: Course ID for cache directory
        include_folders: Optional list of folders to include
        task_id: Task ID for progress tracking
        redis_client: Redis client for progress updates
    
    Returns:
        Stage1Result with repository info and file paths
    """
    # Initialize progress tracker
    progress_tracker = None
    if task_id and redis_client:
        progress_tracker = S1ProgressTracker(redis_client, task_id)
        progress_tracker.update_progress("stage1", 0, "Starting repository setup")
    
    try:
        # make sure the cache dir exists
        S1Config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        repo_manager = RepoManager(S1Config.CACHE_DIR)

        if progress_tracker:
            progress_tracker.update_progress("stage1", 10, "Initializing repository manager")
        
        # Clone repository
        repo_path = repo_manager.clone_or_update_repo(repo_input)
        repo_name = Path(repo_input).name.replace('.git', '')
        
        if progress_tracker:
            progress_tracker.update_progress("stage1", 30, "Repository cloned/accessed")
        
        # Discover available folders and files
        md_files = repo_manager.find_documentation_files(repo_path)
        
        if progress_tracker:
            progress_tracker.update_progress("stage1", 60, f"Found {len(md_files)} documentation files")
        
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
        result = Stage1Result(
            repo_path=str(repo_path),
            repo_name=repo_name,
            available_folders=available_folders,
            available_files=all_files,
            suggested_overview_docs=suggested_overview_docs[:5],  # Top 5 suggested
            all_overview_candidates=overview_candidates,  # All available files
            total_files_count=len(all_files),
            file_size_analysis={},  # Could add file size analysis here if needed
            folder_structure={},  # Could add folder structure here if needed
            metadata={
                'cache_dir': S1Config.CACHE_DIR,
                'total_folders': len(available_folders),
                'total_overview_candidates': len(overview_candidates),
                'repo_type': 'remote' if repo_input.startswith(('http://', 'https://', 'git@')) else 'local'
            }
        )
        
        if progress_tracker:
            progress_tracker.update_progress("stage1", 100, f"Stage 1 complete: {len(all_files)} files found")
        
        logger.info(f"Stage 1 completed: {len(all_files)} files found in {repo_name}")
        return result
        
    except Exception as e:
        logger.error(f"Stage 1 failed: {e}")
        if progress_tracker:
            progress_tracker.update_progress("stage1", -1, f"Stage 1 failed: {str(e)}")
        raise e 