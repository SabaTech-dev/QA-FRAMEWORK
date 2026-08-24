"""
Self-Healing Tests Domain Module

This module provides the domain layer for AI-powered self-healing tests,
enabling automatic detection and repair of broken selectors.
"""

from .entities import HealingResult, HealingSession, Selector
from .interfaces import IConfidenceScorer, ISelectorHealer, ISelectorRepository
from .value_objects import ConfidenceLevel, HealingStatus, SelectorType

__all__ = [
    # Entities
    "Selector",
    "HealingResult",
    "HealingSession",
    # Value Objects
    "SelectorType",
    "HealingStatus",
    "ConfidenceLevel",
    # Interfaces
    "ISelectorHealer",
    "ISelectorRepository",
    "IConfidenceScorer",
]
