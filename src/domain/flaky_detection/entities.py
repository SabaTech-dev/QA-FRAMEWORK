"""
Entities for Flaky Test Detection Domain
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .value_objects import (
    DetectionMethod,
    FailurePattern,
    FlakinessScore,
    FlakyStatus,
    QuarantineReason,
    TestIdentifier,
)


@dataclass
class TestRun:
    """Record of a single test execution."""

    id: str = field(default_factory=lambda: str(uuid4()))
    test_identifier: Optional[TestIdentifier] = None
    passed: bool = True
    duration_ms: int = 0
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None
    run_number: int = 0  # Position in test run
    environment: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    executed_at: datetime = field(default_factory=datetime.utcnow)
    tenant_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "test_identifier": str(self.test_identifier) if self.test_identifier else None,
            "passed": self.passed,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "run_number": self.run_number,
            "executed_at": self.executed_at.isoformat(),
        }


@dataclass
class FlakyTest:
    """
    A test that exhibits flaky behavior.

    Tracks historical data and analysis results for tests
    that may be flaky.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    test_identifier: Optional[TestIdentifier] = None
    status: FlakyStatus = FlakyStatus.HEALTHY
    flakiness_score: Optional[FlakinessScore] = None

    # Statistics
    total_runs: int = 0
    total_passes: int = 0
    total_failures: int = 0
    pass_rate: float = 1.0

    # Timing statistics
    avg_duration_ms: int = 0
    duration_std_dev: float = 0.0
    min_duration_ms: int = 0
    max_duration_ms: int = 0

    # Failure analysis
    failure_pattern: Optional[FailurePattern] = None
    common_errors: List[str] = field(default_factory=list)

    # Detection info
    detection_method: Optional[DetectionMethod] = None
    first_detected: Optional[datetime] = None
    last_flaky_at: Optional[datetime] = None

    # Quarantine info
    quarantine_entry: Optional["QuarantineEntry"] = None

    tenant_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    @property
    def is_quarantined(self) -> bool:
        """Check if test is quarantined."""
        return self.status == FlakyStatus.QUARANTINED

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        return 1.0 - self.pass_rate

    @property
    def duration_variance(self) -> float:
        """Calculate duration variance coefficient."""
        if self.avg_duration_ms == 0:
            return 0.0
        return self.duration_std_dev / self.avg_duration_ms

    def update_stats(self, runs: List[TestRun]) -> "FlakyTest":
        """Update statistics from a list of runs."""
        if not runs:
            return self

        total = len(runs)
        passes = sum(1 for r in runs if r.passed)
        failures = total - passes
        durations = [r.duration_ms for r in runs]

        avg_duration = sum(durations) / len(durations) if durations else 0
        variance = (
            sum((d - avg_duration) ** 2 for d in durations) / len(durations) if durations else 0
        )
        std_dev = variance**0.5

        return FlakyTest(
            id=self.id,
            test_identifier=self.test_identifier,
            status=self.status,
            flakiness_score=self.flakiness_score,
            total_runs=self.total_runs + total,
            total_passes=self.total_passes + passes,
            total_failures=self.total_failures + failures,
            pass_rate=(self.total_passes + passes) / (self.total_runs + total),
            avg_duration_ms=int(avg_duration),
            duration_std_dev=std_dev,
            min_duration_ms=int(min(durations)) if durations else 0,
            max_duration_ms=int(max(durations)) if durations else 0,
            failure_pattern=self.failure_pattern,
            common_errors=self.common_errors,
            detection_method=self.detection_method,
            first_detected=self.first_detected,
            last_flaky_at=datetime.now(timezone.utc) if failures > 0 else self.last_flaky_at,
            quarantine_entry=self.quarantine_entry,
            tenant_id=self.tenant_id,
            created_at=self.created_at,
            updated_at=datetime.now(timezone.utc),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "test_identifier": str(self.test_identifier) if self.test_identifier else None,
            "status": self.status.value,
            "flakiness_score": self.flakiness_score.score if self.flakiness_score else None,
            "total_runs": self.total_runs,
            "pass_rate": self.pass_rate,
            "failure_rate": self.failure_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "duration_variance": self.duration_variance,
            "common_errors": self.common_errors,
            "detection_method": self.detection_method.value if self.detection_method else None,
            "first_detected": self.first_detected.isoformat() if self.first_detected else None,
            "last_flaky_at": self.last_flaky_at.isoformat() if self.last_flaky_at else None,
            "is_quarantined": self.is_quarantined,
        }


@dataclass
class QuarantineEntry:
    """
    Entry for a quarantined test.

    Tracks why a test was quarantined and when it can be
    re-evaluated for stability.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    test_identifier: Optional[TestIdentifier] = None
    reason: QuarantineReason = QuarantineReason.UNKNOWN
    description: Optional[str] = None

    # Quarantine details
    quarantined_at: datetime = field(default_factory=datetime.utcnow)
    quarantined_by: Optional[str] = None  # User ID or 'system'
    expires_at: Optional[datetime] = None  # Auto-expiry

    # Tracking
    attempts_to_fix: int = 0
    last_evaluation: Optional[datetime] = None
    evaluation_results: List[Dict[str, Any]] = field(default_factory=list)

    # Resolution
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None

    tenant_id: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        """Check if quarantine has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_resolved(self) -> bool:
        """Check if quarantine is resolved."""
        return self.resolved_at is not None

    def add_evaluation(self, passed: bool, notes: str = None) -> "QuarantineEntry":
        """Add an evaluation result."""
        new_results = self.evaluation_results + [
            {
                "passed": passed,
                "notes": notes,
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

        return QuarantineEntry(
            id=self.id,
            test_identifier=self.test_identifier,
            reason=self.reason,
            description=self.description,
            quarantined_at=self.quarantined_at,
            quarantined_by=self.quarantined_by,
            expires_at=self.expires_at,
            attempts_to_fix=self.attempts_to_fix + (1 if not passed else 0),
            last_evaluation=datetime.now(timezone.utc),
            evaluation_results=new_results,
            resolved_at=self.resolved_at,
            resolution_notes=self.resolution_notes,
            tenant_id=self.tenant_id,
        )

    def resolve(self, notes: str = None) -> "QuarantineEntry":
        """Mark quarantine as resolved."""
        return QuarantineEntry(
            id=self.id,
            test_identifier=self.test_identifier,
            reason=self.reason,
            description=self.description,
            quarantined_at=self.quarantined_at,
            quarantined_by=self.quarantined_by,
            expires_at=self.expires_at,
            attempts_to_fix=self.attempts_to_fix,
            last_evaluation=self.last_evaluation,
            evaluation_results=self.evaluation_results,
            resolved_at=datetime.now(timezone.utc),
            resolution_notes=notes,
            tenant_id=self.tenant_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "test_identifier": str(self.test_identifier) if self.test_identifier else None,
            "reason": self.reason.value,
            "description": self.description,
            "quarantined_at": self.quarantined_at.isoformat(),
            "quarantined_by": self.quarantined_by,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired,
            "is_resolved": self.is_resolved,
            "attempts_to_fix": self.attempts_to_fix,
            "last_evaluation": self.last_evaluation.isoformat() if self.last_evaluation else None,
        }


@dataclass
class FlakyDetectionSession:
    """
    Session for batch flaky test detection.

    Tracks the overall progress and results of a detection run.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    tenant_id: Optional[str] = None

    # Scope
    suite_ids: List[str] = field(default_factory=list)
    test_ids: List[str] = field(default_factory=list)

    # Results
    tests_analyzed: int = 0
    healthy_tests: int = 0
    suspect_tests: int = 0
    flaky_tests: int = 0
    quarantined_tests: int = 0

    # Details
    detected_flaky: List[str] = field(default_factory=list)
    auto_quarantined: List[str] = field(default_factory=list)

    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    status: str = "pending"

    @property
    def total_issues(self) -> int:
        """Total number of issue tests."""
        return self.suspect_tests + self.flaky_tests + self.quarantined_tests

    @property
    def health_rate(self) -> float:
        """Percentage of healthy tests."""
        if self.tests_analyzed == 0:
            return 0.0
        return self.healthy_tests / self.tests_analyzed

    def complete(self) -> "FlakyDetectionSession":
        """Mark session as completed."""
        return FlakyDetectionSession(
            id=self.id,
            tenant_id=self.tenant_id,
            suite_ids=self.suite_ids,
            test_ids=self.test_ids,
            tests_analyzed=self.tests_analyzed,
            healthy_tests=self.healthy_tests,
            suspect_tests=self.suspect_tests,
            flaky_tests=self.flaky_tests,
            quarantined_tests=self.quarantined_tests,
            detected_flaky=self.detected_flaky,
            auto_quarantined=self.auto_quarantined,
            started_at=self.started_at,
            completed_at=datetime.now(timezone.utc),
            status="completed",
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "tests_analyzed": self.tests_analyzed,
            "healthy_tests": self.healthy_tests,
            "suspect_tests": self.suspect_tests,
            "flaky_tests": self.flaky_tests,
            "quarantined_tests": self.quarantined_tests,
            "total_issues": self.total_issues,
            "health_rate": self.health_rate,
            "detected_flaky": self.detected_flaky,
            "auto_quarantined": self.auto_quarantined,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
        }
