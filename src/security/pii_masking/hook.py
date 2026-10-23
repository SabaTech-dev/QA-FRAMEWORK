"""Single opt-in PII masking hook for the ingest pipeline (S1).

All scrubbing (logs, fixtures, transcripts) goes through `PiiMaskingHook.process`
BEFORE any payload reaches an external LLM or storage. Default is OFF.
"""

from __future__ import annotations

from typing import Any

from src.security.pii_masking.config import MaskingMode, PiiMaskingConfig
from src.security.pii_masking.regex_engine import StructuredRegexScrubber


class PiiMaskingHook:
    """The one ingest hook: scrub a payload before LLM/storage sinks."""

    def __init__(self, config: PiiMaskingConfig) -> None:
        self._config = config
        self._scrubber = StructuredRegexScrubber()

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
            return self._scrubber.scrub(value).text
        if isinstance(value, dict):
            return {k: self._scrub(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return type(value)(self._scrub(v) for v in value)  # type: ignore[return-value]
        return value
