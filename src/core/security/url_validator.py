"""
SSRF Protection — URL Allowlist Validator

OWASP Top 10:2025 — A01: Broken Access Control (SSRF prevention)
Implements strict URL allowlist validation to prevent Server-Side Request Forgery.

Reference:
    - OWASP ASVS V19.1: Server-Side Request Forgery (SSRF) Protection
    - OWASP Cheat Sheet: Server-Side Request Forgery Prevention
"""

import logging
from urllib.parse import urlparse

from src.core.security.domain_normalizer import (
    DomainNormalizationError,
    is_subdomain_of,
    normalize_allowlist,
    url_hostname,
)

logger = logging.getLogger(__name__)


# Default allowlist of trusted domains for production use — FAIL-CLOSED.
# Loopback/local hosts (localhost, 127.0.0.1, 0.0.0.0, [::1], *.local) are
# intentionally NOT allowed by default (SSRF, OWASP A01). For local
# development, pass an explicit ``allowed_domains`` set or override via the
# environment variable SSRF_ALLOWED_DOMAINS (comma-separated), resolved in
# src/adapters/http/httpx_client.py::_load_allowed_domains.
DEFAULT_ALLOWED_DOMAINS: set[str] = {
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
}


class URLValidationError(Exception):
    """Raised when a URL fails allowlist validation."""


def is_allowed_url(
    url: str,
    allowed_domains: set[str] | None = None,
    *,
    allow_subdomains: bool = False,
) -> bool:
    """
    Check whether the given URL is in the allowed domains set.

    Fail-closed: when ``allowed_domains`` is None, the fallback is
    DEFAULT_ALLOWED_DOMAINS, which contains public domains only — local and
    loopback hosts (localhost, 127.0.0.1, [::1], *.local, ...) are rejected
    unless they are explicitly added via ``allowed_domains`` or the
    SSRF_ALLOWED_DOMAINS environment override.

    Comparison contract (card e34711f3, M1): both sides are compared under
    the ``domain_normalizer`` contract (NFKC + lowercase + one root dot +
    IDNA/UTS46), so mixed-case, Unicode or trailing-dot allowlist entries
    match instead of being silent dead rules. IP literals, which IDNA
    rejects, keep an exact raw comparison.

    Subdomain semantics (card e34711f3, H1): a host UNDER an allowlist base
    is no longer automatically allowed — ``*.github.com`` is registrable by
    anyone (GitHub Pages), so ``evil.github.com`` must not pass via
    ``github.com``. Subdomain matching is opt-in via ``allow_subdomains``
    and only meaningful for operator-controlled bases; the builtin default
    list never grants it.

    Args:
        url: The URL to validate.
        allowed_domains: Optional set of allowed domains.
                         Falls back to DEFAULT_ALLOWED_DOMAINS if None.
        allow_subdomains: If True, also allow subdomains of allowlist entries
                         (use ONLY when the operator controls those zones).

    Returns:
        True if the URL's host is in the allowlist, False otherwise.
    """
    if allowed_domains is None:
        allowed_domains = DEFAULT_ALLOWED_DOMAINS
        # The builtin list holds third-party domains whose subdomains are
        # registrable by anyone: it never grants subdomain trust, flag or not.
        allow_subdomains = False

    try:
        raw_hostname = urlparse(url).hostname
    except Exception:
        logger.warning("URL validation failed — cannot parse: %s", url)
        return False

    if not raw_hostname:
        logger.warning("URL validation failed — no hostname in: %s", url)
        return False

    # Track 1 — exact literal comparison (urlparse already lowercases the
    # hostname). The only track that can match IP literals (127.0.0.1, ::1),
    # which the IDNA contract intentionally rejects.
    raw_allowlist = {
        str(entry).strip().lower() for entry in allowed_domains if isinstance(entry, str)
    }
    if raw_hostname in raw_allowlist:
        return True

    # Track 2 — domain_normalizer contract on both sides: URL hostname via
    # url_hostname, allowlist via normalize_allowlist (invalid entries are
    # skipped, never fatal).
    try:
        hostname = url_hostname(url)
    except DomainNormalizationError as exc:
        logger.warning("URL validation failed — invalid hostname in %s: %s", url, exc)
        return False

    normalized_allowlist = normalize_allowlist(allowed_domains)
    if hostname in normalized_allowlist:
        return True

    # Opt-in subdomain semantics, operator-controlled bases only. Label
    # boundaries are enforced: evilstripe.com is NOT under stripe.com.
    if allow_subdomains and any(is_subdomain_of(hostname, base) for base in normalized_allowlist):
        return True

    logger.warning("SSRF block — domain not in allowlist: %s (hostname: %s)", url, hostname)
    return False


def validate_url(
    url: str,
    allowed_domains: set[str] | None = None,
    raise_on_error: bool = True,
    *,
    allow_subdomains: bool = False,
) -> bool:
    """
    Validate a URL against the allowlist.

    Args:
        url: The URL to validate.
        allowed_domains: Optional set of allowed domains.
        raise_on_error: If True, raise URLValidationError on failure.
        allow_subdomains: If True, allow subdomains of allowlist entries
                         (operator-controlled bases only).

    Returns:
        True if allowed, False if blocked (only when raise_on_error is False).

    Raises:
        URLValidationError: If the URL is not in the allowlist and raise_on_error is True.
    """
    if is_allowed_url(url, allowed_domains, allow_subdomains=allow_subdomains):
        return True

    if raise_on_error:
        raise URLValidationError(f"URL not in allowlist: {url}")

    return False
