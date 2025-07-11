"""
Configuration settings for the Course Creator Worker
"""

import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# Model Configuration
# =============================================================================

class ModelConfig:
    """LLM model configuration for DSPy"""
    MODEL_NAME = "gemini/gemini-2.5-flash"
    MAX_TOKENS = 20000
    CACHE_ENABLED = False
    TEMPERATURE = 0.0

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
    LOG_FILE = "worker_output.log"

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

For learning path generation, ALWAYS create complete structured data with:
- Each module MUST have: module_id, title, description, documents, learning_objectives
- Use document file paths from the provided documents list
- Generate meaningful module_id values (e.g., "module_01", "module_02")
- Ensure learning_objectives are specific and measurable
- Assign relevant documents to each module based on content relevance

For document analysis: Focus on extracting key concepts, complexity level, and relationships
""" 