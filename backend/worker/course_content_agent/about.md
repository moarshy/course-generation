# Course Content Agent - Modular Architecture

This module generates structured learning courses from documentation repositories using AI-powered content analysis and multiprocessing for performance.

## File Structure

```
course_content_agent/
├── __init__.py              # Empty package initialization
├── main.py                 # CourseBuilder class and main orchestration logic
├── models.py               # Pydantic data models and enums
├── signatures.py           # DSPy signatures for LLM interactions
├── modules.py              # Implementation classes, utilities, and multiprocessing helpers
└── about.md              # This documentation file
```

## Module Responsibilities

### `models.py`
Contains all Pydantic data models and enums:
- **Enums**: `DocumentType`, `ComplexityLevel`
- **Core Models**: `DocumentMetadata`, `DocumentNode`, `DocumentTree`
- **Learning Models**: `AssessmentPoint`, `LearningModule`, `GroupedLearningPath`
- **Content Models**: `ModuleContent`, `GeneratedCourse`

### `signatures.py`
Contains DSPy signatures for LLM interactions:
- `DocumentClassifier` - Parse and classify markdown documents
- `DocumentClusterer` - Group documents into learning modules
- `WelcomeMessageGenerator` - Generate course information and welcome message
- Content generators: `ModuleIntroGenerator`, `ModuleMainContentGenerator`, `ModuleConclusionGenerator`, `ModuleSummaryGenerator`
- Assessment generator: `AssessmentContentGenerator`
- `CourseConclusionGenerator` - Generate final course wrap-up

### `modules.py`
Contains implementation classes and utilities:
- `RepoManager` - Git repository handling and file discovery
    - clones a repo and cache it
    - finds all documentation files using `find_documentation_files` function
- `ContentExtractor` - Markdown content processing and metadata extraction (Does not use any LLMs)
    - extracts basic metadata from markdown files including frontmatter
    - extracts titles, headings, code blocks, and primary language
- `DocumentParserModule` - DSPy module for document analysis
    - applies LLM analysis to classify documents and extract key concepts
    - falls back to basic metadata if LLM fails
- `LearningPathGenerator` - Creates structured learning paths from documents
    - groups related documents into learning modules using LLM clustering
    - generates course information (title, description, welcome message)
- `CourseGenerator` - Generates complete course content with parallel processing
    - creates 5 components per module (intro, main, conclusion, assessment, summary)
    - uses threading for parallel module generation
- `CourseExporter` - Exports courses to markdown format
    - creates organized folder structure for each module
    - exports all course content to markdown files
- Multiprocessing helper functions: `process_single_document`, `process_llm_analysis`

### `main.py`
Contains the main orchestration logic:
- `CourseBuilder` - Main class that coordinates the entire process
- `build_course_from_repo()` - Convenience function for quick usage
- DSPy configuration (currently using Gemini 2.5 Flash)
- Logging configuration

## How It Works (Process Flow)

1. **Repository Setup** (`RepoManager`)
   - Clone or update repository to local cache
   - Discover all markdown files (filtered by folders if specified)

2. **Content Extraction** (`ContentExtractor` + `DocumentParserModule`)
   - Extract basic metadata from each document (no LLM)
   - Apply LLM analysis for classification and key concepts
   - Build `DocumentTree` with all processed documents

3. **Learning Path Generation** (`LearningPathGenerator`)
   - Group related documents into learning modules using LLM
   - Create structured learning path with course information

4. **Content Generation** (`CourseGenerator`)
   - Generate 5 components per module in parallel:
     - Introduction, Main content, Conclusion, Assessment, Summary
   - Create course-level welcome message and conclusion

5. **Export** (`CourseExporter`)
   - Export all content to organized markdown file structure

## Usage

### Basic Usage
```python
from course_content_agent.main import CourseBuilder

# Initialize with custom settings
builder = CourseBuilder(max_workers=4, cache_dir="./my_cache")

# Build course with all options
success = builder.build_course(
    repo_path="https://github.com/example/docs",
    output_dir="course_output",
    cache_dir="doc_cache",
    batch_size=30,
    skip_llm=False,
    include_folders=["documentation", "guides"],
    overview_doc="architecture.md"
)
```

### Folder Filtering
```python
# Only process specific folders
success = builder.build_course(
    repo_path="/path/to/docs",
    include_folders=["docs", "guides", "api-reference"]
)
```

Folder rules:
- Paths are relative to the repository root
- Use forward slashes (works on all platforms)
- Subfolders are automatically included (e.g., "docs" includes "docs/api", "docs/guides", etc.)
- Use "." to include root-level files

### CourseBuilder Parameters

The `build_course()` method accepts these parameters:
- `repo_path` (str) - Repository URL or local path
- `output_dir` (str) - Output directory for generated course (default: "course_output")
- `cache_dir` (str) - Cache directory for processed documents (default: "doc_cache")
- `batch_size` (int) - Batch size for LLM processing (default: 50)
- `skip_llm` (bool) - Skip LLM analysis and use basic metadata only (default: False)
- `include_folders` (List[str]) - Only process files in these folders (optional)
- `overview_doc` (str) - Filename of overview document for context (optional)

## Configuration

### DSPy LLM Configuration
Currently configured to use Gemini 2.5 Flash in `main.py`:
```python
dspy.configure(lm=dspy.LM("gemini/gemini-2.5-flash", cache=False, max_tokens=20000, temperature=0.))
```

To use a different LLM, modify the configuration before creating `CourseBuilder`:
```python
import dspy
from course_content_agent.main import CourseBuilder

# Configure DSPy before creating CourseBuilder
dspy.configure(lm=dspy.LM("anthropic/claude-3-5-haiku-latest", cache=False))

builder = CourseBuilder()
```

## Output Structure

Generated courses are exported with the following structure:
```
course_output/
├── welcome.md              # Course introduction
├── module_01_introduction/ # First module
│   ├── intro.md           # Module introduction
│   ├── main.md            # Main content
│   ├── conclusion.md      # Module conclusion
│   ├── assessments.md     # Assessment questions
│   └── summary.md         # Module summary
├── module_02_*/           # Additional modules
└── conclusion.md          # Course conclusion
```