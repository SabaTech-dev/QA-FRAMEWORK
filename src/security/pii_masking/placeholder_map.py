"""Reversible placeholder map for LLM round-trips (S2).

MASK mode keeps an in-memory map placeholder -> original so the LLM reply
can be restored. ANONYMIZE mode discards the map: output stays redacted
and is NOT reversible. The placeholder log records types/placeholders
only — never the original values.
"""

from __future__ import annotations

import json
import re
from typing import Any

_PLACEHOLDER_RE = re.compile(r"\[[A-Z_]+_\d+\]")


class PlaceholderMap:
    """Placeholder -> original mapping, reversible or anonymizing."""

    def __init__(self, anonymize: bool = False) -> None:
        self._anonymize = anonymize
        self._map: dict[str, str] = {}
        self._log: list[dict[str, str]] = []

    @property
    def anonymize(self) -> bool:
        return self._anonymize

    def register(self, pii_type: str, original: str, placeholder: str) -> None:
        """Record a placeholder. In anonymize mode nothing is retained."""
        if self._anonymize:
            return
        self._map[placeholder] = original
        self._log.append({"placeholder": placeholder, "type": pii_type})

    def placeholder_log(self) -> list[dict[str, str]]:
        """Log of placeholders and their types (no originals)."""
        return list(self._log)

    def restore(self, text: str) -> str:
        """Fill placeholders back with originals. Anonymize mode refuses."""
        if self._anonymize:
            raise RuntimeError("anonymize mode: placeholder map was discarded")
        out = text
        for placeholder, original in self._map.items():
            out = out.replace(placeholder, original)
        for token in _PLACEHOLDER_RE.findall(text):
            if token not in self._map:
                raise KeyError(f"unknown placeholder: {token}")
        return out

    def to_json(self) -> str:
        """Serialize the map. Empty object in anonymize mode."""
        if self._anonymize:
            return "{}"
        return json.dumps(self._map)

    @classmethod
    def from_json(cls, raw: str) -> "PlaceholderMap":
        data: dict[str, Any] = json.loads(raw)
        pm = cls()
        pm._map = {str(k): str(v) for k, v in data.items()}
        return pm
