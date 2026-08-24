"""Test entity - Domain model for test results"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class TestStatus(Enum):
    """Test execution status"""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    IN_PROGRESS = "in_progress"


@dataclass
class TestResult:
    """
    Entity representing a test execution result.

    Attributes:
        test_name: Name of the test
        status: Test status (passed, failed, skipped, error)
        execution_time: Time taken to execute the test (seconds)
        error_message: Error message if test failed
        metadata: Additional test metadata
        timestamp: When the test was executed
    """

    test_name: str
    status: TestStatus
    execution_time: float
    error_message: str | None = None
    metadata: dict[str, Any] | None = None
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        """Initialize default values"""
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC)

    def is_passed(self) -> bool:
        """Check if test passed"""
        return self.status == TestStatus.PASSED

    def is_failed(self) -> bool:
        """Check if test failed"""
        return self.status == TestStatus.FAILED

    def to_dict(self) -> dict[str, Any]:
        """Convert test result to dictionary"""
        return {
            "test_name": self.test_name,
            "status": self.status.value,
            "execution_time": self.execution_time,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
