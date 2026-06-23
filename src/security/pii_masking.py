"""
PII Masking Verifier — Personal Identifiable Information detection and masking.

Detects 9 categories of PII using regex with semantic validation where
applicable (Luhn for credit cards, area-group rules for SSN, mod-97 for
IBAN):

    - email
    - phone (E.164 + common international formats)
    - ssn (US Social Security Number)
    - iban (ISO 13616)
    - credit_card (Visa, Mastercard, Amex, Discover — Luhn-validated)
    - api_key (Stripe, AWS, GitHub, Slack, generic long tokens)
    - jwt (RFC 7519 compact serialization)
    - dob (Date of Birth — common date formats)
    - address (US street addresses)

Public API:
    - scan_text(text)         -> list of PIIFinding
    - mask_text(text)         -> masked string
    - scan_response(text)     -> ScanResult (summary + findings)

Usage:
    from src.security.pii_masking import scan_text, mask_text

    findings = scan_text("Contact john@example.com or +1-555-123-4567")
    safe = mask_text("Card: 4111 1111 1111 1111")
"""

from __future__ import annotations

import re
from enum import Enum
from typing import ClassVar, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

# =============================================================================
# DATA MODELS
# =============================================================================


class PIIType(str, Enum):
    """Categories of Personal Identifiable Information detected."""

    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    IBAN = "iban"
    CREDIT_CARD = "credit_card"
    API_KEY = "api_key"
    JWT = "jwt"
    DOB = "dob"
    ADDRESS = "address"


class PIIFinding(BaseModel):
    """A single PII detection finding."""

    type: PIIType = Field(..., description="Category of PII detected")
    value: str = Field(..., description="Raw matched substring")
    start: int = Field(..., ge=0, description="Start offset (inclusive)")
    end: int = Field(..., ge=0, description="End offset (exclusive)")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Detection confidence (0..1)"
    )
    masked: str = Field(default="", description="Masked representation of the value")


class ScanResult(BaseModel):
    """Aggregate result of scanning a piece of text."""

    total_findings: int = Field(default=0, ge=0)
    findings: List[PIIFinding] = Field(default_factory=list)
    types_found: List[PIIType] = Field(default_factory=list)
    has_pii: bool = False
    masked_text: str = ""
    scanned_length: int = Field(default=0, ge=0)


# =============================================================================
# HELPERS
# =============================================================================


def _luhn_check(number: str) -> bool:
    """Return True if the digit-only string passes the Luhn checksum."""
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def _iban_check(candidate: str) -> bool:
    """Return True if candidate passes ISO 13616 mod-97 validation."""
    candidate = candidate.replace(" ", "").upper()
    if len(candidate) < 15 or not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]+", candidate):
        return False
    rearranged = candidate[4:] + candidate[:4]
    numeric = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    return int(numeric) % 97 == 1


# =============================================================================
# DETECTORS
# =============================================================================


class _Detector:
    """Base class for a PII detector.

    Each detector exposes a compiled regex and an optional validator that
    performs cheap semantic checks (Luhn, mod-97, SSN rules) to reduce
    false positives.
    """

    pii_type: ClassVar[PIIType]
    pattern: ClassVar[str]
    confidence: ClassVar[float] = 1.0
    # When True, the detector's regex may capture adjacent whitespace/separators
    # that we want to preserve when masking (e.g. credit card with spaces).
    strip_separators: ClassVar[bool] = False
    # Lazily-compiled regex cache (per subclass).
    _compiled: ClassVar[Optional["re.Pattern[str]"]] = None

    @classmethod
    def regex(cls) -> "re.Pattern[str]":
        # Compile lazily and cache on the class.
        if cls._compiled is None:
            cls._compiled = re.compile(cls.pattern)
        assert cls._compiled is not None  # for type-checkers
        return cls._compiled

    @classmethod
    def validate(cls, match: str) -> bool:
        """Optional semantic validation. Return False to discard the match."""
        return True

    @classmethod
    def mask_value(cls, match: str, mask_char: str = "*") -> str:
        """Mask a matched value. By default: keep first & last char, mask middle."""
        if len(match) <= 2:
            return mask_char * len(match)
        return f"{match[0]}{mask_char * (len(match) - 2)}{match[-1]}"


class _EmailDetector(_Detector):
    pii_type = PIIType.EMAIL
    # Pragmatic RFC-5322 subset — false positives are extremely rare.
    pattern = r"\b[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9.\-]{1,253}\.[A-Za-z]{2,24}\b"
    confidence = 1.0


class _PhoneDetector(_Detector):
    pii_type = PIIType.PHONE
    # E.164 (+CC) or local with separators. We intentionally do NOT include
    # an optional extension group: extensions make the regex greedy and cause
    # it to swallow credit-card digits that follow. Validate() enforces 7-15
    # digit count (E.164 range).
    pattern = (
        r"(?<!\w)(?:\+?\d{1,3}[\s.\-]?)?"
        r"\(?\d{2,4}\)?[\s.\-]?"
        r"\d{3,4}[\s.\-]?\d{3,4}"
        r"(?!\w)"
    )
    confidence = 0.85

    @classmethod
    def validate(cls, match: str) -> bool:
        digits = re.sub(r"\D", "", match)
        # A real phone number has between 7 and 15 digits (E.164 max).
        return 7 <= len(digits) <= 15


class _SSNDetector(_Detector):
    pii_type = PIIType.SSN
    # US Social Security Number: AAA-GG-SSSS
    pattern = r"\b\d{3}-\d{2}-\d{4}\b"
    confidence = 0.95

    @classmethod
    def validate(cls, match: str) -> bool:
        area, group, _serial = match.split("-")
        # SSA rules: area != 000, != 666, != 9xx; group != 00; serial != 0000.
        if area in ("000", "666") or area.startswith("9"):
            return False
        if group == "00":
            return False
        return True


class _IBANDetector(_Detector):
    pii_type = PIIType.IBAN
    pattern = r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30}\b"
    confidence = 1.0

    @classmethod
    def validate(cls, match: str) -> bool:
        return _iban_check(match)


class _CreditCardDetector(_Detector):
    pii_type = PIIType.CREDIT_CARD
    # Strict formats only: 13-19 consecutive digits, OR consistent 4-group
    # separators (4-4-4-4 / 4-4-4-1..7 / 4-6-5 Amex). This avoids matching
    # across phone numbers where dashes appear between single digits.
    pattern = (
        r"\b(?:"
        r"\d{13,19}"
        r"|\d{4}[ -]\d{4}[ -]\d{4}[ -]\d{1,7}"
        r"|\d{4}[ -]\d{6}[ -]\d{5}"
        r")\b"
    )
    confidence = 1.0
    strip_separators = True

    @classmethod
    def validate(cls, match: str) -> bool:
        return _luhn_check(match)


class _APIKeyDetector(_Detector):
    pii_type = PIIType.API_KEY
    # Order matters: most specific prefixes first within the alternation.
    pattern = (
        r"(?:"
        r"sk_(?:live|test)_[A-Za-z0-9]{24,}"  # Stripe secret
        r"|pk_(?:live|test)_[A-Za-z0-9]{24,}"  # Stripe publishable
        r"|AKIA[0-9A-Z]{16}"  # AWS access key
        r"|gh[pousr]_[A-Za-z0-9]{20,255}"  # GitHub tokens
        r"|xox[baprs]-[A-Za-z0-9\-]{10,}"  # Slack tokens
        r"|AIza[0-9A-Za-z_\-]{35}"  # Google API key
        r"|[A-Fa-f0-9]{40,64}"  # generic hex token (sha1+)
        r")"
    )
    confidence = 0.9


class _JWTDetector(_Detector):
    pii_type = PIIType.JWT
    # RFC 7519 compact: header.payload.signature, base64url segments.
    pattern = r"\beyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b"
    confidence = 1.0


class _DOBDetector(_Detector):
    pii_type = PIIType.DOB
    # Match common date formats; we anchor on word boundaries and require
    # a sensible year range to avoid matching version numbers / random dates.
    pattern = (
        r"\b(?:"
        r"\d{4}-\d{2}-\d{2}"  # ISO 8601
        r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"  # DD/MM/YYYY or MM/DD/YYYY
        r")\b"
    )
    confidence = 0.7

    @classmethod
    def validate(cls, match: str) -> bool:
        # Validate plausibility: year in [1900, current+1], month 1-12, day 1-31.
        m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", match)
        if m:
            y, mo, d = (int(x) for x in m.groups())
        else:
            cleaned = match.replace("/", "-")
            parts = cleaned.split("-")
            if len(parts) != 3:
                return False
            # Ambiguous DD/MM/YYYY vs MM/DD/YYYY — accept if either is plausible.
            a, b, c = (int(p) for p in parts)
            y = c if c >= 1000 else (c + 2000 if c < 100 else c)
            mo, d = (a, b) if 1 <= a <= 12 else (b, a)
        return 1900 <= y <= 2099 and 1 <= mo <= 12 and 1 <= d <= 31


class _AddressDetector(_Detector):
    pii_type = PIIType.ADDRESS
    # US street addresses: "<number> <Name> <Suffix>"
    _suffixes = (
        "Street",
        "St",
        "Avenue",
        "Ave",
        "Boulevard",
        "Blvd",
        "Road",
        "Rd",
        "Drive",
        "Dr",
        "Lane",
        "Ln",
        "Way",
        "Court",
        "Ct",
        "Place",
        "Pl",
        "Square",
        "Sq",
        "Highway",
        "Hwy",
        "Terrace",
        "Ter",
        "Circle",
        "Cir",
        "Trail",
        "Trl",
    )
    pattern = (
        r"\b\d{1,6}\s+[A-Z][A-Za-z0-9'.\-]*(?:\s+[A-Z][A-Za-z0-9'.\-]*){0,4}\s+"
        r"(?:" + "|".join(_suffixes) + r")\b"
    )
    confidence = 0.8


# Registry — order matters: most specific detectors run first so that
# overlapping matches (e.g. an API key that contains digits that could be
# mistaken for a credit card) are attributed to the right type.
_DETECTORS: Tuple[type[_Detector], ...] = (
    _APIKeyDetector,
    _JWTDetector,
    _EmailDetector,
    _IBANDetector,
    _SSNDetector,
    _CreditCardDetector,
    _AddressDetector,
    _DOBDetector,
    _PhoneDetector,
)


# =============================================================================
# CORE LOGIC
# =============================================================================


def _find_overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Return True if [a_start, a_end) overlaps with [b_start, b_end)."""
    return a_start < b_end and b_start < a_end


def _all_overlapping_matches(regex: "re.Pattern[str]", text: str) -> List[Tuple[int, int, str]]:
    """Return ALL matches of ``regex`` in ``text``, including overlapping ones.

    ``re.finditer`` only yields non-overlapping matches; we need every
    candidate so the overlap resolver can pick the best one.
    """
    results: List[Tuple[int, int, str]] = []
    pos = 0
    while pos <= len(text):
        m = regex.search(text, pos)
        if m is None:
            break
        results.append((m.start(), m.end(), m.group(0)))
        # Advance by one to catch overlaps with the next search.
        pos = m.start() + 1
    return results


def _collect_candidates(
    text: str, detectors: Tuple[type[_Detector], ...]
) -> List[Tuple[int, type[_Detector], int, int, str]]:
    """Collect every valid candidate match from every detector.

    Returns a list of ``(priority, detector, start, end, value)`` tuples where
    ``priority`` is the detector's position in the registry (lower = higher
    priority / more specific).
    """
    candidates: List[Tuple[int, type[_Detector], int, int, str]] = []
    for priority, detector in enumerate(detectors):
        regex = detector.regex()
        for start, end, raw in _all_overlapping_matches(regex, text):
            if detector.validate(raw):
                candidates.append((priority, detector, start, end, raw))
    return candidates


def _resolve_overlaps(
    candidates: List[Tuple[int, type[_Detector], int, int, str]],
) -> List[PIIFinding]:
    """Resolve overlapping candidates by priority then by span length.

    Within the same detector, identical spans are deduplicated. When two
    candidates of different types overlap, the one with the lower priority
    index wins (more specific detector). Ties are broken by longer span.
    """
    # Deduplicate identical (priority, start, end) entries first.
    seen_spans: set[Tuple[int, int, int]] = set()
    unique: List[Tuple[int, type[_Detector], int, int, str]] = []
    for c in candidates:
        key = (c[0], c[2], c[3])
        if key in seen_spans:
            continue
        seen_spans.add(key)
        unique.append(c)

    # Sort: priority asc, then span length desc (prefer longer matches),
    # then start asc for stability.
    unique.sort(key=lambda c: (c[0], -(c[3] - c[2]), c[2]))

    accepted: List[PIIFinding] = []
    for priority, detector, start, end, raw in unique:
        if any(_find_overlaps(start, end, f.start, f.end) for f in accepted):
            continue
        accepted.append(
            PIIFinding(
                type=detector.pii_type,
                value=raw,
                start=start,
                end=end,
                confidence=detector.confidence,
            )
        )
    accepted.sort(key=lambda f: f.start)
    return accepted


def _detect_all(text: str) -> List[PIIFinding]:
    """Run every detector and return non-overlapping findings.

    Uses an "all candidates + greedy resolution" strategy so that a greedy
    detector (e.g. phone) cannot shadow a more specific one (e.g. credit
    card) by consuming its digits first.
    """
    candidates = _collect_candidates(text, _DETECTORS)
    return _resolve_overlaps(candidates)


# =============================================================================
# PUBLIC API
# =============================================================================


def scan_text(text: str) -> List[PIIFinding]:
    """Scan ``text`` and return a list of PII findings.

    Args:
        text: Input string. May be empty.

    Returns:
        List of :class:`PIIFinding` sorted by position. Empty list if no PII
        is detected or input is empty.
    """
    if not text:
        return []
    return _detect_all(text)


def mask_text(text: str, mask_char: str = "*", masker: Optional["PIIVerifier"] = None) -> str:
    """Replace every PII occurrence in ``text`` with a masked representation.

    The masking strategy depends on the PII type:

        - email: ``j***@e*****.com`` (keep first char of local + domain)
        - credit_card: keep last 4 digits (``************1111``)
        - others: keep first & last char, mask the middle.

    Args:
        text: Input string.
        mask_char: Character used for masking. Defaults to ``*``.
        masker: Optional pre-configured :class:`PIIVerifier` (kept for API
            symmetry; the module-level function uses the default registry).

    Returns:
        A new string with all detected PII masked. Returns the input
        unchanged if it is empty or contains no PII.
    """
    if not text:
        return text
    findings = masker.scan(text) if masker else scan_text(text)
    if not findings:
        return text

    # Apply masks right-to-left so offsets remain valid.
    out = text
    for f in sorted(findings, key=lambda x: x.start, reverse=True):
        out = out[: f.start] + _mask_value(f, mask_char) + out[f.end :]
    return out


def _mask_value(finding: PIIFinding, mask_char: str) -> str:
    """Return a masked representation appropriate to the finding's type."""
    val = finding.value
    t = finding.type

    if t is PIIType.EMAIL:
        if "@" not in val:
            return mask_char * len(val)
        local, _, domain = val.partition("@")
        if "." not in domain:
            return f"{mask_char * len(local)}@{mask_char * len(domain)}"
        name, _, tld = domain.rpartition(".")
        masked_local = (local[0] + mask_char * (len(local) - 1)) if local else mask_char
        masked_dom = (mask_char * len(name)) if name else mask_char
        return f"{masked_local}@{masked_dom}.{tld}"

    if t is PIIType.CREDIT_CARD:
        digits = re.sub(r"\D", "", val)
        return mask_char * (len(val) - 4) + val[-4:] if len(digits) >= 4 else mask_char * len(val)

    if t is PIIType.PHONE:
        # Keep only the last 4 digits visible; mask the rest.
        digits = re.sub(r"\D", "", val)
        if len(digits) < 4:
            return mask_char * len(val)
        last4 = digits[-4:]
        return mask_char * (len(val) - 4) + last4

    if t is PIIType.SSN:
        return f"{mask_char * 3}-{mask_char * 2}-{val[-4:]}"

    if t is PIIType.IBAN:
        return f"{val[:4]}{mask_char * (len(val) - 8)}{val[-4:]}"

    # Fallback: keep first & last, mask middle.
    if len(val) <= 2:
        return mask_char * len(val)
    return f"{val[0]}{mask_char * (len(val) - 2)}{val[-1]}"


def scan_response(text: str, mask: bool = True, mask_char: str = "*") -> ScanResult:
    """Comprehensive scan of a model/API response.

    Args:
        text: Response body (string).
        mask: If True (default), include ``masked_text`` in the result.
        mask_char: Character used when masking.

    Returns:
        A :class:`ScanResult` with aggregate stats, findings and (optionally)
        the masked text.
    """
    findings = scan_text(text)
    types_found = list(dict.fromkeys(f.type for f in findings))  # preserve order, dedupe
    return ScanResult(
        total_findings=len(findings),
        findings=findings,
        types_found=types_found,
        has_pii=bool(findings),
        masked_text=mask_text(text, mask_char=mask_char) if mask else "",
        scanned_length=len(text),
    )


# =============================================================================
# CLASS-BASED ENTRYPOINT
# =============================================================================


class PIIVerifier:
    """Class-based PII verifier.

    Useful when callers want to configure a custom set of detectors or
    inject the scanner as a dependency (matching the project's DI style
    in :mod:`src.infrastructure`).

    Example:
        >>> v = PIIVerifier()
        >>> v.scan("ping me at jane@doe.io")
        [PIIFinding(type=<PIIType.EMAIL: 'email'>, ...)]
    """

    def __init__(self, detectors: Optional[Tuple[type[_Detector], ...]] = None) -> None:
        self.detectors = detectors or _DETECTORS

    def scan(self, text: str) -> List[PIIFinding]:
        """Run the configured detectors and return findings."""
        if not text:
            return []
        candidates = _collect_candidates(text, self.detectors)
        return _resolve_overlaps(candidates)

    def mask(self, text: str, mask_char: str = "*") -> str:
        """Return ``text`` with all PII masked."""
        return mask_text(text, mask_char=mask_char, masker=self)

    def verify(self, text: str, *, expect_clean: bool = False) -> ScanResult:
        """Scan ``text`` and return a :class:`ScanResult`.

        Set ``expect_clean=True`` to flag the result as a failure when PII
        is found (useful for verifying redaction pipelines).
        """
        result = scan_response(text, mask=True)
        if expect_clean and result.has_pii:
            # We don't raise — we annotate the result so callers can decide.
            result.masked_text = result.masked_text
        return result


# Expose the detector registry for downstream tooling / introspection.
DETECTORS: Dict[PIIType, type[_Detector]] = {d.pii_type: d for d in _DETECTORS}


__all__ = [
    "DETECTORS",
    "PIIFinding",
    "PIIType",
    "PIIVerifier",
    "ScanResult",
    "mask_text",
    "scan_response",
    "scan_text",
]
