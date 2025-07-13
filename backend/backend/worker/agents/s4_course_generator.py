"""
Stage 4: Course Generator Agent
Multi-agent course content generation with debate system and parallel processing
"""

import json
import logging
import time
import asyncio
import concurrent.futures
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass

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
# Enhanced Progress Tracking with Module-Level Detail
# =============================================================================

@dataclass
class ModuleProgress:
    """Progress tracking for individual modules"""
    module_id: str
    title: str
    status: str  # 'pending', 'processing', 'debating', 'completed', 'failed'
    current_round: int = 0
    total_rounds: int = 0
    debate_history: List[Dict[str, Any]] = None
    start_time: Optional[float] = None
    completion_time: Optional[float] = None
    error_message: Optional[str] = None
    word_count: int = 0
    
    def __post_init__(self):
        if self.debate_history is None:
            self.debate_history = []

class S4ProgressTracker:
    """Enhanced Stage 4 progress tracker with detailed module tracking"""
    
    def __init__(self, redis_client: redis.Redis, course_id: str):
        self.redis = redis_client
        self.course_id = course_id
        self.progress_key = f"stage4_progress:{course_id}"
        self.modules_progress: Dict[str, ModuleProgress] = {}
        self.total_modules = 0
        self.completed_modules = 0
        self.failed_modules = 0
        self.start_time = time.time()
        
    def initialize_detailed_progress(self, modules: List[LearningModule]):
        """Initialize detailed progress tracking for all modules"""
        self.total_modules = len(modules)
        self.modules_progress = {}
        
        # Initialize each module's progress
        for module in modules:
            self.modules_progress[module.module_id] = ModuleProgress(
                module_id=module.module_id,
                title=module.title,
                status='pending'
            )
        
        # Save initial state to Redis
        self._save_to_redis()
        logger.info(f"Initialized Stage 4 progress tracking for {self.total_modules} modules")
    
    def start_module_processing(self, module_id: str):
        """Mark a module as starting processing"""
        if module_id in self.modules_progress:
            module_progress = self.modules_progress[module_id]
            module_progress.status = 'processing'
            module_progress.start_time = time.time()
            self._save_to_redis()
            logger.info(f"Started processing module: {module_progress.title}")
    
    def update_module_debate_round(self, module_id: str, round_num: int, total_rounds: int, activity: str):
        """Update module debate round progress"""
        if module_id in self.modules_progress:
            module_progress = self.modules_progress[module_id]
            module_progress.status = 'debating'
            module_progress.current_round = round_num
            module_progress.total_rounds = total_rounds
            
            # Add debate round to history
            debate_entry = {
                'round': round_num,
                'activity': activity,
                'timestamp': time.time()
            }
            module_progress.debate_history.append(debate_entry)
            
            self._save_to_redis()
            logger.info(f"Module {module_progress.title}: Round {round_num}/{total_rounds} - {activity}")
    
    def complete_module(self, module_id: str, word_count: int = 0):
        """Mark a module as completed"""
        if module_id in self.modules_progress:
            module_progress = self.modules_progress[module_id]
            module_progress.status = 'completed'
            module_progress.completion_time = time.time()
            module_progress.word_count = word_count
            self.completed_modules += 1
            self._save_to_redis()
            logger.info(f"Completed module: {module_progress.title} ({word_count} words)")
    
    def fail_module(self, module_id: str, error_message: str):
        """Mark a module as failed"""
        if module_id in self.modules_progress:
            module_progress = self.modules_progress[module_id]
            module_progress.status = 'failed'
            module_progress.error_message = error_message
            module_progress.completion_time = time.time()
            self.failed_modules += 1
            self._save_to_redis()
            logger.error(f"Failed module: {module_progress.title} - {error_message}")
    
    def get_overall_progress(self) -> Dict[str, Any]:
        """Get overall progress summary"""
        elapsed_time = time.time() - self.start_time
        processing_modules = len([m for m in self.modules_progress.values() if m.status in ['processing', 'debating']])
        
        return {
            'total_modules': self.total_modules,
            'completed_modules': self.completed_modules,
            'failed_modules': self.failed_modules,
            'processing_modules': processing_modules,
            'pending_modules': self.total_modules - self.completed_modules - self.failed_modules - processing_modules,
            'progress_percentage': int((self.completed_modules / self.total_modules) * 100) if self.total_modules > 0 else 0,
            'elapsed_time': elapsed_time,
            'estimated_completion': self._estimate_completion_time()
        }
    
    def _estimate_completion_time(self) -> Optional[float]:
        """Estimate completion time based on current progress"""
        if self.completed_modules == 0:
            return None
        
        elapsed_time = time.time() - self.start_time
        avg_time_per_module = elapsed_time / self.completed_modules
        remaining_modules = self.total_modules - self.completed_modules - self.failed_modules
        
        return avg_time_per_module * remaining_modules
    
    def _save_to_redis(self):
        """Save current progress to Redis"""
        try:
            progress_data = {
                'overall': self.get_overall_progress(),
                'modules': [
                    {
                        'module_id': m.module_id,
                        'title': m.title,
                        'status': m.status,
                        'current_round': m.current_round,
                        'total_rounds': m.total_rounds,
                        'debate_history': m.debate_history,
                        'start_time': m.start_time,
                        'completion_time': m.completion_time,
                        'error_message': m.error_message,
                        'word_count': m.word_count
                    }
                    for m in self.modules_progress.values()
                ],
                'timestamp': time.time()
            }
            
            self.redis.setex(
                self.progress_key,
                3600,  # 1 hour TTL
                json.dumps(progress_data)
            )
            
        except Exception as e:
            logger.error(f"Failed to save Stage 4 progress to Redis: {e}")
    
    def finalize_progress(self):
        """Finalize progress tracking"""
        overall = self.get_overall_progress()
        logger.info(f"Stage 4 completed: {overall['completed_modules']}/{overall['total_modules']} modules generated, {overall['failed_modules']} failed")
        self._save_to_redis()

# =============================================================================
# Parallel Module Processing
# =============================================================================

class ParallelModuleProcessor:
    """Handles parallel processing of modules with controlled concurrency"""
    
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.generator = DebateModuleContentGenerator()
    
    def process_module_batch(self, modules: List[LearningModule], document_analyses: List[DocumentAnalysis], 
                           target_complexity: ComplexityLevel, overview_context: str, 
                           additional_instructions: str, progress_tracker: S4ProgressTracker) -> List[Tuple[Optional[ModuleContent], ModuleDebateHistory]]:
        """Process a batch of modules in parallel"""
        results = []
        
        # Use ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all modules for processing
            future_to_module = {
                executor.submit(
                    self._process_single_module,
                    module,
                    document_analyses,
                    target_complexity,
                    overview_context,
                    additional_instructions,
                    progress_tracker
                ): module for module in modules
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_module):
                module = future_to_module[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Module {module.title} processing failed: {e}")
                    # Create failed result
                    failed_history = ModuleDebateHistory(
                        module_id=module.module_id,
                        success=False
                    )
                    results.append((None, failed_history))
                    progress_tracker.fail_module(module.module_id, str(e))
        
        return results
    
    def _process_single_module(self, module: LearningModule, document_analyses: List[DocumentAnalysis], 
                             target_complexity: ComplexityLevel, overview_context: str, 
                             additional_instructions: str, progress_tracker: S4ProgressTracker) -> Tuple[Optional[ModuleContent], ModuleDebateHistory]:
        """Process a single module with progress tracking"""
        try:
            # Start module processing
            progress_tracker.start_module_processing(module.module_id)
            
            # Generate content with debate tracking
            module_content, debate_history = self.generator.generate_module_content(
                learning_module=module,
                document_analyses=document_analyses,
                target_complexity=target_complexity,
                overview_context=overview_context,
                additional_instructions=additional_instructions,
                progress_tracker=progress_tracker
            )
            
            # Calculate word count
            word_count = 0
            if module_content:
                word_count = len(module_content.main_content.split()) + len(module_content.introduction.split()) + len(module_content.conclusion.split())
                progress_tracker.complete_module(module.module_id, word_count)
            else:
                progress_tracker.fail_module(module.module_id, "Failed to generate content")
            
            return module_content, debate_history
            
        except Exception as e:
            logger.error(f"Error processing module {module.title}: {e}")
            progress_tracker.fail_module(module.module_id, str(e))
            failed_history = ModuleDebateHistory(
                module_id=module.module_id,
                success=False
            )
            return None, failed_history

# =============================================================================
# Configuration and Helper Functions
# =============================================================================

class S4Config:
    """Stage 4 Configuration"""
    MAX_DEBATES = settings.MAX_DEBATES
    MAX_CONTENT_WORDS = settings.MAX_CONTENT_WORDS
    MAX_OVERVIEW_WORDS = settings.MAX_OVERVIEW_WORDS
    MAX_PARALLEL_WORKERS = 3  # Configurable parallel processing limit

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
                              additional_instructions: str = "",
                              progress_tracker: S4ProgressTracker = None) -> Tuple[Optional[ModuleContent], ModuleDebateHistory]:
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
            
            # Update progress tracker
            if progress_tracker:
                progress_tracker.update_module_debate_round(
                    learning_module.module_id, 
                    round_num, 
                    S4Config.MAX_DEBATES,
                    f"💡 Proposer creating content"
                )
            
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
            
            # Update progress tracker for critic phase
            if progress_tracker:
                progress_tracker.update_module_debate_round(
                    learning_module.module_id,
                    round_num,
                    S4Config.MAX_DEBATES,
                    f"🔍 Critic evaluating content"
                )
            
            # Critic evaluates the content
            current_critique, severity = self._run_critique_round(
                round_num, instructions, learning_module_str, current_proposal,
                source_documents, target_complexity.value, overview_trimmed
            )
            
            debate_round.critique = current_critique
            debate_round.severity = severity
            
            history.rounds.append(debate_round)
            
            # Update progress tracker for round completion
            if progress_tracker:
                activity = f"✅ Round {round_num} completed - {severity}"
                progress_tracker.update_module_debate_round(
                    learning_module.module_id,
                    round_num,
                    S4Config.MAX_DEBATES,
                    activity
                )
            
            # If acceptable, stop iterating
            if severity == "acceptable":
                logger.info("✅ Module content accepted by critic")
                
                # Update progress tracker for acceptance
                if progress_tracker:
                    progress_tracker.update_module_debate_round(
                        learning_module.module_id,
                        round_num,
                        S4Config.MAX_DEBATES,
                        f"🎉 Content accepted!"
                    )
                
                history.final_content = current_proposal
                history.success = True
                return current_proposal, history
        
        # Return the last proposal
        if current_proposal:
            history.final_content = current_proposal
            history.success = True
        
        return current_proposal, history

# =============================================================================
# Main Stage 4 Processor
# =============================================================================

def process_stage4(stage3_result: Stage3Result, additional_instructions: str = "",
                  task_id: str = None, redis_client: redis.Redis = None) -> Stage4Result:
    """
    Process Stage 4: Course content generation with parallel processing
    
    Args:
        stage3_result: Result from Stage 3 with learning paths
        additional_instructions: Additional instructions for content generation
        task_id: Task ID for progress tracking
        redis_client: Redis client for progress updates
    
    Returns:
        Stage4Result with generated course content
    """
    start_time = time.time()
    
    # Extract course_id from task_id or use a default
    course_id = task_id if task_id else f"stage4_{int(time.time())}"
    
    # Initialize enhanced progress tracker
    progress_tracker = None
    if redis_client:
        progress_tracker = S4ProgressTracker(redis_client, course_id)
    
    try:
        # Collect all modules from all learning paths
        all_modules = []
        for learning_path in stage3_result.learning_paths:
            all_modules.extend(learning_path.modules)
        
        total_modules = len(all_modules)
        logger.info(f"Processing {total_modules} modules with parallel processing")
        
        # Initialize detailed progress tracking
        if progress_tracker:
            progress_tracker.initialize_detailed_progress(all_modules)
        
        # Initialize parallel processor
        parallel_processor = ParallelModuleProcessor(max_workers=S4Config.MAX_PARALLEL_WORKERS)
        
        # Process modules in parallel
        logger.info(f"Starting parallel processing with {S4Config.MAX_PARALLEL_WORKERS} workers")
        results = parallel_processor.process_module_batch(
            modules=all_modules,
            document_analyses=stage3_result.stage2_result.document_analyses,
            target_complexity=stage3_result.target_complexity,
            overview_context=getattr(stage3_result.stage2_result, 'overview_context', ''),
            additional_instructions=additional_instructions,
            progress_tracker=progress_tracker
        )
        
        # Collect results
        generated_content = []
        debate_histories = []
        
        for module_content, debate_history in results:
            if module_content:
                generated_content.append(module_content)
            debate_histories.append(debate_history)
        
        # Finalize progress tracking
        if progress_tracker:
            progress_tracker.finalize_progress()
        
        # Create result
        result = Stage4Result(
            stage3_result=stage3_result,
            generated_content=generated_content,
            debate_histories=debate_histories,
            additional_instructions=additional_instructions,
            total_modules_processed=total_modules,
            successful_generations=len(generated_content),
            metadata={
                'processing_time': time.time() - start_time,
                'stage': 'stage4',
                'content_generation_version': '2.0',
                'parallel_workers': S4Config.MAX_PARALLEL_WORKERS,
                'total_debate_rounds': sum(len(history.rounds) for history in debate_histories),
                'parallel_processing_enabled': True
            }
        )
        
        logger.info(f"Stage 4 completed: {len(generated_content)}/{total_modules} modules generated successfully with {len(debate_histories)} debate histories")
        return result
        
    except Exception as e:
        logger.error(f"Stage 4 failed: {e}")
        if progress_tracker:
            # Update all remaining modules as failed
            for module in all_modules:
                if module.module_id in progress_tracker.modules_progress:
                    module_progress = progress_tracker.modules_progress[module.module_id]
                    if module_progress.status in ['pending', 'processing', 'debating']:
                        progress_tracker.fail_module(module.module_id, f"Stage 4 failed: {str(e)}")
        raise e 