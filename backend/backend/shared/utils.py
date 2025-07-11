"""
Shared utilities for Course Creator backend services.

Contains essential helper functions for the 4-service architecture.
"""

from typing import Any


def get_n_words(text: str, n: int) -> str:
    """Get the first n words from a text"""
    return ' '.join(text.split()[:n])


def parse_json_safely(json_str: str, default: Any = None) -> Any:
    """Parse JSON string safely, returning default on error."""
    try:
        import json
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default