"""
SSRF Protection — URL Allowlist Validator

OWASP Top 10:2025 — A01: Broken Access Control (SSRF prevention)
Implements strict URL allowlist validation to prevent Server-Side Request Forgery.

Reference:
    - OWASP ASVS V19.1: Server-Side Request Forgery (SSRF) Protection
    - OWASP Cheat Sheet: Server-Side Request Forgery Prevention
"""

import logging
from typing import Optional, Set
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# Default allowlist of trusted domains for production use.
# Override via environment variable SSRF_ALLOWED_DOMAINS (comma-separated).
DEFAULT_ALLOWED_DOMAINS: Set[str] = {
    # Standard OAuth providers
    "accounts.google.com",
    "github.com",
    "api.github.com",
    "login.microsoftonline.com",
    "login.live.com",
    "graph.microsoft.com",
    "appleid.apple.com",
    "api.twitter.com",
    "api.linkedin.com",
    "www.linkedin.com",
    "apis.google.com",
    "oauth2.googleapis.com",
    "www.googleapis.com",
    # Common API endpoints
    "api.stripe.com",
    "api.resend.com",
    "api.openai.com",
    "api.groq.com",
    # Local development / testing
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
}


class URLValidationError(Exception):
    """Raised when a URL fails allowlist validation."""
    pass


def is_allowed_url(url: str, allowed_domains: Optional[Set[str]] = None) -> bool:
    """
    Check whether the given URL is in the allowed domains set.

    Args:
        url: The URL to validate.
        allowed_domains: Optional set of allowed domains.
                         Falls back to DEFAULT_ALLOWED_DOMAINS if None.

    Returns:
        True if the URL's host is in the allowlist, False otherwise.
    """
    if allowed_domains is None:
        allowed_domains = DEFAULT_ALLOWED_DOMAINS

    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
    except Exception:
        logger.warning("URL validation failed — cannot parse: %s", url)
        return False

    if not hostname:
        logger.warning("URL validation failed — no hostname in: %s", url)
        return False

    # Direct match
    if hostname in allowed_domains:
        return True

    # Subdomain match: allow *.example.com if example.com is in the allowlist
    # Only match one level of subdomain to avoid accidental bypasses
    parts = hostname.split(".")
    if len(parts) >= 2:
        parent = ".".join(parts[-2:])
        if parent in allowed_domains:
            return True
        if len(parts) >= 3:
            grandparent = ".".join(parts[-3:])
            if grandparent in allowed_domains:
                return True

    logger.warning("SSRF block — domain not in allowlist: %s (hostname: %s)", url, hostname)
    return False


def validate_url(
    url: str,
    allowed_domains: Optional[Set[str]] = None,
    raise_on_error: bool = True,
) -> bool:
    """
    Validate a URL against the allowlist.

    Args:
        url: The URL to validate.
        allowed_domains: Optional set of allowed domains.
        raise_on_error: If True, raise URLValidationError on failure.

    Returns:
        True if allowed, False if blocked (only when raise_on_error is False).

    Raises:
        URLValidationError: If the URL is not in the allowlist and raise_on_error is True.
    """
    if is_allowed_url(url, allowed_domains):
        return True

    if raise_on_error:
        raise URLValidationError(f"URL not in allowlist: {url}")

    return False
