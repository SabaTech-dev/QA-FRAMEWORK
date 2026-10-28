"""Domain normalization for security comparisons — single source of truth.

Card 2eab7e70 (security audit: domain comparison / IDNA spoofing hardening).

Problem this module solves: allowlist and identity comparisons in this
codebase compared domain strings raw (`hostname in allowed_domains`) or with
plain ``str.lower()`` only. Raw comparisons are sensitive to case, Unicode
compatibility forms (fullwidth chars), trailing-dot FQDN forms, and do not
perform IDNA encoding, so the same logical domain can compare unequal
depending on the byte-level form it arrives in. Conversely, naive
"normalize by lowercasing" merges Unicode lookalikes with their ASCII
targets and is the wrong direction for security comparisons.

Contract (fail-closed):
    - Unicode format characters (category Cf: zero-width space/joiner,
      soft hyphen, BOM, bidi overrides such as U+202E) are REJECTED, not
      stripped — silently stripping them would allow a lookalike hostname
      whose real DNS name (punycode form) differs from the allowlisted one.
    - The remaining string is NFKC-normalized, lowercased, stripped of
      surrounding whitespace and of ONE trailing root dot (``example.com.``
      is the FQDN form of ``example.com``; a doubled dot stays invalid).
    - The result is IDNA-encoded with UTS #46 mapping, non-transitional
      (``transitional=False``), so ``strasse.de`` != ``straße.de`` — the
      IDNA2008/UTS46 behaviour. Transitional mapping (ß→ss) would merge
      distinct registered domains and is not used.
    - Unparseable or invalid input raises :class:`DomainNormalizationError`
      (a ValueError), except :func:`domains_equal` / :func:`is_subdomain_of`
      which return ``False`` on invalid input (allowlist semantics: when in
      doubt, do not match).

Dependency: the ``idna`` package (already a hard transitive dependency of
both pinned HTTP clients: ``httpx`` and ``requests``).

Usage:
    >>> normalize_domain("Apple.COM.")
    'apple.com'
    >>> domains_equal("аpple.com", "apple.com")  # Cyrillic а, U+0430
    False
    >>> is_subdomain_of("api.github.com", "github.com")
    True
    >>> is_subdomain_of("evilstripe.com", "stripe.com")
    False
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

import idna

__all__ = [
    "DomainNormalizationError",
    "normalize_domain",
    "normalize_allowlist",
    "domains_equal",
    "is_subdomain_of",
    "url_hostname",
]


class DomainNormalizationError(ValueError):
    """Raised when a value cannot be normalized into a comparable domain."""


def _reject_format_characters(value: str) -> None:
    """Reject Unicode format/control characters used in spoofing (fail-closed)."""
    for ch in value:
        if unicodedata.category(ch) == "Cf":
            raise DomainNormalizationError(
                f"domain contains Unicode format character U+{ord(ch):04X} — "
                "possible homograph/RTLO spoofing; reject instead of stripping"
            )


def normalize_domain(value: Any) -> str:
    """Normalize a domain name to its lowercase ASCII (punycode) form.

    Steps: type check → reject Cf format characters → NFKC → lowercase →
    strip surrounding whitespace and one trailing root dot → IDNA encode
    (UTS #46, non-transitional).

    Args:
        value: Domain string, e.g. ``"Apple.COM."``, ``"ｅｘａｍｐｌｅ.com"``,
            ``"straße.de"``. Hostname only — no scheme, port, path or
            userinfo (use :func:`url_hostname` for URLs).

    Returns:
        Lowercase ASCII domain (punycode ``xn--`` labels where applicable),
        suitable for allowlist membership and equality comparison.

    Raises:
        DomainNormalizationError: On non-string input, empty input, format
            characters, or any value IDNA rejects (empty label, label
            > 63 octets, disallowed code points, total length > 253).
            Literal IPs and IPv6 are out of scope and will raise; handle
            them before calling this function.
    """
    if not isinstance(value, str):
        raise DomainNormalizationError(f"domain must be a string, got {type(value).__name__}")

    candidate = value.strip()
    if not candidate:
        raise DomainNormalizationError("domain is empty")

    _reject_format_characters(candidate)

    # NFKC folds fullwidth/halfwidth compatibility forms; UTS #46 mapping
    # inside idna.encode(uts46=True) re-applies it per label — doing it here
    # as well keeps behaviour explicit and catches pathological inputs early.
    candidate = unicodedata.normalize("NFKC", candidate)
    candidate = candidate.lower()

    if candidate.endswith("."):
        candidate = candidate[:-1]
        if candidate.endswith("."):
            # The single root dot is the only legal FQDN trailing form and is
            # consumed above. Note the idna package itself tolerates a
            # trailing dot (strict=False re-appends it), so without this
            # explicit check "example.com.." would survive as "example.com."
            # instead of being rejected (empty label at the root).
            raise DomainNormalizationError(
                f"invalid domain {value!r}: multiple trailing dots"
            )

    if not candidate:
        raise DomainNormalizationError("domain is empty after normalization")

    try:
        return idna.encode(candidate, uts46=True, transitional=False).decode("ascii")
    except idna.IDNAError as exc:
        raise DomainNormalizationError(f"invalid domain {value!r}: {exc}") from exc
    except UnicodeError as exc:  # defensive: punycode overflow etc.
        raise DomainNormalizationError(f"invalid domain {value!r}: {exc}") from exc


def normalize_allowlist(domains: Iterable[str]) -> set[str]:
    """Normalize an allowlist; entries that fail normalization are skipped.

    Designed for ``SSRF_ALLOWED_DOMAINS``-style configuration where a
    mixed-case or Unicode entry currently never matches (silent dead rule).
    Invalid entries are skipped rather than raising so one bad config value
    cannot DoS startup; log/monitor at the call site if needed.
    """
    result: set[str] = set()
    for entry in domains:
        try:
            result.add(normalize_domain(entry))
        except DomainNormalizationError:
            continue
    return result


def domains_equal(a: Any, b: Any) -> bool:
    """Compare two domains under the normalization contract.

    Returns ``False`` (never raises) when either side is invalid — the
    fail-closed choice for allowlist-style checks.
    """
    try:
        return normalize_domain(a) == normalize_domain(b)
    except DomainNormalizationError:
        return False


def is_subdomain_of(host: Any, base: Any) -> bool:
    """Label-boundary-safe suffix test: ``host`` is ``base`` or a subdomain.

    Both sides are normalized first. Label boundaries are respected:
    ``evilstripe.com`` is NOT a subdomain of ``stripe.com``.

    Security note for callers building allowlists: a subdomain match means
    any registrable host under ``base`` matches (e.g. attacker-controlled
    ``user.github.com`` under ``github.com``). Only use subdomain semantics
    when you control ``base``'s zone or intend to trust its tenants.
    """
    try:
        h = normalize_domain(host)
        b = normalize_domain(base)
    except DomainNormalizationError:
        return False
    return h == b or h.endswith("." + b)


def url_hostname(url: Any) -> str:
    """Extract the hostname of a URL and normalize it for comparison.

    Args:
        url: Absolute URL, e.g. ``"https://API.Example.COM.:8443/p?q=1"``.
            Userinfo and port are ignored; the host decides.

    Returns:
        Normalized ASCII hostname (see :func:`normalize_domain`).

    Raises:
        DomainNormalizationError: If the URL cannot be parsed or has no
            hostname.
    """
    if not isinstance(url, str):
        raise DomainNormalizationError(f"url must be a string, got {type(url).__name__}")
    try:
        hostname = urlparse(url).hostname
    except ValueError as exc:
        raise DomainNormalizationError(f"unparsable URL {url!r}: {exc}") from exc
    if not hostname:
        raise DomainNormalizationError(f"URL without hostname: {url!r}")
    return normalize_domain(hostname)
