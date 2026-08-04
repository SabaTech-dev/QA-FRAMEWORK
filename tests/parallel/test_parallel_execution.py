"""
Parallel Execution Tests for QA-FRAMEWORK

This module demonstrates parallel test execution with pytest-xdist.

NOTE: Every test here performs live HTTP requests against the public
``jsonplaceholder.typicode.com`` sandbox. Those requests are (a) blocked by the
framework SSRF URL allowlist in hardened environments and (b) inherently flaky
because they depend on a third-party service. They are therefore gated behind
the ``RUN_NETWORK_TESTS=1`` environment variable so the default suite (and CI)
stays green and hermetic. Run them locally with:

    RUN_NETWORK_TESTS=1 pytest tests/parallel -v
"""

import asyncio
import os
import time

import pytest

from src.adapters.http.httpx_client import HTTPXClient

# Gate all network-dependent tests behind an explicit opt-in. Default: skip.
# Reason: third-party sandbox host is not in the SSRF allowlist and external
# network must not be a hard dependency of the test suite.
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_NETWORK_TESTS", "0") != "1",
    reason="Live network test — set RUN_NETWORK_TESTS=1 to enable (requires "
    "jsonplaceholder.typicode.com reachable and allowlisted).",
)


@pytest.fixture
def worker_id(request):
    """Get worker ID for parallel execution."""
    if hasattr(request.config, "workerinput"):
        return request.config.workerinput["workerid"]
    return "master"


class TestParallelAPI:
    """API tests designed for parallel execution."""

    @pytest.mark.api
    @pytest.mark.parallel_safe
    @pytest.mark.asyncio
    async def test_parallel_get_users_a(self, worker_id):
        """Test 1: Get users - safe for parallel execution."""
        client = HTTPXClient(base_url="https://jsonplaceholder.typicode.com")
        response = await client.get("/users")

        assert response.status_code == 200
        assert len(response.json()) == 10

        print(f"[Worker {worker_id}] Test 1 passed: Users retrieved")

    @pytest.mark.api
    @pytest.mark.parallel_safe
    @pytest.mark.asyncio
    async def test_parallel_get_users_b(self, worker_id):
        """Test 2: Get users again - safe for parallel execution."""
        client = HTTPXClient(base_url="https://jsonplaceholder.typicode.com")
        response = await client.get("/users")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

        # worker_id from fixture
        print(f"[Worker {worker_id}] Test 2 passed: Users validated")

    @pytest.mark.api
    @pytest.mark.parallel_safe
    @pytest.mark.asyncio
    async def test_parallel_get_posts_a(self, worker_id):
        """Test 3: Get posts - safe for parallel execution."""
        client = HTTPXClient(base_url="https://jsonplaceholder.typicode.com")
        response = await client.get("/posts")

        assert response.status_code == 200
        assert len(response.json()) > 0

        # worker_id from fixture
        print(f"[Worker {worker_id}] Test 3 passed: Posts retrieved")

    @pytest.mark.api
    @pytest.mark.parallel_safe
    @pytest.mark.asyncio
    async def test_parallel_get_posts_b(self, worker_id):
        """Test 4: Get posts again - safe for parallel execution."""
        client = HTTPXClient(base_url="https://jsonplaceholder.typicode.com")
        response = await client.get("/posts")

        assert response.status_code == 200
        assert len(response.json()) == 100

        # worker_id from fixture
        print(f"[Worker {worker_id}] Test 4 passed: Posts validated")

    @pytest.mark.api
    @pytest.mark.parallel_safe
    @pytest.mark.asyncio
    async def test_parallel_create_post_a(self, worker_id):
        """Test 5: Create post - safe for parallel execution."""
        client = HTTPXClient(base_url="https://jsonplaceholder.typicode.com")

        post_data = {"title": f"Parallel Test {time.time()}", "body": "Test body", "userId": 1}

        response = await client.post("/posts", data=post_data)

        assert response.status_code == 201
        assert "id" in response.json()

        # worker_id from fixture
        print(f"[Worker {worker_id}] Test 5 passed: Post created")

    @pytest.mark.api
    @pytest.mark.parallel_safe
    @pytest.mark.asyncio
    async def test_parallel_create_post_b(self, worker_id):
        """Test 6: Create another post - safe for parallel execution."""
        client = HTTPXClient(base_url="https://jsonplaceholder.typicode.com")

        post_data = {
            "title": f"Parallel Test {time.time()}",
            "body": "Another test body",
            "userId": 2,
        }

        response = await client.post("/posts", data=post_data)

        assert response.status_code == 201
        assert "id" in response.json()

        # worker_id from fixture
        print(f"[Worker {worker_id}] Test 6 passed: Another post created")

    @pytest.mark.api
    @pytest.mark.parallel_safe
    @pytest.mark.asyncio
    async def test_parallel_get_user(self, worker_id):
        """Test 7: Get specific user - safe for parallel execution."""
        client = HTTPXClient(base_url="https://jsonplaceholder.typicode.com")
        response = await client.get("/users/1")

        assert response.status_code == 200
        assert response.json()["id"] == 1
        assert response.json()["name"] == "Leanne Graham"

        # worker_id from fixture
        print(f"[Worker {worker_id}] Test 7 passed: User retrieved")


@pytest.mark.serial
class TestSequentialTests:
    """Tests that must run in sequence - not parallel."""

    order = []

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_sequential_step1(self, worker_id):
        """Step 1: Must run first."""
        client = HTTPXClient(base_url="https://jsonplaceholder.typicode.com")
        response = await client.get("/users")

        assert response.status_code == 200
        TestSequentialTests.order.append(1)

        # worker_id from fixture
        print(f"[Worker {worker_id}] Sequential test 1 completed")

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_sequential_step2(self, worker_id):
        """Step 2: Must run after step 1."""
        assert 1 in TestSequentialTests.order, "Step 1 must run first"

        client = HTTPXClient(base_url="https://jsonplaceholder.typicode.com")
        response = await client.get("/posts")

        assert response.status_code == 200
        TestSequentialTests.order.append(2)

        # worker_id from fixture
        print(f"[Worker {worker_id}] Sequential test 2 completed")

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_sequential_step3(self, worker_id):
        """Step 3: Must run after steps 1 and 2."""
        assert (
            1 in TestSequentialTests.order and 2 in TestSequentialTests.order
        ), "Steps 1 and 2 must run first"

        client = HTTPXClient(base_url="https://jsonplaceholder.typicode.com")
        response = await client.get("/comments")

        assert response.status_code == 200
        TestSequentialTests.order.append(3)

        # worker_id from fixture
        print(f"[Worker {worker_id}] Sequential test 3 completed")


class TestPerformanceMeasurement:
    """Tests with performance measurement."""

    @pytest.mark.api
    @pytest.mark.parallel_safe
    @pytest.mark.asyncio
    async def test_performance_get_users(self, worker_id):
        """Measure performance of API calls."""
        start_time = time.time()

        client = HTTPXClient(base_url="https://jsonplaceholder.typicode.com")
        response = await client.get("/users")

        end_time = time.time()
        elapsed = end_time - start_time

        assert response.status_code == 200
        assert elapsed < 5.0, "API call should complete in under 5 seconds"

        # worker_id from fixture
        print(f"[Worker {worker_id}] Performance test passed: {elapsed:.2f}s")

    @pytest.mark.api
    @pytest.mark.parallel_safe
    @pytest.mark.asyncio
    async def test_performance_batch_requests(self, worker_id):
        """Measure performance of batch requests."""
        start_time = time.time()

        client = HTTPXClient(base_url="https://jsonplaceholder.typicode.com")

        # Make 5 parallel requests
        tasks = [client.get(f"/posts/{i}") for i in range(1, 6)]

        await asyncio.gather(*tasks)

        end_time = time.time()
        elapsed = end_time - start_time

        assert elapsed < 10.0, "Batch requests should complete in under 10 seconds"

        # worker_id from fixture
        print(f"[Worker {worker_id}] Batch performance test passed: {elapsed:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "api"])
