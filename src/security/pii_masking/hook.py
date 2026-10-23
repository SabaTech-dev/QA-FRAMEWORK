"""Single opt-in PII masking hook for the ingest pipeline (S1, S2, S3, S4).

All scrubbing (logs, fixtures, transcripts) goes through
`PiiMaskingHook.process` BEFORE any payload reaches an external LLM or
storage. Default is OFF.

Routing per string value:
- structured isolated field (no whitespace, short) -> deterministic regex
  engine, semantically validated;
- free text -> @desert-ant-labs/redact via the Node sidecar bridge.

MASK mode keeps a reversible PlaceholderMap for LLM round-trips;
ANONYMIZE mode discards the map (one-way).
"""

from __future__ import annotations

from typing import Any

from src.security.pii_masking.config import MaskingMode, PiiMaskingConfig
from src.security.pii_masking.placeholder_map import PlaceholderMap
from src.security.pii_masking.redact_bridge import RedactBridge
from src.security.pii_masking.regex_engine import StructuredRegexScrubber

_STRUCTURED_MAX_LEN = 100


def _is_structured(value: str) -> bool:
    stripped = value.strip()
    return bool(stripped) and len(stripped) <= _STRUCTURED_MAX_LEN and " " not in stripped


class PiiMaskingHook:
    """The one ingest hook: scrub a payload before LLM/storage sinks."""

    def __init__(self, config: PiiMaskingConfig) -> None:
        self._config = config
        self._scrubber = StructuredRegexScrubber()
        self._placeholder_map: PlaceholderMap | None = None
        self._bridge: RedactBridge | None = None
        if config.enabled:
            self._placeholder_map = PlaceholderMap(anonymize=config.mode is MaskingMode.ANONYMIZE)

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    @property
    def placeholder_map(self) -> PlaceholderMap | None:
        """Reversible map (None while the flag is OFF)."""
        return self._placeholder_map

    def process(self, payload: Any) -> Any:
        """Return the scrubbed payload. No-op when the flag is OFF (default)."""
        if not self._config.enabled:
            return payload
        return self._scrub(payload)

    def close(self) -> None:
        if self._bridge is not None:
            self._bridge.close()
            self._bridge = None

    def _scrub(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._scrub_string(value)
        if isinstance(value, dict):
            return {k: self._scrub(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return type(value)(self._scrub(v) for v in value)  # type: ignore[return-value]
        return value

    def _scrub_string(self, value: str) -> str:
        # Deterministic detectors run first everywhere (they complement the
        # SDK on free text and own the structured isolated fields). Their
        # placeholders are registered in the map too, so MASK mode can
        # restore them in LLM round-trips.
        result = self._scrubber.scrub(value)
        if self._placeholder_map is not None:
            counters: dict[str, int] = {}
            for det in result.detections:
                counters[det.label] = counters.get(det.label, 0) + 1
                self._placeholder_map.register(
                    det.label, det.original, f"[{det.label.upper()}_{counters[det.label]}]"
                )
        scrubbed = result.text
        if _is_structured(value):
            return scrubbed
        return self._scrub_free_text(scrubbed)

    def _scrub_free_text(self, value: str) -> str:
        if self._bridge is None:
            self._bridge = RedactBridge(bridge_command=self._config.bridge_command)
        redacted, items = self._bridge.redact_text(value)
        if self._placeholder_map is not None:
            for item in items:
                self._placeholder_map.register(
                    str(item.get("label", "unknown")),
                    str(item.get("original", "")),
                    str(item.get("placeholder", "")),
                )
        return redacted
