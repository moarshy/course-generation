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
    """Course status."""
    DRAFT = "draft"
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