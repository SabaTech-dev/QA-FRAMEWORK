"""Opt-in PII masking module for the QA-FW ingest pipeline.

Hygiene mode, NOT formal DLP. See README.md in this package.
"""

from src.security.pii_masking.config import MaskingMode, PiiMaskingConfig
from src.security.pii_masking.hook import PiiMaskingHook

__all__ = ["MaskingMode", "PiiMaskingConfig", "PiiMaskingHook"]
