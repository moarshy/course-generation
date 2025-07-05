from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import pickle
import os
from pathlib import Path

# Re-export course content agent models
from app.course_content_agent.models import (
    DocumentType, ComplexityLevel, DocumentMetadata, DocumentNode,
    DocumentTree, AssessmentPoint, LearningModule, GroupedLearningPath,
    ModuleContent, GeneratedCourse
)

class CourseGenerationStage(str, Enum):
    CLONE_REPO = "clone_repo"
    DOCUMENT_ANALYSIS = "document_analysis"
    PATHWAY_BUILDING = "pathway_building"
    COURSE_GENERATION = "course_generation"
    COMPLETED = "completed"
    FAILED = "failed"

class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"  # Waiting for user input

class CourseGenerationTask(BaseModel):
    """Main task tracking model"""
    task_id: str
    course_id: str
    user_id: str
    repo_url: str
    current_stage: CourseGenerationStage = CourseGenerationStage.CLONE_REPO
    status: StageStatus = StageStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    
    # Stage-specific data paths (pickle files)
    stage_data_paths: Dict[str, str] = Field(default_factory=dict)
    
    # User selections
    include_folders: Optional[List[str]] = None
    overview_doc: Optional[str] = None
    selected_complexity: Optional[ComplexityLevel] = None

class Stage1Result(BaseModel):
    """Stage 1: Repository cloning result"""
    repo_path: str
    repo_name: str
    available_folders: List[str]
    available_files: List[str]
    suggested_overview_docs: List[str]
    clone_timestamp: datetime = Field(default_factory=datetime.utcnow)

class Stage2Result(BaseModel):
    """Stage 2: Document analysis result"""
    document_tree_path: str  # Path to pickled DocumentTree
    processed_files_count: int
    failed_files_count: int
    include_folders: List[str]
    overview_doc: Optional[str] = None
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)

class Stage3Result(BaseModel):
    """Stage 3: Learning pathway result"""
    learning_paths_path: str  # Path to pickled List[GroupedLearningPath]
    selected_path_index: Optional[int] = None
    custom_modifications: Dict[str, Any] = Field(default_factory=dict)
    pathway_timestamp: datetime = Field(default_factory=datetime.utcnow)

class Stage4Result(BaseModel):
    """Stage 4: Course generation result"""
    generated_course_path: str  # Path to pickled GeneratedCourse
    export_path: str  # Path to exported markdown files
    generation_timestamp: datetime = Field(default_factory=datetime.utcnow)

class StageDataManager:
    """Manages pickle serialization/deserialization of stage data"""
    
    def __init__(self, base_data_dir: str = "../data"):
        self.base_data_dir = Path(base_data_dir)
        self.base_data_dir.mkdir(exist_ok=True)
    
    def get_stage_data_dir(self, user_id: str, course_id: str) -> Path:
        """Get the stage data directory for a specific course"""
        safe_user_id = user_id.replace('|', '_').replace('/', '_')
        stage_dir = self.base_data_dir / safe_user_id / course_id / "stages"
        stage_dir.mkdir(parents=True, exist_ok=True)
        return stage_dir
    
    def save_stage_data(self, user_id: str, course_id: str, stage: CourseGenerationStage, data: Any) -> str:
        """Save stage data to pickle file and return the path"""
        stage_dir = self.get_stage_data_dir(user_id, course_id)
        file_path = stage_dir / f"{stage.value}.pkl"
        
        with open(file_path, 'wb') as f:
            pickle.dump(data, f)
        
        return str(file_path)
    
    def load_stage_data(self, user_id: str, course_id: str, stage: CourseGenerationStage) -> Any:
        """Load stage data from pickle file"""
        stage_dir = self.get_stage_data_dir(user_id, course_id)
        file_path = stage_dir / f"{stage.value}.pkl"
        
        if not file_path.exists():
            raise FileNotFoundError(f"Stage data not found for {stage.value}")
        
        with open(file_path, 'rb') as f:
            return pickle.load(f)
    
    def stage_data_exists(self, user_id: str, course_id: str, stage: CourseGenerationStage) -> bool:
        """Check if stage data exists"""
        stage_dir = self.get_stage_data_dir(user_id, course_id)
        file_path = stage_dir / f"{stage.value}.pkl"
        return file_path.exists()
    
    def cleanup_stage_data(self, user_id: str, course_id: str):
        """Clean up all stage data for a course"""
        import shutil
        stage_dir = self.get_stage_data_dir(user_id, course_id)
        if stage_dir.exists():
            shutil.rmtree(stage_dir)

# User interaction models for each stage
class Stage2UserInput(BaseModel):
    """User input for Stage 2"""
    include_folders: List[str] = Field(default_factory=list)
    overview_doc: Optional[str] = None

class Stage3UserInput(BaseModel):
    """User input for Stage 3"""
    selected_path_index: int
    custom_modifications: Dict[str, Any] = Field(default_factory=dict)
    
class Stage4UserInput(BaseModel):
    """User input for Stage 4"""
    selected_complexity: ComplexityLevel
    custom_pathway: Optional[GroupedLearningPath] = None 