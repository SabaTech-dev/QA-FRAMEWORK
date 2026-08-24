"""
AI Test Generation Domain Module

This module provides intelligent test generation capabilities:
- Generate tests from requirements documents
- Generate tests from UI automation analysis
- Generate edge cases automatically
"""

from .entities import EdgeCase, GeneratedTest, TestGenerationSession, TestScenario
from .value_objects import (
    ConfidenceLevel,
    GenerationStatus,
    GenerationType,
    RequirementSource,
    TestCaseMetadata,
    TestFramework,
    TestPriority,
)

__all__ = [
    # Value Objects
    "GenerationType",
    "TestFramework",
    "TestPriority",
    "GenerationStatus",
    "ConfidenceLevel",
    "RequirementSource",
    "TestCaseMetadata",
    # Entities
    "GeneratedTest",
    "TestScenario",
    "EdgeCase",
    "TestGenerationSession",
]
