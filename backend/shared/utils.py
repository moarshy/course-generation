"""
Shared utilities for Course Creator backend services.

Contains common helper functions and data management utilities.
"""

import os
import json
import pickle
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, TypeVar, Type
from pathlib import Path
from contextlib import contextmanager

from .models import (
    Stage1Result, Stage2Result, Stage3Result, Stage4Result,
    CourseGenerationTask, DocumentTree, GeneratedCourse,
    GroupedLearningPath
)
from .enums import CourseGenerationStage

T = TypeVar('T')


class StageDataManager:
    """Manages data persistence for different stages of course generation."""
    
    def __init__(self, base_dir: str, course_id: str):
        self.base_dir = Path(base_dir)
        self.course_id = course_id
        self.course_dir = self.base_dir / course_id
        self.course_dir.mkdir(parents=True, exist_ok=True)
    
    def save_stage_data(self, stage: CourseGenerationStage, data: Any, suffix: str = ""):
        """Save stage data to a file."""
        filename = f"{stage.value}{f'_{suffix}' if suffix else ''}.pkl"
        filepath = self.course_dir / filename
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        return str(filepath)
    
    def load_stage_data(self, stage: CourseGenerationStage, suffix: str = "", 
                       default: Any = None) -> Any:
        """Load stage data from a file."""
        filename = f"{stage.value}{f'_{suffix}' if suffix else ''}.pkl"
        filepath = self.course_dir / filename
        
        if not filepath.exists():
            return default
        
        try:
            with open(filepath, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error loading stage data from {filepath}: {e}")
            return default
    
    def get_stage_data_path(self, stage: CourseGenerationStage, suffix: str = "") -> str:
        """Get the path for stage data file."""
        filename = f"{stage.value}{f'_{suffix}' if suffix else ''}.pkl"
        return str(self.course_dir / filename)
    
    def stage_data_exists(self, stage: CourseGenerationStage, suffix: str = "") -> bool:
        """Check if stage data exists."""
        filename = f"{stage.value}{f'_{suffix}' if suffix else ''}.pkl"
        filepath = self.course_dir / filename
        return filepath.exists()
    
    def save_json(self, filename: str, data: Any) -> str:
        """Save data as JSON."""
        filepath = self.course_dir / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return str(filepath)
    
    def load_json(self, filename: str, default: Any = None) -> Any:
        """Load data from JSON."""
        filepath = self.course_dir / filename
        if not filepath.exists():
            return default
        
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading JSON from {filepath}: {e}")
            return default


def generate_hash(data: str) -> str:
    """Generate a hash for the given data."""
    return hashlib.md5(data.encode()).hexdigest()


def generate_course_id() -> str:
    """Generate a unique course ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    random_hash = generate_hash(str(datetime.utcnow()))[:8]
    return f"course_{timestamp}_{random_hash}"


def generate_task_id() -> str:
    """Generate a unique task ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    random_hash = generate_hash(str(datetime.utcnow()))[:8]
    return f"task_{timestamp}_{random_hash}"


def ensure_directory(path: Union[str, Path]) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_filename(filename: str) -> str:
    """Clean a filename to be safe for filesystem."""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename


def get_file_extension(filename: str) -> str:
    """Get the file extension in lowercase."""
    return Path(filename).suffix.lower()


def is_markdown_file(filename: str) -> bool:
    """Check if a file is a markdown file."""
    extensions = {'.md', '.markdown', '.mdown', '.mkd', '.mdx'}
    return get_file_extension(filename) in extensions


def is_documentation_file(filename: str) -> bool:
    """Check if a file is likely a documentation file."""
    if is_markdown_file(filename):
        return True
    
    # Check for common documentation file patterns
    doc_patterns = ['readme', 'changelog', 'license', 'contributing', 'docs']
    filename_lower = filename.lower()
    
    return any(pattern in filename_lower for pattern in doc_patterns)


def extract_repo_name(repo_url: str) -> str:
    """Extract repository name from URL."""
    if repo_url.endswith('.git'):
        repo_url = repo_url[:-4]
    
    return repo_url.split('/')[-1]


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human-readable format."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to a maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize dictionary for JSON serialization."""
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[key] = [sanitize_dict(item) if isinstance(item, dict) else item for item in value]
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


@contextmanager
def safe_file_operation(filepath: Union[str, Path], mode: str = 'r'):
    """Context manager for safe file operations."""
    filepath = Path(filepath)
    temp_filepath = filepath.with_suffix(filepath.suffix + '.tmp')
    
    try:
        with open(temp_filepath, mode) as f:
            yield f
        
        # If we get here, the operation succeeded
        if temp_filepath.exists():
            temp_filepath.replace(filepath)
    except Exception as e:
        # Clean up temp file on error
        if temp_filepath.exists():
            temp_filepath.unlink()
        raise e


def get_stage_progress_percentage(stage: CourseGenerationStage) -> int:
    """Get progress percentage for a stage."""
    stage_percentages = {
        CourseGenerationStage.CLONE_REPO: 25,
        CourseGenerationStage.DOCUMENT_ANALYSIS: 50,
        CourseGenerationStage.PATHWAY_BUILDING: 75,
        CourseGenerationStage.COURSE_GENERATION: 90,
        CourseGenerationStage.COMPLETED: 100,
        CourseGenerationStage.FAILED: 0,
    }
    return stage_percentages.get(stage, 0)


def validate_repo_url(repo_url: str) -> bool:
    """Validate if a repository URL is valid."""
    # Basic validation - can be extended
    if not repo_url:
        return False
    
    # Check for common Git hosting patterns
    patterns = [
        'github.com',
        'gitlab.com',
        'bitbucket.org',
        '.git'
    ]
    
    return any(pattern in repo_url for pattern in patterns)


def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """Parse frontmatter from markdown content."""
    try:
        import frontmatter
        post = frontmatter.loads(content)
        return post.metadata, post.content
    except ImportError:
        # Fallback if frontmatter not available
        return {}, content
    except Exception:
        return {}, content 