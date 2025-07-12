#!/usr/bin/env python3
"""
Comprehensive Course Generation Automation Script
Tests all endpoints and runs complete course generation process
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
import sys

# Configuration
BASE_URL = "http://localhost:8000"
DEV_TOKEN = "dev-token-12345"
HEADERS = {
    "Authorization": f"Bearer {DEV_TOKEN}",
    "Content-Type": "application/json"
}

# Test data
REPO_URL = "https://github.com/modelcontextprotocol/docs"
STAGE1_SELECTIONS = {
    "include_folders": ["docs"],
    "overview_doc": "docs/concepts/architecture.mdx"
}
STAGE2_INPUT = {
    "complexity_level": "beginner",
    "additional_info": "i would like to have the following modules - intro to MCP, mcp primitives (cover only tools, resources, prompts), first mcp server, first mcp client, conclusion"
}

def log(message: str, level: str = "INFO"):
    """Enhanced logging with timestamps"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def make_request(method: str, url: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
    """Make HTTP request with error handling"""
    try:
        full_url = f"{BASE_URL}{url}"
        log(f"{method} {full_url}")
        
        if data:
            log(f"Request data: {json.dumps(data, indent=2)}")
            
        if method.upper() == "GET":
            response = requests.get(full_url, headers=HEADERS, params=params)
        elif method.upper() == "POST":
            response = requests.post(full_url, headers=HEADERS, json=data)
        elif method.upper() == "PUT":
            response = requests.put(full_url, headers=HEADERS, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(full_url, headers=HEADERS)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        log(f"Response status: {response.status_code}")
        
        if response.status_code >= 400:
            log(f"Error response: {response.text}", "ERROR")
            
        try:
            result = response.json()
            if response.status_code < 400:
                log(f"Response data: {json.dumps(result, indent=2)}")
            return {"success": response.status_code < 400, "data": result, "status_code": response.status_code}
        except:
            return {"success": response.status_code < 400, "data": response.text, "status_code": response.status_code}
            
    except Exception as e:
        log(f"Request failed: {str(e)}", "ERROR")
        return {"success": False, "error": str(e)}

def test_health_endpoint():
    """Test health endpoint"""
    log("=== Testing Health Endpoint ===")
    result = make_request("GET", "/health")
    return result["success"]

def test_user_endpoints():
    """Test user endpoints"""
    log("=== Testing User Endpoints ===")
    
    # Test get current user
    log("Testing GET /api/users/me")
    result = make_request("GET", "/api/users/me")
    if not result["success"]:
        log("User endpoint failed - this is expected in dev mode", "WARN")
    
    return True

def test_project_endpoints():
    """Test project endpoints"""
    log("=== Testing Project Endpoints ===")
    
    # Test get user courses (should be empty initially)
    log("Testing GET /api/projects/")
    result = make_request("GET", "/api/projects/")
    if result["success"]:
        log(f"Found {len(result['data'])} existing courses")
    
    return result["success"]

def create_test_course():
    """Create a test course"""
    log("=== Creating Test Course ===")
    
    course_data = {
        "title": "MCP Documentation Course",
        "description": "A comprehensive course on Model Context Protocol based on the official documentation"
    }
    
    result = make_request("POST", "/api/projects/", course_data)
    if result["success"]:
        course_id = result["data"]["course_id"]
        log(f"Created course with ID: {course_id}")
        return course_id
    else:
        log("Failed to create course", "ERROR")
        return None

def start_course_generation(course_id: str):
    """Start course generation (Stage 1)"""
    log("=== Starting Course Generation (Stage 1) ===")
    
    generation_data = {
        "repo_url": REPO_URL
    }
    
    result = make_request("POST", f"/api/course-generation/{course_id}/start", generation_data)
    return result["success"]

def wait_for_stage_completion(course_id: str, stage_name: str, max_wait_seconds: int = 300):
    """Wait for a stage to complete"""
    log(f"=== Waiting for {stage_name} completion ===")
    
    # Map stage names to status keys
    stage_mapping = {
        "Stage 1": "CLONE_REPO",
        "Stage 2": "DOCUMENT_ANALYSIS", 
        "Stage 3": "PATHWAY_BUILDING",
        "Stage 4": "COURSE_GENERATION"
    }
    
    stage_key = stage_mapping.get(stage_name)
    if not stage_key:
        log(f"Unknown stage name: {stage_name}", "ERROR")
        return False
    
    start_time = time.time()
    while time.time() - start_time < max_wait_seconds:
        # Check course status
        result = make_request("GET", f"/api/course-generation/{course_id}/status")
        if result["success"]:
            data = result["data"]
            stage_statuses = data.get("stage_statuses", {})
            stage_status = stage_statuses.get(stage_key, "unknown")
            database_status = data.get("database_status", "unknown")
            
            log(f"Current {stage_name} status: {stage_status} (database: {database_status})")
            
            if stage_status == "completed":
                log(f"{stage_name} completed successfully!")
                return True
            elif stage_status == "failed" or "failed" in database_status.lower():
                log(f"{stage_name} failed!", "ERROR")
                return False
                
        time.sleep(10)  # Wait 10 seconds before checking again
    
    log(f"{stage_name} timeout after {max_wait_seconds} seconds", "ERROR")
    return False

def get_stage1_result(course_id: str):
    """Get Stage 1 results"""
    log("=== Getting Stage 1 Results ===")
    
    result = make_request("GET", f"/api/course-generation/{course_id}/stage1")
    if result["success"]:
        stage1_data = result["data"]
        log(f"Stage 1 results:")
        log(f"  - Repo name: {stage1_data.get('repo_name', 'N/A')}")
        log(f"  - Available folders: {len(stage1_data.get('available_folders', []))}")
        log(f"  - Available files: {len(stage1_data.get('available_files', []))}")
        log(f"  - Suggested overview docs: {stage1_data.get('suggested_overview_docs', [])}")
        return stage1_data
    else:
        log("Failed to get Stage 1 results", "ERROR")
        return None

def save_stage1_selections(course_id: str):
    """Save Stage 1 selections"""
    log("=== Saving Stage 1 Selections ===")
    
    result = make_request("POST", f"/api/course-generation/{course_id}/stage1/selections", STAGE1_SELECTIONS)
    if result["success"]:
        log("Stage 1 selections saved successfully")
        return True
    else:
        log("Failed to save Stage 1 selections", "ERROR")
        return False

def start_stage2(course_id: str):
    """Start Stage 2 - Document Analysis"""
    log("=== Starting Stage 2 - Document Analysis ===")
    
    result = make_request("POST", f"/api/course-generation/{course_id}/stage2", STAGE2_INPUT)
    if result["success"]:
        log("Stage 2 started successfully")
        return True
    else:
        log("Failed to start Stage 2", "ERROR")
        return False

def get_stage2_result(course_id: str):
    """Get Stage 2 results"""
    log("=== Getting Stage 2 Results ===")
    
    result = make_request("GET", f"/api/course-generation/{course_id}/stage2")
    if result["success"]:
        stage2_data = result["data"]
        log(f"Stage 2 results:")
        log(f"  - Processed files: {stage2_data.get('processed_files_count', 0)}")
        log(f"  - Failed files: {stage2_data.get('failed_files_count', 0)}")
        log(f"  - Analyzed documents: {len(stage2_data.get('analyzed_documents', []))}")
        return stage2_data
    else:
        log("Failed to get Stage 2 results", "ERROR")
        return None

def start_stage3(course_id: str):
    """Start Stage 3 - Learning Pathway Generation"""
    log("=== Starting Stage 3 - Learning Pathway Generation ===")
    
    stage3_input = {
        "complexity_level": "beginner",
        "additional_instructions": "Focus on practical implementation with hands-on examples"
    }
    
    result = make_request("POST", f"/api/course-generation/{course_id}/stage3", stage3_input)
    if result["success"]:
        log("Stage 3 started successfully")
        return True
    else:
        log("Failed to start Stage 3", "ERROR")
        return False

def get_stage3_result(course_id: str):
    """Get Stage 3 results"""
    log("=== Getting Stage 3 Results ===")
    
    result = make_request("GET", f"/api/course-generation/{course_id}/stage3")
    if result["success"]:
        stage3_data = result["data"]
        log(f"Stage 3 results received")
        # The structure might be complex, so just log that we got it
        return stage3_data
    else:
        log("Failed to get Stage 3 results", "ERROR")
        return None

def start_stage4(course_id: str):
    """Start Stage 4 - Course Generation"""
    log("=== Starting Stage 4 - Course Generation ===")
    
    stage4_input = {
        "selected_complexity": "beginner",
        "additional_instructions": "Focus on practical implementation with hands-on examples"
    }
    
    result = make_request("POST", f"/api/course-generation/{course_id}/stage4", stage4_input)
    if result["success"]:
        log("Stage 4 started successfully")
        return True
    else:
        log("Failed to start Stage 4", "ERROR")
        return False

def get_stage4_result(course_id: str):
    """Get Stage 4 results"""
    log("=== Getting Stage 4 Results ===")
    
    result = make_request("GET", f"/api/course-generation/{course_id}/stage4")
    if result["success"]:
        stage4_data = result["data"]
        log(f"Stage 4 results:")
        course_summary = stage4_data.get("course_summary", {})
        log(f"  - Course title: {course_summary.get('title', 'N/A')}")
        log(f"  - Description: {course_summary.get('description', 'N/A')}")
        log(f"  - Module count: {course_summary.get('module_count', 0)}")
        log(f"  - Export path: {course_summary.get('export_path', 'N/A')}")
        return stage4_data
    else:
        log("Failed to get Stage 4 results", "ERROR")
        return None

def poll_stage_progress(course_id: str, stage_num: int):
    """Poll stage progress"""
    log(f"=== Polling Stage {stage_num} Progress ===")
    
    progress_url = f"/api/course-generation/stage{stage_num}/progress"
    params = {"course_id": course_id}
    
    result = make_request("GET", progress_url, params=params)
    if result["success"]:
        log(f"Stage {stage_num} progress: {result['data']}")
    else:
        log(f"Failed to get Stage {stage_num} progress", "WARN")

def main():
    """Main automation function"""
    log("🚀 Starting Course Generation Automation")
    log(f"Using dev token: {DEV_TOKEN}")
    log(f"Target repo: {REPO_URL}")
    
    # Test all endpoints first
    if not test_health_endpoint():
        log("Health check failed, aborting", "ERROR")
        return
    
    test_user_endpoints()
    
    if not test_project_endpoints():
        log("Project endpoints failed, aborting", "ERROR")
        return
    
    # Create test course
    course_id = create_test_course()
    if not course_id:
        return
    
    # Start course generation
    if not start_course_generation(course_id):
        log("Failed to start course generation", "ERROR")
        return
    
    # Wait for Stage 1 completion
    if not wait_for_stage_completion(course_id, "Stage 1", 180):
        return
    
    # Get Stage 1 results
    stage1_result = get_stage1_result(course_id)
    if not stage1_result:
        return
    
    # Save Stage 1 selections
    if not save_stage1_selections(course_id):
        return
    
    # Start Stage 2
    if not start_stage2(course_id):
        return
    
    # Wait for Stage 2 completion
    if not wait_for_stage_completion(course_id, "Stage 2", 300):
        return
    
    # Get Stage 2 results
    stage2_result = get_stage2_result(course_id)
    if not stage2_result:
        return
    
    # Start Stage 3
    if not start_stage3(course_id):
        return
    
    # Wait for Stage 3 completion
    if not wait_for_stage_completion(course_id, "Stage 3", 300):
        return
    
    # Get Stage 3 results
    stage3_result = get_stage3_result(course_id)
    if not stage3_result:
        return
    
    # Start Stage 4
    if not start_stage4(course_id):
        return
    
    # Wait for Stage 4 completion
    if not wait_for_stage_completion(course_id, "Stage 4", 600):
        return
    
    # Get Stage 4 results
    stage4_result = get_stage4_result(course_id)
    if not stage4_result:
        return
    
    log("🎉 Course Generation Automation Completed Successfully!")
    log(f"Final course ID: {course_id}")

if __name__ == "__main__":
    main() 