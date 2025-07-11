import json
import re
import frontmatter
from typing import Dict, List, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# Helper Functions
# =============================================================================

def extract_basic_metadata(content: str, filepath: Path) -> Dict[str, Any]:
    """Extract basic metadata - similar to existing ContentExtractor"""
    try:
        post = frontmatter.loads(content)
        frontmatter_data = post.metadata
        clean_content = post.content
    except:
        frontmatter_data = {}
        clean_content = content
    
    title = extract_title(clean_content, frontmatter_data, filepath.name)
    headings = extract_headings(clean_content)
    code_blocks = extract_code_blocks(clean_content)
    
    # Get primary language
    code_languages = list(set(block['language'] for block in code_blocks 
                            if block['language'] not in ['text', 'txt', '']))
    
    return {
        'title': title,
        'headings': headings,
        'code_languages': code_languages,
        'frontmatter': frontmatter_data,
        'clean_content': clean_content
    }

def extract_title(content: str, frontmatter_data: dict, filename: str) -> str:
    """Extract document title"""
    if 'title' in frontmatter_data:
        return frontmatter_data['title'].strip()
    
    h1_match = re.search(r'^# (.+)$', content, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()
    
    return filename.replace('.md', '').replace('.mdx', '').replace('_', ' ').replace('-', ' ').title().strip()

def extract_headings(content: str) -> List[str]:
    """Extract all headings from content"""
    headings = []
    for match in re.finditer(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE):
        hashes = match.group(1)
        text = match.group(2).strip()
        headings.append(f"{hashes} {text}")
    return headings

def extract_code_blocks(content: str) -> List[Dict[str, str]]:
    """Extract code blocks with language information"""
    code_blocks = []
    pattern = r'```(\w+)?\n(.*?)\n```'
    for match in re.finditer(pattern, content, re.DOTALL):
        language = match.group(1) or 'text'
        code_content = match.group(2).strip()
        code_blocks.append({
            'language': language,
            'content': code_content
        })
    return code_blocks

def safe_json_parse(json_str: str, fallback: list = None) -> list:
    """Safely parse JSON string with fallback"""
    if fallback is None:
        fallback = []
    try:
        result = json.loads(json_str)
        return result if isinstance(result, list) else fallback
    except:
        # Try to parse as comma-separated string
        if isinstance(json_str, str) and json_str.strip():
            return [item.strip() for item in json_str.split(',') if item.strip()]
        return fallback

def get_n_words(text: str, n: int) -> str:
    """Get the first n words from a text"""
    return ' '.join(text.split()[:n])

def prepare_source_documents_content(learning_module, document_analyses, max_words: int) -> str:
    """Prepare source documents content for module content generation"""
    
    source_content = []
    doc_lookup = {doc.file_path: doc for doc in document_analyses}
    
    for doc_path in learning_module.documents:
        if doc_path in doc_lookup:
            doc = doc_lookup[doc_path]
            try:
                with open(doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Truncate content if too long
                content_excerpt = get_n_words(content, max_words // len(learning_module.documents))
                
                doc_content = f"""## {doc.title}
{content_excerpt}
"""
                source_content.append(doc_content)
            except Exception as e:
                logger.warning(f"Could not read {doc_path}: {e}")
                continue
    
    return "\n".join(source_content) 