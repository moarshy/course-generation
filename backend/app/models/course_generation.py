from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum

class CourseGenerationStage(str, Enum):
    CLONE_REPO = "clone_repo"
    DOCUMENT_ANALYSIS = "document_analysis"
    PATHWAY_BUILDING = "pathway_building"
    COURSE_GENERATION = "course_generation"
    COMPLETED = "completed"
    FAILED = "failed"

class GenerationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"  # Waiting for user input

class CourseGenerationRequest(BaseModel):
    """Request to start course generation"""
    repo_url: str = Field(..., description="Repository URL to generate course from")

class Stage2Input(BaseModel):
    """User input for Stage 2 - Document Analysis"""
    include_folders: List[str] = Field(default_factory=list, description="Folders to include in analysis")
    overview_doc: Optional[str] = Field(None, description="Overview document filename")

class Stage3Input(BaseModel):
    """User input for Stage 3 - Pathway Selection"""
    selected_path_index: int = Field(..., description="Index of selected learning pathway")
    custom_modifications: Dict[str, Any] = Field(default_factory=dict, description="Custom pathway modifications")

class Stage4Input(BaseModel):
    """User input for Stage 4 - Course Generation"""
    selected_complexity: str = Field(..., description="Selected complexity level")
    custom_pathway: Optional[Dict[str, Any]] = Field(None, description="Custom pathway data")

class GenerationTaskStatus(BaseModel):
    """Status of a generation task"""
    task_id: str
    course_id: str
    current_stage: CourseGenerationStage
    status: GenerationStatus
    progress_percentage: int = Field(0, ge=0, le=100)
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

class Stage1Response(BaseModel):
    """Response from Stage 1 - Repository Analysis"""
    repo_name: str
    available_folders: List[str]
    available_files: List[str]
    suggested_overview_docs: List[str]
    total_files: int

class ModuleSummary(BaseModel):
    """Summary of a learning module"""
    title: str
    theme: str
    description: str

class PathwaySummary(BaseModel):
    """Summary of a learning pathway"""
    index: int
    title: str
    description: str
    complexity: str
    module_count: int
    modules: List[ModuleSummary]

class Stage3Response(BaseModel):
    """Response from Stage 3 - Learning Pathways"""
    pathways: List[PathwaySummary]
    total_documents: int
    repo_name: str

class CourseSummary(BaseModel):
    """Summary of generated course"""
    title: str
    description: str
    module_count: int
    export_path: str

class Stage4Response(BaseModel):
    """Response from Stage 4 - Course Generation"""
    course_summary: CourseSummary
    generation_complete: bool = True

class GenerationStageData(BaseModel):
    """Generic stage data container"""
    stage: CourseGenerationStage
    status: GenerationStatus
    data: Optional[Union[Stage1Response, Stage3Response, Stage4Response, Dict[str, Any]]] = None
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow) 