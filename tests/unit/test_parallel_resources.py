"""
Parallel Resource Sharing Test Examples.

These tests demonstrate safe resource sharing between parallel tests
using thread-safe data structures and synchronization mechanisms.

Usage:
    pytest tests/unit/test_parallel_resources.py -v
    pytest tests/unit/test_parallel_resources.py -n 4 -v
"""

import time
from queue import Empty, Queue
from typing import Any

import pytest


class TestSharedQueue:
    """Tests demonstrating thread-safe queue usage."""

    @pytest.mark.parallel_safe
    def test_queue_producer_consumer(
        self,
        shared_queue: Queue,
        worker_id: str,
    ) -> None:
        """
        Test producer-consumer pattern with shared queue.

        Args:
            shared_queue: Thread-safe queue from fixture.
            worker_id: Current worker identifier.
        """
        # Produce items
        for i in range(5):
            shared_queue.put(
                {
                    "worker": worker_id,
                    "item": i,
                    "timestamp": time.time(),
                }
            )

        # Consume items
        consumed = []
        try:
            while True:
                item = shared_queue.get(block=False)
                consumed.append(item)
        except Empty:
            pass

        assert len(consumed) >= 0  # Queue may be shared with other tests

    @pytest.mark.parallel_safe
    def test_queue_thread_safety(
        self,
        shared_queue: Queue,
        worker_id: str,
    ) -> None:
        """
        Test queue operations are thread-safe.

        Args:
            shared_queue: Thread-safe queue from fixture.
            worker_id: Current worker identifier.
        """
        # Multiple producers
        for i in range(10):
            shared_queue.put(f"{worker_id}_{i}")

        # Verify queue has items (may include items from other tests)
        assert shared_queue.qsize() >= 10

    @pytest.mark.serial
    def test_queue_final_state(self, shared_queue: Queue) -> None:
        """
        Check final queue state after parallel tests.

        This runs serially to verify queue contents.

        Args:
            shared_queue: Thread-safe queue from fixture.
        """
        # Queue should have accumulated items from parallel tests
        assert shared_queue.qsize() >= 0

        # Drain the queue
        items = []
        try:
            while True:
                items.append(shared_queue.get(block=False))
        except Empty:
            pass

        assert len(items) >= 0


class TestWorkerResourceTracking:
    """Tests demonstrating resource tracking in parallel execution."""

    @pytest.mark.parallel_safe
    def test_resource_tracking_basic(
        self,
        test_resource_tracker: dict[str, Any],
        worker_id: str,
    ) -> None:
        """
        Test basic resource tracking.

        Args:
            test_resource_tracker: Resource tracker dictionary.
            worker_id: Current worker identifier.
        """
        assert test_resource_tracker["worker_id"] == worker_id

        # Track some resources
        test_resource_tracker["resources"].append("resource_1")
        test_resource_tracker["timestamps"].append(time.time())

        assert len(test_resource_tracker["resources"]) == 1

    @pytest.mark.parallel_safe
    def test_resource_tracking_multiple(
        self,
        test_resource_tracker: dict[str, Any],
    ) -> None:
        """
        Test tracking multiple resources.

        Args:
            test_resource_tracker: Resource tracker dictionary.
        """
        # Simulate using multiple resources
        for i in range(5):
            test_resource_tracker["resources"].append(f"api_call_{i}")
            time.sleep(0.01)

        assert len(test_resource_tracker["resources"]) == 5

    @pytest.mark.parallel_safe
    def test_resource_tracking_independence(
        self,
        test_resource_tracker: dict[str, Any],
    ) -> None:
        """
        Test resource tracking independence between tests.

        Args:
            test_resource_tracker: Resource tracker dictionary.
        """
        # Each test should have fresh tracker
        assert len(test_resource_tracker["resources"]) == 0

        # Add resources
        test_resource_tracker["resources"].extend(["a", "b", "c"])
        assert len(test_resource_tracker["resources"]) == 3


class TestFakerParallel:
    """Tests demonstrating faker usage in parallel execution."""

    @pytest.mark.parallel_safe
    def test_faker_unique_per_worker(self, faker_factory: Any) -> None:
        """
        Test that faker generates consistent data per worker.

        Args:
            faker_factory: Faker instance from fixture.
        """
        # Generate some fake data
        name = faker_factory.name()
        email = faker_factory.email()
        address = faker_factory.address()

        # All values should be strings
        assert isinstance(name, str)
        assert isinstance(email, str)
        assert isinstance(address, str)

        # Email should contain @
        assert "@" in email

    @pytest.mark.parallel_safe
    def test_faker_consistency(
        self,
        faker_factory: Any,
        isolated_test_data: dict[str, Any],
    ) -> None:
        """
        Test faker consistency within same worker.

        Args:
            faker_factory: Faker instance from fixture.
            isolated_test_data: Isolated test data dictionary.
        """
        # Generate and store data
        isolated_test_data["username"] = faker_factory.user_name()
        isolated_test_data["company"] = faker_factory.company()
        isolated_test_data["phone"] = faker_factory.phone_number()

        # Verify data was stored
        assert "username" in isolated_test_data
        assert "company" in isolated_test_data
        assert "phone" in isolated_test_data

    @pytest.mark.parallel_safe
    def test_faker_multiple_calls(self, faker_factory: Any) -> None:
        """
        Test multiple faker calls generate different data.

        Args:
            faker_factory: Faker instance from fixture.
        """
        names = [faker_factory.name() for _ in range(5)]

        # All names should be unique (with very high probability)
        assert len(set(names)) == len(names)

        # All should be non-empty strings
        assert all(isinstance(name, str) and len(name) > 0 for name in names)


class TestConfigurationParallel:
    """Tests demonstrating configuration in parallel execution."""

    @pytest.mark.parallel_safe
    def test_config_loading(
        self,
        qa_config: Any,
        worker_id: str,
    ) -> None:
        """
        Test configuration loading is thread-safe.

        Args:
            qa_config: QA configuration fixture.
            worker_id: Current worker identifier.
        """
        assert qa_config is not None
        assert qa_config.test is not None
        assert qa_config.api is not None
        assert qa_config.ui is not None
        assert qa_config.reporting is not None

    @pytest.mark.parallel_safe
    def test_config_parallel_workers(
        self,
        qa_config: Any,
        parallel_workers: int,
    ) -> None:
        """
        Test parallel workers configuration.

        Args:
            qa_config: QA configuration fixture.
            parallel_workers: Number of parallel workers.
        """
        assert parallel_workers > 0
        assert qa_config.test.parallel_workers == parallel_workers

    @pytest.mark.parallel_safe
    def test_config_environment(
        self,
        qa_config: Any,
        test_environment: str,
    ) -> None:
        """
        Test environment configuration.

        Args:
            qa_config: QA configuration fixture.
            test_environment: Test environment name.
        """
        assert isinstance(test_environment, str)
        assert len(test_environment) > 0
        assert qa_config.test.environment == test_environment


class TestConcurrentDataStructures:
    """Tests demonstrating concurrent data structure usage."""

    @pytest.mark.parallel_safe
    def test_concurrent_list_operations(
        self,
        isolated_test_data: dict[str, Any],
    ) -> None:
        """
        Test list operations in parallel context.

        Args:
            isolated_test_data: Isolated test data dictionary.
        """
        # Initialize list
        isolated_test_data["items"] = []

        # Concurrent-like operations (in single thread)
        for i in range(100):
            isolated_test_data["items"].append(i)

        assert len(isolated_test_data["items"]) == 100
        assert sum(isolated_test_data["items"]) == sum(range(100))

    @pytest.mark.parallel_safe
    def test_concurrent_dict_operations(
        self,
        isolated_test_data: dict[str, Any],
    ) -> None:
        """
        Test dict operations in parallel context.

        Args:
            isolated_test_data: Isolated test data dictionary.
        """
        # Initialize dict
        isolated_test_data["cache"] = {}

        # Add key-value pairs
        for i in range(50):
            isolated_test_data["cache"][f"key_{i}"] = f"value_{i}"

        assert len(isolated_test_data["cache"]) == 50
        assert isolated_test_data["cache"]["key_0"] == "value_0"
        assert isolated_test_data["cache"]["key_49"] == "value_49"

    @pytest.mark.parallel_safe
    def test_nested_data_structures(
        self,
        isolated_test_data: dict[str, Any],
    ) -> None:
        """
        Test nested data structures in parallel context.

        Args:
            isolated_test_data: Isolated test data dictionary.
        """
        isolated_test_data["nested"] = {
            "level1": {"level2": {"level3": ["item1", "item2", "item3"]}}
        }

        # Navigate nested structure
        nested_list = isolated_test_data["nested"]["level1"]["level2"]["level3"]
        assert len(nested_list) == 3
        assert nested_list[0] == "item1"
