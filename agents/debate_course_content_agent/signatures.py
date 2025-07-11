import dspy
from typing import List
from pydantic import BaseModel, Field
from debate_course_content_agent.models import DocumentType, ComplexityLevel, LearningPath

# =============================================================================
# Multi-Agent Document Analysis Signatures
# =============================================================================

class BasicMetadataExtractor(dspy.Signature):
    """Extract basic metadata from document content"""
    agent_instructions: str = dspy.InputField(desc="Instructions for the agent")
    content: str = dspy.InputField(desc="Raw document content")
    filename: str = dspy.InputField(desc="Document filename")
    
    title: str = dspy.OutputField(desc="Document title")
    headings: str = dspy.OutputField(desc="JSON list of document headings")
    code_languages: str = dspy.OutputField(desc="JSON list of programming languages found")

class DocumentClassifier(dspy.Signature):
    """Classify document type and complexity level"""
    agent_instructions: str = dspy.InputField(desc="Instructions for the agent")
    content: str = dspy.InputField(desc="Document content")
    title: str = dspy.InputField(desc="Document title")
    overview_context: str = dspy.InputField(desc="Overview context from the repository")

    doc_type: DocumentType = dspy.OutputField(desc="Document type classification")
    complexity_level: ComplexityLevel = dspy.OutputField(desc="Complexity level assessment")

class ConceptExtractor(dspy.Signature):
    """Extract key concepts and learning objectives from document"""
    agent_instructions: str = dspy.InputField(desc="Instructions for the agent")
    content: str = dspy.InputField(desc="Document content")
    doc_type: str = dspy.InputField(desc="Document type")
    title: str = dspy.InputField(desc="Document title")
    
    key_concepts: str = dspy.OutputField(desc="JSON list of 3-5 key concepts")
    learning_objectives: str = dspy.OutputField(desc="JSON list of learning objectives")

class SemanticAnalyzer(dspy.Signature):
    """Generate semantic summary and analyze relationships"""
    agent_instructions: str = dspy.InputField(desc="Instructions for the agent")
    content: str = dspy.InputField(desc="Document content")
    key_concepts: str = dspy.InputField(desc="Key concepts found")
    doc_type: str = dspy.InputField(desc="Document type")
    
    semantic_summary: str = dspy.OutputField(desc="5-7 sentence semantic summary")
    prerequisites: str = dspy.OutputField(desc="JSON list of prerequisites")
    related_topics: str = dspy.OutputField(desc="JSON list of related topics")

# =============================================================================
# Debate System Signatures
# =============================================================================

class LearningPathProposer(dspy.Signature):
    """Propose a learning path structure with modules and document organization"""
    agent_instructions: str = dspy.InputField(desc="Instructions for the agent")
    documents_with_content: str = dspy.InputField(desc="Complete document information including content")
    target_complexity: str = dspy.InputField(desc="Target complexity level")
    overview_context: str = dspy.InputField(desc="Project overview for context")
    previous_critique: str = dspy.InputField(desc="Previous critique to address (empty for first round)")
    
    learning_path_proposal: LearningPath = dspy.OutputField(desc="JSON structured learning path with modules, documents, and learning objectives")
    reasoning: str = dspy.OutputField(desc="Explanation of the learning progression logic and how critique was addressed")

class LearningPathCritic(dspy.Signature):
    """Critique a learning path proposal and suggest specific improvements"""
    agent_instructions: str = dspy.InputField(desc="Instructions for the agent")
    learning_path_proposal: str = dspy.InputField(desc="Proposed learning path to critique")
    documents_with_content: str = dspy.InputField(desc="Complete document information for reference")
    target_complexity: str = dspy.InputField(desc="Target complexity level")
    overview_context: str = dspy.InputField(desc="Project overview for context")
    
    critique: str = dspy.OutputField(desc="Detailed critique with specific issues and improvement suggestions")
    severity: str = dspy.OutputField(desc="Overall assessment: 'major_issues', 'minor_issues', or 'acceptable'")

# =============================================================================
# Module Content Generation Signatures
# =============================================================================

class ModuleContentProposer(dspy.Signature):
    """Generate comprehensive module content from learning module specification"""
    agent_instructions: str = dspy.InputField(desc="Instructions for the agent")
    learning_module: str = dspy.InputField(desc="Learning module specification with title, description, objectives")
    source_documents: str = dspy.InputField(desc="Source documents content for this module")
    target_complexity: str = dspy.InputField(desc="Target complexity level")
    overview_context: str = dspy.InputField(desc="Project overview for context")
    previous_critique: str = dspy.InputField(desc="Previous critique to address (empty for first round)")
    
    introduction: str = dspy.OutputField(desc="Engaging module introduction in markdown format (2-3 paragraphs)")
    main_content: str = dspy.OutputField(desc="Comprehensive main content synthesized from source documents in markdown format. Must be educational, well-structured, and include examples from the source material.")
    conclusion: str = dspy.OutputField(desc="Module conclusion that reinforces key concepts in markdown format (1-2 paragraphs)")
    assessment: str = dspy.OutputField(desc="Assessment questions with detailed answers in markdown format (3-5 questions)")
    summary: str = dspy.OutputField(desc="Concise module summary highlighting key takeaways in markdown format (1 paragraph)")
    reasoning: str = dspy.OutputField(desc="Explanation of content structure decisions and how critique was addressed")

class ModuleContentCritic(dspy.Signature):
    """Critique module content for educational effectiveness and quality"""
    agent_instructions: str = dspy.InputField(desc="Instructions for the agent")
    learning_module: str = dspy.InputField(desc="Learning module specification")
    proposed_introduction: str = dspy.InputField(desc="Proposed introduction content")
    proposed_main_content: str = dspy.InputField(desc="Proposed main content")
    proposed_conclusion: str = dspy.InputField(desc="Proposed conclusion content")
    proposed_assessment: str = dspy.InputField(desc="Proposed assessment content")
    proposed_summary: str = dspy.InputField(desc="Proposed summary content")
    source_documents: str = dspy.InputField(desc="Source documents for reference")
    target_complexity: str = dspy.InputField(desc="Target complexity level")
    overview_context: str = dspy.InputField(desc="Project overview for context")
    
    critique: str = dspy.OutputField(desc="Detailed critique covering content quality, pedagogical effectiveness, and alignment with learning objectives")
    severity: str = dspy.OutputField(desc="Overall assessment: 'major_issues', 'minor_issues', or 'acceptable'")

 