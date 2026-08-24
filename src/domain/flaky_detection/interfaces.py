"""
Interfaces for Flaky Test Detection Domain
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Protocol

from .entities import FlakyTest, QuarantineEntry, TestRun
from .value_objects import FlakinessScore, FlakyStatus, QuarantineReason, TestIdentifier


class IFlakyDetector(Protocol):
    """Protocol for flaky test detection implementations."""

    def detect(
        self,
        test_identifier: TestIdentifier,
        runs: List[TestRun],
    ) -> FlakinessScore:
        """
        Detect if a test is flaky based on its run history.

        Args:
            test_identifier: The test to analyze
            runs: Historical test runs

        Returns:
            FlakinessScore with detection results
        """
        ...

    def batch_detect(
        self,
        tests: List[tuple],  # List of (test_identifier, runs)
    ) -> List[tuple]:  # List of (test_identifier, score)
        """
        Detect flakiness for multiple tests.

        Args:
            tests: List of (test_identifier, runs) tuples

        Returns:
            List of (test_identifier, score) tuples
        """
        ...


class IQuarantineManager(ABC):
    """Abstract manager for test quarantine."""

    @abstractmethod
    async def quarantine(
        self,
        test_identifier: TestIdentifier,
        reason: QuarantineReason,
        description: Optional[str] = None,
        expires_in_days: Optional[int] = None,
    ) -> QuarantineEntry:
        """Quarantine a flaky test."""
        pass

    @abstractmethod
    async def release(
        self,
        test_identifier: TestIdentifier,
        notes: Optional[str] = None,
    ) -> Optional[QuarantineEntry]:
        """Release a test from quarantine."""
        pass

    @abstractmethod
    async def get_quarantined(
        self,
        tenant_id: str,
    ) -> List[QuarantineEntry]:
        """Get all quarantined tests for a tenant."""
        pass

    @abstractmethod
    async def evaluate(
        self,
        test_identifier: TestIdentifier,
        recent_runs: List[TestRun],
    ) -> Optional[QuarantineEntry]:
        """Evaluate if a quarantined test can be released."""
        pass

    @abstractmethod
    async def get_expired(self) -> List[QuarantineEntry]:
        """Get quarantined tests that have expired."""
        pass


class ITestRunRepository(ABC):
    """Abstract repository for test run data."""

    @abstractmethod
    async def get_runs(
        self,
        test_identifier: TestIdentifier,
        limit: int = 100,
    ) -> List[TestRun]:
        """Get recent runs for a test."""
        pass

    @abstractmethod
    async def save_run(self, run: TestRun) -> TestRun:
        """Save a test run."""
        pass

    @abstractmethod
    async def get_runs_for_suite(
        self,
        suite_id: str,
        limit: int = 1000,
    ) -> List[TestRun]:
        """Get runs for all tests in a suite."""
        pass

    @abstractmethod
    async def get_recent_failures(
        self,
        tenant_id: str,
        limit: int = 100,
    ) -> List[TestRun]:
        """Get recent failed tests."""
        pass


class IFlakyTestRepository(ABC):
    """Abstract repository for flaky test data."""

    @abstractmethod
    async def get_by_identifier(
        self,
        test_identifier: TestIdentifier,
    ) -> Optional[FlakyTest]:
        """Get flaky test by identifier."""
        pass

    @abstractmethod
    async def save(self, flaky_test: FlakyTest) -> FlakyTest:
        """Save flaky test data."""
        pass

    @abstractmethod
    async def get_by_status(
        self,
        status: FlakyStatus,
        tenant_id: str,
        limit: int = 100,
    ) -> List[FlakyTest]:
        """Get flaky tests by status."""
        pass

    @abstractmethod
    async def get_all_flaky(
        self,
        tenant_id: str,
    ) -> List[FlakyTest]:
        """Get all confirmed flaky tests."""
        pass


class IRootCauseAnalyzer(Protocol):
    """Protocol for root cause analysis of flaky tests."""

    def analyze(
        self,
        test_identifier: TestIdentifier,
        runs: List[TestRun],
    ) -> dict:
        """
        Analyze root causes of flakiness.

        Returns dict with:
        - likely_causes: List of identified causes
        - confidence: Confidence in analysis
        - recommendations: List of fix recommendations
        """
        ...
