"""Configuration for the opt-in PII masking hook (DEFAULT OFF)."""

from __future__ import annotations

import os
from enum import Enum

from pydantic import BaseModel, Field


class MaskingMode(str, Enum):
    """Masking mode: reversible masking or one-way anonymization."""

    MASK = "mask"
    ANONYMIZE = "anonymize"


_ENV_FLAG = "QAFW_PII_MASKING"
_ENV_MODE = "QAFW_PII_MASKING_MODE"


class PiiMaskingConfig(BaseModel):
    """Opt-in configuration for PII masking. Disabled by default (S1)."""

    enabled: bool = Field(default=False)
    mode: MaskingMode = Field(default=MaskingMode.MASK)
    bridge_command: list[str] | None = Field(
        default=None,
        description="Override for the Node redact bridge command.",
    )

    @classmethod
    def from_env(cls) -> "PiiMaskingConfig":
        """Build config from environment. Flag is opt-in: absent/any non-truthy -> OFF."""
        raw = os.environ.get(_ENV_FLAG, "").strip().lower()
        enabled = raw in {"1", "true", "yes", "on"}
        mode_raw = os.environ.get(_ENV_MODE, MaskingMode.MASK.value).strip().lower()
        mode = (
            MaskingMode(mode_raw)
            if mode_raw in {m.value for m in MaskingMode}
            else MaskingMode.MASK
        )
        return cls(enabled=enabled, mode=mode)
