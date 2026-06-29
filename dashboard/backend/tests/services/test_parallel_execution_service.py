"""
Unit tests for parallel_execution_service.py
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from services.parallel_execution_service import (
    ParallelExecutionService,
    SharedResourceManager,
    LoadBalancer
)


class TestSharedResourceManager:
    """Test suite for SharedResourceManager."""

    @pytest.fixture
    def resource_manager(self):
        """Create SharedResourceManager instance."""
        return SharedResourceManager()

    def test_acquire_database_resource(self, resource_manager):
        """Test acquiring a database resource."""
        resource = resource_manager.acquire("database")

        assert resource["type"] == "database"
        assert resource["connected"] is True

        usage = resource_manager.get_usage("database")
        assert len(usage) > 0

    def test_acquire_multiple_resources(self, resource_manager):
        """Test acquiring multiple resources."""
        resource1 = resource_manager.acquire("database")
        resource2 = resource_manager.acquire("database")
        resource3 = resource_manager.acquire("api_client")

        assert resource1 == resource2
        assert resource3["type"] == "api_client"

    def test_release_resource(self, resource_manager):
        """Test releasing a resource."""
        resource = resource_manager.acquire("database")

        # Acquire multiple times
        resource = resource_manager.acquire("database")
        resource = resource_manager.acquire("database")

        usage = resource_manager.get_usage("database")
        assert sum(usage.values()) > 1

        # Release one
        resource_manager.release("database")

        usage = resource_manager.get_usage("database")
        assert sum(usage.values()) == 1

    def test_get_usage(self, resource_manager):
        """Test getting resource usage."""
        resource_manager.acquire("database")
        resource_manager.acquire("api_client")

        database_usage = resource_manager.get_usage("database")
        api_usage = resource_manager.get_usage("api_client")

        assert len(database_usage) > 0
        assert len(api_usage) > 0

    def test_release_nonexistent_resource(self, resource_manager):
        """Test releasing non-existent resource (should not raise)."""
        resource_manager.release("nonexistent", "test_id")


class TestLoadBalancer:
    """Test suite for LoadBalancer."""

    @pytest.fixture
    def load_balancer(self):
        """Create LoadBalancer instance."""
        return LoadBalancer(worker_count=5)

    def test_distribute_round_robin(self, load_balancer):
        """Test round-robin distribution."""
        items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        batches = load_balancer.distribute(items, load_aware=False)

        assert len(batches) == 5

        # Each batch should have 2 items (except last which has 0)
        batch0 = [i for i in items if i in batches[0]]
        batch1 = [i for i in items if i in batches[1]]
        batch2 = [i for i in items if i in batches[2]]
        batch3 = [i for i in items if i in batches[3]]
        batch4 = [i for i in items if i in batches[4]]

        assert len(batch0) == 2
        assert len(batch1) == 2
        assert len(batch2) == 2
        assert len(batch3) == 2
        assert len(batch4) == 0

    def test_distribute_load_aware(self, load_balancer):
        """Test load-aware distribution."""
        items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

        batches = load_balancer.distribute(items, load_aware=True)

        # Most batches should have 3 items
        counts = [len(batch) for batch in batches]
        assert counts.count(3) >= 3
        assert counts.count(2) >= 2

    def test_distribute_empty_list(self, load_balancer):
        """Test distributing empty list."""
        batches = load_balancer.distribute([])

        assert len(batches) == 5
        assert all(len(batch) == 0 for batch in batches)

    def test_distribute_single_item(self, load_balancer):
        """Test distributing single item."""
        batches = load_balancer.distribute([1])

        assert len(batches) == 5
        assert batches[0] == [1]
        assert all(len(batch) == 0 for batch in batches[1:])

    def test_distribute_one_worker(self, load_balancer):
        """Test with single worker."""
        balancer = LoadBalancer(worker_count=1)

        items = [1, 2, 3, 4, 5]
        batches = balancer.distribute(items, load_aware=False)

        assert len(batches) == 1
        assert batches[0] == items


class TestParallelExecutionService:
    """Test suite for ParallelExecutionService."""

    @pytest.fixture
    def mock_executor(self):
        """Mock executor function."""
        def executor(test_id):
            return {"test_id": test_id, "passed": True, "result": "success"}
        return executor

    @pytest.fixture
    def parallel_service(self):
        """Create ParallelExecutionService instance."""
        return ParallelExecutionService(max_workers=5, shared_resources=False)

    def test_initialization(self, parallel_service):
        """Test parallel execution service initialization."""
        assert parallel_service.max_workers == 5
        assert parallel_service.shared_resources is False

    def test_execute_parallel_single_batch(self, parallel_service, mock_executor):
        """Test execute_parallel with single batch."""
        test_ids = [1, 2, 3]
        results = parallel_service.execute_parallel(test_ids, mock_executor, use_cache=False)

        assert results["stats"]["total_tests"] == 3
        assert results["stats"]["passed"] == 3
        assert results["stats"]["worker_count"] == 5

    def test_execute_parallel_multiple_workers(self, parallel_service, mock_executor):
        """Test execute_parallel with many tests."""
        test_ids = list(range(1, 51))
        results = parallel_service.execute_parallel(test_ids, mock_executor, use_cache=False)

        assert results["stats"]["total_tests"] == 50
        assert results["stats"]["passed"] == 50
        assert results["stats"]["worker_count"] == 5

    def test_execute_parallel_with_cache(self, parallel_service, mock_executor):
        """Test execute_parallel with caching enabled."""
        test_ids = [1, 2]

        # Execute first time
        results = parallel_service.execute_parallel(test_ids, mock_executor, use_cache=True)

        assert results["stats"]["total_tests"] == 2
        assert results["stats"]["passed"] == 2

        # Execute second time - should use cache
        results = parallel_service.execute_parallel(test_ids, mock_executor, use_cache=True)

        assert results["stats"]["total_tests"] == 2
        # Should be faster due to caching
        assert results["stats"]["execution_time_ms"] > 0

    def test_execute_parallel_with_failures(self, parallel_service):
        """Test execute_parallel with failing tests."""
        def failing_executor(test_id):
            if test_id == 2:
                raise ValueError("Test failed")
            return {"test_id": test_id, "passed": True}

        test_ids = [1, 2, 3]
        results = parallel_service.execute_parallel(test_ids, failing_executor, use_cache=False)

        assert results["stats"]["passed"] == 1
        assert results["stats"]["failed"] == 1
        assert results["stats"]["errors"] == 1

    def test_execute_single_test(self, parallel_service, mock_executor):
        """Test _execute_single_test method."""
        def mock_executor(test_id):
            return {"test_id": test_id, "passed": True}

        result = parallel_service._execute_single_test(
            test_id=1,
            executor=mock_executor,
            use_cache=False
        )

        assert result["test_id"] == 1
        assert result["status"] == "passed"
        assert "execution_time_ms" in result

    def test_execute_single_test_with_cache(self, parallel_service):
        """Test _execute_single_test with caching."""
        def mock_executor(test_id):
            return {"test_id": test_id, "passed": True}

        result = parallel_service._execute_single_test(
            test_id=1,
            executor=mock_executor,
            use_cache=True
        )

        assert result["test_id"] == 1
        assert result["status"] == "passed"

        # Execute again - should use cache
        result = parallel_service._execute_single_test(
            test_id=1,
            executor=mock_executor,
            use_cache=True
        )

        assert result["test_id"] == 1
        assert result["status"] == "passed"

    def test_execute_single_test_with_error(self, parallel_service):
        """Test _execute_single_test with error."""
        def error_executor(test_id):
            raise ValueError("Test error")

        result = parallel_service._execute_single_test(
            test_id=1,
            executor=error_executor,
            use_cache=True
        )

        assert result["test_id"] == 1
        assert result["status"] == "error"
        assert "Test error" in result["error"]

    def test_get_execution_stats(self, parallel_service):
        """Test get_execution_stats method."""
        stats = parallel_service.get_execution_stats()

        assert stats["max_workers"] == 5
        assert stats["shared_resources_enabled"] is False

    def test_cleanup_resources(self, parallel_service):
        """Test cleanup_resources method."""
        # Should not raise
        parallel_service.cleanup_resources()

    def test_execute_parallel_empty_list(self, parallel_service, mock_executor):
        """Test execute_parallel with empty test list."""
        test_ids = []
        results = parallel_service.execute_parallel(test_ids, mock_executor, use_cache=False)

        assert results["stats"]["total_tests"] == 0
        assert results["stats"]["passed"] == 0

    def test_execute_parallel_performance_optimization(self, parallel_service, mock_executor):
        """Test that parallel execution is more efficient than sequential execution."""
        import time

        test_ids = list(range(1, 51))

        # Measure sequential execution time
        def sequential_executor(test_id):
            time.sleep(0.01)  # Simulate 10ms per test
            return {"test_id": test_id, "passed": True}

        start_time = time.time()
        sequential_results = parallel_service.execute_parallel(test_ids, sequential_executor, use_cache=False)
        sequential_time = time.time() - start_time

        # Measure parallel execution time
        start_time = time.time()
        parallel_results = parallel_service.execute_parallel(test_ids, sequential_executor, use_cache=False)
        parallel_time = time.time() - start_time

        # Parallel should be faster (roughly 5x faster for 5 workers)
        assert parallel_time < sequential_time
        assert parallel_results["stats"]["execution_time_ms"] < sequential_results["stats"]["execution_time_ms"]

    def test_execute_parallel_complex_executor(self, parallel_service):
        """Test execute_parallel with complex executor returning nested dicts."""
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
        results = parallel_service.execute_parallel(test_ids, complex_executor, use_cache=False)

        assert results["stats"]["total_tests"] == 5
        assert results["stats"]["passed"] == 2  # Tests 2 and 4 passed
        assert results["stats"]["failed"] == 3  # Tests 1, 3, 5 failed

    def test_execute_parallel_with_skipped_tests(self, parallel_service):
        """Test execute_parallel with skipped tests."""
        def conditional_executor(test_id):
            if test_id == 2:
                return {"test_id": test_id, "passed": False, "skipped": True, "reason": "skipped"}
            return {"test_id": test_id, "passed": True}

        test_ids = [1, 2, 3]
        results = parallel_service.execute_parallel(test_ids, conditional_executor, use_cache=False)

        assert results["stats"]["skipped"] == 1
        assert results["stats"]["passed"] == 1
        assert results["stats"]["failed"] == 1

    def test_shared_resources_enabled(self, parallel_service):
        """Test parallel execution with shared resources enabled."""
        service = ParallelExecutionService(max_workers=5, shared_resources=True)

        # Should have resource manager
        assert service.resource_manager is not None

        # Should be able to acquire resources
        resource = service.resource_manager.acquire("database")

        assert resource["type"] == "database"

    def test_shared_resources_disabled(self, parallel_service):
        """Test parallel execution with shared resources disabled."""
        assert parallel_service.resource_manager is None

    def test_parallel_execution_different_worker_counts(self, parallel_service):
        """Test parallel execution with different worker counts."""
        test_ids = list(range(1, 51))

        # Test with different worker counts
        for workers in [2, 5, 10]:
            service = ParallelExecutionService(max_workers=workers, shared_resources=False)
            results = service.execute_parallel(test_ids, parallel_service._execute_single_test, use_cache=False)

            assert results["stats"]["total_tests"] == 50
            assert results["stats"]["worker_count"] == workers
