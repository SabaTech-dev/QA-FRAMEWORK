"""Performance metrics collection and analysis"""

import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from src.core.interfaces import IMetricsCollector


@dataclass
class PerformanceMetrics:
    """
    Data class for performance test metrics.

    Attributes:
        total_requests: Total number of requests made
        successful_requests: Number of successful requests
        failed_requests: Number of failed requests
        response_times: List of all response times in milliseconds
        error_types: Dictionary mapping error types to their counts
        start_time: Test start timestamp
        end_time: Test end timestamp
    """

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    response_times: list[float] = field(default_factory=list)
    error_types: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    start_time: float | None = None
    end_time: float | None = None

    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100

    @property
    def throughput(self) -> float:
        """Calculate throughput (requests per second)."""
        if not self.start_time or not self.end_time:
            return 0.0
        duration = self.end_time - self.start_time
        if duration == 0:
            return 0.0
        return self.total_requests / duration

    @property
    def avg_response_time(self) -> float:
        """Calculate average response time."""
        if not self.response_times:
            return 0.0
        return statistics.mean(self.response_times)

    @property
    def min_response_time(self) -> float:
        """Get minimum response time."""
        if not self.response_times:
            return 0.0
        return min(self.response_times)

    @property
    def max_response_time(self) -> float:
        """Get maximum response time."""
        if not self.response_times:
            return 0.0
        return max(self.response_times)

    @property
    def median_response_time(self) -> float:
        """Calculate median response time."""
        if not self.response_times:
            return 0.0
        return statistics.median(self.response_times)

    @property
    def p95_response_time(self) -> float:
        """Calculate 95th percentile response time."""
        if not self.response_times:
            return 0.0
        return (
            statistics.quantiles(self.response_times, n=20)[18]
            if len(self.response_times) >= 20
            else max(self.response_times)
        )

    @property
    def p99_response_time(self) -> float:
        """Calculate 99th percentile response time."""
        if not self.response_times:
            return 0.0
        return (
            statistics.quantiles(self.response_times, n=100)[98]
            if len(self.response_times) >= 100
            else max(self.response_times)
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "error_rate": self.error_rate,
            "throughput": round(self.throughput, 2),
            "response_times": {
                "avg": round(self.avg_response_time, 2),
                "min": round(self.min_response_time, 2),
                "max": round(self.max_response_time, 2),
                "median": round(self.median_response_time, 2),
                "p95": round(self.p95_response_time, 2),
                "p99": round(self.p99_response_time, 2),
            },
            "error_types": dict(self.error_types),
            "duration": (
                round(self.end_time - self.start_time, 2)
                if self.start_time and self.end_time
                else 0
            ),
        }


class MetricsCollector(IMetricsCollector):
    """
    Collector for performance test metrics.

    This class implements the IMetricsCollector interface and provides
    thread-safe metric collection during performance testing.

    Example:
        collector = MetricsCollector()
        collector.start_collection()
        collector.record_response_time(150.5)
        collector.record_error("timeout", "Connection timeout")
        metrics = collector.get_metrics()
    """

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self._metrics = PerformanceMetrics()
        self._collecting = False

    def start_collection(self) -> None:
        """Start collecting metrics."""
        self._metrics = PerformanceMetrics()
        self._metrics.start_time = time.time()
        self._collecting = True

    def stop_collection(self) -> None:
        """Stop collecting metrics."""
        self._metrics.end_time = time.time()
        self._collecting = False

    def record_response_time(self, response_time_ms: float) -> None:
        """
        Record a response time measurement.

        Args:
            response_time_ms: Response time in milliseconds
        """
        if not self._collecting:
            return
        self._metrics.response_times.append(response_time_ms)
        self._metrics.total_requests += 1
        self._metrics.successful_requests += 1

    def record_error(self, error_type: str, error_message: str) -> None:
        """
        Record an error occurrence.

        Args:
            error_type: Type of error (e.g., 'timeout', 'connection_error')
            error_message: Error message or description
        """
        if not self._collecting:
            return
        self._metrics.total_requests += 1
        self._metrics.failed_requests += 1
        self._metrics.error_types[error_type] += 1

    def record_throughput(self, requests_count: int, time_window_ms: float) -> None:
        """
        Record throughput metrics.

        Args:
            requests_count: Number of requests in the time window
            time_window_ms: Time window in milliseconds
        """
        # Throughput is calculated from total requests and duration

    def get_metrics(self) -> dict[str, Any]:
        """
        Get collected metrics.

        Returns:
            Dictionary with all collected metrics.
        """
        return self._metrics.to_dict()

    def reset(self) -> None:
        """Reset all collected metrics."""
        self._metrics = PerformanceMetrics()
        self._collecting = False

    def get_metrics_object(self) -> PerformanceMetrics:
        """
        Get the PerformanceMetrics object directly.

        Returns:
            PerformanceMetrics object with all metrics.
        """
        return self._metrics
