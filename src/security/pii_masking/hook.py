"""Single opt-in PII masking hook for the ingest pipeline (S1).

All scrubbing (logs, fixtures, transcripts) goes through `PiiMaskingHook.process`
BEFORE any payload reaches an external LLM or storage. Default is OFF.
"""

from __future__ import annotations

import re
from typing import Any

from src.security.pii_masking.config import MaskingMode, PiiMaskingConfig

# Deterministic scrub for structured isolated fields (expanded in T2/S3).
_CARD_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _mask_card(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if 13 <= len(digits) <= 19 and _luhn_ok(digits):
        return "[CREDIT_CARD_1]"
    return value


def _scrub_string(value: str) -> str:
    return _CARD_RE.sub(lambda m: _mask_card(m.group(0)), value)


class PiiMaskingHook:
    """The one ingest hook: scrub a payload before LLM/storage sinks."""

    def __init__(self, config: PiiMaskingConfig) -> None:
        self._config = config

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def process(self, payload: Any) -> Any:
        """Return the scrubbed payload. No-op when the flag is OFF (default)."""
        if not self._config.enabled:
            return payload
        return self._scrub(payload)

    def _scrub(self, value: Any) -> Any:
        if isinstance(value, str):
            return _scrub_string(value)
        if isinstance(value, dict):
            return {k: self._scrub(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return type(value)(self._scrub(v) for v in value)  # type: ignore[return-value]
        return value
