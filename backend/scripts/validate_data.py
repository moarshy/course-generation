#!/usr/bin/env python3
"""
Data Validation and Cleanup Script
Validates and fixes data integrity issues in the course generation database
"""

import sys
import os
import sqlite3
import json
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def validate_analyzed_documents(cursor):
    """Validate and fix analyzed_documents table"""
    print("🔍 Validating analyzed_documents table...")
    
    issues_fixed = 0
    
    # Check for NULL or invalid doc_type
    cursor.execute("""
        SELECT id, file_path, doc_type FROM analyzed_documents 
        WHERE doc_type IS NULL OR doc_type = '' OR doc_type = 'None'
    """)
    invalid_doc_types = cursor.fetchall()
    
    if invalid_doc_types:
        print(f"  ⚠️  Found {len(invalid_doc_types)} documents with invalid doc_type")
        cursor.execute("""
            UPDATE analyzed_documents 
            SET doc_type = 'guide' 
            WHERE doc_type IS NULL OR doc_type = '' OR doc_type = 'None'
        """)
        issues_fixed += len(invalid_doc_types)
        print(f"  ✅ Fixed doc_type for {len(invalid_doc_types)} documents")
    
    # Check for NULL or invalid complexity_level
    cursor.execute("""
        SELECT id, file_path, complexity_level FROM analyzed_documents 
        WHERE complexity_level IS NULL OR complexity_level = '' OR complexity_level = 'None'
    """)
    invalid_complexity = cursor.fetchall()
    
    if invalid_complexity:
        print(f"  ⚠️  Found {len(invalid_complexity)} documents with invalid complexity_level")
        cursor.execute("""
            UPDATE analyzed_documents 
            SET complexity_level = 'intermediate' 
            WHERE complexity_level IS NULL OR complexity_level = '' OR complexity_level = 'None'
        """)
        issues_fixed += len(invalid_complexity)
        print(f"  ✅ Fixed complexity_level for {len(invalid_complexity)} documents")
    
    # Check for NULL or invalid titles
    cursor.execute("""
        SELECT id, file_path, title FROM analyzed_documents 
        WHERE title IS NULL OR title = '' OR title = 'None'
    """)
    invalid_titles = cursor.fetchall()
    
    if invalid_titles:
        print(f"  ⚠️  Found {len(invalid_titles)} documents with invalid title")
        for doc_id, file_path, title in invalid_titles:
            # Extract filename as fallback title
            filename = Path(file_path).stem if file_path else 'Untitled Document'
            cursor.execute("""
                UPDATE analyzed_documents 
                SET title = ? 
                WHERE id = ?
            """, (filename, doc_id))
        issues_fixed += len(invalid_titles)
        print(f"  ✅ Fixed titles for {len(invalid_titles)} documents")
    
    # Check for malformed JSON fields
    json_fields = ['key_concepts', 'learning_objectives', 'prerequisites', 'related_topics', 'headings', 'code_languages']
    
    for field in json_fields:
        cursor.execute(f"SELECT id, file_path, {field} FROM analyzed_documents WHERE {field} IS NOT NULL")
        rows = cursor.fetchall()
        
        for doc_id, file_path, json_data in rows:
            if json_data:
                try:
                    json.loads(json_data)
                except json.JSONDecodeError:
                    print(f"  ⚠️  Invalid JSON in {field} for document {file_path}")
                    cursor.execute(f"""
                        UPDATE analyzed_documents 
                        SET {field} = '[]' 
                        WHERE id = ?
                    """, (doc_id,))
                    issues_fixed += 1
                    print(f"  ✅ Fixed JSON in {field} for document {file_path}")
    
    return issues_fixed

def validate_courses(cursor):
    """Validate courses table"""
    print("🔍 Validating courses table...")
    
    issues_fixed = 0
    
    # Check for courses with invalid status
    valid_statuses = [
        'draft', 'stage1_running', 'stage1_complete', 'stage1_failed',
        'stage2_running', 'stage2_complete', 'stage2_failed',
        'stage3_running', 'stage3_complete', 'stage3_failed',
        'stage4_running', 'stage4_complete', 'stage4_failed',
        'generating', 'active', 'completed', 'archived', 'failed'
    ]
    
    cursor.execute("SELECT course_id, status FROM courses WHERE status IS NULL OR status = ''")
    invalid_status = cursor.fetchall()
    
    if invalid_status:
        print(f"  ⚠️  Found {len(invalid_status)} courses with invalid status")
        cursor.execute("UPDATE courses SET status = 'draft' WHERE status IS NULL OR status = ''")
        issues_fixed += len(invalid_status)
        print(f"  ✅ Fixed status for {len(invalid_status)} courses")
    
    return issues_fixed

def generate_report(cursor):
    """Generate a data quality report"""
    print("\n📊 Data Quality Report")
    print("=" * 50)
    
    # Count total records
    cursor.execute("SELECT COUNT(*) FROM courses")
    total_courses = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analyzed_documents")
    total_documents = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM pathways")
    total_pathways = cursor.fetchone()[0]
    
    print(f"📈 Total Records:")
    print(f"  - Courses: {total_courses}")
    print(f"  - Analyzed Documents: {total_documents}")
    print(f"  - Learning Pathways: {total_pathways}")
    
    # Check for any remaining issues
    cursor.execute("""
        SELECT COUNT(*) FROM analyzed_documents 
        WHERE doc_type IS NULL OR doc_type = '' OR doc_type = 'None'
        OR complexity_level IS NULL OR complexity_level = '' OR complexity_level = 'None'
        OR title IS NULL OR title = '' OR title = 'None'
    """)
    remaining_issues = cursor.fetchone()[0]
    
    if remaining_issues == 0:
        print(f"✅ Data Quality: GOOD (no issues found)")
    else:
        print(f"⚠️  Data Quality: {remaining_issues} issues found")
    
    # Show distribution of doc_types
    cursor.execute("SELECT doc_type, COUNT(*) FROM analyzed_documents GROUP BY doc_type")
    doc_type_dist = cursor.fetchall()
    
    if doc_type_dist:
        print(f"\n📋 Document Type Distribution:")
        for doc_type, count in doc_type_dist:
            print(f"  - {doc_type}: {count}")
    
    # Show complexity level distribution
    cursor.execute("SELECT complexity_level, COUNT(*) FROM analyzed_documents GROUP BY complexity_level")
    complexity_dist = cursor.fetchall()
    
    if complexity_dist:
        print(f"\n🎯 Complexity Level Distribution:")
        for level, count in complexity_dist:
            print(f"  - {level}: {count}")

def main():
    """Main validation function"""
    print("🚀 Starting Data Validation and Cleanup")
    print(f"⏰ Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Connect to database
    db_path = Path(__file__).parent.parent.parent / "data" / "course_creator.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        total_issues_fixed = 0
        
        # Validate different tables
        total_issues_fixed += validate_analyzed_documents(cursor)
        total_issues_fixed += validate_courses(cursor)
        
        # Commit changes
        if total_issues_fixed > 0:
            conn.commit()
            print(f"\n✅ Successfully fixed {total_issues_fixed} data integrity issues")
        else:
            print(f"\n✅ No data integrity issues found!")
        
        # Generate report
        generate_report(cursor)
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during validation: {e}")
        sys.exit(1)
    
    finally:
        conn.close()
    
    print("\n🎉 Data validation completed successfully!")

if __name__ == "__main__":
    main() 