"""
Stage 3: Learning Pathway Generator Agent
Multi-agent learning pathway generation with debate system
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

import dspy
import redis

from backend.shared.models import (
    DocumentAnalysis, ComplexityLevel, LearningPath, LearningModule,
    Stage2Result, Stage3Result
)
from backend.worker.config import ProcessingConfig, AGENT_INSTRUCTIONS

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

class S3Config:
    """Stage 3 Configuration"""
    MAX_DEBATES = ProcessingConfig.MAX_DEBATES
    MIN_MODULES = ProcessingConfig.MIN_MODULES
    MAX_MODULES = ProcessingConfig.MAX_MODULES
    MAX_OVERVIEW_WORDS = ProcessingConfig.MAX_OVERVIEW_WORDS
    MAX_CONTENT_WORDS = ProcessingConfig.MAX_CONTENT_WORDS
    MAX_DOCUMENTS = 30

# =============================================================================
# Utility Functions
# =============================================================================

def get_n_words(text: str, n: int) -> str:
    """Get the first n words from a text"""
    return ' '.join(text.split()[:n])

def prepare_document_info(analyses: List[DocumentAnalysis]) -> str:
    """Prepare comprehensive document information including content"""
    documents_info = []
    
    for doc in analyses[:S3Config.MAX_DOCUMENTS]:
        # Read actual document content
        try:
            with open(doc.file_path, 'r', encoding='utf-8') as f:
                full_content = f.read()
            content_excerpt = get_n_words(full_content, S3Config.MAX_CONTENT_WORDS)
        except Exception as e:
            logger.warning(f"Could not read {doc.file_path}: {e}")
            content_excerpt = f"Content unavailable: {e}"
        
        doc_info = {
            'file_name': Path(doc.file_path).name,
            'file_path': doc.file_path,
            'title': doc.title,
            'doc_type': doc.doc_type.value,
            'complexity_level': doc.complexity_level.value,
            'key_concepts': doc.key_concepts,
            'learning_objectives': doc.learning_objectives,
            'semantic_summary': doc.semantic_summary,
            'prerequisites': doc.prerequisites,
            'related_topics': doc.related_topics,
            'content_excerpt': content_excerpt,
            'code_languages': doc.code_languages
        }
        documents_info.append(doc_info)
    
    return json.dumps(documents_info, indent=2)

def create_fallback_path(document_analyses: List[DocumentAnalysis], 
                        target_complexity: ComplexityLevel, 
                        repo_name: str) -> Tuple[List[LearningPath], List[str]]:
    """Create a simple fallback learning path"""
    logger.warning("Creating fallback learning path")
    
    # Simple fallback: group documents by type
    modules = []
    for i, doc in enumerate(document_analyses[:5]):  # Limit to first 5 docs
        module = LearningModule(
            module_id=f"module_{i+1:02d}",
            title=f"Module {i+1}: {doc.title}",
            description=doc.semantic_summary,
            documents=[doc.file_path],
            learning_objectives=doc.learning_objectives or [f"Understand {doc.title}"]
        )
        modules.append(module)
    
    fallback_path = LearningPath(
        path_id=f"{repo_name.lower()}_{target_complexity.value}_fallback",
        title=f"{repo_name} - {target_complexity.value.title()} Course",
        description=f"Basic {target_complexity.value} course for {repo_name}",
        target_complexity=target_complexity,
        modules=modules
    )
    
    return [fallback_path], ["Fallback path created due to debate system failure"]

# =============================================================================
# DSPy Signatures
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
# Debate Learning Path Generator
# =============================================================================

class DebateLearningPathGenerator(dspy.Module):
    """Generate learning paths through multi-agent debate"""
    
    def __init__(self):
        super().__init__()
        self.proposer = dspy.ChainOfThought(LearningPathProposer)
        self.critic = dspy.ChainOfThought(LearningPathCritic)
    
    def _run_debate_round(self, round_num: int, documents_info: str, target_complexity: str,
                         overview_context: str, previous_critique: str, 
                         additional_instructions: str) -> Tuple[Optional[LearningPath], str]:
        """Run a single debate round"""
        logger.info(f"🔄 Debate Round {round_num}")
        
        # Proposer creates/refines learning path
        try:
            proposal_result = self.proposer(
                agent_instructions=f"{AGENT_INSTRUCTIONS}\n{additional_instructions}",
                documents_with_content=documents_info,
                target_complexity=target_complexity,
                overview_context=overview_context,
                previous_critique=previous_critique
            )
            
            current_proposal = proposal_result.learning_path_proposal
            logger.info(f"📝 Proposer reasoning: {proposal_result.reasoning[:200]}...")
            
        except Exception as e:
            logger.error(f"❌ Proposer failed in round {round_num}: {e}")
            return None, f"Proposer failed: {e}"
        
        # Critic evaluates the proposal
        try:
            critique_result = self.critic(
                agent_instructions=f"{AGENT_INSTRUCTIONS}\n{additional_instructions}",
                learning_path_proposal=current_proposal.model_dump_json(),
                documents_with_content=documents_info,
                target_complexity=target_complexity,
                overview_context=overview_context
            )
            
            current_critique = critique_result.critique
            severity = critique_result.severity
            
            logger.info(f"🔍 Critic assessment: {severity}")
            logger.info(f"🔍 Critique: {current_critique[:200]}...")
            
            return current_proposal, current_critique
            
        except Exception as e:
            logger.error(f"❌ Critic failed in round {round_num}: {e}")
            return current_proposal, f"Critic failed: {e}"
    
    def generate_learning_path(self, 
                             document_analyses: List[DocumentAnalysis],
                             target_complexity: ComplexityLevel,
                             additional_instructions: str = "",
                             overview_context: str = "",
                             repo_name: str = "Documentation") -> Tuple[List[LearningPath], List[str]]:
        """Generate learning path through iterative debate process"""
        
        logger.info(f"🎭 Starting debate-style learning path generation for {target_complexity.value}")
        
        # Prepare document information
        documents_info = prepare_document_info(document_analyses)
        overview_trimmed = get_n_words(overview_context, S3Config.MAX_OVERVIEW_WORDS)
        
        # Format additional instructions
        if additional_instructions:
            additional_instructions = f"Additional instructions: {additional_instructions}"
        else:
            additional_instructions = ""
        
        all_proposals = []
        all_critiques = []
        current_critique = ""
        
        # Iterative debate process
        for round_num in range(1, S3Config.MAX_DEBATES + 1):
            proposal, critique = self._run_debate_round(
                round_num, documents_info, target_complexity.value,
                overview_trimmed, current_critique, additional_instructions
            )
            
            if proposal is None:
                # If first round fails, create fallback
                if round_num == 1:
                    return create_fallback_path(document_analyses, target_complexity, repo_name)
                else:
                    break
            
            all_proposals.append(proposal)
            all_critiques.append(critique)
            current_critique = critique
            
            # Check if acceptable
            if "acceptable" in critique.lower():
                logger.info("✅ Learning path accepted by critic")
                break
        
        return all_proposals, all_critiques

# =============================================================================
# Progress Tracker
# =============================================================================

class S3ProgressTracker:
    """Tracks and updates Stage 3 progress"""
    
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
            
            logger.info(f"Stage 3 Progress: {progress}% - {message}")
        except Exception as e:
            logger.error(f"Failed to update progress: {e}")

# =============================================================================
# Main Stage 3 Processor
# =============================================================================

def process_stage3(stage2_result: Stage2Result, target_complexity: ComplexityLevel = ComplexityLevel.INTERMEDIATE,
                  additional_instructions: str = "", task_id: str = None, 
                  redis_client: redis.Redis = None) -> Stage3Result:
    """
    Process Stage 3: Learning pathway generation
    
    Args:
        stage2_result: Result from Stage 2 with document analyses
        target_complexity: Target complexity level for the learning path
        additional_instructions: Additional instructions for path generation
        task_id: Task ID for progress tracking
        redis_client: Redis client for progress updates
    
    Returns:
        Stage3Result with learning paths and debate history
    """
    start_time = time.time()
    
    # Initialize progress tracker
    progress_tracker = None
    if task_id and redis_client:
        progress_tracker = S3ProgressTracker(redis_client, task_id)
        progress_tracker.update_progress("stage3", 0, "Starting learning pathway generation")
    
    try:
        # Initialize learning path generator
        generator = DebateLearningPathGenerator()
        
        if progress_tracker:
            progress_tracker.update_progress("stage3", 10, "Initializing learning path generator")
        
        # Generate learning paths through debate
        all_proposals, all_critiques = generator.generate_learning_path(
            document_analyses=stage2_result.document_analyses,
            target_complexity=target_complexity,
            additional_instructions=additional_instructions,
            overview_context=getattr(stage2_result, 'overview_context', ''),
            repo_name=getattr(stage2_result, 'repo_name', 'Documentation')
        )
        
        # Use the last (best) proposal as the final learning paths
        learning_paths = all_proposals[-1:] if all_proposals else []
        
        # Format debate history for storage
        debate_history = []
        for i, (proposal, critique) in enumerate(zip(all_proposals, all_critiques)):
            debate_history.append(f"Round {i+1}: Proposal generated | Critique: {critique[:200]}...")
        
        if not learning_paths:
            # Fallback if no proposals generated
            learning_paths, fallback_history = create_fallback_path(
                stage2_result.document_analyses, target_complexity, 
                getattr(stage2_result, 'repo_name', 'Documentation')
            )
            debate_history.extend(fallback_history)
        
        if progress_tracker:
            progress_tracker.update_progress("stage3", 80, f"Generated {len(learning_paths)} learning paths")
        
        # Create result
        result = Stage3Result(
            stage2_result=stage2_result,
            learning_paths=learning_paths,
            target_complexity=target_complexity,
            debate_history=debate_history,
            additional_instructions=additional_instructions,
            total_modules=sum(len(path.modules) for path in learning_paths),
            metadata={
                'processing_time': time.time() - start_time,
                'stage': 'stage3',
                'debate_rounds': len(debate_history),
                'path_generation_version': '1.0'
            }
        )
        
        if progress_tracker:
            total_modules = sum(len(path.modules) for path in learning_paths)
            progress_tracker.update_progress("stage3", 100, f"Stage 3 complete: {len(learning_paths)} paths, {total_modules} modules")
        
        logger.info(f"Stage 3 completed: {len(learning_paths)} learning paths generated with {len(debate_history)} debate rounds")
        return result
        
    except Exception as e:
        logger.error(f"Stage 3 failed: {e}")
        if progress_tracker:
            progress_tracker.update_progress("stage3", -1, f"Stage 3 failed: {str(e)}")
        raise e 