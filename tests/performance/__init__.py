# Performance Tests Module
"""Performance and benchmark tests for QA-FRAMEWORK."""

import pytest


@pytest.fixture
def benchmark_config():
    """Configuration for performance benchmarks."""
    return {
        "max_time": 1.0,  # Max execution time in seconds
        "min_ops": 100,  # Minimum operations per second
    }
