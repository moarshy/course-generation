import os
import logging
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import dspy
from typing import Optional, List

from debate_course_content_agent.models import ComplexityLevel
from debate_course_content_agent.modules import (
    RepoManager, DocumentAnalyzer, DebateLearningPathGenerator,
    DebateModuleContentGenerator
)
from debate_course_content_agent.config import (
    ModelConfig, SystemConfig
)

load_dotenv()

# =============================================================================
# Configuration (imported from config.py)
# =============================================================================

# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(
    level=getattr(logging, SystemConfig.LOG_LEVEL),
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler(SystemConfig.LOG_FILE, mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Suppress litellm logs below WARNING
logging.getLogger("litellm").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# =============================================================================
# Configuration
# =============================================================================

# Configure DSPy with settings from config
dspy.configure(lm=dspy.LM(
    ModelConfig.MODEL_NAME, 
    max_tokens=ModelConfig.MAX_TOKENS, 
    cache=ModelConfig.CACHE_ENABLED
))

# =============================================================================
# Debate Course Builder
# =============================================================================

class DebateCourseBuilder:
    """Build courses using debate-based learning path generation"""
    
    def __init__(self, cache_dir: str = SystemConfig.CACHE_DIR):
        self.repo_manager = RepoManager(cache_dir)
        self.document_analyzer = DocumentAnalyzer()
        self.learning_path_generator = DebateLearningPathGenerator()
        self.module_content_generator = DebateModuleContentGenerator()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def build_course(self, 
                     repo_path: str, 
                     target_complexity: ComplexityLevel = ComplexityLevel.BEGINNER,
                     include_folders: Optional[List[str]] = None,
                     overview_doc: Optional[str] = None,
                     additional_instructions: str = "") -> bool:
        """
        Build a course using debate-based learning path generation
        
        Args:
            repo_path: Path to the documentation repository
            target_complexity: Target complexity level for the course
            include_folders: Optional list of folder paths to include
            overview_doc: Optional filename of overview document for context
            additional_instructions: Additional instructions for the agents
        
        Returns:
            bool: True if course generation was successful
        """
        try:
            logger.info(f"🎓 Starting debate-based course generation from: {repo_path}")
            logger.info(f"🎯 Target complexity: {target_complexity.value}")
            
            # Get repository path (clone if remote, validate if local)
            try:
                repo_path_obj = self.repo_manager.get_repo_path(repo_path)
            except Exception as e:
                logger.error(f"Failed to get repository: {e}")
                return False
            
            # Find documentation files
            doc_files = self.repo_manager.find_documentation_files(
                repo_path_obj, include_folders=include_folders
            )
            
            if not doc_files:
                logger.error("No documentation files found")
                return False
            
            logger.info(f"📚 Found {len(doc_files)} documentation files")
            
            # Find overview document content for context
            overview_content = self._find_overview_document(doc_files, overview_doc)
            
            # Analyze documents with multi-agent approach
            logger.info("🔍 Analyzing documents with multi-agent system...")
            document_analyses = self.document_analyzer.analyze_batch(
                [str(f) for f in doc_files], 
                overview_context=overview_content
            )
            
            if not document_analyses:
                logger.error("No documents were successfully analyzed")
                return False
            
            logger.info(f"✅ Successfully analyzed {len(document_analyses)} documents")
            
            # Generate learning path using debate system
            logger.info("🎭 Generating learning path using debate system...")
            all_proposals, all_critiques = self.learning_path_generator.generate_learning_path(
                document_analyses=document_analyses,
                target_complexity=target_complexity,
                additional_instructions=additional_instructions,
                overview_context=overview_content,
                repo_name=repo_path_obj.name
            )
            
            if not all_proposals:
                logger.error("No learning paths were generated")
                return False
            
            final_path = all_proposals[-1]  # Use the last (most refined) proposal
            
            logger.info(f"🎯 Generated learning path: {final_path.title}")
            logger.info(f"📝 Path contains {len(final_path.modules)} modules")
            
            # Log the debate process
            logger.info("📋 Debate Summary:")
            for i, (proposal, critique) in enumerate(zip(all_proposals, all_critiques)):
                logger.info(f"Round {i+1}: {proposal.title}")
                logger.info(f"  Critique: {critique[:100]}...")
            
            # Display final learning path
            self._display_learning_path(final_path)
            
            # Generate module content using debate system
            logger.info("\n🎭 Generating module content using debate system...")
            module_contents = self.generate_module_content(
                learning_path=final_path,
                document_analyses=document_analyses,
                target_complexity=target_complexity,
                overview_context=overview_content,
                additional_instructions=additional_instructions
            )
            
            if module_contents:
                logger.info(f"✅ Successfully generated content for {len(module_contents)} modules")
                self._display_module_content_summary(module_contents)
            else:
                logger.warning("❌ Failed to generate module content")
            
            return True
            
        except Exception as e:
            logger.error(f"Course generation failed: {e}")
            return False
    
    def _find_overview_document(self, doc_files: List[Path], overview_filename: Optional[str]) -> str:
        """Find and extract overview document content for context"""
        if not overview_filename:
            return ""
            
        for file_path in doc_files:
            if file_path.name.lower() == overview_filename.lower():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    logger.info(f"📖 Using overview document: {file_path.name}")
                    return content
                except Exception as e:
                    logger.warning(f"Failed to read overview file {file_path}: {e}")
                    return ""
        
        logger.warning(f"Overview file '{overview_filename}' not found in documentation files")
        return ""
    
    def _display_learning_path(self, learning_path):
        """Display the generated learning path in a nice format"""
        logger.info("\n" + "="*60)
        logger.info(f"📚 GENERATED LEARNING PATH: {learning_path.title}")
        logger.info("="*60)
        logger.info(f"📝 Description: {learning_path.description}")
        logger.info(f"🎯 Target Complexity: {learning_path.target_complexity.value}")
        logger.info(f"📊 Number of Modules: {len(learning_path.modules)}")
        logger.info("\n📋 MODULES:")
        
        for i, module in enumerate(learning_path.modules, 1):
            logger.info(f"\n{i}. {module.title}")
            logger.info(f"   📄 Documents: {len(module.documents)}")
            logger.info(f"   🎯 Learning Objectives: {len(module.learning_objectives)}")
            logger.info(f"   📝 Description: {module.description[:100]}...")
        
        logger.info("\n" + "="*60)
    
    def generate_module_content(self, learning_path, document_analyses, target_complexity, 
                               overview_context="", additional_instructions=""):
        """Generate content for all modules in the learning path"""
        
        logger.info(f"🎭 Starting module content generation for {len(learning_path.modules)} modules")
        
        module_contents = []
        
        for i, module in enumerate(learning_path.modules, 1):
            logger.info(f"🎯 Generating content for module {i}/{len(learning_path.modules)}: {module.title}")
            
            # Generate module content through debate process
            module_content, debate_history = self.module_content_generator.generate_module_content(
                learning_module=module,
                document_analyses=document_analyses,
                target_complexity=target_complexity,
                overview_context=overview_context,
                additional_instructions=additional_instructions
            )
            
            if module_content:
                module_contents.append(module_content)
                logger.info(f"✅ Successfully generated content for: {module.title}")
                logger.info(f"📝 Debate rounds: {len(debate_history.rounds)}")
                logger.info(f"🎯 Success: {debate_history.success}")
            else:
                logger.error(f"❌ Failed to generate content for: {module.title}")
        
        logger.info(f"🎉 Generated content for {len(module_contents)}/{len(learning_path.modules)} modules")
        return module_contents
    
    def _display_module_content_summary(self, module_contents):
        """Display summary of generated module content"""
        logger.info("\n" + "="*60)
        logger.info(f"📖 GENERATED MODULE CONTENT SUMMARY")
        logger.info("="*60)
        
        for i, content in enumerate(module_contents, 1):
            logger.info(f"\n{i}. {content.title}")
            logger.info(f"   📖 Introduction: {content.introduction[:150]}...")
            logger.info(f"   📚 Main Content: {content.main_content[:150]}...")
            logger.info(f"   🎯 Assessment: {content.assessment[:150]}...")
            logger.info(f"   📝 Summary: {content.summary[:150]}...")
        
        logger.info("\n" + "="*60)

# =============================================================================
# Convenience Functions
# =============================================================================

def build_course_from_repo(repo_path: str, 
                          target_complexity: ComplexityLevel = ComplexityLevel.BEGINNER,
                          include_folders: Optional[List[str]] = None,
                          overview_doc: Optional[str] = None,
                          additional_instructions: str = "") -> bool:
    """
    Convenience function for quick course building
    
    Args:
        repo_path: Path to repository (local path or remote URL like https://github.com/user/repo)
        target_complexity: Target complexity level for the course
        include_folders: Optional list of folder paths to include  
        overview_doc: Optional filename of overview document for context
        additional_instructions: Additional instructions for the agents
    
    Returns:
        bool: True if course generation was successful
    """
    builder = DebateCourseBuilder()
    return builder.build_course(
        repo_path=repo_path,
        target_complexity=target_complexity,
        include_folders=include_folders,
        overview_doc=overview_doc,
        additional_instructions=additional_instructions
    )

# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    # Example usage with local repository
    # repo_path = "/path/to/your/documentation"
    
    # Example usage with remote repository
    repo_path = "https://github.com/user/repo"  # Replace with actual repository URL
    
    success = build_course_from_repo(
        repo_path=repo_path,
        target_complexity=ComplexityLevel.BEGINNER,
        include_folders=["docs"],
        overview_doc="README.md",
        additional_instructions="Focus on practical examples and hands-on learning"
    )
    
    if success:
        print("✅ Course generation completed successfully!")
    else:
        print("❌ Course generation failed!")
        sys.exit(1) 