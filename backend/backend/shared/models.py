"""
Shared models for Course Creator backend services.

Contains essential data models for the 4-service architecture.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator

from .enums import (
    CourseGenerationStage, StageStatus, GenerationStatus, CourseStatus,
    DocumentType, ComplexityLevel
)


# =============================================================================
# Document Models (for AI processing)
# =============================================================================


class DocumentAnalysis(BaseModel):
    """Document analysis result from AI processing."""
    file_path: str
    title: str
    doc_type: DocumentType
    complexity_level: ComplexityLevel
    key_concepts: List[str]
    learning_objectives: List[str]
    semantic_summary: str
    prerequisites: List[str]
    related_topics: List[str]
    headings: List[str] = Field(default_factory=list)
    code_languages: List[str] = Field(default_factory=list)
    frontmatter: Dict[str, Any] = Field(default_factory=dict)
    word_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 0.0
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)



# =============================================================================
# API Request/Response Models
# =============================================================================

class CourseGenerationRequest(BaseModel):
    """Request to start course generation."""
    repo_url: str = Field(..., description="Repository URL to generate course from")

class Stage1Input(BaseModel):
    """User input for Stage 1 - Repository selections."""
    include_folders: List[str] = Field(default_factory=list)
    overview_doc: Optional[str] = None

class Stage2Input(BaseModel):
    """User input for Stage 2 - Document Analysis."""
    complexity_level: str = Field(default="intermediate", description="Target complexity level")
    additional_info: Optional[str] = Field(None, description="Additional instructions for analysis")

class DocumentMetadataUpdate(BaseModel):
    """Update data for a document's metadata."""
    doc_type: Optional[DocumentType] = None
    semantic_summary: Optional[str] = None
    key_concepts: Optional[List[str]] = None
    learning_objectives: Optional[List[str]] = None

class UpdateDocumentRequest(BaseModel):
    """Request to update a document's metadata."""
    document_id: str
    metadata_updates: DocumentMetadataUpdate

class ModuleUpdate(BaseModel):
    """Update data for a learning module."""
    title: Optional[str] = None
    description: Optional[str] = None
    learning_objectives: Optional[List[str]] = None
    linked_documents: Optional[List[str]] = None
    theme: Optional[str] = None
    target_complexity: Optional[ComplexityLevel] = None

class ModuleCreate(BaseModel):
    """Data for creating a new learning module."""
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=1000)
    learning_objectives: List[str] = Field(default_factory=list)
    linked_documents: List[str] = Field(default_factory=list)
    theme: str = Field(default="General")
    target_complexity: ComplexityLevel = ComplexityLevel.INTERMEDIATE

class PathwayUpdate(BaseModel):
    """Update data for a learning pathway."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    target_complexity: Optional[ComplexityLevel] = None
    estimated_duration: Optional[str] = None
    prerequisites: Optional[List[str]] = None

class ModuleReorderRequest(BaseModel):
    """Request to reorder modules in a pathway."""
    module_order: List[int] = Field(..., description="New order of module indices")

class UpdateModuleRequest(BaseModel):
    """Request to update a specific module."""
    pathway_index: int
    module_index: int
    module_updates: ModuleUpdate

class CreateModuleRequest(BaseModel):
    """Request to create a new module in a pathway."""
    pathway_index: int
    module_data: ModuleCreate

class UpdatePathwayRequest(BaseModel):
    """Request to update pathway details."""
    pathway_index: int
    pathway_updates: PathwayUpdate

class Stage3Input(BaseModel):
    """User input for Stage 3 - Pathway Building."""
    complexity_level: Optional[str] = Field(default="intermediate")
    additional_instructions: Optional[str] = Field(default="")

class Stage4Input(BaseModel):
    """User input for Stage 4 - Course Generation."""
    selected_complexity: ComplexityLevel


# =============================================================================
# Course Models
# =============================================================================

class CourseCreate(BaseModel):
    """Data for creating a new course."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

class CourseUpdate(BaseModel):
    """Data for updating an existing course."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[CourseStatus] = None

class Course(BaseModel):
    """Course model for API responses."""
    course_id: str
    title: str
    description: Optional[str] = None
    status: CourseStatus = CourseStatus.DRAFT
    created_at: datetime
    updated_at: datetime

class CourseInDB(BaseModel):
    """Course model as stored in database."""
    course_id: str
    title: str
    description: Optional[str] = None
    status: CourseStatus = CourseStatus.DRAFT
    user_id: str
    repo_url: Optional[str] = None
    repo_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# User Models
# =============================================================================

class UserBase(BaseModel):
    """Base user model."""
    email: str
    name: str
    picture: Optional[str] = None
    email_verified: bool = False

class UserCreate(UserBase):
    """Data for creating a new user."""
    auth0_id: str

class UserUpdate(BaseModel):
    """Data for updating a user."""
    name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: Optional[bool] = None

class UserSync(UserBase):
    """Data for syncing user from Auth0."""
    auth0_id: str

class User(UserBase):
    """User model for API responses."""
    auth0_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class UserInDB(User):
    """User model as stored in database."""
    pass


# =============================================================================
# API Response Models
# =============================================================================

class GenerationTaskStatus(BaseModel):
    """Status of a generation task for API responses."""
    task_id: str
    course_id: str
    current_stage: CourseGenerationStage
    status: GenerationStatus
    progress_percentage: int = Field(0, ge=0, le=100)
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

class ModuleSummary(BaseModel):
    """Summary of a learning module."""
    title: str
    theme: str
    description: str

class PathwaySummary(BaseModel):
    """Summary of a learning pathway."""
    index: int
    title: str
    description: str
    complexity: str
    module_count: int
    modules: List[ModuleSummary]

class Stage1Response(BaseModel):
    """Response from Stage 1 - Repository Analysis."""
    repo_name: str
    available_folders: List[str]
    available_files: List[str]
    suggested_overview_docs: List[str]
    all_overview_candidates: List[str]
    total_files: int

class DocumentSummary(BaseModel):
    """Summary of an analyzed document for frontend display."""
    id: str
    filename: str
    path: str
    content: str  # Truncated content for preview
    metadata: Dict[str, Any]

class Stage2Response(BaseModel):
    """Response from Stage 2 - Document Analysis."""
    processed_files_count: int
    failed_files_count: int
    include_folders: List[str]
    overview_doc: Optional[str]
    analysis_timestamp: Optional[str] = None
    analyzed_documents: List[DocumentSummary]
    
    @validator('analysis_timestamp', pre=True)
    def convert_datetime_to_string(cls, v):
        if v is None:
            return datetime.utcnow().isoformat()
        if isinstance(v, datetime):
            return v.isoformat()
        return v

class Stage3Response(BaseModel):
    """Response from Stage 3 - Learning Pathways."""
    pathways: List[PathwaySummary]
    total_documents: int
    repo_name: str

class CourseSummary(BaseModel):
    """Summary of generated course."""
    title: str
    description: str
    module_count: int
    export_path: str

class Stage4Response(BaseModel):
    """Response from Stage 4 - Course Generation."""
    course_summary: CourseSummary
    generation_complete: bool = True

class GenerationStageData(BaseModel):
    """Generic stage data container."""
    stage: CourseGenerationStage
    status: GenerationStatus
    data: Optional[Union[Stage1Response, Stage3Response, Stage4Response, Dict[str, Any]]] = None
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


 