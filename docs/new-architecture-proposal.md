# Course Generation System - New Architecture Proposal

## 🎯 Overview

This document outlines a simplified architecture to replace the current pickle-file based system with a clean, database-driven approach using 4 focused services running as **Celery tasks** for asynchronous processing.

## 🔧 Current Issues

- **Pickle File Complexity**: Multiple `.pkl` files (`clone_repo.pkl`, `document_analysis_tree.pkl`, `pathway_building.pkl`)
- **Service Bloat**: `CourseGenerationService` is 1200+ lines with mixed responsibilities
- **Data Conversion**: Heavy "glue code" for transforming data between layers
- **Model Proliferation**: 40+ overlapping model classes

## 🏗️ New 4-Service Architecture with Celery

### Service Flow (Async Task Chain)
```
[User Request] → [Celery Task Chain]
    ↓
RepositoryCloneTask → DocumentAnalyserTask → LearningPathwayTask → ModulesGenerationTask
    ↓                    ↓                      ↓                     ↓
[DB Update]         [DB Update]           [DB Update]           [DB Update]
    ↓                    ↓                      ↓                     ↓
[Frontend Poll]     [Frontend Poll]       [Frontend Poll]       [Course Ready]
```

## 📊 Database Schema

### Core Tables

```sql
-- Main course tracking
CREATE TABLE courses (
    course_id TEXT PRIMARY KEY,  -- Using TEXT for SQLite compatibility
    user_id TEXT NOT NULL,
    repo_url TEXT NOT NULL,
    repo_name TEXT,
    title TEXT,
    description TEXT,
    status TEXT DEFAULT 'draft', -- 'draft', 'stage1_running', 'stage1_complete', 'stage2_running', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Celery task tracking
CREATE TABLE course_tasks (
    course_id TEXT REFERENCES courses(course_id) ON DELETE CASCADE,
    stage TEXT NOT NULL, -- 'stage1', 'stage2', 'stage3', 'stage4'
    task_id TEXT NOT NULL, -- Celery task ID
    status TEXT NOT NULL, -- 'PENDING', 'STARTED', 'SUCCESS', 'FAILURE', 'RETRY'
    progress_percentage INTEGER DEFAULT 0,
    current_step TEXT,
    error_message TEXT,
    metadata TEXT, -- JSON string for stage-specific data
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    PRIMARY KEY (course_id, stage)
);

-- Repository file structure from Stage 1
CREATE TABLE repository_files (
    id TEXT PRIMARY KEY,
    course_id TEXT REFERENCES courses(course_id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL, -- 'folder' or 'file'
    is_documentation BOOLEAN DEFAULT false,
    is_overview_candidate BOOLEAN DEFAULT false,
    file_size INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User selections from Stage 1
CREATE TABLE stage1_selections (
    course_id TEXT PRIMARY KEY REFERENCES courses(course_id) ON DELETE CASCADE,
    selected_folders TEXT NOT NULL, -- JSON array of folder paths
    overview_document TEXT,  -- selected overview doc path
    selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User inputs for Stage 2
CREATE TABLE stage2_inputs (
    course_id TEXT PRIMARY KEY REFERENCES courses(course_id) ON DELETE CASCADE,
    complexity_level TEXT NOT NULL, -- 'beginner', 'intermediate', 'advanced'
    additional_info TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analyzed documents from Stage 2
CREATE TABLE analyzed_documents (
    id TEXT PRIMARY KEY,
    course_id TEXT REFERENCES courses(course_id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    title TEXT,
    doc_type TEXT, -- 'guide', 'api', 'reference', etc.
    complexity_level TEXT,
    key_concepts TEXT, -- JSON array of concepts
    learning_objectives TEXT, -- JSON array of objectives
    summary TEXT,
    prerequisites TEXT, -- JSON array of prerequisites
    related_topics TEXT, -- JSON array of related topics
    word_count INTEGER,
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User inputs for Stage 3
CREATE TABLE stage3_inputs (
    course_id TEXT PRIMARY KEY REFERENCES courses(course_id) ON DELETE CASCADE,
    additional_info TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Learning pathways from Stage 3
CREATE TABLE pathways (
    id TEXT PRIMARY KEY,
    course_id TEXT REFERENCES courses(course_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    complexity_level TEXT,
    estimated_duration TEXT,
    prerequisites TEXT, -- JSON array of prerequisites
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Modules within pathways
CREATE TABLE modules (
    id TEXT PRIMARY KEY,
    pathway_id TEXT REFERENCES pathways(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    sequence_order INTEGER NOT NULL,
    learning_objectives TEXT, -- JSON array of objectives
    estimated_time TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document-module relationships
CREATE TABLE module_documents (
    module_id TEXT REFERENCES modules(id) ON DELETE CASCADE,
    document_id TEXT REFERENCES analyzed_documents(id) ON DELETE CASCADE,
    PRIMARY KEY (module_id, document_id)
);

-- User selection from Stage 3
CREATE TABLE stage3_selections (
    course_id TEXT PRIMARY KEY REFERENCES courses(course_id) ON DELETE CASCADE,
    selected_pathway_id TEXT REFERENCES pathways(id),
    selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Generated course content from Stage 4
CREATE TABLE generated_courses (
    course_id TEXT PRIMARY KEY REFERENCES courses(course_id) ON DELETE CASCADE,
    pathway_id TEXT REFERENCES pathways(id),
    export_path TEXT,
    status TEXT DEFAULT 'generating', -- 'generating', 'completed', 'failed'
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Generated module content
CREATE TABLE module_content (
    module_id TEXT PRIMARY KEY REFERENCES modules(id) ON DELETE CASCADE,
    introduction TEXT,
    main_content TEXT,
    conclusion TEXT,
    assessment TEXT,
    summary TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🔧 Celery Task Definitions

### 1. RepositoryCloneTask

**Celery Task**: `tasks.repository_clone_task`

**Input**: 
- `course_id: str`
- `repo_url: str`

**Process**:
- Updates task status to 'STARTED'
- Clone/access repository (progress: 20%)
- Scan for documentation files (progress: 60%)
- Identify folder structure (progress: 80%)
- Save to `repository_files` table (progress: 100%)

**Output**:
- Database records in `repository_files`
- Task status 'SUCCESS'
- Course status → 'stage1_complete'

**Celery Implementation**:
```python
@celery_app.task(bind=True)
def repository_clone_task(self, course_id: str, repo_url: str):
    # Update task status
    update_task_progress(course_id, 'stage1', self.request.id, 'STARTED', 0)
    
    try:
        # Step 1: Clone repository
        update_task_progress(course_id, 'stage1', self.request.id, 'STARTED', 20, "Cloning repository...")
        repo_data = clone_repository(repo_url)
        
        # Step 2: Scan for files
        update_task_progress(course_id, 'stage1', self.request.id, 'STARTED', 60, "Scanning files...")
        files = scan_documentation_files(repo_data)
        
        # Step 3: Save to database
        update_task_progress(course_id, 'stage1', self.request.id, 'STARTED', 80, "Saving to database...")
        save_repository_files(course_id, files)
        
        # Complete
        update_task_progress(course_id, 'stage1', self.request.id, 'SUCCESS', 100, "Repository analysis complete")
        update_course_status(course_id, 'stage1_complete')
        
        return {"status": "success", "files_count": len(files)}
        
    except Exception as e:
        update_task_progress(course_id, 'stage1', self.request.id, 'FAILURE', 0, str(e))
        update_course_status(course_id, 'stage1_failed')
        raise
```

### 2. DocumentAnalyserTask

**Celery Task**: `tasks.document_analyser_task`

**Input**: 
- `course_id: str`
- `complexity_level: str`
- `additional_info: str`

**Process**:
- Load selected documents from database
- AI analysis for each document (progress tracking per doc)
- Save analysis to `analyzed_documents` table

**Trigger**: After user makes Stage 1 selections

**Celery Implementation**:
```python
@celery_app.task(bind=True)
def document_analyser_task(self, course_id: str, complexity_level: str, additional_info: str):
    update_task_progress(course_id, 'stage2', self.request.id, 'STARTED', 0)
    
    try:
        # Get selected documents
        selected_docs = get_selected_documents(course_id)
        total_docs = len(selected_docs)
        
        for i, doc in enumerate(selected_docs):
            progress = int((i / total_docs) * 100)
            update_task_progress(course_id, 'stage2', self.request.id, 'STARTED', progress, f"Analyzing {doc.file_path}...")
            
            # AI analysis
            analysis = analyze_document_with_ai(doc, complexity_level, additional_info)
            save_document_analysis(course_id, doc.file_path, analysis)
        
        update_task_progress(course_id, 'stage2', self.request.id, 'SUCCESS', 100, "Document analysis complete")
        update_course_status(course_id, 'stage2_complete')
        
        return {"status": "success", "analyzed_docs": total_docs}
        
    except Exception as e:
        update_task_progress(course_id, 'stage2', self.request.id, 'FAILURE', 0, str(e))
        update_course_status(course_id, 'stage2_failed')
        raise
```

### 3. LearningPathwayTask

**Celery Task**: `tasks.learning_pathway_task`

**Input**: 
- `course_id: str`
- `additional_info: str`

**Process**:
- Load analyzed documents
- Generate multiple pathway options using AI
- Save to `pathways` and `modules` tables

**Trigger**: After user provides Stage 2 inputs

### 4. ModulesGenerationTask

**Celery Task**: `tasks.modules_generation_task`

**Input**: 
- `course_id: str`
- `selected_pathway_id: str`

**Process**:
- Load selected pathway and modules
- Generate content for each module using AI
- Export course files
- Save to `module_content` and `generated_courses`

**Trigger**: After user selects pathway in Stage 3

## 🚀 API Endpoints with Celery Integration

### Stage 1: Repository Analysis
```python
# Start repository analysis (async)
POST /api/courses/{course_id}/analyze-repository
{
    "repo_url": "https://github.com/user/repo"
}
# Returns: {"task_id": "celery-task-id", "status": "started"}

# Check task progress
GET /api/courses/{course_id}/stage1/status
# Returns: {"status": "STARTED", "progress": 45, "current_step": "Scanning files..."}

# Get results (when complete)
GET /api/courses/{course_id}/repository-files
# Returns: folders, files, overview_candidates

# Submit user selections (triggers Stage 2)
POST /api/courses/{course_id}/stage1-selections
{
    "selected_folders": ["docs", "guides"],
    "overview_document": "README.md"
}
# Returns: {"message": "Selections saved", "next_stage": "stage2"}
```

### Stage 2: Document Analysis
```python
# Start document analysis (async)
POST /api/courses/{course_id}/analyze-documents
{
    "complexity_level": "intermediate",
    "additional_info": "Focus on practical examples"
}
# Returns: {"task_id": "celery-task-id", "status": "started"}

# Check progress
GET /api/courses/{course_id}/stage2/status
# Returns: {"status": "STARTED", "progress": 60, "current_step": "Analyzing docs/guide.md..."}

# Get results
GET /api/courses/{course_id}/analyzed-documents
# Returns: document analyses with concepts, objectives
```

### Stage 3: Learning Pathway Generation
```python
# Start pathway generation (async)
POST /api/courses/{course_id}/generate-pathways
{
    "additional_info": "Beginner-friendly with hands-on exercises"
}
# Returns: {"task_id": "celery-task-id", "status": "started"}

# Check progress
GET /api/courses/{course_id}/stage3/status

# Get pathway options
GET /api/courses/{course_id}/pathways

# Select pathway (triggers Stage 4)
POST /api/courses/{course_id}/stage3-selections
{
    "selected_pathway_id": "pathway-123"
}
```

### Stage 4: Course Generation
```python
# Start course generation (async)
POST /api/courses/{course_id}/generate-course
# Returns: {"task_id": "celery-task-id", "status": "started"}

# Check progress
GET /api/courses/{course_id}/stage4/status

# Get final course
GET /api/courses/{course_id}/generated-course
```

## 🔄 Frontend Integration

### Real-time Progress Updates
```javascript
// Frontend polling for task status
const checkStageProgress = async (courseId, stage) => {
    const response = await fetch(`/api/courses/${courseId}/${stage}/status`);
    const data = await response.json();
    
    if (data.status === 'STARTED') {
        updateProgressBar(data.progress, data.current_step);
        // Poll again in 2 seconds
        setTimeout(() => checkStageProgress(courseId, stage), 2000);
    } else if (data.status === 'SUCCESS') {
        showStageComplete(stage);
        loadStageResults(courseId, stage);
    } else if (data.status === 'FAILURE') {
        showError(data.error_message);
    }
};
```

### Simplified State Management
```javascript
// No more complex file polling - just simple API calls
const courseState = {
    stage1: { status: 'pending', progress: 0 },
    stage2: { status: 'pending', progress: 0 },
    stage3: { status: 'pending', progress: 0 },
    stage4: { status: 'pending', progress: 0 }
};
```

## 🚀 Implementation Benefits

### Eliminated Complexity
- ❌ No more pickle files
- ❌ No file-based polling
- ❌ No data conversion layers
- ❌ No massive service classes
- ❌ No synchronous blocking operations

### Added Simplicity
- ✅ Proper async task processing with Celery
- ✅ Database-driven progress tracking
- ✅ Clear task status monitoring
- ✅ Automatic retry and error handling
- ✅ Scalable background processing
- ✅ Real-time progress updates

### Task Flow
```
User Request → Celery Task → Database Update → Frontend Poll → Next Stage
```

## 📋 Migration Strategy

### Phase 1: Database & Task Setup
1. ✅ Create SQLite database schema  
2. ✅ Set up Celery task infrastructure
3. ✅ Implement RepositoryCloneTask

### Phase 2: Task Implementation
1. Implement DocumentAnalyserTask
2. Implement LearningPathwayTask  
3. Implement ModulesGenerationTask
4. Add task chaining and error handling

### Phase 3: Frontend Integration
1. Update frontend to trigger async tasks
2. Add progress monitoring components
3. Remove file-based polling system

### Phase 4: Cleanup
1. Remove all pickle file handling
2. Delete old synchronous services
3. Clean up model definitions

## 🔍 Technical Considerations

### Celery Configuration
```python
# celery_config.py
broker_url = 'redis://redis:6379/0'
result_backend = 'redis://redis:6379/0'
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# Task routing
task_routes = {
    'tasks.repository_clone_task': {'queue': 'repo_analysis'},
    'tasks.document_analyser_task': {'queue': 'ai_processing'},
    'tasks.learning_pathway_task': {'queue': 'ai_processing'},
    'tasks.modules_generation_task': {'queue': 'ai_processing'},
}
```

### Error Handling & Retries
```python
@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def document_analyser_task(self, course_id: str, complexity_level: str, additional_info: str):
    # Task implementation with automatic retries
```

### Monitoring & Debugging
- Celery Flower dashboard for task monitoring
- Database logs for progress tracking
- Structured error messages in task results
- Task execution time tracking

This architecture ensures proper async processing while maintaining simplicity and eliminating the pickle file complexity. 