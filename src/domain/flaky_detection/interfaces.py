"""
Interfaces for Flaky Test Detection Domain
"""

from abc import ABC, abstractmethod
from typing import Protocol

from .entities import FlakyTest, QuarantineEntry, TestRun
from .value_objects import FlakinessScore, FlakyStatus, QuarantineReason, TestIdentifier


class IFlakyDetector(Protocol):
    """Protocol for flaky test detection implementations."""

    def detect(
        self,
        test_identifier: TestIdentifier,
        runs: list[TestRun],
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
        tests: list[tuple],  # List of (test_identifier, runs)
    ) -> list[tuple]:  # List of (test_identifier, score)
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
        description: str | None = None,
        expires_in_days: int | None = None,
    ) -> QuarantineEntry:
        """Quarantine a flaky test."""

    @abstractmethod
    async def release(
        self,
        test_identifier: TestIdentifier,
        notes: str | None = None,
    ) -> QuarantineEntry | None:
        """Release a test from quarantine."""

    @abstractmethod
    async def get_quarantined(
        self,
        tenant_id: str,
    ) -> list[QuarantineEntry]:
        """Get all quarantined tests for a tenant."""

    @abstractmethod
    async def evaluate(
        self,
        test_identifier: TestIdentifier,
        recent_runs: list[TestRun],
    ) -> QuarantineEntry | None:
        """Evaluate if a quarantined test can be released."""

    @abstractmethod
    async def get_expired(self) -> list[QuarantineEntry]:
        """Get quarantined tests that have expired."""


class ITestRunRepository(ABC):
    """Abstract repository for test run data."""

    @abstractmethod
    async def get_runs(
        self,
        test_identifier: TestIdentifier,
        limit: int = 100,
    ) -> list[TestRun]:
        """Get recent runs for a test."""

    @abstractmethod
    async def save_run(self, run: TestRun) -> TestRun:
        """Save a test run."""

    @abstractmethod
    async def get_runs_for_suite(
        self,
        suite_id: str,
        limit: int = 1000,
    ) -> list[TestRun]:
        """Get runs for all tests in a suite."""

    @abstractmethod
    async def get_recent_failures(
        self,
        tenant_id: str,
        limit: int = 100,
    ) -> list[TestRun]:
        """Get recent failed tests."""


class IFlakyTestRepository(ABC):
    """Abstract repository for flaky test data."""

    @abstractmethod
    async def get_by_identifier(
        self,
        test_identifier: TestIdentifier,
    ) -> FlakyTest | None:
        """Get flaky test by identifier."""

    @abstractmethod
    async def save(self, flaky_test: FlakyTest) -> FlakyTest:
        """Save flaky test data."""

    @abstractmethod
    async def get_by_status(
        self,
        status: FlakyStatus,
        tenant_id: str,
        limit: int = 100,
    ) -> list[FlakyTest]:
        """Get flaky tests by status."""

    @abstractmethod
    async def get_all_flaky(
        self,
        tenant_id: str,
    ) -> list[FlakyTest]:
        """Get all confirmed flaky tests."""


class IRootCauseAnalyzer(Protocol):
    """Protocol for root cause analysis of flaky tests."""

    def analyze(
        self,
        test_identifier: TestIdentifier,
        runs: list[TestRun],
    ) -> dict:
        """
        Analyze root causes of flakiness.

        Returns dict with:
        - likely_causes: List of identified causes
        - confidence: Confidence in analysis
        - recommendations: List of fix recommendations
        """
        ...
