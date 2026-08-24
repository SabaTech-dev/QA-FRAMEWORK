"""
Parallel Performance Test Examples.

These tests demonstrate performance improvements with parallel execution.
Includes benchmarks and timing comparisons.

Usage:
    # Sequential execution
    pytest tests/unit/test_parallel_performance.py -v

    # Parallel execution (4 workers)
    pytest tests/unit/test_parallel_performance.py -n 4 -v

    # Compare timing
    time pytest tests/unit/test_parallel_performance.py::TestParallelBenchmark -n 1
    time pytest tests/unit/test_parallel_performance.py::TestParallelBenchmark -n 4
"""

import time
from typing import Any

import pytest


class TestParallelBenchmark:
    """Benchmark tests for parallel execution performance."""

    @pytest.mark.parallel_safe
    def test_benchmark_1(self) -> None:
        """Benchmark test 1 - simulates API call."""
        time.sleep(0.1)  # Simulate 100ms API call
        assert True

    @pytest.mark.parallel_safe
    def test_benchmark_2(self) -> None:
        """Benchmark test 2 - simulates API call."""
        time.sleep(0.1)
        assert True

    @pytest.mark.parallel_safe
    def test_benchmark_3(self) -> None:
        """Benchmark test 3 - simulates API call."""
        time.sleep(0.1)
        assert True

    @pytest.mark.parallel_safe
    def test_benchmark_4(self) -> None:
        """Benchmark test 4 - simulates API call."""
        time.sleep(0.1)
        assert True

    @pytest.mark.parallel_safe
    def test_benchmark_5(self) -> None:
        """Benchmark test 5 - simulates API call."""
        time.sleep(0.1)
        assert True

    @pytest.mark.parallel_safe
    def test_benchmark_6(self) -> None:
        """Benchmark test 6 - simulates API call."""
        time.sleep(0.1)
        assert True

    @pytest.mark.parallel_safe
    def test_benchmark_7(self) -> None:
        """Benchmark test 7 - simulates API call."""
        time.sleep(0.1)
        assert True

    @pytest.mark.parallel_safe
    def test_benchmark_8(self) -> None:
        """Benchmark test 8 - simulates API call."""
        time.sleep(0.1)
        assert True


class TestParallelTiming:
    """Tests for measuring parallel execution timing."""

    @pytest.mark.parallel_safe
    def test_measure_execution_time(
        self,
        timer: dict[str, float],
    ) -> None:
        """
        Measure test execution time.

        Args:
            timer: Timer fixture dictionary.
        """
        # timer["start"] is already set
        time.sleep(0.05)
        # timer["end"] and timer["elapsed"] will be set after yield

    @pytest.mark.parallel_safe
    def test_with_varying_delays_1(self) -> None:
        """Test with 50ms delay."""
        time.sleep(0.05)
        assert True

    @pytest.mark.parallel_safe
    def test_with_varying_delays_2(self) -> None:
        """Test with 100ms delay."""
        time.sleep(0.1)
        assert True

    @pytest.mark.parallel_safe
    def test_with_varying_delays_3(self) -> None:
        """Test with 150ms delay."""
        time.sleep(0.15)
        assert True

    @pytest.mark.parallel_safe
    def test_with_varying_delays_4(self) -> None:
        """Test with 200ms delay."""
        time.sleep(0.2)
        assert True


class TestParallelComputation:
    """Tests demonstrating parallel computation."""

    @pytest.mark.parallel_safe
    def test_computation_heavy_1(self) -> None:
        """CPU-intensive computation test 1."""
        result = sum(i**2 for i in range(10000))
        assert result > 0

    @pytest.mark.parallel_safe
    def test_computation_heavy_2(self) -> None:
        """CPU-intensive computation test 2."""
        result = sum(i**3 for i in range(10000))
        assert result > 0

    @pytest.mark.parallel_safe
    def test_computation_heavy_3(self) -> None:
        """CPU-intensive computation test 3."""
        result = sum(i**4 for i in range(10000))
        assert result > 0

    @pytest.mark.parallel_safe
    def test_computation_heavy_4(self) -> None:
        """CPU-intensive computation test 4."""
        result = sum(i**5 for i in range(10000))
        assert result > 0


class TestParallelScalability:
    """Tests for demonstrating scalability with more workers."""

    @pytest.mark.parallel_safe
    def test_scalability_1(self) -> None:
        """Scalability test 1."""
        time.sleep(0.05)
        assert True

    @pytest.mark.parallel_safe
    def test_scalability_2(self) -> None:
        """Scalability test 2."""
        time.sleep(0.05)
        assert True

    @pytest.mark.parallel_safe
    def test_scalability_3(self) -> None:
        """Scalability test 3."""
        time.sleep(0.05)
        assert True

    @pytest.mark.parallel_safe
    def test_scalability_4(self) -> None:
        """Scalability test 4."""
        time.sleep(0.05)
        assert True

    @pytest.mark.parallel_safe
    def test_scalability_5(self) -> None:
        """Scalability test 5."""
        time.sleep(0.05)
        assert True

    @pytest.mark.parallel_safe
    def test_scalability_6(self) -> None:
        """Scalability test 6."""
        time.sleep(0.05)
        assert True

    @pytest.mark.parallel_safe
    def test_scalability_7(self) -> None:
        """Scalability test 7."""
        time.sleep(0.05)
        assert True

    @pytest.mark.parallel_safe
    def test_scalability_8(self) -> None:
        """Scalability test 8."""
        time.sleep(0.05)
        assert True

    @pytest.mark.parallel_safe
    def test_scalability_9(self) -> None:
        """Scalability test 9."""
        time.sleep(0.05)
        assert True

    @pytest.mark.parallel_safe
    def test_scalability_10(self) -> None:
        """Scalability test 10."""
        time.sleep(0.05)
        assert True

    @pytest.mark.parallel_safe
    def test_scalability_11(self) -> None:
        """Scalability test 11."""
        time.sleep(0.05)
        assert True

    @pytest.mark.parallel_safe
    def test_scalability_12(self) -> None:
        """Scalability test 12."""
        time.sleep(0.05)
        assert True


class TestParallelWithWorkers:
    """Tests demonstrating worker-specific behavior."""

    @pytest.mark.parallel_safe
    def test_worker_distribution_1(
        self,
        worker_id: str,
        execution_context: dict[str, Any],
    ) -> None:
        """
        Test worker distribution - test 1.

        Args:
            worker_id: Current worker identifier.
            execution_context: Execution context dictionary.
        """
        time.sleep(0.03)
        assert worker_id in execution_context["worker_id"]

    @pytest.mark.parallel_safe
    def test_worker_distribution_2(
        self,
        worker_id: str,
        execution_context: dict[str, Any],
    ) -> None:
        """Test worker distribution - test 2."""
        time.sleep(0.03)
        assert worker_id in execution_context["worker_id"]

    @pytest.mark.parallel_safe
    def test_worker_distribution_3(
        self,
        worker_id: str,
        execution_context: dict[str, Any],
    ) -> None:
        """Test worker distribution - test 3."""
        time.sleep(0.03)
        assert worker_id in execution_context["worker_id"]

    @pytest.mark.parallel_safe
    def test_worker_distribution_4(
        self,
        worker_id: str,
        execution_context: dict[str, Any],
    ) -> None:
        """Test worker distribution - test 4."""
        time.sleep(0.03)
        assert worker_id in execution_context["worker_id"]


class TestParallelSpeedup:
    """Tests designed to show parallel speedup."""

    # Each test takes ~0.1s, 8 tests = ~0.8s sequential
    # With 4 workers: ~0.2s (4x speedup)

    @pytest.mark.parallel_safe
    def test_speedup_demo_1(self) -> None:
        """Speedup demonstration test 1."""
        time.sleep(0.1)
        assert True

    @pytest.mark.parallel_safe
    def test_speedup_demo_2(self) -> None:
        """Speedup demonstration test 2."""
        time.sleep(0.1)
        assert True

    @pytest.mark.parallel_safe
    def test_speedup_demo_3(self) -> None:
        """Speedup demonstration test 3."""
        time.sleep(0.1)
        assert True

    @pytest.mark.parallel_safe
    def test_speedup_demo_4(self) -> None:
        """Speedup demonstration test 4."""
        time.sleep(0.1)
        assert True

    @pytest.mark.parallel_safe
    def test_speedup_demo_5(self) -> None:
        """Speedup demonstration test 5."""
        time.sleep(0.1)
        assert True

    @pytest.mark.parallel_safe
    def test_speedup_demo_6(self) -> None:
        """Speedup demonstration test 6."""
        time.sleep(0.1)
        assert True

    @pytest.mark.parallel_safe
    def test_speedup_demo_7(self) -> None:
        """Speedup demonstration test 7."""
        time.sleep(0.1)
        assert True

    @pytest.mark.parallel_safe
    def test_speedup_demo_8(self) -> None:
        """Speedup demonstration test 8."""
        time.sleep(0.1)
        assert True

    @pytest.mark.serial
    def test_speedup_summary(self) -> None:
        """
        Summary test running serially after parallel tests.

        This test documents expected speedup:
        - Sequential: ~0.8s
        - 2 workers: ~0.4s
        - 4 workers: ~0.2s
        - 8 workers: ~0.1s
        """
        # This is a documentation test
        expected_speedups = {
            1: "0.8s (baseline)",
            2: "~0.4s (2x speedup)",
            4: "~0.2s (4x speedup)",
            8: "~0.1s (8x speedup)",
        }

        assert len(expected_speedups) == 4
        print("\nExpected speedups for TestParallelSpeedup:")
        for workers, time_str in expected_speedups.items():
            print(f"  {workers} worker(s): {time_str}")
