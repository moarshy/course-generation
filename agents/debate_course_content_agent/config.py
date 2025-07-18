"""
Configuration settings for the Debate Course Content Agent
"""

# =============================================================================
# Model Configuration
# =============================================================================

class ModelConfig:
    """LLM model configuration"""
    MODEL_NAME = "gemini/gemini-2.5-flash"
    MAX_TOKENS = 20000
    CACHE_ENABLED = False

# =============================================================================
# Processing Configuration
# =============================================================================

class ProcessingConfig:
    """Configuration for document processing and generation"""
    
    # Document analysis
    MAX_OVERVIEW_WORDS = 10000
    MAX_CONTENT_WORDS = 20000
    
    # Debate rounds
    MAX_DEBATES = 3
    
    # Learning path constraints
    MIN_MODULES = 5
    MAX_MODULES = 10
    
    # File patterns
    INCLUDE_EXTENSIONS = ['*.md', '*.mdx']
    EXCLUDE_PATTERNS = {
        'node_modules', '.git', '__pycache__', '.pytest_cache',
        'venv', 'env', '.venv', 'build', 'dist', 'tests'
    }
    EXCLUDE_FILE_PREFIXES = {
        'license', 'contributing', 'code_of_conduct', 'security', 'patents'
    }

# =============================================================================
# System Configuration
# =============================================================================

class SystemConfig:
    """General system configuration"""
    CACHE_DIR = ".cache"
    LOG_LEVEL = "INFO"
    LOG_FILE = "debate_output.log"

# =============================================================================
# Agent Instructions
# =============================================================================

AGENT_INSTRUCTIONS = """
You are an expert educational content developer working as part of a multi-agent system. 
Your role is to create high-quality, engaging educational content that aligns with 
specified learning objectives and complexity levels.

Core principles:
1. Make content clear, concise, and pedagogically sound
2. Include practical examples and use cases
3. Structure content logically with clear sections
4. Ensure assessments test the learning objectives
5. Match the specified complexity level appropriately
6. Use provided source documents as the foundation for content
7. Collaborate effectively with other agents through iterative refinement

Adapt your approach based on the specific task:
- For document analysis: Focus on extracting key concepts, complexity level, and relationships
- For learning path design: Create logical, progressive sequences with clear prerequisites
- For content creation: Generate engaging material with clear structure and practical examples
""" 