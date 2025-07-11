"""
Shared enums for Course Creator backend services.
"""

from enum import Enum


class CourseGenerationStage(str, Enum):
    """Stages of course generation process."""
    CLONE_REPO = "clone_repo"
    DOCUMENT_ANALYSIS = "document_analysis"
    PATHWAY_BUILDING = "pathway_building"
    COURSE_GENERATION = "course_generation"
    COMPLETED = "completed"
    FAILED = "failed"


class StageStatus(str, Enum):
    """Status of a generation stage."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"  # Waiting for user input


class GenerationStatus(str, Enum):
    """Overall generation status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class CourseStatus(str, Enum):
    """Course status with detailed stage tracking."""
    # Initial states
    DRAFT = "draft"
    
    # Stage 1 - Repository cloning
    STAGE1_RUNNING = "stage1_running"
    STAGE1_COMPLETE = "stage1_complete"
    STAGE1_FAILED = "stage1_failed"
    
    # Stage 2 - Document analysis
    STAGE2_RUNNING = "stage2_running"
    STAGE2_COMPLETE = "stage2_complete"
    STAGE2_FAILED = "stage2_failed"
    
    # Stage 3 - Learning pathway building
    STAGE3_RUNNING = "stage3_running"
    STAGE3_COMPLETE = "stage3_complete"
    STAGE3_FAILED = "stage3_failed"
    
    # Stage 4 - Course generation
    STAGE4_RUNNING = "stage4_running"
    STAGE4_COMPLETE = "stage4_complete"
    STAGE4_FAILED = "stage4_failed"
    
    # Legacy statuses for backward compatibility
    GENERATING = "generating"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Types of documentation."""
    GUIDE = "guide"
    REFERENCE = "reference"
    API = "api"
    EXAMPLE = "example"
    OVERVIEW = "overview"
    CONFIGURATION = "configuration"
    TROUBLESHOOTING = "troubleshooting"
    FAQ = "faq"
    TUTORIAL = "tutorial"


class ComplexityLevel(str, Enum):
    """Complexity levels for content."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    # EXPERT = "expert" 