"""
Shared models and utilities for Course Creator backend services.

This package contains essential models, enums, and utilities used by
the 4-service architecture.
"""

# Export essential models
from .models import (
    # Core AI processing models
    DocumentAnalysis,
    
    # API request/response models
    CourseGenerationRequest, Stage1Input, Stage2Input, Stage3Input, Stage4Input,
    DocumentMetadataUpdate, UpdateDocumentRequest, ModuleUpdate, ModuleCreate, PathwayUpdate,
    ModuleReorderRequest, UpdateModuleRequest, CreateModuleRequest, UpdatePathwayRequest,
    
    # Course models
    CourseCreate, CourseUpdate, Course, CourseInDB,
    
    # User models
    UserBase, UserCreate, UserUpdate, UserSync, User, UserInDB,
    
    # Response models
    GenerationTaskStatus, ModuleSummary, PathwaySummary,
    Stage1Response, DocumentSummary, Stage2Response, Stage3Response, 
    CourseSummary, Stage4Response, GenerationStageData
)

# Export enums
from .enums import (
    CourseGenerationStage, StageStatus, GenerationStatus, CourseStatus,
    DocumentType, ComplexityLevel
)

# Export essential utilities  
from .utils import parse_json_safely, get_n_words


__version__ = "0.1.0" 