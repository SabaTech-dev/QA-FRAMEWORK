"""
SARIF Message Sanitizer

Filters Unicode control characters from SARIF message text
to prevent injection and ensure valid JSON output.

Security:
- Filters control characters \x00-\x1f except \n\r\t
- Prevents malformed JSON in SARIF output
- Protects against unicode-based injection attacks
"""

import re
from typing import Optional

# Pattern to match control characters \x00-\x1f except \n\r\t
_CONTROL_CHAR_PATTERN = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


def sanitize_message_text(text: Optional[str]) -> Optional[str]:
    """
    Sanitize SARIF message text by removing dangerous control characters.
    
    Args:
        text: Raw message text (may contain control characters)
        
    Returns:
        Sanitized text with control characters removed, or None if input is None
        
    Security:
    - Removes control chars \x00-\x1f except \n\r\t
    - json.dumps() handles remaining escaping for JSON validity
    - Prevents malformed output and unicode injection
    """
    if text is None:
        return None
        
    if not isinstance(text, str):
        text = str(text)
    
    # Remove dangerous control characters
    sanitized = _CONTROL_CHAR_PATTERN.sub('', text)
    
    return sanitized


def sanitize_dict_strings(data: dict) -> dict:
    """
    Sanitize all string values in a dictionary recursively.
    
    Useful for sanitizing SARIF result properties and artifact_data.
    
    Args:
        data: Dictionary with potentially unsanitized string values
        
    Returns:
        Dictionary with all string values sanitized
    """
    sanitized = {}
    
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_message_text(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict_strings(value)
        elif isinstance(value, list):
            sanitized[key] = _sanitize_list_strings(value)
        else:
            sanitized[key] = value
    
    return sanitized


def _sanitize_list_strings(data: list) -> list:
    """Sanitize string values in a list recursively."""
    sanitized = []
    
    for item in data:
        if isinstance(item, str):
            sanitized.append(sanitize_message_text(item))
        elif isinstance(item, dict):
            sanitized.append(sanitize_dict_strings(item))
        elif isinstance(item, list):
            sanitized.append(_sanitize_list_strings(item))
        else:
            sanitized.append(item)
    
    return sanitized