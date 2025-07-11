"""
Shared models for Course Creator backend services.

Contains core data models used by both API server and Celery workers.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator

from .enums import (
    CourseGenerationStage, StageStatus, GenerationStatus, CourseStatus,
    DocumentType, ComplexityLevel
)


# =============================================================================
# Document Models
# =============================================================================

class DocumentMetadata(BaseModel):
    """Metadata extracted from a document."""
    title: str
    doc_type: DocumentType = DocumentType.GUIDE
    key_concepts: List[str] = Field(default_factory=list)
    learning_objectives: List[str] = Field(default_factory=list)
    semantic_summary: str = ""
    headings: List[str] = Field(default_factory=list)
    code_blocks: List[Dict[str, str]] = Field(default_factory=list)
    frontmatter: Dict[str, Any] = Field(default_factory=dict)
    primary_language: Optional[str] = None

class DocumentAnalysis(BaseModel):
    """Comprehensive document analysis result from multi-agent analysis"""
    file_path: str
    title: str
    doc_type: DocumentType
    complexity_level: ComplexityLevel
    key_concepts: List[str]
    learning_objectives: List[str]
    semantic_summary: str
    code_languages: List[str]
    headings: List[str]
    prerequisites: List[str]
    related_topics: List[str]
    
    # Enhanced metadata
    word_count: int = 0
    code_block_count: int = 0
    confidence_score: float = 0.0
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)

class DocumentNode(BaseModel):
    """A document node in the document tree."""
    id: str
    path: str
    filename: str
    content: str
    metadata: DocumentMetadata
    parent_path: Optional[str] = None


class DocumentTree(BaseModel):
    """Tree structure representing analyzed documents."""
    repo_url: str
    repo_name: str
    root_path: str
    nodes: Dict[str, DocumentNode] = Field(default_factory=dict)
    tree_structure: Dict[str, Any] = Field(default_factory=dict)
    cross_references: Dict[str, List[str]] = Field(default_factory=dict)
    last_updated: Optional[datetime] = None
    document_categories: Dict[str, List[str]] = Field(default_factory=dict)
    complexity_distribution: Dict[str, int] = Field(default_factory=dict)
    learning_paths: List[str] = Field(default_factory=list)


# =============================================================================
# Learning & Course Models
# =============================================================================

class AssessmentPoint(BaseModel):
    """Assessment point for a learning module."""
    assessment_id: str
    title: str
    concepts_to_assess: List[str]


class ModuleContent(BaseModel):
    """Content for a learning module."""
    welcome_message: str = ""
    main_content: str = ""
    examples: List[str] = Field(default_factory=list)
    exercises: List[str] = Field(default_factory=list)
    conclusion: str = ""
    summary: str = ""


class LearningModule(BaseModel):
    """Learning module with documents and objectives"""
    module_id: str
    title: str
    description: str
    documents: List[str]
    learning_objectives: List[str]

class LearningPath(BaseModel):
    """Complete learning path with debate-generated structure"""
    path_id: str
    title: str
    description: str
    target_complexity: ComplexityLevel
    modules: List[LearningModule]

class GroupedLearningPath(BaseModel):
    """A structured learning pathway."""
    title: str
    description: str
    target_complexity: ComplexityLevel
    modules: List[LearningModule]
    estimated_duration: str = "2-4 weeks"
    prerequisites: List[str] = Field(default_factory=list)


class GeneratedCourse(BaseModel):
    """A complete generated course."""
    title: str
    description: str
    modules: List[LearningModule]
    pathway: GroupedLearningPath
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Stage Result Models
# =============================================================================

class Stage1Result(BaseModel):
    """Stage 1: Repository cloning result."""
    repo_path: str
    repo_name: str
    available_folders: List[str]
    available_files: List[str]
    suggested_overview_docs: List[str]
    all_overview_candidates: List[str]
    clone_timestamp: datetime = Field(default_factory=datetime.utcnow)


class Stage2Result(BaseModel):
    """Stage 2: Document analysis result."""
    stage1_result: Optional['Stage1Result'] = None
    document_analyses: List[DocumentAnalysis] = Field(default_factory=list)
    total_concepts: int = 0
    avg_complexity: str = ""
    language_distribution: Dict[str, int] = Field(default_factory=dict)
    document_type_distribution: Dict[str, int] = Field(default_factory=dict)
    overview_context: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)


class Stage3Result(BaseModel):
    """Stage 3: Learning pathway result."""
    stage2_result: Optional['Stage2Result'] = None
    learning_paths: List[LearningPath] = Field(default_factory=list)
    target_complexity: Optional[ComplexityLevel] = None
    debate_history: List[str] = Field(default_factory=list)
    additional_instructions: str = ""
    total_modules: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    pathway_timestamp: datetime = Field(default_factory=datetime.utcnow)


class Stage4Result(BaseModel):
    """Stage 4: Course generation result."""
    generated_course_path: str
    export_path: str
    generation_timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Task Management Models
# =============================================================================

class CourseGenerationTask(BaseModel):
    """Main task tracking model."""
    task_id: str
    course_id: str
    user_id: str
    repo_url: str
    current_stage: CourseGenerationStage = CourseGenerationStage.CLONE_REPO
    status: StageStatus = StageStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    stage_data_paths: Dict[str, str] = Field(default_factory=dict)
    include_folders: Optional[List[str]] = None
    overview_doc: Optional[str] = None
    selected_complexity: Optional[ComplexityLevel] = None


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


# =============================================================================
# API Request Models
# =============================================================================

class CourseGenerationRequest(BaseModel):
    """Request to start course generation"""
    repo_url: str = Field(..., description="Repository URL to generate course from")


# =============================================================================
# User Input Models
# =============================================================================

class Stage1UserInput(BaseModel):
    """User input for Stage 1 - Repository selections."""
    include_folders: List[str] = Field(default_factory=list)
    overview_doc: Optional[str] = None
    selection_timestamp: datetime = Field(default_factory=datetime.utcnow)


class Stage2UserInput(BaseModel):
    """User input for Stage 2 - Document Analysis."""
    include_folders: List[str] = Field(default_factory=list)
    overview_doc: Optional[str] = None


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


class Stage3UserInput(BaseModel):
    """User input for Stage 3 - Pathway Building."""
    complexity_level: Optional[str] = Field(default="intermediate", description="Target complexity level: beginner, intermediate, or advanced")
    additional_instructions: Optional[str] = Field(default="", description="Additional instructions for pathway generation")


class Stage4UserInput(BaseModel):
    """User input for Stage 4 - Course Generation."""
    selected_complexity: ComplexityLevel
    custom_pathway: Optional[GroupedLearningPath] = None


# API Input aliases for backward compatibility
Stage1Input = Stage1UserInput
Stage2Input = Stage2UserInput
Stage3Input = Stage3UserInput
Stage4Input = Stage4UserInput


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
    """Course model as stored in database/Redis."""
    course_id: str
    title: str
    description: Optional[str] = None
    status: CourseStatus = CourseStatus.DRAFT
    user_id: str
    cache_dir: str
    generated_course_dir: str
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
    """User model as stored in database/Redis."""
    pass


# =============================================================================
# API Response Models
# =============================================================================

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


class Stage1Response(BaseModel):
    """Response from Stage 1 - Repository Analysis"""
    repo_name: str
    available_folders: List[str]
    available_files: List[str]
    suggested_overview_docs: List[str]
    all_overview_candidates: List[str]  # All available markdown files for overview selection
    total_files: int


class DocumentSummary(BaseModel):
    """Summary of an analyzed document for frontend display"""
    id: str
    filename: str
    path: str
    content: str  # Truncated content for preview
    metadata: Dict[str, Any]


class Stage2Response(BaseModel):
    """Response from Stage 2 - Document Analysis"""
    processed_files_count: int
    failed_files_count: int
    include_folders: List[str]
    overview_doc: Optional[str]
    analysis_timestamp: str
    analyzed_documents: List[DocumentSummary]
    
    @validator('analysis_timestamp', pre=True)
    def convert_datetime_to_string(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v


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