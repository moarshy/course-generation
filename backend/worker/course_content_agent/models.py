from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

# =============================================================================
# Enums
# =============================================================================

class DocumentType(Enum):
    """Document type"""
    REFERENCE = "reference"
    GUIDE = "guide"
    API = "api"
    EXAMPLE = "example"
    OVERVIEW = "overview"
    CONFIG = "configuration"
    TROUBLESHOOTING = "troubleshooting"
    CHANGELOG = "changelog"

class ComplexityLevel(Enum):
    """Complexity level"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

# =============================================================================
# Data Models
# =============================================================================

class DocumentMetadata(BaseModel):
    """Enhanced metadata extracted from a document"""
    model_config = ConfigDict(use_enum_values=True)
    
    # Basic extracted metadata
    title: str
    headings: List[str]
    code_blocks: List[Dict[str, str]] 
    frontmatter: Dict[str, Any]
    primary_language: Optional[str] = None
    
    # LLM-enhanced metadata
    doc_type: Optional[DocumentType] = DocumentType.GUIDE
    key_concepts: List[str] = Field(default_factory=list)
    learning_objectives: List[str] = Field(default_factory=list)
    semantic_summary: Optional[str] = None

class DocumentNode(BaseModel):
    """Represents a single documentation file"""
    model_config = ConfigDict(use_enum_values=True)
    
    id: str
    path: str  # relative path from repo root
    filename: str
    content: str
    metadata: DocumentMetadata
    parent_path: Optional[str] = None
    children_paths: List[str] = Field(default_factory=list)
    
    # Enhanced relationships
    related_documents: List[str] = Field(default_factory=list)
    prerequisite_documents: List[str] = Field(default_factory=list)
    follow_up_documents: List[str] = Field(default_factory=list)
    
class DocumentTree(BaseModel):
    """Complete documentation tree structure"""
    model_config = ConfigDict(use_enum_values=True)
    
    repo_url: str
    repo_name: str
    root_path: str
    nodes: Dict[str, DocumentNode] = Field(..., description="Path to node mapping")
    tree_structure: Dict[str, List[str]] = Field(..., description="Folder to list of files/folders mapping")
    cross_references: Dict[str, List[str]] = Field(..., description="File to list of referenced files mapping")
    last_updated: datetime = Field(default_factory=datetime.now)
    
    # Enhanced tree-level metadata
    document_categories: Dict[str, List[str]] = Field(default_factory=dict)  # Changed from DocumentType keys
    complexity_distribution: Dict[str, int] = Field(default_factory=dict)  # Changed from ComplexityLevel keys
    learning_paths: List[List[str]] = Field(default_factory=list)

class AssessmentPoint(BaseModel):
    """Simple assessment point within a learning module"""
    assessment_id: str
    title: str
    concepts_to_assess: List[str]

class LearningModule(BaseModel):
    """A group of related documents forming a learning unit"""
    module_id: str
    title: str
    theme: str  # Core concept/technology focus
    description: str
    learning_objectives: List[str]
    linked_documents: List[str]  
    target_complexity: ComplexityLevel
    assessment: AssessmentPoint

class GroupedLearningPath(BaseModel):
    """Learning path with organized modules"""
    model_config = ConfigDict(use_enum_values=True)
    
    pathway_id: str
    title: str
    description: str
    target_complexity: ComplexityLevel
    modules: List[LearningModule]
    welcome_message: str

class ModuleContent(BaseModel):
    """Generated content for a single module - all 5 components"""
    module_id: str
    title: str = Field(..., description="The title of the learning module.")
    description: str = Field(..., description="A detailed description of the module's content and goals.")
    learning_objectives: List[str] = Field(default_factory=list, description="List of learning objectives for the module.")
    introduction: str  # Module introduction content (markdown)
    main_content: str  # Synthesized main content from source documents (markdown)
    conclusion: str  # Module conclusion content (markdown)
    assessment: str  # Assessment questions with answers (markdown)
    summary: str  # Module summary/wrap-up (markdown)

class GeneratedCourse(BaseModel):
    """Complete generated course"""
    course_id: str
    title: str
    description: str
    welcome_message: str  # Course introduction
    modules: List[ModuleContent]
    course_conclusion: str  # Final wrap-up 