import os
import pickle
import hashlib
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import git
import dspy
from urllib.parse import urlparse
import re
import frontmatter
import logging


from course_content_agent.models import (
    DocumentType, ComplexityLevel, DocumentMetadata, DocumentNode,
    DocumentTree, AssessmentPoint, LearningModule, GroupedLearningPath,
    ModuleContent, GeneratedCourse
)
from course_content_agent.signatures import (
    DocumentClassifier, DocumentClusterer,
    WelcomeMessageGenerator, ModuleIntroGenerator, ModuleMainContentGenerator, 
    ModuleConclusionGenerator, ModuleSummaryGenerator, AssessmentContentGenerator, 
    CourseConclusionGenerator
)

logger = logging.getLogger(__name__)

# =============================================================================
# Multiprocessing Helper Functions (must be at module level)
# =============================================================================

def process_single_document(args):
    """Process a single document - must be top-level function for multiprocessing"""
    file_path, repo_path, use_llm = args
    
    try:
        relative_path = str(file_path.relative_to(repo_path))
        
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create basic metadata
        basic_data = ContentExtractor.extract_basic_metadata(content, file_path)
        
        # For multiprocessing, we'll do LLM processing in the main thread
        # This avoids complex serialization issues with dspy modules
        doc_id = hashlib.md5(relative_path.encode()).hexdigest()
        
        return {
            'success': True,
            'relative_path': relative_path,
            'doc_id': doc_id,
            'content': content,
            'basic_data': basic_data,
            'file_path': file_path
        }
        
    except Exception as e:
        return {
            'success': False,
            'relative_path': str(file_path.relative_to(repo_path)) if file_path else 'unknown',
            'error': str(e)
        }

def process_llm_analysis(args):
    """Process LLM analysis for a single document - must be top-level function for multiprocessing"""
    result, tree_root_path, overview_context = args
    
    try:
        # Load environment variables and configure DSPy for this worker process (needed for multiprocessing)
        from dotenv import load_dotenv
        import dspy
        load_dotenv()
        dspy.configure(lm=dspy.LM("gemini/gemini-2.5-flash", cache=False, max_tokens=20000, temperature=0.))
        
        relative_path = result['relative_path']
        
        # Initialize parser module for this worker process
        parser_module = DocumentParserModule()
        
        # Apply LLM analysis
        try:
            metadata = parser_module(
                content=result['content'], 
                filename=result['file_path'].name, 
                filepath=result['file_path'],
                overview_context=overview_context
            )
            llm_success = True
            error_msg = None
        except Exception as e:
            # Fall back to basic metadata if LLM fails
            metadata = create_basic_metadata_from_result(result)
            llm_success = False
            error_msg = str(e)
        
        # Create node data (don't create the actual node object due to serialization)
        node_data = {
            'id': result['doc_id'],
            'path': relative_path,
            'filename': result['file_path'].name,
            'content': result['content'],
            'metadata': metadata,
            'parent_path': str(result['file_path'].parent.relative_to(Path(tree_root_path))) 
            if result['file_path'].parent != Path(tree_root_path) else None
        }
        
        return {
            'success': True,
            'llm_success': llm_success,
            'relative_path': relative_path,
            'node_data': node_data,
            'error_msg': error_msg if not llm_success else None
        }
        
    except Exception as e:
        return {
            'success': False,
            'relative_path': result.get('relative_path', 'unknown'),
            'error': str(e)
        }


def create_basic_metadata_from_result(result):
    """Create basic metadata from processed result - helper function for multiprocessing"""
    basic_data = result['basic_data']
    
    return DocumentMetadata(
        title=basic_data['title'],
        headings=basic_data['headings'],
        code_blocks=basic_data['code_blocks'],
        frontmatter=basic_data['frontmatter'],
        primary_language=basic_data['primary_language'],
        doc_type=DocumentType.GUIDE,
        key_concepts=[],
        learning_objectives=[],
        semantic_summary=f"Documentation for {basic_data['title']}"
    )

# =============================================================================
# Repository Manager
# =============================================================================

class RepoManager:
    """Handles repository cloning, caching, and file discovery"""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
    def _get_repo_cache_path(self, repo_url: str) -> Path:
        """Generate cache path for repository"""
        repo_hash = hashlib.md5(repo_url.encode()).hexdigest()
        repo_name = urlparse(repo_url).path.strip('/').replace('/', '_')
        return self.cache_dir / f"{repo_name}_{repo_hash}"
    
    def _get_tree_cache_path(self, repo_url: str) -> Path:
        """Generate cache path for processed document tree"""
        cache_path = self._get_repo_cache_path(repo_url)
        return cache_path / "document_tree.pkl"
    
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
    
    def find_documentation_files(self, repo_path: Path, include_folders: Optional[List[str]] = None) -> List[Path]:
        """Find all markdown files in repository, optionally filtered by folders"""
        md_files = []
        for ext in ['*.md', '*.mdx']:
            md_files.extend(repo_path.rglob(ext))
        
        excluded_patterns = {
            'node_modules', '.git', '__pycache__', '.pytest_cache',
            'venv', 'env', '.venv', 'build', 'dist', 'tests'
        }
        
        filtered_files = []
        for file_path in md_files:
            if not any(excluded in file_path.parts for excluded in excluded_patterns):
                filtered_files.append(file_path)

        # Remove common non-content files
        filtered_files = [
            file for file in filtered_files 
            if not file.name.lower().startswith(('license', 'contributing', 'code_of_conduct', 'security', 'patents'))
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
    
    def save_tree_cache(self, tree: DocumentTree, repo_url: str):
        """Save processed document tree to cache"""
        cache_path = self._get_tree_cache_path(repo_url)
        cache_path.parent.mkdir(exist_ok=True)
        
        with open(cache_path, 'wb') as f:
            pickle.dump(tree, f)
        logger.info(f"Saved document tree cache to {cache_path}")
    
    def load_tree_cache(self, repo_url: str) -> Optional[DocumentTree]:
        """Load processed document tree from cache"""
        cache_path = self._get_tree_cache_path(repo_url)
        
        if not cache_path.exists():
            return None
            
        try:
            with open(cache_path, 'rb') as f:
                tree = pickle.load(f)
            logger.info(f"Loaded document tree cache from {cache_path}")
            return tree
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return None

# =============================================================================
# Enhanced Content Processors
# =============================================================================

class ContentExtractor:
    """Extract structured content from markdown files"""
    
    @staticmethod
    def extract_basic_metadata(content: str, filepath: Path) -> Dict[str, Any]:
        """Extract basic metadata from markdown content"""
        try:
            post = frontmatter.loads(content)
            frontmatter_data = post.metadata
            clean_content = post.content
        except:
            frontmatter_data = {}
            clean_content = content
        
        title = ContentExtractor._extract_title(clean_content, frontmatter_data, filepath.name)
        headings = ContentExtractor._extract_headings(clean_content)
        code_blocks = ContentExtractor._extract_code_blocks(clean_content)
        
        # Compute additional features
        primary_language = ContentExtractor._get_primary_language(code_blocks)
        
        return {
            'title': title,
            'headings': headings,
            'code_blocks': code_blocks,
            'frontmatter': frontmatter_data,
            'primary_language': primary_language
        }
    
    @staticmethod
    def _extract_title(content: str, frontmatter_data: dict, filename: str) -> str:
        """Extract document title"""
        if 'title' in frontmatter_data:
            return frontmatter_data['title'].strip()
        
        h1_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        if h1_match:
            return h1_match.group(1).strip()
        
        return filename.replace('.md', '').replace('.mdx', '').replace('_', ' ').replace('-', ' ').title().strip()
    
    @staticmethod
    def _extract_headings(content: str) -> List[str]:
        """Extract all headings from content, retaining Markdown # characters."""
        headings = []
        for match in re.finditer(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE):
            hashes = match.group(1)
            text = match.group(2).strip()
            headings.append(f"{hashes} {text}")
        return headings
    
    @staticmethod
    def _extract_code_blocks(content: str) -> List[Dict[str, str]]:
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
    
    @staticmethod
    def _get_primary_language(code_blocks: List[Dict[str, str]]) -> Optional[str]:
        """Determine the primary programming language"""
        if not code_blocks:
            return None
        
        # Count languages by total characters
        lang_chars = {}
        for block in code_blocks:
            lang = block['language'].lower()
            if lang not in ['text', 'txt', '']:
                lang_chars[lang] = lang_chars.get(lang, 0) + len(block['content'])
        
        if not lang_chars:
            return None
        
        return max(lang_chars.items(), key=lambda x: x[1])[0]

# =============================================================================
# Document Parser Module
# =============================================================================

class DocumentParserModule(dspy.Module):
    """Enhanced DSPy module for comprehensive document parsing"""
    
    def __init__(self):
        super().__init__()
        self.classifier = dspy.ChainOfThought(DocumentClassifier)
    
    def forward(self, content: str, filename: str, filepath: Path, overview_context: str = "") -> DocumentMetadata:
        """Parse document and extract comprehensive metadata"""
        
        # Extract basic metadata
        basic_data = ContentExtractor.extract_basic_metadata(content, filepath)
        
        # Set content limit for LLM processing
        DOCUMENT_PARSER_MAX_CHARS = 3000
        
        try:
            # Get LLM-enhanced analysis using single classifier
            classification = self.classifier(
                content=content[:DOCUMENT_PARSER_MAX_CHARS],
                overview_context=overview_context
            )
            
            # Parse LLM outputs with safe extraction
            semantic_summary = getattr(classification, 'semantic_summary', f"Documentation for {basic_data['title']}")
            
            # Safely handle key_concepts (could be string or list)
            key_concepts_raw = getattr(classification, 'key_concepts', "")
            if isinstance(key_concepts_raw, list):
                key_concepts = key_concepts_raw
            elif isinstance(key_concepts_raw, str):
                key_concepts = [concept.strip() for concept in key_concepts_raw.split(",") if concept.strip()] if key_concepts_raw else []
            else:
                key_concepts = []
            
            # Safely handle learning_objectives (could be string or list)
            learning_objectives_raw = getattr(classification, 'learning_objectives', "")
            if isinstance(learning_objectives_raw, list):
                learning_objectives = learning_objectives_raw
            elif isinstance(learning_objectives_raw, str):
                learning_objectives = [obj.strip() for obj in learning_objectives_raw.split(",") if obj.strip()] if learning_objectives_raw else []
            else:
                learning_objectives = []
            
            doc_type = self._safe_enum_parse(classification.doc_type, DocumentType, DocumentType.GUIDE)
            
        except Exception as e:
            logger.error(f"LLM parsing failed for {filename}: {e}")
            # Fallback to basic classification
            semantic_summary = f"Documentation for {basic_data['title']}"
            key_concepts = []
            learning_objectives = []
            doc_type = DocumentType.GUIDE
        
        # Create comprehensive metadata
        return DocumentMetadata(
            # Basic metadata
            title=basic_data['title'],
            headings=basic_data['headings'],
            code_blocks=basic_data['code_blocks'],
            frontmatter=basic_data['frontmatter'],
            primary_language=basic_data['primary_language'],
            
            # LLM-enhanced metadata
            doc_type=doc_type,
            key_concepts=key_concepts,
            learning_objectives=learning_objectives,
            semantic_summary=semantic_summary
        )
    
    def _safe_enum_parse(self, value: str, enum_class, default):
        """Safely parse enum value with fallback"""
        try:
            return enum_class(value.lower())
        except:
            return default


# =============================================================================
# Learning Path Generator
# =============================================================================

class LearningPathGenerator(dspy.Module):
    """DSPy module to generate comprehensive learning paths with Introduction → Topic modules → Conclusion"""
    
    def __init__(self):
        super().__init__()
        self.clusterer = dspy.ChainOfThought(DocumentClusterer)
        self.welcome_generator = dspy.ChainOfThought(WelcomeMessageGenerator)
    
    def forward(self, documents: List[DocumentNode], complexity: ComplexityLevel, 
                repo_name: str, overview_context: str = "") -> GroupedLearningPath:
        """
        Generate a comprehensive learning path for the given complexity level
        
        Args:
            documents: All available documents (no pre-filtering by complexity)
            complexity: Target complexity level
            repo_name: Name of the repository/project
            overview_context: Overview document content for context
            
        Returns:
            GroupedLearningPath: Complete learning path with modules and welcome message
        """
        
        logger.info(f"Generating learning path for {complexity.value} level with {len(documents)} documents")
        
        # Prepare comprehensive document information for the LLM
        documents_info = self._prepare_documents_info(documents)
        
        # Use LLM to intelligently cluster documents into modules
        try:
            cluster_result = self.clusterer(
                documents_info=json.dumps(documents_info),
                target_complexity=complexity.value,
                overview_context=overview_context
            )
            
            # Parse the modules from LLM output
            modules = self._parse_modules_from_llm(cluster_result.modules, documents)
            
        except Exception as e:
            logger.error(f"Error in LLM clustering: {e}")
        
        if not modules:
            logger.warning(f"No modules generated for {complexity.value} level")
            return None
        
        # Generate comprehensive course information
        course_info = self._generate_course_info(modules, complexity, repo_name, overview_context)
        
        # Create the complete learning path
        grouped_path = GroupedLearningPath(
            pathway_id=f"{repo_name}_{complexity.value}",
            title=course_info['title'],
            description=course_info['description'],
            target_complexity=complexity,
            modules=modules,
            welcome_message=course_info['welcome_message']
        )
        
        logger.info(f"Generated learning path with {len(modules)} modules for {complexity.value}")
        return grouped_path
    
    def generate_grouped_paths(self, tree: DocumentTree, overview_context: str = "") -> List[GroupedLearningPath]:
        """Generate learning paths for all complexity levels"""
        grouped_paths = []
        
        # Get all documents (no complexity filtering - let LLM decide)
        all_documents = list(tree.nodes.values())
        
        if not all_documents:
            logger.warning("No documents found for learning path generation")
            return grouped_paths
            
        logger.info(f"Generating learning paths for {len(all_documents)} documents")
        
        for complexity in ComplexityLevel:
            try:
                # Generate learning path for this complexity level
                grouped_path = self.forward(
                    documents=all_documents,
                    complexity=complexity,
                    repo_name=tree.repo_name or "Documentation",
                    overview_context=overview_context
                )
                
                if grouped_path:
                    grouped_paths.append(grouped_path)
                    
            except Exception as e:
                logger.error(f"Error generating learning path for {complexity.value}: {e}")
                continue
        
        return grouped_paths
    
    def _prepare_documents_info(self, documents: List[DocumentNode], n: int = 1000) -> Dict[str, Any]:
        """Prepare comprehensive document information for the LLM"""

        # add a function to get the first 1000 words of the document content
        def get_first_n_words(content: str, n: int) -> str:
            return ' '.join(content.split()[:n])
        
        docs_info = {}
        
        for doc in documents:
            # Create rich document information
            doc_info = {
                'title': doc.metadata.title,
                'filename': doc.filename,
                'semantic_summary': doc.metadata.semantic_summary or "No summary available",
                'key_concepts': doc.metadata.key_concepts or [],
                'learning_objectives': doc.metadata.learning_objectives or [],
                'primary_language': doc.metadata.primary_language,
                'headings': doc.metadata.headings[:5] if doc.metadata.headings else [],  # First 5 headings
                'document_content': get_first_n_words(doc.content, n)
            }
            
            docs_info[doc.path] = doc_info
        
        logger.info(f"Prepared information for {len(docs_info)} documents")
        return docs_info
    
    def _parse_modules_from_llm(self, modules_json: str, documents: List[DocumentNode]) -> List[LearningModule]:
        """Parse modules from LLM JSON output and create LearningModule objects"""
        
        try:
            modules_data = json.loads(modules_json)
            if not isinstance(modules_data, list):
                logger.error("LLM output is not a list of modules")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM modules JSON: {e}")
            return []
        
        modules = []
        doc_path_map = {doc.path: doc for doc in documents}
        
        for i, module_data in enumerate(modules_data):
            try:
                # Extract module information
                module_id = module_data.get('id', f"module_{i+1:02d}")
                name = module_data.get('name', f"Module {i+1}")
                description = module_data.get('detailed_description', module_data.get('description', ''))
                linked_docs = module_data.get('linked_docs', [])
                learning_objectives = module_data.get('learning_objectives', [])
                theme = module_data.get('theme', 'General')
                
                # Validate linked documents exist
                valid_linked_docs = []
                for doc_path in linked_docs:
                    if doc_path in doc_path_map:
                        valid_linked_docs.append(doc_path)
                    else:
                        logger.warning(f"Document not found: {doc_path}")
                
                # Create assessment
                assessment = AssessmentPoint(
                    assessment_id=f"{module_id}_assessment",
                    title=f"{name} Assessment",
                    concepts_to_assess=module_data.get('key_concepts', [name.lower()])[:5]
                )
                
                # Create learning module
                module = LearningModule(
                    module_id=module_id,
                    title=name,
                    theme=theme,
                    description=description,
                    documents=valid_linked_docs,
                    learning_objectives=learning_objectives,
                    assessment=assessment
                )
                
                modules.append(module)
                
            except Exception as e:
                logger.error(f"Error parsing module {i}: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(modules)} modules from LLM output")
        return modules
    
    def _generate_course_info(self, modules: List[LearningModule], 
                             complexity: ComplexityLevel, repo_name: str, overview_context: str = "") -> dict:
        """Generate comprehensive course information including title, description, and welcome message"""
        
        # Create modules overview
        modules_overview = []
        for i, module in enumerate(modules):
            modules_overview.append(f"Module {i+1}: {module.title}")
        
        try:
            course_info_result = self.welcome_generator(
                repo_name=repo_name,
                target_complexity=complexity.value,
                modules_overview="\n".join(modules_overview),
                overview_context=overview_context
            )
            
            return {
                'title': course_info_result.course_title,
                'description': course_info_result.course_description,
                'welcome_message': course_info_result.welcome_message
            }
            
        except Exception as e:
            logger.error(f"Error generating course info: {e}")
            raise
    

# =============================================================================
# Course Generator
# =============================================================================

class CourseGenerator(dspy.Module):
    """Generate complete course content with all 5 module components"""
    
    def __init__(self):
        super().__init__()
        # Use Predict instead of ChainOfThought for content generators to avoid reasoning field issues
        self.intro_generator = dspy.ChainOfThought(ModuleIntroGenerator)
        self.main_content_generator = dspy.ChainOfThought(ModuleMainContentGenerator)
        self.conclusion_generator = dspy.ChainOfThought(ModuleConclusionGenerator)
        self.summary_generator = dspy.ChainOfThought(ModuleSummaryGenerator)
        self.assessment_content_generator = dspy.ChainOfThought(AssessmentContentGenerator)
        self.course_conclusion_generator = dspy.ChainOfThought(CourseConclusionGenerator)
        self.max_workers = 10
    
    def forward(self, pathway: GroupedLearningPath, tree: DocumentTree, overview_context: str = "") -> GeneratedCourse:
        """Generate complete course content with full context"""
        return self.generate_course(pathway, tree, overview_context)
    
    def generate_course(self, pathway: GroupedLearningPath, tree: DocumentTree, overview_context: str = "") -> GeneratedCourse:
        """Generate complete course content with full context"""
        
        logger.info(f"Generating course content for {pathway.title}")
        
        # Generate content for each module in parallel
        logger.info(f"Generating {len(pathway.modules)} modules in parallel...")
        parallel_module_contents = self._generate_modules_parallel(pathway, tree, overview_context)
                
        # Generate course conclusion
        course_conclusion = self._generate_course_conclusion(pathway)
        
        # Create complete course
        course = GeneratedCourse(
            course_id=pathway.pathway_id,
            title=pathway.title,
            description=pathway.description,
            welcome_message=pathway.welcome_message,
            modules=parallel_module_contents,
            course_conclusion=course_conclusion
        )
        
        logger.info(f"Generated complete course with {len(parallel_module_contents)} modules (including intro)")
        return course
    
    def _generate_modules_parallel(self, pathway: GroupedLearningPath, tree: DocumentTree, overview_context: str) -> List[ModuleContent]:
        """Generate modules in parallel using threading (DSPy modules are not picklable for multiprocessing)"""
        
        from concurrent.futures import ThreadPoolExecutor
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Create a list of futures for each module
            futures = []
            for i, module in enumerate(pathway.modules):
                future = executor.submit(self._generate_module_content, module, pathway, tree, overview_context, i)
                futures.append(future)
            
            # Collect results
            module_contents = []
            for future in futures:
                module_contents.append(future.result())

        return module_contents    
    
    def _generate_module_content(self, module: LearningModule, pathway: GroupedLearningPath,
                               tree: DocumentTree, overview_context: str, module_index: int) -> ModuleContent:
        """
        Generate all 5 content pieces for a single module.
        """
        logger.info(f"-> Generating content for module: {module.title}")
        
        # Get source documents
        source_documents = self._get_source_documents_content(module, tree)
        
        # Generate all 5 components for the module
        course_context = f"This module, '{module.title}', is part of the '{pathway.title}' course. It covers: {module.description}"
        
        intro = self._generate_module_introduction(module, overview_context, course_context)
        main_content = self._generate_main_content(module, overview_context, source_documents)
        conclusion = self._generate_module_conclusion(module, overview_context)
        assessment = self._generate_assessment_content(module, overview_context, source_documents)
        summary = self._generate_module_summary(module, overview_context)
        
        return ModuleContent(
            module_id=f"module_{module_index:02d}",
            title=module.title,
            description=module.description,
            learning_objectives=module.learning_objectives,
            introduction=intro,
            main_content=main_content,
            conclusion=conclusion,
            assessment=assessment,
            summary=summary
        )
    
    def _get_source_documents_content(self, module: LearningModule, tree: DocumentTree) -> str:
        """Get filtered and cleaned content from source documents for this module"""
        
        source_content = []
        
        logger.info(f"Getting source documents for module {module.title}: {module.documents}")
        
        for doc_path in module.documents:
            if doc_path in tree.nodes:
                node = tree.nodes[doc_path]
                
                if node.content.strip():
                    doc_content = f"""
## {node.metadata.title}
{node.content}
"""
                    source_content.append(doc_content)
                    logger.info(f"Added document: {node.filename} ({len(node.content)} chars)")
                else:
                    logger.info(f"Skipped document {node.filename} - no relevant content after cleaning")
            else:
                logger.warning(f"Document not found in tree.nodes: {doc_path}")
        
        result = "\n".join(source_content)
        logger.info(f"Total cleaned source content length: {len(result)} chars")
        return result
    
    def _generate_module_introduction(self, module: LearningModule, overview_context: str, course_context: str) -> str:
        """Generate module introduction with full context"""
        
        result = self.intro_generator(
            module_title=module.title,
            module_description=module.description,
            learning_objectives=", ".join(module.learning_objectives),
            overview_context=overview_context,
            course_context=course_context
        )
        return result.introduction
    
    def _generate_main_content(self, module: LearningModule, overview_context: str, source_documents: str) -> str:
        """Generate synthesized main content from source documents"""
        
        result = self.main_content_generator(
            module_title=module.title,
            module_description=module.description,
            learning_objectives=", ".join(module.learning_objectives),
            overview_context=overview_context,
            source_documents=source_documents
        )
        return result.main_content
    
    def _generate_module_conclusion(self, module: LearningModule, overview_context: str) -> str:
        """Generate module conclusion"""
        
        result = self.conclusion_generator(
            module_title=module.title,
            learning_objectives=", ".join(module.learning_objectives),
            key_concepts=", ".join(module.assessment.concepts_to_assess),
            overview_context=overview_context
        )
        return result.conclusion
    
    def _generate_assessment_content(self, module: LearningModule, overview_context: str, source_documents: str) -> str:
        """Generate assessment with questions and answers"""
        
        result = self.assessment_content_generator(
            assessment_title=module.assessment.title,
            concepts_to_assess=", ".join(module.assessment.concepts_to_assess),
            module_theme=module.theme
        )
        return result.assessment_content
    
    def _generate_module_summary(self, module: LearningModule, overview_context: str) -> str:
        """Generate module summary"""
        
        result = self.summary_generator(
            module_title=module.title,
            learning_objectives=", ".join(module.learning_objectives),
            key_concepts=", ".join(module.assessment.concepts_to_assess),
            overview_context=overview_context
        )
        return result.summary
    
    def _generate_course_conclusion(self, pathway: GroupedLearningPath) -> str:
        """Generate course conclusion"""
        
        modules_summary = []
        for i, module in enumerate(pathway.modules):
            modules_summary.append(f"Module {i+1}: {module.title} - {module.theme}")
        
        result = self.course_conclusion_generator(
            course_title=pathway.title,
            modules_completed="\n".join(modules_summary)
        )
        return result.conclusion


# =============================================================================
# Course Exporter
# =============================================================================

class CourseExporter:
    """Handles exporting the generated course to markdown files."""
    
    def export_to_markdown(self, course: GeneratedCourse, output_dir: str) -> bool:
        """Exports the generated course content to a structured markdown directory."""
        
        try:
            output_path = Path(output_dir)
            
            # Extract complexity level from course_id for simplified folder naming
            # e.g., "repo_name_hash_beginner" -> "beginner"
            try:
                complexity_level = course.course_id.split('_')[-1]
                # Validate that it's a real complexity level
                if complexity_level not in [c.value for c in ComplexityLevel]:
                    complexity_level = "default"
            except IndexError:
                complexity_level = "default"

            course_output_dir = output_path / complexity_level
            course_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Write main welcome and conclusion files
            (course_output_dir / "00_welcome.md").write_text(course.welcome_message, encoding="utf-8")
            (course_output_dir / "99_conclusion.md").write_text(course.course_conclusion, encoding="utf-8")
                
            # Create modules
            module_info_list = []
            for i, module in enumerate(course.modules, 1):
                module_dir_name = f"module_{i:02d}"
                module_dir = course_output_dir / module_dir_name
                module_dir.mkdir(exist_ok=True)
                
                file_info = {
                    "intro": "01_intro.md",
                    "main": "02_main.md",
                    "conclusion": "03_conclusion.md",
                    "assessment": "04_assessments.md",
                    "summary": "05_summary.md",
                }
                
                # Write module files
                (module_dir / file_info['intro']).write_text(module.introduction, encoding='utf-8')
                (module_dir / file_info['main']).write_text(module.main_content, encoding='utf-8')
                (module_dir / file_info['conclusion']).write_text(module.conclusion, encoding='utf-8')
                (module_dir / file_info['assessment']).write_text(module.assessment, encoding='utf-8')
                (module_dir / file_info['summary']).write_text(module.summary, encoding='utf-8')

                module_info_list.append({
                    "module_id": module_dir_name,
                    "title": module.title,
                    "description": module.description,
                    "learning_objectives": module.learning_objectives,
                    "files": list(file_info.values())
                })
            
            # Create course_info.json
            course_info = {
                "title": course.title,
                "description": course.description,
                "modules": module_info_list
            }
            
            with open(course_output_dir / "course_info.json", 'w', encoding='utf-8') as f:
                json.dump(course_info, f, indent=2)
            
            logger.info(f"Course exported to {course_output_dir}")
            print(f"Course exported to: {course_output_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export course: {e}", exc_info=True)
            return False 