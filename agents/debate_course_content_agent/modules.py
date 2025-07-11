import os
import json
import logging
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from urllib.parse import urlparse
import dspy
from concurrent.futures import ThreadPoolExecutor
import git

from debate_course_content_agent.config import (
    ProcessingConfig, SystemConfig, AGENT_INSTRUCTIONS
)

from debate_course_content_agent.models import (
    DocumentType, ComplexityLevel, DocumentAnalysis, LearningModule, LearningPath,
    ModuleContent, ModuleDebateRound, ModuleDebateHistory
)
from debate_course_content_agent.signatures import (
    BasicMetadataExtractor, DocumentClassifier, ConceptExtractor, SemanticAnalyzer,
    LearningPathProposer, LearningPathCritic, ModuleContentProposer, ModuleContentCritic
)
from debate_course_content_agent.utils import (
    extract_basic_metadata, extract_title, extract_headings, extract_code_blocks,
    safe_json_parse, get_n_words, prepare_source_documents_content
)

logger = logging.getLogger(__name__)


# =============================================================================
# Repository Manager
# =============================================================================

class RepoManager:
    """Handles repository operations, cloning, caching, and file discovery"""
    
    def __init__(self, cache_dir: str = SystemConfig.CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def _get_repo_cache_path(self, repo_url: str) -> Path:
        """Generate cache path for repository"""
        repo_hash = hashlib.md5(repo_url.encode()).hexdigest()
        repo_name = urlparse(repo_url).path.strip('/').replace('/', '_')
        return self.cache_dir / f"{repo_name}_{repo_hash}"
    
    def clone_or_update_repo(self, repo_url: str, force_update: bool = False) -> Path:
        """Clone repository or update if it exists"""
        repo_path = self._get_repo_cache_path(repo_url)
        
        if repo_path.exists() and not force_update:
            logger.info(f"Repository already cached at {repo_path}")
            try:
                repo = git.Repo(repo_path)
                repo.remotes.origin.pull()
                logger.info("Updated repository with latest changes")
            except Exception as e:
                logger.warning(f"Warning: Could not update repository: {e}")
            return repo_path
        
        if repo_path.exists():
            import shutil
            shutil.rmtree(repo_path)
            
        logger.info(f"Cloning repository to {repo_path}")
        git.Repo.clone_from(repo_url, repo_path)
        return repo_path
    
    def get_repo_path(self, repo_input: str) -> Path:
        """Get repository path - either clone remote repo or use local path"""
        if repo_input.startswith(('http://', 'https://', 'git@')):
            # Remote repository - clone it
            return self.clone_or_update_repo(repo_input)
        else:
            # Local path
            local_path = Path(repo_input).resolve()
            if not local_path.exists():
                raise ValueError(f"Local repository path does not exist: {local_path}")
            return local_path
    
    def find_documentation_files(self, repo_path: Path, include_folders: Optional[List[str]] = None) -> List[Path]:
        """Find all markdown files in repository, optionally filtered by folders"""
        md_files = []
        for ext in ProcessingConfig.INCLUDE_EXTENSIONS:
            md_files.extend(repo_path.rglob(ext))
        
        excluded_patterns = ProcessingConfig.EXCLUDE_PATTERNS
        
        filtered_files = []
        for file_path in md_files:
            if not any(excluded in file_path.parts for excluded in excluded_patterns):
                filtered_files.append(file_path)

        # Remove common non-content files
        filtered_files = [
            file for file in filtered_files 
            if not file.name.lower().startswith(tuple(ProcessingConfig.EXCLUDE_FILE_PREFIXES))
        ]
        
        # Filter by include_folders if specified
        if include_folders:
            folder_filtered_files = []
            for file_path in filtered_files:
                # Get relative path from repo root
                rel_path = file_path.relative_to(repo_path)
                rel_path_str = str(rel_path)
                
                # Check if file is in any of the included folders
                for include_folder in include_folders:
                    # Normalize folder path (remove leading/trailing slashes)
                    include_folder = include_folder.strip('/')
                    
                    # Check if file path starts with the include folder
                    if rel_path_str.startswith(include_folder + '/') or rel_path_str.startswith(include_folder + '\\'):
                        folder_filtered_files.append(file_path)
                        break
                    # Also check if the file is directly in the include folder (for root level includes)
                    elif include_folder == '.' and '/' not in rel_path_str and '\\' not in rel_path_str:
                        folder_filtered_files.append(file_path)
                        break
                    # Check if the include folder is the exact parent directory
                    elif str(rel_path.parent) == include_folder or str(rel_path.parent).replace('\\', '/') == include_folder:
                        folder_filtered_files.append(file_path)
                        break
            
            filtered_files = folder_filtered_files
            logger.info(f"Filtered to {len(filtered_files)} files from specified folders: {include_folders}")
        
        return sorted(filtered_files)

# =============================================================================
# Multi-Agent Document Analyzer
# =============================================================================

class DocumentAnalyzer(dspy.Module):
    """Multi-agent document analyzer with specialized analysis components"""
    
    def __init__(self):
        super().__init__()
        self.metadata_extractor = dspy.ChainOfThought(BasicMetadataExtractor)
        self.classifier = dspy.ChainOfThought(DocumentClassifier)
        self.concept_extractor = dspy.ChainOfThought(ConceptExtractor)
        self.semantic_analyzer = dspy.ChainOfThought(SemanticAnalyzer)

        # Configuration
        self.max_overview_words = ProcessingConfig.MAX_OVERVIEW_WORDS
        self.max_content_words = ProcessingConfig.MAX_CONTENT_WORDS
    
    def analyze_document(self, file_path: str, overview_context: str = "") -> DocumentAnalysis:
        """Analyze a single document with multi-agent approach"""
        
        # Read document
        if isinstance(file_path, Path):
            file_path = str(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filepath = Path(file_path)
        
        # Extract basic metadata
        basic_data = extract_basic_metadata(content, filepath)
        
        # Step 1: Enhanced metadata extraction (only if basic data is incomplete)
        needs_enhanced_extraction = (
            not basic_data['title'] or 
            not basic_data['headings'] or 
            not basic_data['code_languages']
        )
        
        if needs_enhanced_extraction:
            try:
                metadata_result = self.metadata_extractor(
                    agent_instructions=AGENT_INSTRUCTIONS,
                    content=get_n_words(content, self.max_content_words),
                    filename=filepath.name
                )
                
                # Merge with basic extraction
                title = metadata_result.title or basic_data['title']
                headings = safe_json_parse(metadata_result.headings, basic_data['headings'])
                code_languages = safe_json_parse(metadata_result.code_languages, basic_data['code_languages'])
                
            except Exception as e:
                logger.error(f"Error in metadata extraction: {e}")
                # Fallback to basic extraction
                title = basic_data['title']
                headings = basic_data['headings']
                code_languages = basic_data['code_languages']
        else:
            # Use basic extraction results directly
            title = basic_data['title']
            headings = basic_data['headings']
            code_languages = basic_data['code_languages']
        
        # Step 2: Classification
        try:
            classification_result = self.classifier(
                agent_instructions=AGENT_INSTRUCTIONS,
                content=get_n_words(content, self.max_content_words),
                title=title,
                overview_context=get_n_words(overview_context, self.max_overview_words)
            )
            doc_type = classification_result.doc_type
            complexity_level = classification_result.complexity_level
        except Exception as e:
            logger.error(f"Error in classification: {e}")
            doc_type = DocumentType.GUIDE
            complexity_level = ComplexityLevel.INTERMEDIATE
        
        # Step 3: Concept extraction
        try:
            concept_result = self.concept_extractor(
                agent_instructions=AGENT_INSTRUCTIONS,
                content=get_n_words(content, self.max_content_words),
                doc_type=doc_type.value,
                title=title
            )
            key_concepts = safe_json_parse(concept_result.key_concepts)
            learning_objectives = safe_json_parse(concept_result.learning_objectives)
        except Exception as e:
            logger.error(f"Error in concept extraction: {e}")
            key_concepts = []
            learning_objectives = []
        
        # Step 4: Semantic analysis
        try:
            semantic_result = self.semantic_analyzer(
                agent_instructions=AGENT_INSTRUCTIONS,
                content=get_n_words(content, self.max_content_words),
                title=title,
                key_concepts=', '.join(key_concepts),
                doc_type=doc_type.value
            )
            semantic_summary = semantic_result.semantic_summary
            prerequisites = safe_json_parse(semantic_result.prerequisites)
            related_topics = safe_json_parse(semantic_result.related_topics)
        except Exception as e:
            logger.error(f"Error in semantic analysis: {e}")
            semantic_summary = f"Documentation about {title}"
            prerequisites = []
            related_topics = []
        
        # Create analysis result
        return DocumentAnalysis(
            file_path=file_path,
            title=title,
            doc_type=doc_type,
            complexity_level=complexity_level,
            key_concepts=key_concepts,
            learning_objectives=learning_objectives,
            semantic_summary=semantic_summary,
            code_languages=code_languages,
            headings=headings,
            prerequisites=prerequisites,
            related_topics=related_topics
        )
    
    def analyze_batch(self, file_paths: List[str], overview_context: str = "") -> List[DocumentAnalysis]:
        """Analyze multiple documents"""
        results = []
        
        for file_path in file_paths:
            try:
                analysis = self.analyze_document(file_path, overview_context)
                results.append(analysis)
                logger.info(f"✓ Analyzed: {Path(file_path).name}")
            except Exception as e:
                logger.error(f"✗ Failed to analyze {Path(file_path).name}: {e}")
                continue
        
        return results

# =============================================================================
# Debate-Style Learning Path Generator
# =============================================================================

class DebateLearningPathGenerator(dspy.Module):
    """Generate learning paths through debate between proposer and critic agents"""
    
    def __init__(self):
        super().__init__()
        self.proposer = dspy.ChainOfThought(LearningPathProposer)
        self.critic = dspy.ChainOfThought(LearningPathCritic)
        
        # Configuration
        self.max_docs = 30
        self.max_content_words = ProcessingConfig.MAX_CONTENT_WORDS
        self.max_overview_words = ProcessingConfig.MAX_OVERVIEW_WORDS
        self.max_debates = ProcessingConfig.MAX_DEBATES
    
    def generate_learning_path(self, 
                             document_analyses: List[DocumentAnalysis],
                             target_complexity: ComplexityLevel,
                             additional_instructions: str = "",
                             overview_context: str = "",
                             repo_name: str = "Documentation") -> Tuple[List[LearningPath], List[str]]:
        """Generate learning path through iterative debate process"""
        
        logger.info(f"🎭 Starting debate-style learning path generation for {target_complexity.value}")
        
        # Prepare rich document information with content
        docs_with_content = self._prepare_rich_document_info(document_analyses)
        overview_trimmed = get_n_words(overview_context, self.max_overview_words)

        if additional_instructions:
            additional_instructions = f"Additional instructions: {additional_instructions}"
        else:
            additional_instructions = ""
                    
        current_proposal = None
        current_critique = ""
        
        all_proposals = []
        all_critiques = []
        
        # Iterative debate process
        for round_num in range(1, self.max_debates + 1):
            logger.info(f"🔄 Debate Round {round_num}")
            
            # Proposer creates/refines learning path
            try:
                proposal_result = self.proposer(
                    agent_instructions=f"{AGENT_INSTRUCTIONS}\n{additional_instructions}",
                    documents_with_content=docs_with_content,
                    target_complexity=target_complexity.value,
                    overview_context=overview_trimmed,
                    previous_critique=current_critique
                )
                
                current_proposal = proposal_result.learning_path_proposal
                all_proposals.append(current_proposal)
                logger.info(f"📝 Proposer reasoning: {proposal_result.reasoning[:200]}...")
                
            except Exception as e:
                logger.error(f"❌ Proposer failed in round {round_num}: {e}")
                if round_num == 1:
                    return self._create_fallback_path(document_analyses, target_complexity, repo_name)
                else:
                    break
            
            # Critic evaluates the proposal
            try:
                critique_result = self.critic(
                    agent_instructions=f"{AGENT_INSTRUCTIONS}\n{additional_instructions}",
                    learning_path_proposal=current_proposal.model_dump_json(),
                    documents_with_content=docs_with_content,
                    target_complexity=target_complexity.value,
                    overview_context=overview_trimmed
                )
                
                current_critique = critique_result.critique
                severity = critique_result.severity
                
                all_critiques.append(current_critique)

                logger.info(f"🔍 Critic assessment: {severity}")
                logger.info(f"🔍 Critique: {current_critique[:200]}...")
                
                # If acceptable, stop iterating
                if severity == "acceptable":
                    logger.info("✅ Learning path accepted by critic")
                    break
                    
            except Exception as e:
                logger.error(f"❌ Critic failed in round {round_num}: {e}")
                break
        
        return all_proposals, all_critiques
    
    def _prepare_rich_document_info(self, analyses: List[DocumentAnalysis]) -> str:
        """Prepare comprehensive document information including content"""
        
        documents_info = []
        
        for doc in analyses[:self.max_docs]:
            # Read actual document content
            try:
                with open(doc.file_path, 'r', encoding='utf-8') as f:
                    full_content = f.read()
                content_excerpt = get_n_words(full_content, self.max_content_words)
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
    
    def _create_fallback_path(self, document_analyses: List[DocumentAnalysis], 
                            target_complexity: ComplexityLevel, repo_name: str) -> Tuple[List[LearningPath], List[str]]:
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
# Debate-Style Module Content Generator
# =============================================================================

class DebateModuleContentGenerator(dspy.Module):
    """Generate module content through debate between proposer and critic agents"""
    
    def __init__(self):
        super().__init__()
        self.proposer = dspy.ChainOfThought(ModuleContentProposer)
        self.critic = dspy.ChainOfThought(ModuleContentCritic)
        
        # Configuration
        self.max_content_words = ProcessingConfig.MAX_CONTENT_WORDS
        self.max_overview_words = ProcessingConfig.MAX_OVERVIEW_WORDS
        self.max_debates = ProcessingConfig.MAX_DEBATES
    
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
        learning_module_str = json.dumps({
            'module_id': learning_module.module_id,
            'title': learning_module.title,
            'description': learning_module.description,
            'learning_objectives': learning_module.learning_objectives,
            'documents': learning_module.documents
        }, indent=2)
        
        source_documents = prepare_source_documents_content(
            learning_module, 
            document_analyses, 
            self.max_content_words
        )
        
        overview_trimmed = get_n_words(overview_context, self.max_overview_words)
        
        if additional_instructions:
            instructions = f"{AGENT_INSTRUCTIONS}\n\nAdditional instructions: {additional_instructions}"
        else:
            instructions = AGENT_INSTRUCTIONS
        
        current_proposal = None
        current_critique = ""
        
        # Iterative debate process
        for round_num in range(1, self.max_debates + 1):
            logger.info(f"🔄 Module Content Debate Round {round_num}")
            
            debate_round = ModuleDebateRound(round_number=round_num)
            
            # Proposer creates/refines module content
            try:
                proposal_result = self.proposer(
                    agent_instructions=instructions,
                    learning_module=learning_module_str,
                    source_documents=source_documents,
                    target_complexity=target_complexity.value,
                    overview_context=overview_trimmed,
                    previous_critique=current_critique
                )
                
                # Create ModuleContent from structured outputs
                current_proposal = ModuleContent(
                    module_id=learning_module.module_id,
                    title=learning_module.title,
                    description=learning_module.description,
                    learning_objectives=learning_module.learning_objectives,
                    introduction=proposal_result.introduction,
                    main_content=proposal_result.main_content,
                    conclusion=proposal_result.conclusion,
                    assessment=proposal_result.assessment,
                    summary=proposal_result.summary
                )
                
                debate_round.proposal = current_proposal
                debate_round.proposal_reasoning = proposal_result.reasoning
                
                logger.info(f"📝 Proposer created content sections")
                logger.info(f"📝 Reasoning: {proposal_result.reasoning[:200]}...")
                
            except Exception as e:
                debate_round.error_message = f"Proposer failed: {str(e)}"
                logger.error(f"❌ Proposer failed in round {round_num}: {e}")
                
                # If first round fails completely, use fallback
                if round_num == 1 and current_proposal is None:
                    history.rounds.append(debate_round)
                    fallback = self._create_fallback_content(learning_module, document_analyses)
                    history.final_content = fallback
                    history.success = False
                    return fallback, history
            
            # Only proceed with critic if we have a valid proposal
            if current_proposal:
                # Critic evaluates the content
                try:
                    critique_result = self.critic(
                        agent_instructions=instructions,
                        learning_module=learning_module_str,
                        proposed_introduction=current_proposal.introduction,
                        proposed_main_content=current_proposal.main_content,
                        proposed_conclusion=current_proposal.conclusion,
                        proposed_assessment=current_proposal.assessment,
                        proposed_summary=current_proposal.summary,
                        source_documents=source_documents,
                        target_complexity=target_complexity.value,
                        overview_context=overview_trimmed
                    )
                    
                    current_critique = critique_result.critique
                    severity = critique_result.severity
                    
                    debate_round.critique = current_critique
                    debate_round.severity = severity
                    
                    logger.info(f"🔍 Critic assessment: {severity}")
                    logger.info(f"🔍 Critique: {current_critique[:200]}...")
                    
                    # If acceptable, stop iterating
                    if severity == "acceptable":
                        logger.info("✅ Module content accepted by critic")
                        history.rounds.append(debate_round)
                        history.final_content = current_proposal
                        history.success = True
                        return current_proposal, history
                        
                except Exception as e:
                    debate_round.error_message += f" Critic failed: {str(e)}"
                    logger.error(f"❌ Critic failed in round {round_num}: {e}")
                    # Continue with current proposal
                    history.rounds.append(debate_round)
                    break
            
            history.rounds.append(debate_round)
        
        # Return the last proposal
        if current_proposal:
            history.final_content = current_proposal
            history.success = True
        
        return current_proposal, history
    
    def _create_fallback_content(self, learning_module: LearningModule, 
                               document_analyses: List[DocumentAnalysis]) -> ModuleContent:
        """Create simple fallback content when debate fails"""
        logger.warning(f"Creating fallback content for module: {learning_module.title}")
        
        # Get basic content from source documents
        source_content = prepare_source_documents_content(
            learning_module, document_analyses, 5000
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