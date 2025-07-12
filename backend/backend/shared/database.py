"""
Database setup and models for the 4-service course generation architecture.
Uses SQLite with SQLAlchemy for simplicity.
"""

import os
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import create_engine, Column, String, Text, Integer, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from backend.core.config import settings

# Database URL for SQLite
DATABASE_URL = f"sqlite:///{settings.ROOT_DATA_DIR}/course_creator.db"

# Create database engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Database Models
class Course(Base):
    __tablename__ = "courses"
    
    course_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    repo_url = Column(String, nullable=True)  # Allow NULL for draft courses
    repo_name = Column(String)
    repo_path = Column(String, nullable=True)
    title = Column(String)
    description = Column(Text)
    status = Column(String, default='draft')  # 'draft', 'stage1_running', 'stage1_complete', etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    repository_files = relationship("RepositoryFile", back_populates="course", cascade="all, delete-orphan")
    course_tasks = relationship("CourseTask", back_populates="course", cascade="all, delete-orphan")

class CourseTask(Base):
    __tablename__ = "course_tasks"
    
    course_id = Column(String, ForeignKey('courses.course_id', ondelete='CASCADE'), primary_key=True)
    stage = Column(String, primary_key=True)  # 'stage1', 'stage2', 'stage3', 'stage4'
    task_id = Column(String, nullable=False)  # Celery task ID
    status = Column(String, nullable=False)  # 'PENDING', 'STARTED', 'SUCCESS', 'FAILURE', 'RETRY'
    progress_percentage = Column(Integer, default=0)
    current_step = Column(String)
    error_message = Column(Text)
    task_metadata = Column(Text)  # JSON string for stage-specific data (renamed from metadata)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    course = relationship("Course", back_populates="course_tasks")

class RepositoryFile(Base):
    __tablename__ = "repository_files"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String, ForeignKey('courses.course_id', ondelete='CASCADE'), nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # 'folder' or 'file'
    is_documentation = Column(Boolean, default=False)
    is_overview_candidate = Column(Boolean, default=False)
    file_size = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    course = relationship("Course", back_populates="repository_files")

class Stage1Selection(Base):
    __tablename__ = "stage1_selections"
    
    course_id = Column(String, ForeignKey('courses.course_id', ondelete='CASCADE'), primary_key=True)
    selected_folders = Column(Text, nullable=False)  # JSON array of folder paths
    overview_document = Column(String)  # selected overview doc path
    selected_at = Column(DateTime, default=datetime.utcnow)

class Stage2Input(Base):
    __tablename__ = "stage2_inputs"
    
    course_id = Column(String, ForeignKey('courses.course_id', ondelete='CASCADE'), primary_key=True)
    complexity_level = Column(String, nullable=False)  # 'beginner', 'intermediate', 'advanced'
    additional_info = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class AnalyzedDocument(Base):
    __tablename__ = "analyzed_documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String, ForeignKey('courses.course_id', ondelete='CASCADE'), nullable=False)
    file_path = Column(String, nullable=False)
    title = Column(String)
    doc_type = Column(String)  # 'guide', 'api', 'reference', etc.
    complexity_level = Column(String)
    key_concepts = Column(Text)  # JSON array of concepts
    learning_objectives = Column(Text)  # JSON array of objectives
    summary = Column(Text)
    prerequisites = Column(Text)  # JSON array of prerequisites
    related_topics = Column(Text)  # JSON array of related topics
    headings = Column(Text)  # JSON array of headings
    code_languages = Column(Text)  # JSON array of programming languages
    frontmatter = Column(Text)  # JSON object of frontmatter data
    doc_metadata = Column(Text)  # JSON object of metadata
    word_count = Column(Integer)
    analyzed_at = Column(DateTime, default=datetime.utcnow)

class Stage3Input(Base):
    __tablename__ = "stage3_inputs"
    
    course_id = Column(String, ForeignKey('courses.course_id', ondelete='CASCADE'), primary_key=True)
    complexity_level = Column(String, default="intermediate")
    additional_instructions = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Pathway(Base):
    __tablename__ = "pathways"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String, ForeignKey('courses.course_id', ondelete='CASCADE'), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    complexity_level = Column(String)
    estimated_duration = Column(String)
    prerequisites = Column(Text)  # JSON array of prerequisites
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    modules = relationship("Module", back_populates="pathway", cascade="all, delete-orphan")

class Module(Base):
    __tablename__ = "modules"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pathway_id = Column(String, ForeignKey('pathways.id', ondelete='CASCADE'), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    sequence_order = Column(Integer, nullable=False)
    learning_objectives = Column(Text)  # JSON array of objectives
    estimated_time = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    pathway = relationship("Pathway", back_populates="modules")

class Stage3Selection(Base):
    __tablename__ = "stage3_selections"
    
    course_id = Column(String, ForeignKey('courses.course_id', ondelete='CASCADE'), primary_key=True)
    selected_pathway_id = Column(String, ForeignKey('pathways.id'))
    selected_at = Column(DateTime, default=datetime.utcnow)

class GeneratedCourse(Base):
    __tablename__ = "generated_courses"
    
    course_id = Column(String, ForeignKey('courses.course_id', ondelete='CASCADE'), primary_key=True)
    pathway_id = Column(String, ForeignKey('pathways.id'))
    export_path = Column(String)
    status = Column(String, default='generating')  # 'generating', 'completed', 'failed'
    generated_at = Column(DateTime, default=datetime.utcnow)

class ModuleContent(Base):
    __tablename__ = "module_content"
    
    module_id = Column(String, ForeignKey('modules.id', ondelete='CASCADE'), primary_key=True)
    introduction = Column(Text)
    main_content = Column(Text)
    conclusion = Column(Text)
    assessment = Column(Text)
    summary = Column(Text)
    generated_at = Column(DateTime, default=datetime.utcnow)

# Database functions
def init_database():
    """Initialize the database by creating all tables"""
    try:
        # Ensure the data directory exists
        os.makedirs(settings.ROOT_DATA_DIR, exist_ok=True)
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print(f"✅ Database initialized at {DATABASE_URL}")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return False

def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session() -> Session:
    """Get database session (for direct use, not dependency injection)"""
    return SessionLocal()

# Database helper functions for tasks
def update_task_progress(course_id: str, stage: str, task_id: str, status: str, 
                        progress: int, current_step: str = None, error_msg: str = None):
    """Update task progress in database"""
    db = get_db_session()
    try:
        # Check if task record exists
        task = db.query(CourseTask).filter(
            CourseTask.course_id == course_id,
            CourseTask.stage == stage
        ).first()
        
        if task:
            # Update existing task
            task.task_id = task_id
            task.status = status
            task.progress_percentage = progress
            task.current_step = current_step
            task.error_message = error_msg
            if status == 'SUCCESS':
                task.completed_at = datetime.utcnow()
        else:
            # Create new task record
            task = CourseTask(
                course_id=course_id,
                stage=stage,
                task_id=task_id,
                status=status,
                progress_percentage=progress,
                current_step=current_step,
                error_message=error_msg
            )
            db.add(task)
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to update task progress: {e}")
    finally:
        db.close()

def update_course_status(course_id: str, status: str):
    """Update course status"""
    db = get_db_session()
    try:
        course = db.query(Course).filter(Course.course_id == course_id).first()
        if course:
            course.status = status
            course.updated_at = datetime.utcnow()
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to update course status: {e}")
    finally:
        db.close()

def save_repository_files(course_id: str, files_data: list):
    """Save repository files to database"""
    db = get_db_session()
    try:
        # Clear existing files for this course
        db.query(RepositoryFile).filter(RepositoryFile.course_id == course_id).delete()
        
        # Add new files
        for file_data in files_data:
            repo_file = RepositoryFile(
                course_id=course_id,
                file_path=file_data.get('path', ''),
                file_type=file_data.get('type', 'file'),
                is_documentation=file_data.get('is_documentation', False),
                is_overview_candidate=file_data.get('is_overview_candidate', False),
                file_size=file_data.get('size', 0)
            )
            db.add(repo_file)
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to save repository files: {e}")
        raise
    finally:
        db.close() 