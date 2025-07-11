# Project Endpoints Architecture Analysis

## 🏗️ **System Overview**

The course generation system is built with a clear separation of concerns between **course management** and **course generation**:

- **Project Endpoints** (`/api/projects/*`): Handle course CRUD operations
- **Course-Generation Endpoints** (`/api/course-generation/*`): Handle async processing with Celery
- **Unified Database**: SQLite stores all data for both systems

## 🔄 **Project Endpoints Flow Analysis**

### Architecture Diagram

```
[Client Request] → [Authentication] → [Project Endpoint] → [CourseService] → [SQLite Database] → [Response]
                                                                ↓
[Course Generation] → [Celery Tasks] → [Task Progress] → [Database Updates] → [Status Monitoring]
```

---

## 📋 **Endpoint Breakdown**

### 1️⃣ **POST `/api/projects/`** - Create Course

**Purpose**: Create a new course project in draft status

**Request**:
```bash
POST /api/projects/
Content-Type: application/json
Authorization: Bearer <token>

{
  "title": "My Course",
  "description": "Course description"
}
```

**Flow**:
```
Client Request → Auth Check → CourseService.create_course → Generate UUID → SQLite INSERT → Return CourseInDB
```

**Database Interaction**:
- **Table**: `courses`
- **Operation**: `INSERT`
- **Data Created**:
  ```sql
  INSERT INTO courses (
    course_id, user_id, title, description, status, 
    repo_url, repo_name, created_at, updated_at
  ) VALUES (
    'generated-uuid', 'user-id', 'My Course', 'Description', 'draft',
    NULL, NULL, NOW(), NOW()
  )
  ```

**Response**:
```json
{
  "course_id": "abc-123-def",
  "title": "My Course", 
  "description": "Course description",
  "status": "draft",
  "user_id": "auth0|123",
  "repo_url": null,
  "repo_name": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**External Systems**:
- ❌ **Redis**: Not used
- ❌ **Celery**: Not triggered

---

### 2️⃣ **GET `/api/projects/`** - List User Courses

**Purpose**: Retrieve all courses belonging to the authenticated user

**Request**:
```bash
GET /api/projects/
Authorization: Bearer <token>
```

**Flow**:
```
Client Request → Auth Check → CourseService.get_user_courses → SQLite SELECT → Convert Models → Return List
```

**Database Interaction**:
- **Table**: `courses`
- **Operation**: `SELECT`
- **Query**:
  ```sql
  SELECT * FROM courses 
  WHERE user_id = 'auth0|123' 
  ORDER BY created_at DESC
  ```

**Response**:
```json
[
  {
    "course_id": "abc-123-def",
    "title": "My Course",
    "description": "Course description",
    "status": "draft",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

**External Systems**:
- ❌ **Redis**: Not used
- ❌ **Celery**: Not triggered

---

### 3️⃣ **GET `/api/projects/{course_id}`** - Get Specific Course

**Purpose**: Retrieve details of a specific course (with ownership verification)

**Request**:
```bash
GET /api/projects/abc-123-def
Authorization: Bearer <token>
```

**Flow**:
```
Client Request → Auth Check → Verify Ownership → CourseService.get_course_by_id → SQLite SELECT → Return Course
```

**Database Interactions**:

1. **Ownership Verification**:
   ```sql
   SELECT * FROM courses 
   WHERE course_id = 'abc-123-def' AND user_id = 'auth0|123'
   ```

2. **Course Retrieval**:
   ```sql
   SELECT * FROM courses 
   WHERE course_id = 'abc-123-def'
   ```

**Response**:
```json
{
  "course_id": "abc-123-def",
  "title": "My Course",
  "description": "Course description", 
  "status": "draft",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Error Handling**:
- Returns `404` if course doesn't exist or user doesn't own it

**External Systems**:
- ❌ **Redis**: Not used
- ❌ **Celery**: Not triggered

---

### 4️⃣ **PUT `/api/projects/{course_id}`** - Update Course

**Purpose**: Update course metadata (title, description, status)

**Request**:
```bash
PUT /api/projects/abc-123-def
Authorization: Bearer <token>

{
  "title": "Updated Title",
  "description": "New description",
  "status": "generating"
}
```

**Flow**:
```
Client Request → Auth Check → Verify Ownership → CourseService.update_course → SQLite UPDATE → Return Updated Course
```

**Database Interaction**:
- **Table**: `courses`
- **Operation**: `UPDATE`
- **Query**:
  ```sql
  UPDATE courses 
  SET title = 'Updated Title', 
      description = 'New description', 
      status = 'generating',
      updated_at = NOW()
  WHERE course_id = 'abc-123-def'
  ```

**Response**:
```json
{
  "course_id": "abc-123-def",
  "title": "Updated Title",
  "description": "New description",
  "status": "generating",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:45:00Z"
}
```

**External Systems**:
- ❌ **Redis**: Not used
- ❌ **Celery**: Not triggered

---

### 5️⃣ **DELETE `/api/projects/{course_id}`** - Delete Course

**Purpose**: Permanently delete a course and all associated data

**Request**:
```bash
DELETE /api/projects/abc-123-def
Authorization: Bearer <token>
```

**Flow**:
```
Client Request → Auth Check → Verify Ownership → CourseService.delete_course → SQLite DELETE → Delete File System → Return Success
```

**Database Interaction**:
- **Primary Delete**:
  ```sql
  DELETE FROM courses 
  WHERE course_id = 'abc-123-def' AND user_id = 'auth0|123'
  ```

- **CASCADE Deletes** (automatic):
  - `course_tasks` - All Celery task records
  - `repository_files` - Repository structure data
  - `stage1_selections` - User folder selections
  - `analyzed_documents` - Document analysis results
  - `pathways` & `modules` - Learning pathway data
  - `generated_courses` - Final course content
  - All other related tables

**File System Cleanup**:
- Deletes course directory: `data/{user_id}/{course_id}/`
- Removes all cached repository files
- Removes all generated course content

**Response**:
```json
{
  "message": "Course deleted successfully"
}
```

**External Systems**:
- ❌ **Redis**: Not used
- ❌ **Celery**: Not triggered (tasks may be running but will handle missing data gracefully)

---

## 🔍 **Task Status Monitoring System**

**Important**: Task monitoring is handled by **separate endpoints** under `/api/course-generation/*`

### 📊 **Status Tracking Endpoints**

```bash
# Overall generation status across all stages
GET /api/course-generation/{course_id}/status

# Individual stage progress
GET /api/course-generation/stage2/progress?course_id={id}
GET /api/course-generation/stage3/progress?course_id={id}  
GET /api/course-generation/stage4/progress?course_id={id}
```

### 🔄 **Task Lifecycle Flow**

```
[Celery Task Starts] → [Update course_tasks Table] → [Progress Updates During Execution] 
                                    ↓
[Frontend Polls Status] ← [Read from course_tasks] ← [Return Progress to Frontend]
```

### 💾 **Task Status Database Schema**

```sql
CREATE TABLE course_tasks (
    course_id TEXT,              -- Links to courses.course_id
    stage TEXT,                  -- 'stage1', 'stage2', 'stage3', 'stage4'
    task_id TEXT,                -- Celery task ID for tracking
    status TEXT,                 -- 'PENDING', 'STARTED', 'SUCCESS', 'FAILURE'
    progress_percentage INTEGER, -- 0-100 progress indicator
    current_step TEXT,           -- Human-readable current operation
    error_message TEXT,          -- Error details if failed
    started_at TIMESTAMP,        -- When task began
    completed_at TIMESTAMP,      -- When task finished
    PRIMARY KEY (course_id, stage)
);
```

### 📈 **Progress Tracking Example**

**1. Task Initialization**:
```sql
INSERT INTO course_tasks (
    course_id, stage, task_id, status, progress_percentage, 
    current_step, started_at
) VALUES (
    'abc-123', 'stage2', 'celery-task-456', 'STARTED', 0,
    'Starting document analysis...', NOW()
);
```

**2. Progress Updates** (called by Celery task):
```sql
UPDATE course_tasks 
SET progress_percentage = 45, 
    current_step = 'Analyzing file 15 of 33: README.md'
WHERE course_id = 'abc-123' AND stage = 'stage2';
```

**3. Task Completion**:
```sql
UPDATE course_tasks 
SET status = 'SUCCESS', 
    progress_percentage = 100,
    current_step = 'Document analysis complete',
    completed_at = NOW()
WHERE course_id = 'abc-123' AND stage = 'stage2';
```

### 🔄 **Frontend Monitoring Pattern**

**JavaScript Polling Implementation**:
```javascript
const pollTaskStatus = async (courseId) => {
  try {
    const response = await fetch(`/api/course-generation/${courseId}/status`);
    const status = await response.json();
    
    // Update UI with progress
    updateProgressBar(status.progress_percentage);
    updateCurrentStep(status.current_step);
    
    if (status.status === 'STARTED') {
      // Continue polling every 2 seconds
      setTimeout(() => pollTaskStatus(courseId), 2000);
    } else if (status.status === 'SUCCESS') {
      // Load stage results
      loadStageResults(courseId, status.current_stage);
    } else if (status.status === 'FAILURE') {
      // Show error
      showError(status.error_message);
    }
  } catch (error) {
    console.error('Status polling failed:', error);
  }
};
```

---

## 🎯 **Architecture Insights**

### ✅ **What Project Endpoints Handle:**
- **Course Metadata Management**: CRUD operations on course basic info
- **User Authorization**: Ownership verification for all operations
- **Data Validation**: Input validation and sanitization
- **Immediate Responses**: Synchronous operations with instant feedback

### ❌ **What Project Endpoints DON'T Handle:**
- **Content Generation**: No AI processing or course content creation
- **Async Processing**: No long-running operations
- **Task Management**: No Celery task coordination
- **Progress Tracking**: No status monitoring capabilities

### 🔗 **Clean Separation of Concerns:**

| Component | Responsibility | Data Store | Processing Type |
|-----------|---------------|------------|-----------------|
| **Project Endpoints** | Course CRUD | SQLite | Synchronous |
| **Course-Generation Endpoints** | Content processing | SQLite + Celery | Asynchronous |
| **Database Layer** | Unified data storage | SQLite | Persistent |
| **Celery Workers** | Background tasks | Redis (queue) | Distributed |

### 🚀 **Benefits of This Architecture:**

1. **Fast Project Operations**: Course management is instant (no waiting for generation)
2. **Scalable Generation**: Heavy processing doesn't block the API
3. **Real-time Monitoring**: Progress updates without blocking operations
4. **Data Consistency**: Single source of truth (SQLite) for all persistent data
5. **Error Isolation**: Generation failures don't affect course management
6. **User Experience**: Users can manage courses while generation runs in background

### 📊 **Data Flow Summary:**

```
Course Creation:    Client → Project API → SQLite → Response
Course Generation:  Client → Generation API → Celery → SQLite → Progress Updates
Status Monitoring:  Client → Status API → SQLite → Real-time Updates
```

This architecture ensures that course management remains fast and reliable while allowing complex AI-powered generation to run asynchronously in the background with proper progress tracking. 