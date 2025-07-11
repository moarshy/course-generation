from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

# =============================================================================
# Enums
# =============================================================================

class DocumentType(str, Enum):
    REFERENCE = "reference"
    GUIDE = "guide"
    API = "api"
    EXAMPLE = "example"
    OVERVIEW = "overview"
    CONFIG = "configuration"
    TROUBLESHOOTING = "troubleshooting"
    CHANGELOG = "changelog"

class ComplexityLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

# =============================================================================
# Document Analysis Models
# =============================================================================

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

# =============================================================================
# Learning Path Models
# =============================================================================

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

# =============================================================================
# Module Content Models
# =============================================================================

class ModuleContent(BaseModel):
    """Generated content for a single module"""
    module_id: str
    title: str
    description: str
    learning_objectives: List[str]
    introduction: str
    main_content: str
    conclusion: str
    assessment: str
    summary: str

# =============================================================================
# Module Content Debate Models
# =============================================================================

class ModuleDebateRound(BaseModel):
    """Single round of module content debate"""
    round_number: int
    proposal: Optional[ModuleContent] = None
    proposal_reasoning: str = ""
    critique: str = ""
    severity: str = ""  # 'major_issues', 'minor_issues', 'acceptable'
    error_message: str = ""

class ModuleDebateHistory(BaseModel):
    """Complete debate history for module content generation"""
    module_id: str
    rounds: List[ModuleDebateRound] = Field(default_factory=list)
    final_content: Optional[ModuleContent] = None
    success: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)

 