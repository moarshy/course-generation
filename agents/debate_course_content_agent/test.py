#!/usr/bin/env python3
"""
Test script for the Debate Course Content Agent
Demonstrates the complete workflow from document analysis to course generation
"""

import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
import dspy

# Add the parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from debate_course_content_agent.models import ComplexityLevel
from debate_course_content_agent.modules import (
    RepoManager, DocumentAnalyzer, DebateLearningPathGenerator,
    DebateModuleContentGenerator
)
from debate_course_content_agent.config import ModelConfig

load_dotenv()

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )

def test_document_analysis():
    """Test the multi-agent document analysis system"""
    
    print("\n" + "="*60)
    print("Testing Multi-Agent Document Analysis")
    print("="*60)
    
    # Configure DSPy
    dspy.configure(lm=dspy.LM(
        ModelConfig.MODEL_NAME, 
        max_tokens=ModelConfig.MAX_TOKENS, 
        cache=ModelConfig.CACHE_ENABLED
    ))
    
    # Initialize components
    repo_manager = RepoManager()
    analyzer = DocumentAnalyzer()
    
    # Example: analyze documents from a repository
    # Option 1: Local repository
    # repo_path = Path("/path/to/your/documentation")
    
    # Option 2: Remote repository (will be cloned automatically)
    repo_url = "https://github.com/your-org/your-repo"  # Replace with actual repository URL
    
    # Use RepoManager to handle both local and remote repositories
    try:
        repo_path = repo_manager.get_repo_path(repo_url)
    except Exception as e:
        print(f"⚠️  Failed to get repository: {e}")
        print("⚠️  Please update repo_url with a real repository URL or use a local path")
        return []
    
    # Find documentation files
    doc_files = repo_manager.find_documentation_files(
        repo_path, 
        include_folders=["docs"]  # Adjust as needed
    )
    
    if not doc_files:
        print("❌ No documentation files found")
        return []
    
    print(f"📚 Found {len(doc_files)} documentation files")
    
    # Read overview document if available
    overview_content = ""
    for file_path in doc_files:
        if "architecture" in file_path.name.lower() or "overview" in file_path.name.lower():
            try:
                overview_content = file_path.read_text(encoding='utf-8')
                print(f"📖 Using overview document: {file_path.name}")
                break
            except Exception as e:
                print(f"⚠️  Could not read overview file: {e}")
    
    # Analyze documents (limit to first 5 for testing)
    test_files = doc_files[:5]
    print(f"🔍 Analyzing {len(test_files)} documents...")
    
    document_analyses = analyzer.analyze_batch(
        [str(f) for f in test_files], 
        overview_context=overview_content
    )
    
    print(f"✅ Successfully analyzed {len(document_analyses)} documents")
    
    # Display results
    for analysis in document_analyses[:3]:  # Show first 3
        print(f"\n📄 {analysis.title}")
        print(f"   Type: {analysis.doc_type.value}")
        print(f"   Complexity: {analysis.complexity_level.value}")
        print(f"   Key Concepts: {', '.join(analysis.key_concepts[:3])}...")
        print(f"   Summary: {analysis.semantic_summary[:100]}...")
    
    return document_analyses

def test_learning_path_generation(document_analyses):
    """Test the debate-based learning path generation"""
    
    print("\n" + "="*60)
    print("Testing Debate-Based Learning Path Generation")
    print("="*60)
    
    if not document_analyses:
        print("❌ No document analyses available for testing")
        return None
    
    # Initialize learning path generator
    path_generator = DebateLearningPathGenerator()
    
    # Generate learning path with debate system
    print("🎭 Starting debate-based learning path generation...")
    
    all_proposals, all_critiques = path_generator.generate_learning_path(
        document_analyses=document_analyses,
        target_complexity=ComplexityLevel.BEGINNER,
        additional_instructions="Focus on practical examples and hands-on learning",
        overview_context="",  # Could use overview content here
        repo_name="TestDocumentation"
    )
    
    if not all_proposals:
        print("❌ No learning paths were generated")
        return None
    
    final_path = all_proposals[-1]
    
    print(f"🎯 Generated learning path: {final_path.title}")
    print(f"📝 Contains {len(final_path.modules)} modules")
    
    # Display debate history
    print("\n📋 Debate Summary:")
    for i, (proposal, critique) in enumerate(zip(all_proposals, all_critiques)):
        print(f"Round {i+1}: {proposal.title}")
        print(f"  Modules: {len(proposal.modules)}")
        print(f"  Critique: {critique[:150]}...")
    
    # Display final modules
    print(f"\n📚 Final Learning Path: {final_path.title}")
    for i, module in enumerate(final_path.modules, 1):
        print(f"{i}. {module.title}")
        print(f"   📄 Documents: {len(module.documents)}")
        print(f"   🎯 Objectives: {len(module.learning_objectives)}")
    
    return final_path

def test_module_content_generation(learning_path, document_analyses):
    """Test the debate-based module content generation"""
    
    print("\n" + "="*60)
    print("Testing Debate-Based Module Content Generation")
    print("="*60)
    
    if not learning_path or not document_analyses:
        print("❌ Missing learning path or document analyses")
        return
    
    # Initialize module content generator
    content_generator = DebateModuleContentGenerator()
    
    # Test with first module
    test_module = learning_path.modules[0]
    print(f"🎭 Generating content for module: {test_module.title}")
    
    # Generate module content with debate system
    module_content, debate_history = content_generator.generate_module_content(
        learning_module=test_module,
        document_analyses=document_analyses,
        target_complexity=learning_path.target_complexity,
        overview_context="",
        additional_instructions="Make it engaging and practical"
    )
    
    if module_content:
        print(f"✅ Successfully generated content for: {module_content.title}")
        print(f"📝 Debate rounds: {len(debate_history.rounds)}")
        print(f"🎯 Success: {debate_history.success}")
        
        # Show content sections (truncated)
        print(f"\n📖 Introduction: {module_content.introduction[:200]}...")
        print(f"📚 Main Content: {module_content.main_content[:200]}...")
        print(f"🎯 Assessment: {module_content.assessment[:200]}...")
        
        # Show debate history
        print(f"\n📋 Content Generation Debate History:")
        for round_info in debate_history.rounds:
            print(f"Round {round_info.round_number}: {round_info.severity}")
            if round_info.critique:
                print(f"  Critique: {round_info.critique[:100]}...")
            if round_info.error_message:
                print(f"  Errors: {round_info.error_message}")
    else:
        print("❌ Failed to generate module content")
        print(f"Debate rounds: {len(debate_history.rounds)}")

def test_complete_workflow():
    """Test the complete workflow from analysis to content generation"""
    
    print("🚀 Starting Complete Debate Course Content Agent Test")
    print("="*80)
    
    # Step 1: Document Analysis
    document_analyses = test_document_analysis()
    
    if not document_analyses:
        print("❌ Cannot proceed without document analyses")
        return False
    
    # Step 2: Learning Path Generation
    learning_path = test_learning_path_generation(document_analyses)
    
    if not learning_path:
        print("❌ Cannot proceed without learning path")
        return False
    
    # Step 3: Module Content Generation
    test_module_content_generation(learning_path, document_analyses)
    
    print("\n🎉 Complete workflow test finished!")
    return True

if __name__ == "__main__":
    setup_logging()
    
    print("Debate Course Content Agent Test Suite")
    print("="*50)
    
    try:
        # Run complete workflow test
        success = test_complete_workflow()
        
        if success:
            print("\n✅ All tests completed!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 