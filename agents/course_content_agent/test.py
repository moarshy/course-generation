#!/usr/bin/env python3
"""
Test script for the Course Content Agent based on content-generation.ipynb
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import the course_content_agent
sys.path.append(str(Path(__file__).parent.parent))
from course_content_agent.main import CourseBuilder

from datetime import datetime
import hashlib
import dspy
import logging

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )

def test_simple_course_builder():
    """Test using the simplified CourseBuilder interface"""
    
    print("\n" + "="*60)
    print("Testing simplified CourseBuilder interface")
    print("="*60)
    
    # Setup
    cache_dir = Path(__file__).parent.parent / '.cache'
    builder = CourseBuilder(cache_dir=str(cache_dir), max_workers=4)
    
    # Test build_course method
    success = builder.build_course(
        repo_path='https://github.com/modelcontextprotocol/docs',
        output_dir="course_output",
        cache_dir=".cache",
        batch_size=30,
        skip_llm=False,
        include_folders=["docs", "tutorials", "quickstart"],
        overview_doc="architecture.mdx"
    )
    
    if success:
        print("✓ CourseBuilder.build_course() completed successfully")
    else:
        print("✗ CourseBuilder.build_course() failed")
    
    return success

if __name__ == "__main__":
    setup_logging()
    
    print("Course Content Agent Test Suite")
    print("="*50)
    
    try:
        # Test 1: Simplified interface
        print("\nTest 1: Simplified CourseBuilder interface")
        success1 = test_simple_course_builder()
        if success1:
            print("\n✓ All tests passed!")
            sys.exit(0)
        else:
            print("\n✗ Some tests failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 