"""
Stage 2: Document Analyzer Agent
Multi-agent document analysis with debate system
"""

import os
import json
import logging
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import re
import threading

import dspy
import redis
import frontmatter

from backend.shared.models import (
    DocumentAnalysis, DocumentType, ComplexityLevel, 
    Stage1Result, Stage2Result, Stage2UserInput
)
from backend.shared.utils import parse_json_safely
from backend.worker.agents.config import ProcessingConfig, AGENT_INSTRUCTIONS

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

class S2Config:
    """Stage 2 Configuration"""
    MAX_OVERVIEW_WORDS = ProcessingConfig.MAX_OVERVIEW_WORDS
    MAX_CONTENT_WORDS = ProcessingConfig.MAX_CONTENT_WORDS
    MAX_WORKERS = 4

# =============================================================================
# DSPy Signatures
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
# Utility Functions
# =============================================================================

def get_n_words(text: str, n: int) -> str:
    """Get the first n words from a text"""
    return ' '.join(text.split()[:n])

def extract_basic_metadata(content: str, filepath: Path) -> Dict[str, Any]:
    """Extract basic metadata from document content"""
    try:
        post = frontmatter.loads(content)
        frontmatter_data = post.metadata
        clean_content = post.content
    except:
        frontmatter_data = {}
        clean_content = content
    
    title = extract_title(clean_content, frontmatter_data, filepath.name)
    headings = extract_headings(clean_content)
    code_blocks = extract_code_blocks(clean_content)
    
    # Get unique programming languages
    code_languages = list(set(
        block['language'] for block in code_blocks 
        if block['language'] not in ['text', 'txt', '']
    ))
    
    return {
        'title': title,
        'headings': headings,
        'code_languages': code_languages,
        'frontmatter': frontmatter_data,
        'clean_content': clean_content
    }

def extract_title(content: str, frontmatter_data: dict, filename: str) -> str:
    """Extract document title from various sources"""
    # Priority: frontmatter > first H1 > filename
    if 'title' in frontmatter_data:
        return frontmatter_data['title'].strip()
    
    h1_match = re.search(r'^# (.+)$', content, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()
    
    # Clean filename for title
    return (filename.replace('.md', '').replace('.mdx', '')
            .replace('_', ' ').replace('-', ' ').title().strip())

def extract_headings(content: str) -> List[str]:
    """Extract all headings from markdown content"""
    headings = []
    for match in re.finditer(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE):
        level = match.group(1)
        text = match.group(2).strip()
        headings.append(f"{level} {text}")
    return headings

def extract_code_blocks(content: str) -> List[Dict[str, str]]:
    """Extract code blocks with language information"""
    code_blocks = []
    pattern = r'```(\w+)?\n(.*?)\n```'
    for match in re.finditer(pattern, content, re.DOTALL):
        language = match.group(1) or 'text'
        code_content = match.group(2).strip()
        code_blocks.append({
            'language': language,
            'content': code_content
        })
    return code_blocks

def filter_files_by_folders(files: List[str], repo_path: str, include_folders: List[str]) -> List[str]:
    """Filter files based on included folders"""
    if not include_folders:
        return files
    
    filtered_files = []
    repo_path_obj = Path(repo_path)
    
    for file_path in files:
        file_path_obj = Path(file_path)
        rel_path = file_path_obj.relative_to(repo_path_obj)
        
        for include_folder in include_folders:
            include_folder = include_folder.strip('/')
            if (str(rel_path).startswith(include_folder + '/') or 
                str(rel_path).startswith(include_folder + '\\')):
                filtered_files.append(file_path)
                break
    
    return filtered_files

def prepare_overview_context(stage1_result: Stage1Result, stage2_input: Stage2UserInput, 
                           files_count: int) -> str:
    """Prepare overview context from repository and user input"""
    context = f"Repository: {stage1_result.repo_name}\n"
    context += f"Total files: {files_count}\n"
    
    if stage2_input.include_folders:
        context += f"Focused on folders: {', '.join(stage2_input.include_folders)}\n"
    
    # Load overview document if provided
    if stage2_input.overview_doc:
        overview_path = Path(stage1_result.repo_path) / stage2_input.overview_doc
        if overview_path.exists():
            try:
                with open(overview_path, 'r', encoding='utf-8') as f:
                    overview_content = f.read()
                # Limit overview content to max words
                overview_content = get_n_words(overview_content, S2Config.MAX_OVERVIEW_WORDS)
                context += f"\nOverview Document ({stage2_input.overview_doc}):\n{overview_content}\n"
                logger.info(f"Loaded overview document: {stage2_input.overview_doc}")
            except Exception as e:
                logger.warning(f"Could not load overview document {stage2_input.overview_doc}: {e}")
        else:
            logger.warning(f"Overview document not found: {stage2_input.overview_doc}")
    
    return context

def calculate_statistics(document_analyses: List[DocumentAnalysis]) -> Dict[str, Any]:
    """Calculate statistics from document analyses"""
    total_concepts = sum(len(doc.key_concepts) for doc in document_analyses)
    
    complexity_counts = {}
    language_counts = {}
    doc_type_counts = {}
    
    for doc in document_analyses:
        # Count complexity levels
        complexity = doc.complexity_level.value
        complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
        
        # Count languages
        for lang in doc.code_languages:
            language_counts[lang] = language_counts.get(lang, 0) + 1
        
        # Count document types
        doc_type = doc.doc_type.value
        doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1
    
    # Calculate average complexity (most common)
    avg_complexity = "intermediate"
    if complexity_counts:
        avg_complexity = max(complexity_counts.items(), key=lambda x: x[1])[0]
    
    return {
        'total_concepts': total_concepts,
        'avg_complexity': avg_complexity,
        'language_distribution': language_counts,
        'document_type_distribution': doc_type_counts
    }

# =============================================================================
# Document Analyzer
# =============================================================================

class DocumentAnalyzer(dspy.Module):
    """Multi-agent document analyzer with specialized analysis components"""
    
    def __init__(self):
        super().__init__()
        self.metadata_extractor = dspy.ChainOfThought(BasicMetadataExtractor)
        self.classifier = dspy.ChainOfThought(DocumentClassifier)
        self.concept_extractor = dspy.ChainOfThought(ConceptExtractor)
        self.semantic_analyzer = dspy.ChainOfThought(SemanticAnalyzer)
    
    def _extract_enhanced_metadata(self, content: str, filename: str) -> Dict[str, Any]:
        """Extract enhanced metadata using DSPy agent"""
        try:
            result = self.metadata_extractor(
                agent_instructions=AGENT_INSTRUCTIONS,
                content=get_n_words(content, S2Config.MAX_CONTENT_WORDS),
                filename=filename
            )
            
            return {
                'title': result.title,
                'headings': parse_json_safely(result.headings, []),
                'code_languages': parse_json_safely(result.code_languages, [])
            }
        except Exception as e:
            logger.warning(f"Enhanced metadata extraction failed: {e}")
            return {}
    
    def _classify_document(self, content: str, title: str, overview_context: str) -> Dict[str, Any]:
        """Classify document type and complexity"""
        try:
            result = self.classifier(
                agent_instructions=AGENT_INSTRUCTIONS,
                content=get_n_words(content, S2Config.MAX_CONTENT_WORDS),
                title=title,
                overview_context=overview_context
            )
            
            return {
                'doc_type': result.doc_type,
                'complexity_level': result.complexity_level
            }
        except Exception as e:
            logger.warning(f"Document classification failed: {e}")
            return {
                'doc_type': DocumentType.DOCUMENTATION,
                'complexity_level': ComplexityLevel.INTERMEDIATE
            }
    
    def _extract_concepts(self, content: str, doc_type: str, title: str) -> Dict[str, Any]:
        """Extract key concepts and learning objectives"""
        try:
            result = self.concept_extractor(
                agent_instructions=AGENT_INSTRUCTIONS,
                content=get_n_words(content, S2Config.MAX_CONTENT_WORDS),
                doc_type=doc_type,
                title=title
            )
            
            return {
                'key_concepts': parse_json_safely(result.key_concepts, []),
                'learning_objectives': parse_json_safely(result.learning_objectives, [])
            }
        except Exception as e:
            logger.warning(f"Concept extraction failed: {e}")
            return {
                'key_concepts': [],
                'learning_objectives': []
            }
    
    def _analyze_semantics(self, content: str, key_concepts: List[str], doc_type: str) -> Dict[str, Any]:
        """Analyze semantic relationships and generate summary"""
        try:
            result = self.semantic_analyzer(
                agent_instructions=AGENT_INSTRUCTIONS,
                content=get_n_words(content, S2Config.MAX_CONTENT_WORDS),
                key_concepts=json.dumps(key_concepts),
                doc_type=doc_type
            )
            
            return {
                'semantic_summary': result.semantic_summary,
                'prerequisites': parse_json_safely(result.prerequisites, []),
                'related_topics': parse_json_safely(result.related_topics, [])
            }
        except Exception as e:
            logger.warning(f"Semantic analysis failed: {e}")
            return {
                'semantic_summary': "Analysis not available",
                'prerequisites': [],
                'related_topics': []
            }
    
    def analyze_document(self, file_path: str, overview_context: str = "") -> DocumentAnalysis:
        """Analyze a single document with multi-agent approach"""
        start_time = time.time()
        
        # Read document
        if isinstance(file_path, Path):
            file_path = str(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filepath = Path(file_path)
        
        # Extract basic metadata
        basic_data = extract_basic_metadata(content, filepath)
        
        # Enhanced metadata extraction (if basic data needs enrichment)
        enhanced_data = self._extract_enhanced_metadata(content, filepath.name)
        
        # Merge metadata (basic data takes precedence)
        title = basic_data.get('title') or enhanced_data.get('title', filepath.name)
        headings = basic_data.get('headings', []) or enhanced_data.get('headings', [])
        code_languages = basic_data.get('code_languages', []) or enhanced_data.get('code_languages', [])
        
        # Document classification
        classification = self._classify_document(content, title, overview_context)
        
        # Concept extraction
        concepts = self._extract_concepts(content, classification['doc_type'].value, title)
        
        # Semantic analysis
        semantics = self._analyze_semantics(content, concepts['key_concepts'], classification['doc_type'].value)
        
        # Create DocumentAnalysis object
        return DocumentAnalysis(
            file_path=file_path,
            title=title,
            doc_type=classification['doc_type'],
            complexity_level=classification['complexity_level'],
            key_concepts=concepts['key_concepts'],
            learning_objectives=concepts['learning_objectives'],
            semantic_summary=semantics['semantic_summary'],
            prerequisites=semantics['prerequisites'],
            related_topics=semantics['related_topics'],
            headings=headings,
            code_languages=code_languages,
            frontmatter=basic_data['frontmatter'],
            word_count=len(content.split()),
            metadata={
                'processing_time': time.time() - start_time,
                'stage': 'stage2',
                'analysis_version': '1.0'
            }
        )
    
    def analyze_batch(self, file_paths: List[str], overview_context: str = "", 
                     progress_tracker: 'S2ProgressTracker' = None) -> List[DocumentAnalysis]:
        """Analyze multiple documents in parallel"""
        with ThreadPoolExecutor(max_workers=S2Config.MAX_WORKERS) as executor:
            futures = [
                executor.submit(self.analyze_document, file_path, overview_context)
                for file_path in file_paths
            ]
            
            results = []
            failed_files = 0
            
            for i, future in enumerate(futures):
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Update detailed progress
                    if progress_tracker:
                        current_file = Path(file_paths[i]).name
                        progress_tracker.update_detailed_progress(
                            total_files=len(file_paths),
                            processed_files=len(results),
                            current_file=current_file,
                            failed_files=failed_files
                        )
                        
                except Exception as e:
                    failed_files += 1
                    logger.error(f"Error analyzing document: {e}")
                    
                    # Update detailed progress for failed file
                    if progress_tracker:
                        current_file = Path(file_paths[i]).name if i < len(file_paths) else "unknown"
                        progress_tracker.update_detailed_progress(
                            total_files=len(file_paths),
                            processed_files=len(results),
                            current_file=f"Failed: {current_file}",
                            failed_files=failed_files
                        )
                    continue
            
            return results

# =============================================================================
# Progress Tracker
# =============================================================================

class S2ProgressTracker:
    """Tracks and updates Stage 2 progress"""
    
    def __init__(self, redis_client: redis.Redis, task_id: str, course_id: str = None):
        self.redis = redis_client
        self.task_id = task_id
        self.course_id = course_id
        self.progress_key = f"task:{task_id}:progress"
        self.detailed_progress_key = f"stage2_progress:{course_id}" if course_id else None
    
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
            
            logger.info(f"Stage 2 Progress: {progress}% - {message}")
        except Exception as e:
            logger.error(f"Failed to update progress: {e}")
    
    def update_detailed_progress(self, total_files: int, processed_files: int, 
                               current_file: str = "", failed_files: int = 0):
        """Update detailed progress for Stage 2"""
        if not self.detailed_progress_key:
            return
            
        try:
            detailed_data = {
                'total_files': total_files,
                'processed_files': processed_files,
                'failed_files': failed_files,
                'current_file': current_file,
                'stage': 'analyzing',
                'stage_description': f'Analyzing document {processed_files + 1} of {total_files}',
                'updated_at': datetime.now().isoformat()
            }
            
            self.redis.set(self.detailed_progress_key, json.dumps(detailed_data), ex=3600)
            logger.info(f"Stage 2 Detailed Progress: {processed_files}/{total_files} files")
        except Exception as e:
            logger.error(f"Failed to update detailed progress: {e}")

# =============================================================================
# Main Stage 2 Processor
# =============================================================================

def process_stage2(stage1_result: Stage1Result, user_input: Dict[str, Any] = None,
                  task_id: str = None, redis_client: redis.Redis = None, 
                  course_id: str = None) -> Stage2Result:
    """
    Process Stage 2: Document analysis with parallel processing
    
    Args:
        stage1_result: Result from Stage 1 with file paths
        user_input: User input dict with include_folders and overview_doc
        task_id: Task ID for progress tracking
        redis_client: Redis client for progress updates
        course_id: Course ID for detailed progress tracking
    
    Returns:
        Stage2Result with document analyses
    """
    # Parse user input
    if user_input:
        stage2_input = Stage2UserInput(**user_input)
    else:
        stage2_input = Stage2UserInput()

    try:
        # Convert relative paths to full paths for processing
        
        full_file_paths = [
            str(Path(stage1_result.repo_path) / file_path) 
            for file_path in stage1_result.available_files
        ]
        
        # Filter files based on user-selected folders
        files_to_analyze = filter_files_by_folders(
            full_file_paths,
            stage1_result.repo_path,
            stage2_input.include_folders
        )
        
        if stage2_input.include_folders:
            logger.info(f"Filtered to {len(files_to_analyze)} files based on selected folders")
        
        repo_path = Path(stage1_result.repo_path)
        
        # Initialize detailed progress tracking in Redis
        if course_id and redis_client:
            progress_key = f"stage2_progress:{course_id}"
            
            # Create list of relative file paths for progress display
            files_to_process = []
            for file_path in files_to_analyze:
                try:
                    relative_path = str(Path(file_path).relative_to(repo_path))
                    files_to_process.append(relative_path)
                except ValueError:
                    files_to_process.append(Path(file_path).name)
            
            # Initialize progress data for raw processing stage
            progress_data = {
                'total_files': len(files_to_process),
                'processed_files': 0,
                'failed_files': 0,
                'current_file': '',
                'files_to_process': files_to_process,
                'completed_files': [],
                'failed_files_list': [],
                'stage': 'raw_processing',
                'stage_description': 'Extracting content from markdown files',
                'updated_at': datetime.utcnow().isoformat()
            }
            redis_client.set(progress_key, json.dumps(progress_data))
            logger.info(f"Initialized Stage 2 progress tracking for {len(files_to_process)} files")
        
        # Stage 1: Raw document processing (reading files, basic extraction) - Sequential
        logger.info("Starting raw document processing...")
        
        raw_processed_files = []
        failed_files = 0
        
        for i, file_path in enumerate(files_to_analyze):
            try:
                # Update progress for current file
                if course_id and redis_client:
                    try:
                        relative_path = str(Path(file_path).relative_to(repo_path))
                    except ValueError:
                        relative_path = Path(file_path).name
                    
                    progress_data['current_file'] = relative_path
                    progress_data['processed_files'] = i
                    progress_data['updated_at'] = datetime.utcnow().isoformat()
                    redis_client.set(progress_key, json.dumps(progress_data))
                
                # Read and validate file
                if Path(file_path).exists():
                    raw_processed_files.append(file_path)
                    
                    # Add to completed list for progress tracking
                    if course_id and redis_client:
                        progress_data['completed_files'].append(relative_path)
                else:
                    failed_files += 1
                    if course_id and redis_client:
                        progress_data['failed_files_list'].append(relative_path)
                        progress_data['failed_files'] = failed_files
                    
            except Exception as e:
                failed_files += 1
                logger.error(f"Error in raw processing for {file_path}: {e}")
                if course_id and redis_client:
                    try:
                        relative_path = str(Path(file_path).relative_to(repo_path))
                    except ValueError:
                        relative_path = Path(file_path).name
                    progress_data['failed_files_list'].append(relative_path)
                    progress_data['failed_files'] = failed_files
        
        # Update progress for LLM analysis stage
        if course_id and redis_client:
            progress_data['stage'] = 'llm_analysis'
            progress_data['stage_description'] = 'Analyzing content with AI for key concepts and structure'
            progress_data['processed_files'] = 0  # Reset for LLM stage
            progress_data['completed_files'] = []
            progress_data['current_file'] = ''
            progress_data['total_files'] = len(raw_processed_files)  # Update total to successful raw files
            progress_data['updated_at'] = datetime.utcnow().isoformat()
            redis_client.set(progress_key, json.dumps(progress_data))
        
        logger.info(f"Starting parallel LLM analysis for {len(raw_processed_files)} files...")
        
        # Stage 2: LLM Analysis with parallel processing
        analyzer = DocumentAnalyzer()
        overview_context = prepare_overview_context(stage1_result, stage2_input, len(raw_processed_files))
        
        # Thread-safe counters and lists for progress tracking
        processed_count = threading.Event()
        failed_count = threading.Event() 
        progress_lock = threading.Lock()
        completed_files = []
        failed_files_list = []
        llm_failed_files = 0
        
        def analyze_document_with_progress(file_path: str, index: int) -> Optional[DocumentAnalysis]:
            """Analyze document with thread-safe progress updates"""
            nonlocal llm_failed_files
            
            try:
                # Get relative path for progress display
                try:
                    relative_path = str(Path(file_path).relative_to(repo_path))
                except ValueError:
                    relative_path = Path(file_path).name
                
                # Update progress (thread-safe)
                if course_id and redis_client:
                    with progress_lock:
                        progress_data['current_file'] = relative_path
                        progress_data['processed_files'] = len(completed_files)
                        progress_data['updated_at'] = datetime.utcnow().isoformat()
                        redis_client.set(progress_key, json.dumps(progress_data))
                
                # Analyze document with LLM
                doc_analysis = analyzer.analyze_document(file_path, overview_context)
                
                # Update completed list (thread-safe)
                if course_id and redis_client:
                    with progress_lock:
                        completed_files.append(relative_path)
                        progress_data['completed_files'] = completed_files.copy()
                        progress_data['processed_files'] = len(completed_files)
                        progress_data['updated_at'] = datetime.utcnow().isoformat()
                        redis_client.set(progress_key, json.dumps(progress_data))
                
                return doc_analysis
                    
            except Exception as e:
                logger.error(f"Error in LLM analysis for {file_path}: {e}")
                
                # Update failed list (thread-safe)
                if course_id and redis_client:
                    with progress_lock:
                        llm_failed_files += 1
                        failed_files_list.append(f"LLM: {relative_path}")
                        progress_data['failed_files_list'] = failed_files_list.copy()
                        progress_data['failed_files'] = failed_files + llm_failed_files
                        progress_data['updated_at'] = datetime.utcnow().isoformat()
                        redis_client.set(progress_key, json.dumps(progress_data))
                
                return None
        
        # Execute parallel analysis with ThreadPoolExecutor
        document_analyses = []
        with ThreadPoolExecutor(max_workers=S2Config.MAX_WORKERS) as executor:
            # Submit all tasks
            futures = [
                executor.submit(analyze_document_with_progress, file_path, i)
                for i, file_path in enumerate(raw_processed_files)
            ]
            
            # Collect results
            for future in futures:
                try:
                    result = future.result()
                    if result is not None:
                        document_analyses.append(result)
                except Exception as e:
                    logger.error(f"Error getting analysis result: {e}")
        
        # Final progress update
        if course_id and redis_client:
            progress_data['stage'] = 'completed'
            progress_data['stage_description'] = 'Document analysis completed'
            progress_data['current_file'] = ''
            progress_data['processed_files'] = len(document_analyses)
            progress_data['updated_at'] = datetime.utcnow().isoformat()
            redis_client.set(progress_key, json.dumps(progress_data))
        
        # Calculate statistics
        stats = calculate_statistics(document_analyses)
        
        # Create result
        result = Stage2Result(
            document_tree_path="",  # Will be set after saving if needed
            processed_files_count=len(document_analyses),
            failed_files_count=failed_files + llm_failed_files,
            include_folders=stage2_input.include_folders,
            overview_doc=stage2_input.overview_doc,
            analysis_timestamp=datetime.utcnow(),
            document_analyses=document_analyses,
            total_concepts=stats['total_concepts'],
            avg_complexity=stats['avg_complexity'],
            language_distribution=stats['language_distribution'],
            document_type_distribution=stats['document_type_distribution']
        )
        
        # Clean up progress data after completion
        if course_id and redis_client:
            # Keep progress for a bit for frontend to read, then clean up
            redis_client.expire(progress_key, 300)  # Expire after 5 minutes
        
        logger.info(f"Stage 2 completed: {len(document_analyses)} documents analyzed with parallel processing")
        return result
        
    except Exception as e:
        logger.error(f"Stage 2 failed: {e}")
        
        # Update progress with error
        if course_id and redis_client:
            try:
                progress_key = f"stage2_progress:{course_id}"
                progress_data = {
                    'stage': 'failed',
                    'stage_description': f'Document analysis failed: {str(e)}',
                    'error': str(e),
                    'updated_at': datetime.utcnow().isoformat()
                }
                redis_client.set(progress_key, json.dumps(progress_data))
            except Exception as progress_error:
                logger.error(f"Failed to update error progress: {progress_error}")
        
        raise e 