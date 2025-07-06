import dspy
from typing import List
from pydantic import BaseModel, Field
from .models import DocumentType, ComplexityLevel

# =============================================================================
# Enhanced DSPy Signatures
# =============================================================================

class DocumentClassifier(dspy.Signature):
    """Parse and classify a markdown document to extract structured metadata"""
    content: str = dspy.InputField(desc="Raw markdown content")
    overview_context: str = dspy.InputField(desc="Overview of the entire documentation project for context")
    
    # Combined outputs from parsing and classification
    semantic_summary: str = dspy.OutputField(desc="2-3 sentence summary of the document's purpose and content")
    key_concepts: List[str] = dspy.OutputField(desc="List of 3-5 key concepts or terms covered in this document")
    learning_objectives: List[str] = dspy.OutputField(desc="List of what a reader should learn from this document")
    doc_type: DocumentType = dspy.OutputField(desc="Document type: reference, guide, api, example, overview, configuration, troubleshooting, changelog")

class DocumentClusterer(dspy.Signature):
    """Group related documents into learning modules for a comprehensive course"""
    documents_info: str = dspy.InputField(desc="JSON of documents with summaries, key concepts, learning objectives, and metadata")
    target_complexity: str = dspy.InputField(desc="Target complexity level: beginner, intermediate, advanced")
    overview_context: str = dspy.InputField(desc="Overview of the entire documentation project for context")
    
    modules: str = dspy.OutputField(desc="JSON list of modules with name, detailed_description, linked_docs, and learning_objectives. Should include Introduction, core topic modules, and Conclusion modules for a complete learning path")

class WelcomeMessageGenerator(dspy.Signature):
    """Generate comprehensive course information including title, description, and welcome message"""
    repo_name: str = dspy.InputField(desc="Name of the repository/project")
    target_complexity: str = dspy.InputField(desc="Target complexity level")
    modules_overview: str = dspy.InputField(desc="Overview of modules in the path")
    overview_context: str = dspy.InputField(desc="Overview of the entire documentation project for context")
    
    course_title: str = dspy.OutputField(desc="Engaging course title based on repository and complexity level")
    course_description: str = dspy.OutputField(desc="Comprehensive course description explaining what learners will gain")
    welcome_message: str = dspy.OutputField(desc="Welcome message for the learning path")

class ModuleIntroGenerator(dspy.Signature):
    """Generate module introduction with full context"""
    module_title: str = dspy.InputField(desc="Title of the module")
    module_description: str = dspy.InputField(desc="Detailed description of the module")
    learning_objectives: str = dspy.InputField(desc="Comma-separated list of learning objectives")
    overview_context: str = dspy.InputField(desc="Overview of the entire documentation project")
    course_context: str = dspy.InputField(desc="How this fits in the overall course")
    
    introduction: str = dspy.OutputField(desc="Module introduction in markdown format")

class ModuleMainContentGenerator(dspy.Signature):
    """Generate comprehensive module main content from source documents. You MUST use the provided source documents as your primary information source."""
    module_title: str = dspy.InputField(desc="Title of the module")
    module_description: str = dspy.InputField(desc="Detailed description of the module")
    learning_objectives: str = dspy.InputField(desc="Comma-separated list of learning objectives")
    overview_context: str = dspy.InputField(desc="Overview of the entire documentation project")
    source_documents: str = dspy.InputField(desc="Markdown documentation content for this module - USE THIS CONTENT as your primary source")
    
    main_content: str = dspy.OutputField(desc="Comprehensive educational content in markdown format. MUST be valid markdown text starting with headers (# or ##). MUST extract and synthesize information from the provided source_documents. Do NOT generate JSON, package.json, or code configuration files. Do NOT say information is unavailable if it exists in source_documents. Provide detailed explanations based on the source material as educational content for learners.")

class ModuleConclusionGenerator(dspy.Signature):
    """Generate module conclusion"""
    module_title: str = dspy.InputField(desc="Title of the module")
    learning_objectives: str = dspy.InputField(desc="Comma-separated list of learning objectives covered")
    key_concepts: str = dspy.InputField(desc="Comma-separated list of key concepts from the module")
    overview_context: str = dspy.InputField(desc="Overview of the entire documentation project")
    
    conclusion: str = dspy.OutputField(desc="Module conclusion in markdown format")

class ModuleSummaryGenerator(dspy.Signature):
    """Generate module summary/wrap-up"""
    module_title: str = dspy.InputField(desc="Title of the module")
    learning_objectives: str = dspy.InputField(desc="Comma-separated list of learning objectives covered")
    key_concepts: str = dspy.InputField(desc="Comma-separated list of key concepts from the module")
    overview_context: str = dspy.InputField(desc="Overview of the entire documentation project")
    
    summary: str = dspy.OutputField(desc="Module summary in markdown format")

class AssessmentContentGenerator(dspy.Signature):
    """Generate actual assessment content"""
    assessment_title: str = dspy.InputField(desc="Title of the assessment")
    concepts_to_assess: str = dspy.InputField(desc="Comma-separated list of concepts to test")
    module_theme: str = dspy.InputField(desc="Theme of the module")
    
    assessment_content: str = dspy.OutputField(desc="Complete assessment with questions AND detailed answers in markdown format")

class CourseConclusionGenerator(dspy.Signature):
    """Generate course conclusion"""
    course_title: str = dspy.InputField(desc="Title of the course")
    modules_completed: str = dspy.InputField(desc="Summary of modules completed")
    
    conclusion: str = dspy.OutputField(desc="Course conclusion in markdown format") 