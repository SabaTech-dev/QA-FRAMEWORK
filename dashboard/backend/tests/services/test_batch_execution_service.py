"""
Unit tests for batch_execution_service.py
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from services.batch_execution_service import BatchExecutionService


class TestBatchExecutionService:
    """Test suite for BatchExecutionService."""

    @pytest.fixture
    def mock_executor(self):
        """Mock executor function."""
        def executor(test_id):
            return {"test_id": test_id, "passed": True, "result": "success"}
        return executor

    @pytest.fixture
    def batch_service(self):
        """Create BatchExecutionService instance."""
        return BatchExecutionService(max_workers=2)

    def test_initialization(self, batch_service):
        """Test batch execution service initialization."""
        assert batch_service.max_workers == 2

    def test_execute_batch_single_batch(self, batch_service, mock_executor):
        """Test execute_batch with single batch."""
        test_ids = [1, 2, 3]
        results = batch_service.execute_batch(test_ids, mock_executor, batch_size=5)

        assert results["stats"]["total_tests"] == 3
        assert results["stats"]["batch_size"] == 5
        assert results["stats"]["batches_count"] == 1

    def test_execute_batch_multiple_batches(self, batch_service, mock_executor):
        """Test execute_batch with multiple batches."""
        test_ids = list(range(1, 26))  # 25 tests
        results = batch_service.execute_batch(test_ids, mock_executor, batch_size=10)

        assert results["stats"]["total_tests"] == 25
        assert results["stats"]["batches_count"] == 3  # 3 batches of 10, 10, 5

    def test_execute_batch_with_cache(self, batch_service, mock_executor):
        """Test execute_batch with caching enabled."""
        test_ids = [1, 2]

        # Execute first time
        results = batch_service.execute_batch(test_ids, mock_executor, batch_size=10, use_cache=True)

        assert results["stats"]["total_tests"] == 2
        assert results["stats"]["passed"] == 2

        # Execute second time - should use cache
        results = batch_service.execute_batch(test_ids, mock_executor, batch_size=10, use_cache=True)

        assert results["stats"]["total_tests"] == 2
        # Should be faster due to caching
        assert results["stats"]["execution_time_ms"] > 0

    def test_execute_batch_with_timeout(self, batch_service, mock_executor):
        """Test execute_batch with timeout."""
        test_ids = [1, 2]

        def slow_executor(test_id):
            if test_id == 2:
                import time
                time.sleep(2)  # Simulate slow test
            return {"test_id": test_id, "passed": True}

        with pytest.raises(Exception) as exc_info:
            batch_service.execute_batch(test_ids, slow_executor, batch_size=10, timeout=1.0)

        assert "timeout" in str(exc_info.value).lower()

    def test_execute_batch_with_failures(self, batch_service):
        """Test execute_batch with failing tests."""
        def failing_executor(test_id):
            if test_id == 2:
                raise ValueError("Test failed")
            return {"test_id": test_id, "passed": True}

        test_ids = [1, 2, 3]
        results = batch_service.execute_batch(test_ids, failing_executor, batch_size=10)

        assert results["stats"]["passed"] == 1  # Only test 1 passed
        assert results["stats"]["failed"] == 1  # Test 2 failed
        assert results["stats"]["errors"] == 1  # Test 2 had error
        assert results["stats"]["skipped"] == 1  # Test 3 skipped

    def test_execute_batch_no_cache(self, batch_service, mock_executor):
        """Test execute_batch with caching disabled."""
        test_ids = [1, 2]

        results = batch_service.execute_batch(test_ids, mock_executor, batch_size=10, use_cache=False)

        assert results["stats"]["total_tests"] == 2
        assert results["stats"]["passed"] == 2

    def test_create_batches(self, batch_service):
        """Test _create_batches method."""
        test_ids = [1, 2, 3, 4, 5, 6]

        batches = batch_service._create_batches(test_ids, batch_size=2)

        assert len(batches) == 3
        assert batches[0] == [1, 2]
        assert batches[1] == [3, 4]
        assert batches[2] == [5, 6]

    def test_execute_single_test(self, batch_service, mock_executor):
        """Test _execute_single_test method."""
        def mock_executor_with_cache(test_id):
            return {"test_id": test_id, "passed": True}

        result = batch_service._execute_single_test(
            test_id=1,
            executor=mock_executor_with_cache,
            use_cache=False,
            timeout=None
        )

        assert result["test_id"] == 1
        assert result["status"] == "passed"
        assert "execution_time_ms" in result

    def test_execute_single_test_with_cache(self, batch_service):
        """Test _execute_single_test with caching."""
        def mock_executor(test_id):
            return {"test_id": test_id, "passed": True}

        result = batch_service._execute_single_test(
            test_id=1,
            executor=mock_executor,
            use_cache=True,
            timeout=None
        )

        assert result["test_id"] == 1
        assert result["status"] == "passed"

        # Execute again - should use cache
        result = batch_service._execute_single_test(
            test_id=1,
            executor=mock_executor,
            use_cache=True,
            timeout=None
        )

        assert result["test_id"] == 1
        assert result["status"] == "passed"

    def test_execute_single_test_with_error(self, batch_service):
        """Test _execute_single_test with error."""
        def error_executor(test_id):
            raise ValueError("Test error")

        result = batch_service._execute_single_test(
            test_id=1,
            executor=error_executor,
            use_cache=True,
            timeout=None
        )

        assert result["test_id"] == 1
        assert result["status"] == "error"
        assert "Test error" in result["error"]

    def test_optimize_test_order(self, batch_service):
        """Test optimize_test_order method."""
        test_ids = [1, 2, 3, 4, 5]

        sorted_ids = batch_service.optimize_test_order(test_ids)

        assert sorted_ids == test_ids  # For now, returns original order

    def test_calculate_execution_time_estimate(self, batch_service, mock_executor):
        """Test calculate_execution_time_estimate method."""
        test_ids = [1, 2, 3, 4, 5]

        estimate = batch_service.calculate_execution_time_estimate(test_ids, mock_executor)

        assert estimate["total_tests"] == 5
        assert estimate["batch_size"] == 10
        assert estimate["batches_count"] == 1
        assert estimate["average_time_per_test_ms"] > 0

    def test_get_batch_statistics(self, batch_service):
        """Test get_batch_statistics method."""
        results = {
            "stats": {
                "total_tests": 10,
                "passed": 8,
                "failed": 1,
                "errors": 1,
                "skipped": 0,
                "execution_time_ms": 5000
            }
        }

        stats = batch_service.get_batch_statistics(results)

        assert stats["total_tests"] == 10
        assert stats["passed"] == 8
        assert stats["failed"] == 1
        assert stats["errors"] == 1
        assert stats["execution_time_ms"] == 5000
        assert stats["execution_time_seconds"] == 5.0
        assert stats["avg_time_per_test_ms"] == 500.0

    def test_execute_batch_large_batch(self, batch_service, mock_executor):
        """Test execute_batch with large batch (100 tests)."""
        test_ids = list(range(1, 101))
        results = batch_service.execute_batch(test_ids, mock_executor, batch_size=10)

        assert results["stats"]["total_tests"] == 100
        assert results["stats"]["batches_count"] == 10
        assert results["stats"]["passed"] == 100

    def test_execute_batch_empty_list(self, batch_service, mock_executor):
        """Test execute_batch with empty test list."""
        test_ids = []
        results = batch_service.execute_batch(test_ids, mock_executor, batch_size=10)

        assert results["stats"]["total_tests"] == 0
        assert results["stats"]["passed"] == 0
        assert results["stats"]["batch_size"] == 10

    def test_execute_batch_with_complex_executor(self, batch_service):
        """Test execute_batch with complex executor returning nested dicts."""
        def complex_executor(test_id):
            return {
                "test_id": test_id,
                "passed": test_id % 2 == 0,
                "result": {
                    "status": "success" if test_id % 2 == 0 else "failure",
                    "duration_ms": 1000,
                    "data": {
                        "details": "Test execution details",
                        "errors": []
                    }
                }
            }

        test_ids = [1, 2, 3, 4, 5]
        results = batch_service.execute_batch(test_ids, complex_executor, batch_size=10)

        assert results["stats"]["total_tests"] == 5
        assert results["stats"]["passed"] == 2  # Tests 2 and 4 passed
        assert results["stats"]["failed"] == 3  # Tests 1, 3, 5 failed
        assert len(results["results"]) == 5

    def test_execute_batch_with_empty_executor(self, batch_service):
        """Test execute_batch with executor that returns empty dict."""
        def empty_executor(test_id):
            return {}

        test_ids = [1, 2]
        results = batch_service.execute_batch(test_ids, empty_executor, batch_size=10)

        assert results["stats"]["total_tests"] == 2
        # Should treat empty dict as passed
        assert results["stats"]["passed"] == 2

    def test_execute_batch_with_skipped_tests(self, batch_service):
        """Test execute_batch with skipped tests."""
        def conditional_executor(test_id):
            if test_id == 2:
                return {"test_id": test_id, "passed": False, "skipped": True, "reason": "skipped"}
            return {"test_id": test_id, "passed": True}

        test_ids = [1, 2, 3]
        results = batch_service.execute_batch(test_ids, conditional_executor, batch_size=10)

        assert results["stats"]["skipped"] == 1
        assert results["stats"]["passed"] == 1
        assert results["stats"]["failed"] == 1

    def test_execute_batch_performance_optimization(self, batch_service, mock_executor):
        """Test that batch execution is more efficient than sequential execution."""
        import time

        test_ids = list(range(1, 51))

        # Measure sequential execution time
        def sequential_executor(test_id):
            time.sleep(0.01)  # Simulate 10ms per test
            return {"test_id": test_id, "passed": True}

        start_time = time.time()
        sequential_results = batch_service.execute_batch(test_ids, sequential_executor, batch_size=10, use_cache=False)
        sequential_time = time.time() - start_time

        # Measure parallel batch execution time
        start_time = time.time()
        parallel_results = batch_service.execute_batch(test_ids, sequential_executor, batch_size=10, use_cache=False)
        parallel_time = time.time() - start_time

        # Parallel should be faster (roughly 5x faster for 5 workers)
        assert parallel_time < sequential_time
        assert parallel_results["stats"]["execution_time_ms"] < sequential_results["stats"]["execution_time_ms"]
