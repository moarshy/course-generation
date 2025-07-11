"""
Stage 4: Course Generator Agent
Multi-agent course content generation with debate system
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

import dspy
import redis

from backend.shared.models import (
    DocumentAnalysis, ComplexityLevel
)
from backend.shared.utils import get_n_words
from backend.core.config import settings, AGENT_INSTRUCTIONS
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# =============================================================================
# DSPy-Compatible Models (matching debate_course_content_agent structure)
# =============================================================================

class LearningModule(BaseModel):
    """Learning module with documents and objectives"""
    module_id: str
    title: str
    description: str
    documents: List[str]
    learning_objectives: List[str]

class ModuleContent(BaseModel):
    """Generated content for a single module - all 5 components"""
    module_id: str
    title: str
    description: str
    learning_objectives: List[str] = Field(default_factory=list)
    introduction: str  # Module introduction content (markdown)
    main_content: str  # Synthesized main content from source documents (markdown)
    conclusion: str  # Module conclusion content (markdown)
    assessment: str  # Assessment questions with answers (markdown)
    summary: str  # Module summary/wrap-up (markdown)

class ModuleDebateRound(BaseModel):
    """Single round of module content debate"""
    round_number: int
    proposal: Optional[ModuleContent] = None
    proposal_reasoning: str = ""
    critique: str = ""
    severity: str = ""  # 'major_issues', 'minor_issues', 'acceptable'
    error_message: Optional[str] = None

class ModuleDebateHistory(BaseModel):
    """Complete debate history for a module"""
    module_id: str
    rounds: List[ModuleDebateRound] = Field(default_factory=list)
    final_content: Optional[ModuleContent] = None
    success: bool = False

class Stage3Result(BaseModel):
    """Local Stage3Result model for s4 processing"""
    learning_paths: List[Any] = Field(default_factory=list)  # Will contain LearningPath objects
    target_complexity: Optional[ComplexityLevel] = None
    stage2_result: Optional[Any] = None  # Contains document_analyses

class Stage4Result(BaseModel):
    """Local Stage4Result model for s4 processing"""
    stage3_result: Optional[Stage3Result] = None
    generated_content: List[ModuleContent] = Field(default_factory=list)
    debate_histories: List[ModuleDebateHistory] = Field(default_factory=list)
    additional_instructions: str = ""
    total_modules_processed: int = 0
    successful_generations: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

# =============================================================================
# Configuration
# =============================================================================

class S4Config:
    """Stage 4 Configuration"""
    MAX_DEBATES = settings.MAX_DEBATES
    MAX_CONTENT_WORDS = settings.MAX_CONTENT_WORDS
    MAX_OVERVIEW_WORDS = settings.MAX_OVERVIEW_WORDS

# =============================================================================
# Utility Functions
# =============================================================================

def prepare_source_documents_content(learning_module: LearningModule, 
                                   document_analyses: List[DocumentAnalysis], 
                                   max_words: int) -> str:
    """Prepare source documents content for module content generation"""
    source_content = []
    doc_lookup = {doc.file_path: doc for doc in document_analyses}
    
    for doc_path in learning_module.documents:
        if doc_path in doc_lookup:
            doc = doc_lookup[doc_path]
            try:
                with open(doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Truncate content if too long
                content_excerpt = get_n_words(content, max_words)
                
                doc_content = f"""## {doc.title}
{content_excerpt}
"""
                source_content.append(doc_content)
            except Exception as e:
                logger.warning(f"Could not read {doc_path}: {e}")
                continue
    
    return "\n".join(source_content)

def create_fallback_content(learning_module: LearningModule, 
                          document_analyses: List[DocumentAnalysis]) -> ModuleContent:
    """Create simple fallback content when debate fails"""
    logger.warning(f"Creating fallback content for module: {learning_module.title}")
    
    # Get basic content from source documents
    source_content = prepare_source_documents_content(
        learning_module, document_analyses, S4Config.MAX_CONTENT_WORDS
    )
    
    return ModuleContent(
        module_id=learning_module.module_id,
        title=learning_module.title,
        description=learning_module.description,
        learning_objectives=learning_module.learning_objectives,
        introduction=f"# {learning_module.title}\n\n{learning_module.description}",
        main_content=source_content or f"## {learning_module.title}\n\nContent for this module is being developed.",
        conclusion=f"## Conclusion\n\nThis concludes the {learning_module.title} module.",
        assessment=f"## Assessment\n\nReview the key concepts from {learning_module.title}.",
        summary=f"## Summary\n\nKey takeaways from {learning_module.title}."
    )

def prepare_module_info(learning_module: LearningModule) -> str:
    """Prepare learning module information for debate"""
    return json.dumps({
        'module_id': learning_module.module_id,
        'title': learning_module.title,
        'description': learning_module.description,
        'learning_objectives': learning_module.learning_objectives,
        'documents': learning_module.documents
    }, indent=2)

# =============================================================================
# DSPy Signatures
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

# =============================================================================
# Debate Module Content Generator
# =============================================================================

class DebateModuleContentGenerator(dspy.Module):
    """Generate module content through multi-agent debate"""
    
    def __init__(self):
        super().__init__()
        self.proposer = dspy.ChainOfThought(ModuleContentProposer)
        self.critic = dspy.ChainOfThought(ModuleContentCritic)
    
    def _run_proposal_round(self, round_num: int, instructions: str, learning_module_str: str,
                           source_documents: str, target_complexity: str, overview_context: str,
                           previous_critique: str) -> Tuple[Optional[ModuleContent], str]:
        """Run a single proposal round"""
        try:
            proposal_result = self.proposer(
                agent_instructions=instructions,
                learning_module=learning_module_str,
                source_documents=source_documents,
                target_complexity=target_complexity,
                overview_context=overview_context,
                previous_critique=previous_critique
            )
            
            # Create ModuleContent from structured outputs
            module_content = ModuleContent(
                module_id=learning_module_str.split('"module_id": "')[1].split('"')[0],
                title=proposal_result.main_content.split('\n')[0].replace('# ', ''),
                description=learning_module_str.split('"description": "')[1].split('"')[0],
                learning_objectives=[],  # Will be parsed separately
                introduction=proposal_result.introduction,
                main_content=proposal_result.main_content,
                conclusion=proposal_result.conclusion,
                assessment=proposal_result.assessment,
                summary=proposal_result.summary
            )
            
            logger.info(f"📝 Proposer created content sections")
            logger.info(f"📝 Reasoning: {proposal_result.reasoning[:200]}...")
            
            return module_content, proposal_result.reasoning
            
        except Exception as e:
            logger.error(f"❌ Proposer failed in round {round_num}: {e}")
            return None, f"Proposer failed: {str(e)}"
    
    def _run_critique_round(self, round_num: int, instructions: str, learning_module_str: str,
                           module_content: ModuleContent, source_documents: str,
                           target_complexity: str, overview_context: str) -> Tuple[str, str]:
        """Run a single critique round"""
        try:
            critique_result = self.critic(
                agent_instructions=instructions,
                learning_module=learning_module_str,
                proposed_introduction=module_content.introduction,
                proposed_main_content=module_content.main_content,
                proposed_conclusion=module_content.conclusion,
                proposed_assessment=module_content.assessment,
                proposed_summary=module_content.summary,
                source_documents=source_documents,
                target_complexity=target_complexity,
                overview_context=overview_context
            )
            
            logger.info(f"🔍 Critic assessment: {critique_result.severity}")
            logger.info(f"🔍 Critique: {critique_result.critique[:200]}...")
            
            return critique_result.critique, critique_result.severity
            
        except Exception as e:
            logger.error(f"❌ Critic failed in round {round_num}: {e}")
            return f"Critic failed: {str(e)}", "error"
    
    def generate_module_content(self,
                              learning_module: LearningModule,
                              document_analyses: List[DocumentAnalysis],
                              target_complexity: ComplexityLevel,
                              overview_context: str = "",
                              additional_instructions: str = "") -> Tuple[Optional[ModuleContent], ModuleDebateHistory]:
        """Generate complete module content through iterative debate process"""
        
        logger.info(f"🎭 Starting module content generation for: {learning_module.title}")
        
        # Initialize debate history
        history = ModuleDebateHistory(module_id=learning_module.module_id)
        
        # Prepare inputs
        learning_module_str = prepare_module_info(learning_module)
        source_documents = prepare_source_documents_content(
            learning_module, document_analyses, S4Config.MAX_CONTENT_WORDS
        )
        overview_trimmed = get_n_words(overview_context, S4Config.MAX_OVERVIEW_WORDS)
        
        # Format instructions
        if additional_instructions:
            instructions = f"{AGENT_INSTRUCTIONS}\n\nAdditional instructions: {additional_instructions}"
        else:
            instructions = AGENT_INSTRUCTIONS
        
        current_proposal = None
        current_critique = ""
        
        # Iterative debate process
        for round_num in range(1, S4Config.MAX_DEBATES + 1):
            logger.info(f"🔄 Module Content Debate Round {round_num}")
            
            debate_round = ModuleDebateRound(round_number=round_num)
            
            # Proposer creates/refines module content
            current_proposal, reasoning = self._run_proposal_round(
                round_num, instructions, learning_module_str, source_documents,
                target_complexity.value, overview_trimmed, current_critique
            )
            
            if current_proposal is None:
                debate_round.error_message = reasoning
                history.rounds.append(debate_round)
                
                # If first round fails completely, use fallback
                if round_num == 1:
                    fallback = create_fallback_content(learning_module, document_analyses)
                    history.final_content = fallback
                    history.success = False
                    return fallback, history
                else:
                    break
            
            debate_round.proposal = current_proposal
            debate_round.proposal_reasoning = reasoning
            
            # Critic evaluates the content
            current_critique, severity = self._run_critique_round(
                round_num, instructions, learning_module_str, current_proposal,
                source_documents, target_complexity.value, overview_trimmed
            )
            
            debate_round.critique = current_critique
            debate_round.severity = severity
            
            history.rounds.append(debate_round)
            
            # If acceptable, stop iterating
            if severity == "acceptable":
                logger.info("✅ Module content accepted by critic")
                history.final_content = current_proposal
                history.success = True
                return current_proposal, history
        
        # Return the last proposal
        if current_proposal:
            history.final_content = current_proposal
            history.success = True
        
        return current_proposal, history

# =============================================================================
# Progress Tracker
# =============================================================================

class S4ProgressTracker:
    """Tracks and updates Stage 4 progress"""
    
    def __init__(self, redis_client: redis.Redis, task_id: str):
        self.redis = redis_client
        self.task_id = task_id
        self.progress_key = f"task:{task_id}:progress"
    
    def update_progress(self, stage: str, progress: int, message: str = ""):
        """Update progress in Redis"""
        try:
            progress_data = {
                'stage': stage,
                'progress': progress,
                'message': message,
                'timestamp': str(int(time.time()))
            }
            
            self.redis.hset(self.progress_key, mapping=progress_data)
            self.redis.expire(self.progress_key, 3600)  # Expire after 1 hour
            
            logger.info(f"Stage 4 Progress: {progress}% - {message}")
        except Exception as e:
            logger.error(f"Failed to update progress: {e}")

# =============================================================================
# Main Stage 4 Processor
# =============================================================================

def process_stage4(stage3_result: Stage3Result, additional_instructions: str = "",
                  task_id: str = None, redis_client: redis.Redis = None) -> Stage4Result:
    """
    Process Stage 4: Course content generation
    
    Args:
        stage3_result: Result from Stage 3 with learning paths
        additional_instructions: Additional instructions for content generation
        task_id: Task ID for progress tracking
        redis_client: Redis client for progress updates
    
    Returns:
        Stage4Result with generated course content
    """
    start_time = time.time()
    
    # Initialize progress tracker
    progress_tracker = None
    if task_id and redis_client:
        progress_tracker = S4ProgressTracker(redis_client, task_id)
        progress_tracker.update_progress("stage4", 0, "Starting course content generation")
    
    try:
        # Initialize content generator
        generator = DebateModuleContentGenerator()
        
        if progress_tracker:
            progress_tracker.update_progress("stage4", 5, "Initializing content generator")
        
        # Generate content for all modules in all learning paths
        generated_content = []
        debate_histories = []
        
        total_modules = sum(len(path.modules) for path in stage3_result.learning_paths)
        processed_modules = 0
        
        for learning_path in stage3_result.learning_paths:
            for module in learning_path.modules:
                logger.info(f"Generating content for module: {module.title}")
                
                # Generate content for this module
                module_content, debate_history = generator.generate_module_content(
                    learning_module=module,
                    document_analyses=stage3_result.stage2_result.document_analyses,
                    target_complexity=stage3_result.target_complexity,
                    overview_context=getattr(stage3_result.stage2_result, 'overview_context', ''),
                    additional_instructions=additional_instructions
                )
                
                if module_content:
                    generated_content.append(module_content)
                
                debate_histories.append(debate_history)
                processed_modules += 1
                
                # Update progress
                if progress_tracker:
                    progress_percent = 5 + int((processed_modules / total_modules) * 85)
                    progress_tracker.update_progress("stage4", progress_percent, f"Generated content for {processed_modules}/{total_modules} modules")
        
        # Create result
        result = Stage4Result(
            stage3_result=stage3_result,
            generated_content=generated_content,
            debate_histories=debate_histories,
            additional_instructions=additional_instructions,
            total_modules_processed=processed_modules,
            successful_generations=len(generated_content),
            metadata={
                'processing_time': time.time() - start_time,
                'stage': 'stage4',
                'content_generation_version': '1.0',
                'total_debate_rounds': sum(len(history.rounds) for history in debate_histories)
            }
        )
        
        if progress_tracker:
            progress_tracker.update_progress("stage4", 100, f"Stage 4 complete: {len(generated_content)} modules generated")
        
        logger.info(f"Stage 4 completed: {len(generated_content)} modules generated with {len(debate_histories)} debate histories")
        return result
        
    except Exception as e:
        logger.error(f"Stage 4 failed: {e}")
        if progress_tracker:
            progress_tracker.update_progress("stage4", -1, f"Stage 4 failed: {str(e)}")
        raise e 