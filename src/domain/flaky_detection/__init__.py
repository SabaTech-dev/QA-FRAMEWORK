"""
Flaky Test Detection Domain Module

AI-powered detection and analysis of flaky tests.
"""

from .entities import FlakyDetectionSession, FlakyTest, QuarantineEntry, TestRun
from .interfaces import IFlakyDetector, IQuarantineManager, ITestRunRepository
from .value_objects import DetectionMethod, FlakyStatus, QuarantineReason

__all__ = [
    # Entities
    "FlakyTest",
    "FlakyDetectionSession",
    "TestRun",
    "QuarantineEntry",
    # Value Objects
    "FlakyStatus",
    "QuarantineReason",
    "DetectionMethod",
    # Interfaces
    "IFlakyDetector",
    "IQuarantineManager",
    "ITestRunRepository",
]
