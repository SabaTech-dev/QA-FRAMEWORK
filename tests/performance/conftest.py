"""Configuration for performance tests."""

import pytest


def pytest_configure(config):
    """Configure custom markers for performance tests."""
    config.addinivalue_line("markers", "performance: mark test as a performance benchmark")


@pytest.fixture(scope="session")
def performance_threshold():
    """Default performance thresholds."""
    return {"max_time_seconds": 1.0, "min_ops_per_second": 100, "max_memory_mb": 100}
