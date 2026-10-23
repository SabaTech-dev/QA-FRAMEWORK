"""Deterministic regex engine for structured isolated fields (S3).

Complements the @desert-ant-labs/redact SDK (free text) with fully
deterministic, semantics-validated detectors for structured fields:
credit cards (Luhn), IBANs (mod-97), SSNs (SSA rules), emails, JWTs,
API keys and phone numbers. Detectors run in parallel threads for batch
inputs; results are identical to sequential runs.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass


@dataclass(frozen=True)
class Detection:
    """A single deterministic PII detection."""

    label: str
    original: str
    start: int
    end: int


@dataclass(frozen=True)
class ScrubResult:
    """Scrubbed text plus the detections that produced it."""

    text: str
    detections: tuple[Detection, ...]


def _luhn_check(number: str) -> bool:
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
    candidate = candidate.replace(" ", "").upper()
    if len(candidate) < 15 or not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]+", candidate):
        return False
    rearranged = candidate[4:] + candidate[:4]
    numeric = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    return int(numeric) % 97 == 1


def _phone_digits_ok(match: str) -> bool:
    return 7 <= len(re.sub(r"\D", "", match)) <= 15


def _ssn_ok(match: str) -> bool:
    area, group, _serial = match.split("-")
    if area in ("000", "666") or area.startswith("9"):
        return False
    return group != "00"


# (label, compiled pattern, validator). Order matters: more specific
# detectors (JWT, API key) run before generic ones (phone) so their
# spans are removed before cheaper detectors can overlap them.
_DETECTORS: tuple[tuple[str, re.Pattern[str], object], ...] = (
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9.\-]{1,253}\.[A-Za-z]{2,24}\b"),
        None,
    ),
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b"),
        None,
    ),
    (
        "api_key",
        re.compile(
            r"(?:"
            r"sk_(?:live|test)_[A-Za-z0-9]{24,}"
            r"|pk_(?:live|test)_[A-Za-z0-9]{24,}"
            r"|AKIA[0-9A-Z]{16}"
            r"|gh[pousr]_[A-Za-z0-9]{20,255}"
            r"|xox[baprs]-[A-Za-z0-9\-]{10,}"
            r"|AIza[0-9A-Za-z_\-]{35}"
            r")"
        ),
        None,
    ),
    (
        "iban",
        re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30}\b"),
        _iban_check,
    ),
    (
        "credit_card",
        re.compile(
            r"\b(?:"
            r"\d{13,19}"
            r"|\d{4}[ -]\d{4}[ -]\d{4}[ -]\d{1,7}"
            r"|\d{4}[ -]\d{6}[ -]\d{5}"
            r")\b"
        ),
        _luhn_check,
    ),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), _ssn_ok),
    (
        "phone",
        re.compile(
            r"(?<!\w)(?:\+?\d{1,3}[\s.\-]?)?"
            r"\(?\d{2,4}\)?[\s.\-]?"
            r"\d{3,4}[\s.\-]?\d{3,4}"
            r"(?!\w)"
        ),
        _phone_digits_ok,
    ),
)


class StructuredRegexScrubber:
    """Deterministic scrubber for structured isolated fields."""

    def scrub(self, text: str) -> ScrubResult:
        """Scrub one string. Placeholders are [LABEL_N], numbered per label."""
        detections: list[Detection] = []
        for label, pattern, validator in _DETECTORS:
            for m in pattern.finditer(text):
                if validator is not None and not validator(m.group(0)):
                    continue
                span = m.span()
                if any(
                    s < span[1] and span[0] < e for s, e in ((d.start, d.end) for d in detections)
                ):
                    continue
                detections.append(
                    Detection(label=label, original=m.group(0), start=span[0], end=span[1])
                )
        detections.sort(key=lambda d: d.start)
        counters: dict[str, int] = {}
        placeholders: dict[Detection, str] = {}
        for d in detections:
            counters[d.label] = counters.get(d.label, 0) + 1
            placeholders[d] = f"[{d.label.upper()}_{counters[d.label]}]"
        out = text
        for d in reversed(detections):
            out = out[: d.start] + placeholders[d] + out[d.end :]
        return ScrubResult(text=out, detections=tuple(detections))

    def scrub_many(self, texts: list[str], max_workers: int = 4) -> list[ScrubResult]:
        """Scrub many strings in parallel. Results match sequential order."""
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            return list(pool.map(self.scrub, texts))
