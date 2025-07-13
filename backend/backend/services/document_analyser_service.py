"""
DocumentAnalyserService - Service 2 of 4

Responsibility: AI-powered document analysis
- Triggers Celery task for document analysis
- Manages Stage 2 user inputs and results
- Database-driven, no pickle files
"""

import logging
import time
from typing import List, Dict, Any, Optional

from backend.shared.database import (
    get_db_session, AnalyzedDocument, Stage2Input
)
from backend.services.base_service import BaseService

logger = logging.getLogger(__name__)


class DocumentAnalyserService(BaseService):
    """Lean service for document analysis"""
    
    def start_document_analysis(self, course_id: str, user_id: str, 
                              complexity_level: str, additional_info: str = "") -> str:
        """Start document analysis (Stage 2) - Triggers Celery task"""
        try:
            # Save user input to database
            db = get_db_session()
            try:
                stage2_input = Stage2Input(
                    course_id=course_id,
                    complexity_level=complexity_level,
                    additional_info=additional_info
                )
                db.merge(stage2_input)
                db.commit()
                
                # Trigger Celery task using base class method
                task_id = self.trigger_celery_task(
                    'backend.worker.tasks.stage2_document_analysis',
                    [user_id, course_id, {
                        "complexity_level": complexity_level,
                        "additional_info": additional_info
                    }]
                )
                
                logger.info(f"Started document analysis for course {course_id}, task {task_id}")
                return task_id
                
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to start document analysis: {e}")
            raise
    
    def get_analyzed_documents(self, course_id: str) -> Dict[str, Any]:
        """Get analyzed documents from database"""
        db = get_db_session()
        try:
            # Get analyzed documents
            docs = db.query(AnalyzedDocument).filter(AnalyzedDocument.course_id == course_id).all()
            
            analyzed_documents = []
            for doc in docs:
                import json
                from pathlib import Path
                
                # Extract filename from file_path
                filename = Path(doc.file_path).name if doc.file_path else "unknown.md"
                
                # Create a content preview (first 200 characters of summary)
                content_preview = (doc.summary[:200] + "...") if doc.summary and len(doc.summary) > 200 else (doc.summary or "No summary available")
                
                # Build metadata object with all the analysis data
                metadata = {
                    "title": doc.title,
                    "doc_type": doc.doc_type,
                    "complexity_level": doc.complexity_level,
                    "key_concepts": json.loads(doc.key_concepts) if doc.key_concepts else [],
                    "learning_objectives": json.loads(doc.learning_objectives) if doc.learning_objectives else [],
                    "summary": doc.summary,
                    "prerequisites": json.loads(doc.prerequisites) if doc.prerequisites else [],
                    "related_topics": json.loads(doc.related_topics) if doc.related_topics else [],
                    "headings": json.loads(doc.headings) if doc.headings else [],
                    "code_languages": json.loads(doc.code_languages) if doc.code_languages else [],
                    "frontmatter": json.loads(doc.frontmatter) if doc.frontmatter else {},
                    "doc_metadata": json.loads(doc.doc_metadata) if doc.doc_metadata else {},
                    "word_count": doc.word_count,
                    "analyzed_at": doc.analyzed_at.isoformat() if doc.analyzed_at else None
                }
                
                # Format according to DocumentSummary model
                analyzed_documents.append({
                    "id": doc.id,
                    "filename": filename,
                    "path": doc.file_path,
                    "content": content_preview,
                    "metadata": metadata
                })
            
            return {
                "analyzed_documents": analyzed_documents,
                "total_documents": len(analyzed_documents),
                "analysis_complete": len(analyzed_documents) > 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get analyzed documents: {e}")
            return {"error": str(e)}
        finally:
            db.close()
    
    def get_stage2_input(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Get Stage 2 user input from database"""
        db = get_db_session()
        try:
            input_data = db.query(Stage2Input).filter(Stage2Input.course_id == course_id).first()
            if not input_data:
                return None
            
            return {
                "complexity_level": input_data.complexity_level,
                "additional_info": input_data.additional_info,
                "created_at": input_data.created_at.isoformat() if input_data.created_at else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get Stage 2 input: {e}")
            return None
        finally:
            db.close()
    
    def get_task_status(self, course_id: str) -> Dict[str, Any]:
        """Get task status from database"""
        return super().get_task_status(course_id, 'stage2')
    
    def update_document_metadata(self, course_id: str, document_id: str, metadata_updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update document metadata in database with retry mechanism for race condition"""
        max_retries = 3
        retry_delay = 0.5  # 500ms between retries
        
        for attempt in range(max_retries):
            try:
                db = get_db_session()
                try:
                    # Find the document
                    doc = db.query(AnalyzedDocument).filter(
                        AnalyzedDocument.course_id == course_id,
                        AnalyzedDocument.id == document_id
                    ).first()
                    
                    if not doc:
                        if attempt < max_retries - 1:
                            logger.warning(f"Document {document_id} not found for course {course_id}, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                            time.sleep(retry_delay)
                            continue
                        else:
                            logger.error(f"Document {document_id} not found for course {course_id} after {max_retries} attempts")
                            return {"error": f"Document {document_id} not found for course {course_id}"}
                    
                    # Update metadata fields
                    import json
                    
                    if 'doc_type' in metadata_updates:
                        doc.doc_type = metadata_updates['doc_type']
                    
                    if 'semantic_summary' in metadata_updates:
                        doc.summary = metadata_updates['semantic_summary']
                    
                    if 'key_concepts' in metadata_updates:
                        doc.key_concepts = json.dumps(metadata_updates['key_concepts'])
                    
                    if 'learning_objectives' in metadata_updates:
                        doc.learning_objectives = json.dumps(metadata_updates['learning_objectives'])
                    
                    # Update the timestamp
                    from datetime import datetime, timezone
                    doc.updated_at = datetime.now(timezone.utc)
                    
                    db.commit()
                    
                    logger.info(f"Successfully updated document metadata for document {document_id} in course {course_id}")
                    return {"message": "Document metadata updated successfully"}
                    
                except Exception as e:
                    db.rollback()
                    raise e
                finally:
                    db.close()
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Failed to update document metadata (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"Failed to update document metadata after {max_retries} attempts: {e}")
                    return {"error": str(e)}
        
        # Should not reach here, but just in case
        return {"error": "Maximum retries exceeded"} 