"""
Basic Parallel Test Examples.

These tests demonstrate basic parallel execution with pytest-xdist.
Each test is independent and can run in parallel without conflicts.

Usage:
    pytest tests/unit/test_parallel_basic.py -v
    pytest tests/unit/test_parallel_basic.py -n 4 -v  # Parallel with 4 workers
    pytest tests/unit/test_parallel_basic.py -n auto -v  # Auto-detect workers
"""

import time
from typing import Any

import pytest


class TestParallelBasic:
    """Basic parallel tests that can run concurrently."""

    @pytest.mark.parallel_safe
    def test_worker_identification(self, worker_id: str) -> None:
        """
        Test that worker identification is working correctly.

        Args:
            worker_id: Current worker identifier.
        """
        assert worker_id is not None
        assert isinstance(worker_id, str)
        assert worker_id.startswith("gw") or worker_id == "master"

    @pytest.mark.parallel_safe
    def test_session_isolation(self, session_id: str) -> None:
        """
        Test that each test gets proper session identification.

        Args:
            session_id: Current session identifier.
        """
        assert session_id is not None
        assert isinstance(session_id, str)
        assert len(session_id) == 8

    @pytest.mark.parallel_safe
    def test_execution_context(self, execution_context: dict[str, Any]) -> None:
        """
        Test execution context contains required information.

        Args:
            execution_context: Execution context dictionary.
        """
        assert "worker_id" in execution_context
        assert "session_id" in execution_context
        assert "timestamp" in execution_context
        assert "process_id" in execution_context
        assert "thread_id" in execution_context

    @pytest.mark.parallel_safe
    def test_parallel_calculation_1(self) -> None:
        """Simple calculation test 1."""
        result = sum(range(100))
        assert result == 4950

    @pytest.mark.parallel_safe
    def test_parallel_calculation_2(self) -> None:
        """Simple calculation test 2."""
        result = sum(range(200))
        assert result == 19900

    @pytest.mark.parallel_safe
    def test_parallel_calculation_3(self) -> None:
        """Simple calculation test 3."""
        result = sum(range(300))
        assert result == 44850

    @pytest.mark.parallel_safe
    def test_parallel_calculation_4(self) -> None:
        """Simple calculation test 4."""
        result = sum(range(400))
        assert result == 79800


class TestParallelWithTiming:
    """Tests demonstrating parallel execution timing."""

    @pytest.mark.parallel_safe
    def test_with_delay_1(self) -> None:
        """Test with small delay."""
        time.sleep(0.1)
        assert True

    @pytest.mark.parallel_safe
    def test_with_delay_2(self) -> None:
        """Test with small delay."""
        time.sleep(0.1)
        assert True

    @pytest.mark.parallel_safe
    def test_with_delay_3(self) -> None:
        """Test with small delay."""
        time.sleep(0.1)
        assert True

    @pytest.mark.parallel_safe
    def test_with_delay_4(self) -> None:
        """Test with small delay."""
        time.sleep(0.1)
        assert True

    @pytest.mark.parallel_safe
    def test_timing_measurement(self, timer: dict[str, float]) -> None:
        """
        Test that timer fixture works in parallel.

        Args:
            timer: Timer dictionary from fixture.
        """
        # timer["start"] is already set by fixture
        time.sleep(0.05)
        # timer["end"] and timer["elapsed"] will be set after yield


class TestParallelDataIsolation:
    """Tests demonstrating data isolation in parallel execution."""

    @pytest.mark.parallel_safe
    def test_isolated_data_1(self, isolated_test_data: dict[str, Any]) -> None:
        """
        Test data isolation with unique keys.

        Args:
            isolated_test_data: Isolated test data dictionary.
        """
        isolated_test_data["test_name"] = "test_1"
        isolated_test_data["value"] = 100

        # Verify data is stored
        assert isolated_test_data["test_name"] == "test_1"
        assert isolated_test_data["value"] == 100

    @pytest.mark.parallel_safe
    def test_isolated_data_2(self, isolated_test_data: dict[str, Any]) -> None:
        """
        Test data isolation doesn't interfere with other tests.

        Args:
            isolated_test_data: Isolated test data dictionary.
        """
        # This test should NOT see data from test_isolated_data_1
        assert "test_name" not in isolated_test_data

        isolated_test_data["test_name"] = "test_2"
        isolated_test_data["value"] = 200

        assert isolated_test_data["test_name"] == "test_2"
        assert isolated_test_data["value"] == 200

    @pytest.mark.parallel_safe
    def test_isolated_data_3(self, isolated_test_data: dict[str, Any]) -> None:
        """
        Test data isolation with complex data structures.

        Args:
            isolated_test_data: Isolated test data dictionary.
        """
        isolated_test_data["list"] = [1, 2, 3]
        isolated_test_data["dict"] = {"key": "value"}
        isolated_test_data["nested"] = {"a": {"b": "c"}}

        assert isolated_test_data["list"] == [1, 2, 3]
        assert isolated_test_data["dict"]["key"] == "value"
        assert isolated_test_data["nested"]["a"]["b"] == "c"


class TestWorkerResourcePool:
    """Tests demonstrating worker-scoped resource pools."""

    @pytest.mark.parallel_safe
    def test_worker_pool_basic(
        self,
        worker_resource_pool: dict[str, Any],
        worker_id: str,
    ) -> None:
        """
        Test worker resource pool initialization.

        Args:
            worker_resource_pool: Worker resource pool.
            worker_id: Current worker identifier.
        """
        assert worker_resource_pool["worker_id"] == worker_id
        assert "created_at" in worker_resource_pool

    @pytest.mark.parallel_safe
    def test_worker_pool_persistence_1(
        self,
        worker_resource_pool: dict[str, Any],
    ) -> None:
        """
        Test worker pool persists across tests in same worker.

        Args:
            worker_resource_pool: Worker resource pool.
        """
        worker_resource_pool["counter"] = worker_resource_pool.get("counter", 0) + 1
        assert worker_resource_pool["counter"] >= 1

    @pytest.mark.parallel_safe
    def test_worker_pool_persistence_2(
        self,
        worker_resource_pool: dict[str, Any],
    ) -> None:
        """
        Test worker pool state from previous test.

        Args:
            worker_resource_pool: Worker resource pool.
        """
        # This test should see the counter from the previous test
        # if running on the same worker
        if "counter" in worker_resource_pool:
            previous_count = worker_resource_pool["counter"]
            worker_resource_pool["counter"] = previous_count + 1
            assert worker_resource_pool["counter"] > previous_count
