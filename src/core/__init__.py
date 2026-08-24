"""Core module - Business logic and use cases"""

from src.core.entities.test_result import TestResult, TestStatus
from src.core.use_cases.test_runner import TestRunner

__all__ = [
    "TestResult",
    "TestRunner",
    "TestStatus",
]
