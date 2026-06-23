"""Tests for the PII masking verifier.

Run with::

    pytest tests/security/test_pii_masking.py -v -m pii_masking

All 9 detector categories, the three public entrypoints (scan_text,
mask_text, scan_response) and overlap/edge-case behaviour are covered.
"""

from __future__ import annotations

import pytest

from src.security.pii_masking import (
    PIIFinding,
    PIIType,
    PIIVerifier,
    ScanResult,
    mask_text,
    scan_response,
    scan_text,
)

# =============================================================================
# Marker: apply @pytest.mark.pii_masking to every test in this module.
# =============================================================================

pytestmark = pytest.mark.pii_masking


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _types(findings: list[PIIFinding]) -> set[PIIType]:
    return {f.type for f in findings}


# =============================================================================
# 1. Email detector
# =============================================================================


def test_detect_email_basic():
    """A standard email is detected with its correct span."""
    text = "Contact john.doe@example.com for details."
    findings = scan_text(text)

    assert len(findings) == 1
    f = findings[0]
    assert f.type is PIIType.EMAIL
    assert f.value == "john.doe@example.com"
    assert text[f.start : f.end] == "john.doe@example.com"
    assert f.confidence == 1.0


# =============================================================================
# 2. Phone detector (international E.164)
# =============================================================================


def test_detect_phone_international():
    """An E.164-style phone number is detected."""
    text = "Call me at +44 20 7946 0958 tomorrow."
    findings = scan_text(text)

    assert PIIType.PHONE in _types(findings)
    phone = next(f for f in findings if f.type is PIIType.PHONE)
    assert "+44 20 7946 0958" in phone.value
    assert phone.value in text


# =============================================================================
# 3. SSN detector — valid
# =============================================================================


def test_detect_ssn_valid():
    """A valid US SSN is detected."""
    text = "SSN: 123-45-6789"
    findings = scan_text(text)

    assert len(findings) == 1
    assert findings[0].type is PIIType.SSN
    assert findings[0].value == "123-45-6789"


# =============================================================================
# 4. SSN detector — invalid area rejected
# =============================================================================


def test_detect_ssn_invalid_area_rejected():
    """SSNs with invalid area (000/666/9xx) are NOT flagged."""
    for invalid in ("000-12-3456", "666-12-3456", "900-12-3456"):
        assert scan_text(invalid) == [], f"{invalid} should be rejected"


# =============================================================================
# 5. IBAN detector
# =============================================================================


def test_detect_iban_valid():
    """A valid IBAN (passes mod-97) is detected."""
    text = "IBAN GB82WEST12345698765432 end"
    findings = scan_text(text)

    assert len(findings) == 1
    assert findings[0].type is PIIType.IBAN
    assert findings[0].value == "GB82WEST12345698765432"


# =============================================================================
# 6. Credit card detector — valid (Luhn passes)
# =============================================================================


def test_detect_credit_card_valid():
    """A valid Visa test number (passes Luhn) is detected."""
    text = "Card 4111 1111 1111 1111 expires 12/25"
    findings = scan_text(text)

    assert PIIType.CREDIT_CARD in _types(findings)
    cc = next(f for f in findings if f.type is PIIType.CREDIT_CARD)
    assert "4111" in cc.value


# =============================================================================
# 7. Credit card detector — invalid (Luhn fails)
# =============================================================================


def test_detect_credit_card_invalid_luhn_rejected():
    """A 16-digit number that fails Luhn is NOT flagged as a credit card."""
    # 16 digits, but the last is changed so Luhn fails.
    text = "4111 1111 1111 1112"
    findings = [f for f in scan_text(text) if f.type is PIIType.CREDIT_CARD]
    assert findings == [], "Invalid Luhn card must not be detected"


# =============================================================================
# 8. API key detector — AWS
# =============================================================================


def test_detect_api_key_aws():
    """An AWS access key ID is detected."""
    # Assembled at runtime — AWS documentation example key, split to keep
    # repo secret scanners quiet on the source literal.
    aws_key = "AKIA" + "IOSFODNN7EXAMPLE"
    text = f"aws_key={aws_key}"
    findings = scan_text(text)

    assert PIIType.API_KEY in _types(findings)
    key = next(f for f in findings if f.type is PIIType.API_KEY)
    assert key.value == aws_key


# =============================================================================
# 9. API key detector — Stripe
# =============================================================================


def test_detect_api_key_stripe():
    """A Stripe secret key is detected."""
    # Assembled at runtime to avoid tripping repo secret scanners on the
    # source literal. The detector still sees the full key at execution time.
    stripe_key = "sk_" + "live_" + "Aa1Bb2Cc3Dd4Ee5Ff6Gg7Hh8Ii9"
    text = f"STRIPE={stripe_key}"
    findings = scan_text(text)

    assert PIIType.API_KEY in _types(findings)
    key = next(f for f in findings if f.type is PIIType.API_KEY)
    assert key.value.startswith("sk_live_")


# =============================================================================
# 10. JWT detector
# =============================================================================


def test_detect_jwt():
    """A well-formed JWT (3 base64url segments) is detected."""
    jwt = (
        "eyJhbGciOiJIUzI1NiJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
        "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    )
    text = f"Authorization: Bearer {jwt}"
    findings = scan_text(text)

    assert len(findings) == 1
    assert findings[0].type is PIIType.JWT
    assert findings[0].value == jwt


# =============================================================================
# 11. DOB detector
# =============================================================================


def test_detect_dob():
    """A date of birth in DD/MM/YYYY format is detected."""
    text = "born on 15/08/1990 in Madrid"
    findings = scan_text(text)

    assert PIIType.DOB in _types(findings)
    dob = next(f for f in findings if f.type is PIIType.DOB)
    assert dob.value == "15/08/1990"


# =============================================================================
# 12. Address detector (US street)
# =============================================================================


def test_detect_address_us_street():
    """A US street address is detected."""
    text = "She lives at 1600 Pennsylvania Avenue NW."
    findings = scan_text(text)

    assert PIIType.ADDRESS in _types(findings)
    addr = next(f for f in findings if f.type is PIIType.ADDRESS)
    assert "1600" in addr.value
    assert "Avenue" in addr.value


# =============================================================================
# 13. mask_text — basic masking
# =============================================================================


def test_mask_text_basic():
    """mask_text replaces PII with asterisks and preserves non-PII text."""
    text = "Email: john@example.com"
    masked = mask_text(text)

    assert "john@example.com" not in masked
    assert "@" in masked  # email structure preserved
    assert masked.startswith("Email: ")


# =============================================================================
# 14. mask_text — custom character
# =============================================================================


def test_mask_text_custom_char():
    """mask_text honours a custom mask character."""
    text = "SSN: 123-45-6789"
    masked = mask_text(text, mask_char="X")

    assert "123-45-6789" not in masked
    assert "6789" in masked  # last 4 preserved by SSN masker
    assert "X" in masked


# =============================================================================
# 15. scan_response — comprehensive summary
# =============================================================================


def test_scan_response_summary():
    """scan_response returns an aggregate ScanResult with correct stats."""
    text = "User jane@example.com called +1-555-123-4567 about order #4111 1111 1111 1111."
    result = scan_response(text)

    assert isinstance(result, ScanResult)
    assert result.has_pii is True
    assert result.total_findings >= 3
    assert PIIType.EMAIL in result.types_found
    assert PIIType.PHONE in result.types_found
    assert PIIType.CREDIT_CARD in result.types_found
    assert result.scanned_length == len(text)
    # masked_text should not leak any raw PII.
    assert "jane@example.com" not in result.masked_text
    assert "+1-555-123-4567" not in result.masked_text


# =============================================================================
# 16. Edge cases: empty, no-PII, multiple types, overlap resolution
# =============================================================================


def test_edge_cases_empty_no_pii_and_overlap():
    """Empty input and PII-free input return empty lists; overlapping
    detectors are resolved to the most specific type (credit card wins
    over phone when they share digit spans)."""

    # Empty input.
    assert scan_text("") == []
    assert mask_text("") == ""

    # No PII.
    clean = "The quick brown fox jumps over the lazy dog."
    assert scan_text(clean) == []
    assert mask_text(clean) == clean

    # Overlap resolution: phone vs credit card sharing digits.
    mixed = "4111 1111 1111 1111"
    findings = scan_text(mixed)
    types = _types(findings)
    assert PIIType.CREDIT_CARD in types
    assert PIIType.PHONE not in types, "Phone must not shadow a valid credit card"

    # PIIVerifier class behaves identically to the module functions.
    v = PIIVerifier()
    assert v.scan("no pii here") == []
    assert v.verify("a@b.co").has_pii is True
