# Course Management Documentation

## Overview

The course management feature allows users to create, read, update, and delete course projects. Each course is a separate project with its own dedicated file system structure for storing generated content and cache files.

## Data Structure

### Course Models

#### CourseCreate (Request)
```python
class CourseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
```

#### CourseUpdate (Request)
```python
class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[CourseStatus] = Field(None)
```

#### Course (Response)
```python
class Course(BaseModel):
    course_id: str
    title: str
    description: Optional[str] = None
    status: CourseStatus = CourseStatus.DRAFT
    created_at: datetime
    updated_at: datetime
```

#### CourseInDB (Internal)
```python
class CourseInDB(BaseModel):
    course_id: str
    title: str
    description: Optional[str] = None
    status: CourseStatus = CourseStatus.DRAFT
    user_id: str  # Auth0 user ID
    cache_dir: str  # Path to cache directory
    generated_course_dir: str  # Path to generated course directory
    created_at: datetime
    updated_at: datetime
```

### Course Status Enum
```python
class CourseStatus(str, Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
```

## File System Structure

The course management system creates a organized directory structure for each user and course:

```
data/                           # Root data directory (configurable)
├── google-oauth2_111962...     # User directory (sanitized Auth0 ID)
│   ├── course-uuid-1/
│   │   ├── cache/             # Cache files for this course
│   │   └── generated/         # Generated course content
│   ├── course-uuid-2/
│   │   ├── cache/
│   │   └── generated/
│   └── ...
└── auth0_user_456789/         # Another user's directory
    ├── course-uuid-3/
    │   ├── cache/
    │   └── generated/
    └── ...
```

### Directory Naming
- **User directories**: Auth0 user ID with `|` and `/` characters replaced with `_`
- **Course directories**: UUID v4 generated for each course
- **Cache directory**: Stores temporary files and processing data
- **Generated directory**: Stores final course content

## API Endpoints

### Authentication
All course endpoints require JWT authentication via the `Authorization: Bearer <token>` header.

### POST /api/projects/
Create a new course project.

**Request Body:**
```json
{
  "title": "Introduction to Python",
  "description": "A comprehensive course covering Python basics"
}
```

**Response:**
```json
{
  "course_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Introduction to Python",
  "description": "A comprehensive course covering Python basics",
  "status": "draft",
  "user_id": "google-oauth2|111962411139153579092",
  "cache_dir": "/path/to/data/google-oauth2_111962411139153579092/550e8400-e29b-41d4-a716-446655440000/cache",
  "generated_course_dir": "/path/to/data/google-oauth2_111962411139153579092/550e8400-e29b-41d4-a716-446655440000/generated",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### GET /api/projects/
Get all courses for the authenticated user.

**Response:**
```json
[
  {
    "course_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Introduction to Python",
    "description": "A comprehensive course covering Python basics",
    "status": "draft",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  },
  {
    "course_id": "550e8400-e29b-41d4-a716-446655440001",
    "title": "Advanced JavaScript",
    "description": "Deep dive into JavaScript concepts",
    "status": "completed",
    "created_at": "2024-01-14T15:20:00Z",
    "updated_at": "2024-01-15T09:45:00Z"
  }
]
```

### GET /api/projects/{course_id}
Get a specific course by ID.

**Response:**
```json
{
  "course_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Introduction to Python",
  "description": "A comprehensive course covering Python basics",
  "status": "draft",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### PUT /api/projects/{course_id}
Update an existing course.

**Request Body:**
```json
{
  "title": "Advanced Introduction to Python",
  "description": "An updated comprehensive course covering Python basics and advanced topics",
  "status": "generating"
}
```

**Response:**
```json
{
  "course_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Advanced Introduction to Python",
  "description": "An updated comprehensive course covering Python basics and advanced topics",
  "status": "generating",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:45:00Z"
}
```

### DELETE /api/projects/{course_id}
Delete a course and all associated files.

**Response:**
```json
{
  "message": "Course deleted successfully"
}
```

## Redis Data Schema

### Course Storage
```
Key: course:{course_id}
Value: {
  "course_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Introduction to Python",
  "description": "A comprehensive course covering Python basics",
  "status": "draft",
  "user_id": "google-oauth2|111962411139153579092",
  "cache_dir": "/path/to/cache",
  "generated_course_dir": "/path/to/generated",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### User Course Index
```
Key: user_courses:{user_id}
Value: Set of course_ids belonging to the user
```

## Frontend Components

### Dashboard
- **Location**: `src/pages/Dashboard.jsx`
- **Purpose**: Main course management interface
- **Features**: Course listing, creation, editing, deletion

### CourseCard
- **Location**: `src/components/CourseCard.jsx`
- **Purpose**: Individual course display component
- **Features**: Course info display, status indicators, action buttons

### CreateCourseModal
- **Location**: `src/components/CreateCourseModal.jsx`
- **Purpose**: Modal for creating new courses
- **Features**: Form validation, loading states, error handling

### EditCourseModal
- **Location**: `src/components/EditCourseModal.jsx`
- **Purpose**: Modal for editing existing courses
- **Features**: Pre-populated form, validation, save functionality

## Security Features

### Authorization
- **Course Ownership**: Users can only access their own courses
- **JWT Verification**: All endpoints require valid JWT tokens
- **Ownership Verification**: Each operation verifies course ownership

### Data Isolation
- **User Directories**: Each user has their own data directory
- **Course Isolation**: Each course has its own subdirectory
- **Path Sanitization**: User IDs are sanitized for filesystem safety

## Environment Configuration

### Backend Configuration
```bash
# Course Data Configuration
ROOT_DATA_DIR=./data  # Directory for storing course files
```

### Frontend Configuration
```bash
# API Configuration
VITE_API_BASE_URL=http://localhost:8000/api
```

## Error Handling

### Common Errors

1. **Course Not Found (404)**
   - Cause: Course doesn't exist or user doesn't have access
   - Response: `{"detail": "Course not found"}`

2. **Validation Error (422)**
   - Cause: Invalid input data
   - Response: Detailed validation error messages

3. **Server Error (500)**
   - Cause: Internal server error
   - Response: `{"detail": "Failed to create/update/delete course"}`

### Frontend Error Handling
- **Network Errors**: Retry buttons and error messages
- **Validation Errors**: Real-time form validation
- **Loading States**: Spinner animations and disabled buttons

## Usage Examples

### Creating a Course
```javascript
const courseData = {
  title: "React Fundamentals",
  description: "Learn React from scratch"
};

const response = await axios.post('/api/projects/', courseData, {
  headers: { Authorization: `Bearer ${token}` }
});
```

### Updating a Course
```javascript
const updateData = {
  title: "Advanced React Fundamentals",
  status: "generating"
};

const response = await axios.put(`/api/projects/${courseId}`, updateData, {
  headers: { Authorization: `Bearer ${token}` }
});
```

### Deleting a Course
```javascript
await axios.delete(`/api/projects/${courseId}`, {
  headers: { Authorization: `Bearer ${token}` }
});
```

## Testing

### Manual Testing
1. **Create Course**: Use the "New Course" button on the dashboard
2. **Edit Course**: Click "Edit" on any course card
3. **Delete Course**: Click "Delete" and confirm the action
4. **View Courses**: Navigate to the dashboard to see all courses

### API Testing
```bash
# Create a course
curl -X POST http://localhost:8000/api/projects/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Course", "description": "Test description"}'

# Get all courses
curl -X GET http://localhost:8000/api/projects/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Update a course
curl -X PUT http://localhost:8000/api/projects/COURSE_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Course Title"}'

# Delete a course
curl -X DELETE http://localhost:8000/api/projects/COURSE_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Troubleshooting

### Common Issues

1. **Directory Creation Errors**
   - Check write permissions for ROOT_DATA_DIR
   - Ensure the directory exists and is writable

2. **Course Not Found**
   - Verify course ownership
   - Check course ID format (should be UUID)

3. **Authentication Errors**
   - Ensure JWT token is valid and not expired
   - Check user authentication status

### Debug Commands

```bash
# Check if data directory exists
ls -la ./data

# Check course directories for a user
ls -la ./data/google-oauth2_111962411139153579092/

# Check Redis course data
redis-cli GET "course:550e8400-e29b-41d4-a716-446655440000"

# Check user course index
redis-cli SMEMBERS "user_courses:google-oauth2|111962411139153579092"
``` 