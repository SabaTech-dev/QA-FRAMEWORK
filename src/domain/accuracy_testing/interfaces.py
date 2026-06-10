"""
Interfaces for AI Accuracy Testing Domain

Abstract interfaces defining contracts for the accuracy testing system.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Protocol
from .entities import AccuracyEvaluation, AccuracyBenchmark, AccuracyTestSession
from .value_objects import LegalDomain


class IAccuracyEvaluator(Protocol):
    """Protocol for evaluating AI response accuracy."""

    def evaluate(
        self,
        benchmark: AccuracyBenchmark,
        ai_response: str,
        ai_model: str = "",
    ) -> AccuracyEvaluation:
        """
        Evaluate an AI response against a benchmark.

        Args:
            benchmark: The benchmark with ground truth
            ai_response: The AI's response to evaluate
            ai_model: Name/identifier of the AI model

        Returns:
            AccuracyEvaluation with scores and verdict
        """
        ...


class IResponseProvider(Protocol):
    """Protocol for obtaining AI responses for testing."""

    def get_response(self, prompt: str, model: str = "") -> str:
        """
        Get an AI response for a given prompt.

        Args:
            prompt: The question/prompt to send
            model: Optional model override

        Returns:
            The AI's response text
        """
        ...


class IBenchmarkRepository(ABC):
    """Abstract repository for benchmark persistence."""

    @abstractmethod
    async def get_by_id(self, benchmark_id: str) -> Optional[AccuracyBenchmark]:
        """Retrieve a benchmark by ID."""
        pass

    @abstractmethod
    async def get_by_domain(
        self,
        legal_domain: LegalDomain,
        limit: int = 100,
    ) -> List[AccuracyBenchmark]:
        """Get benchmarks for a legal domain."""
        pass

    @abstractmethod
    async def save(self, benchmark: AccuracyBenchmark) -> AccuracyBenchmark:
        """Save a benchmark (create or update)."""
        pass

    @abstractmethod
    async def delete(self, benchmark_id: str) -> bool:
        """Delete a benchmark."""
        pass


class ITestSessionRepository(ABC):
    """Abstract repository for test session persistence."""

    @abstractmethod
    async def get_by_id(self, session_id: str) -> Optional[AccuracyTestSession]:
        """Retrieve a test session by ID."""
        pass

    @abstractmethod
    async def save(self, session: AccuracyTestSession) -> AccuracyTestSession:
        """Save a test session."""
        pass

    @abstractmethod
    async def get_recent(
        self,
        tenant_id: str,
        limit: int = 10,
    ) -> List[AccuracyTestSession]:
        """Get recent test sessions for a tenant."""
        pass
