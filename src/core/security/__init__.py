"""
Security utilities for the QA-FRAMEWORK.

Includes SSRF protection (URL allowlist validation) per OWASP A01.
"""

from src.core.security.url_validator import (
    validate_url,
    is_allowed_url,
    URLValidationError,
    DEFAULT_ALLOWED_DOMAINS,
)

__all__ = [
    "validate_url",
    "is_allowed_url",
    "URLValidationError",
    "DEFAULT_ALLOWED_DOMAINS",
]
