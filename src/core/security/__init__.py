"""
Security utilities for the QA-FRAMEWORK.

Includes SSRF protection (URL allowlist validation) per OWASP A01.
"""

from src.core.security.url_validator import (
    DEFAULT_ALLOWED_DOMAINS,
    URLValidationError,
    is_allowed_url,
    validate_url,
)

__all__ = [
    "DEFAULT_ALLOWED_DOMAINS",
    "URLValidationError",
    "is_allowed_url",
    "validate_url",
]
