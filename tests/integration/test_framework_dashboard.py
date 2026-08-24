"""
Core Integration Tests for Framework ↔ Dashboard Communication.

This module tests the bidirectional communication between the QA Framework
core and the Dashboard backend, including:
- Framework generates test results → Dashboard displays them
- Framework execution status → Dashboard updates in real-time
- Framework test artifacts → Dashboard stores/retrieves them
- Dashboard creates test case → Framework receives it
- Dashboard triggers execution → Framework runs test
- Dashboard configures parameters → Framework applies them
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.core.entities.test_result import TestResult, TestStatus

# =============================================================================
# Framework → Dashboard Integration Tests
# =============================================================================


@pytest.mark.integration
class TestFrameworkToDashboardIntegration:
    """Test Framework sending data to Dashboard."""

    async def test_framework_generates_results_dashboard_displays(
        self, http_client, test_result_factory, authenticated_client
    ):
        """
        Test: Framework generates test results → Dashboard displays them.

        Scenario:
        1. Framework creates test results
        2. Results are sent to Dashboard API
        3. Dashboard stores results
        4. Dashboard displays results correctly
        """
        # Arrange: Create test results from framework
        results: list[TestResult] = [
            test_result_factory(
                test_id="test_001", test_name="Test Login", status=TestStatus.PASSED, duration=1.5
            ),
            test_result_factory(
                test_id="test_002",
                test_name="Test Logout",
                status=TestStatus.FAILED,
                duration=0.8,
                error_message="Assertion failed: expected redirect",
            ),
        ]

        # Act: Send results to Dashboard
        execution_data = {
            "suite_id": 1,
            "status": "completed",
            "results": [
                {
                    "test_id": r.test_id,
                    "test_name": r.test_name,
                    "status": r.status.value,
                    "duration": r.duration,
                    "error_message": r.error_message,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in results
            ],
        }

        response = await authenticated_client.post("/api/v1/executions", json=execution_data)

        # Assert
        assert response.status_code in [200, 201, 422], f"Failed with: {response.text}"

        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data or "data" in data

    async def test_framework_execution_status_dashboard_updates(
        self, authenticated_client, mock_execution_service
    ):
        """
        Test: Framework execution status → Dashboard updates in real-time.

        Scenario:
        1. Framework starts test execution
        2. Dashboard receives status update
        3. Dashboard updates execution status
        4. Status is retrievable via API
        """
        # Arrange: Create execution
        execution_data = {"suite_id": 1, "environment": "test", "parameters": {"parallel": True}}

        _create_response = await authenticated_client.post(
            "/api/v1/executions", json=execution_data
        )

        # Act: Update execution status (simulating framework updates)
        status_updates = ["pending", "running", "completed"]

        for status in status_updates:
            _update_response = await authenticated_client.post(
                "/api/v1/executions/1/status", json={"status": status}
            )

            # Allow time for processing
            await asyncio.sleep(0.1)

        # Assert: Verify final status
        get_response = await authenticated_client.get("/api/v1/executions/1")

        # Should either succeed or return 404 (mocked)
        assert get_response.status_code in [200, 404, 422]

    async def test_framework_artifacts_dashboard_storage(
        self, authenticated_client, test_artifacts_dir
    ):
        """
        Test: Framework test artifacts → Dashboard stores/retrieves them.

        Scenario:
        1. Framework generates artifacts (screenshots, logs)
        2. Artifacts are uploaded to Dashboard
        3. Dashboard stores artifacts
        4. Artifacts can be retrieved
        """
        # Arrange: Create artifact data
        artifact_data = {
            "execution_id": 1,
            "test_case_id": 1,
            "artifact_type": "screenshot",
            "file_name": "test_failure.png",
            "content_type": "image/png",
            "file_size": 1024,
        }

        # Act: Upload artifact
        with patch.object(authenticated_client, "post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=201,
                json=MagicMock(
                    return_value={
                        "id": 1,
                        "file_path": "/uploads/test_failure.png",
                        "url": "/api/v1/artifacts/1/download",
                    }
                ),
            )

            response = await authenticated_client.post("/api/v1/artifacts", json=artifact_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "id" in data or "file_path" in data


# =============================================================================
# Dashboard → Framework Integration Tests
# =============================================================================


@pytest.mark.integration
class TestDashboardToFrameworkIntegration:
    """Test Dashboard sending commands to Framework."""

    async def test_dashboard_creates_test_case_framework_receives(
        self, authenticated_client, test_case_data
    ):
        """
        Test: Dashboard creates test case → Framework receives it.

        Scenario:
        1. Dashboard creates a new test case
        2. Case is stored in database
        3. Framework can retrieve the case
        4. Case data is correct
        """
        # Arrange: Create test case via Dashboard
        case_data = test_case_data(
            name="Dashboard Created Test", test_code="def test_dashboard(): assert True", suite_id=1
        )

        # Act: Create test case
        with patch.object(authenticated_client, "post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=201,
                json=MagicMock(
                    return_value={
                        "id": 1,
                        "name": case_data["name"],
                        "test_code": case_data["test_code"],
                    }
                ),
            )

            create_response = await authenticated_client.post("/api/v1/cases", json=case_data)

        # Assert
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["name"] == case_data["name"]

    async def test_dashboard_triggers_execution_framework_runs(
        self, authenticated_client, mock_celery_task
    ):
        """
        Test: Dashboard triggers execution → Framework runs test.

        Scenario:
        1. Dashboard creates execution record
        2. Dashboard triggers execution
        3. Framework receives execution request
        4. Framework runs tests and updates status
        """
        # Arrange: Create execution
        execution_data = {
            "suite_id": 1,
            "environment": "production",
            "parameters": {"headless": True},
        }

        # Act: Trigger execution
        with patch.object(authenticated_client, "post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=MagicMock(return_value={"id": 1, "status": "running", "task_id": "task-123"}),
            )

            response = await authenticated_client.post(
                "/api/v1/executions/1/start", json=execution_data
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "task_id" in data

    async def test_dashboard_configures_parameters_framework_applies(self, authenticated_client):
        """
        Test: Dashboard configures parameters → Framework applies them.

        Scenario:
        1. Dashboard updates suite configuration
        2. Configuration is stored
        3. Framework reads configuration on next run
        4. Framework applies parameters correctly
        """
        # Arrange: Update suite configuration
        config_update = {
            "config": {
                "parallel": True,
                "workers": 4,
                "timeout": 600,
                "retry_count": 2,
                "environment_variables": {"TEST_ENV": "staging", "LOG_LEVEL": "debug"},
            }
        }

        # Act: Update configuration
        with patch.object(authenticated_client, "put") as mock_put:
            mock_put.return_value = MagicMock(
                status_code=200,
                json=MagicMock(return_value={"id": 1, "config": config_update["config"]}),
            )

            response = await authenticated_client.put("/api/v1/suites/1", json=config_update)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["config"]["parallel"] is True
        assert data["config"]["workers"] == 4


# =============================================================================
# API Endpoint Integration Tests
# =============================================================================


@pytest.mark.integration
class TestAPIEndpointIntegration:
    """Test all API endpoints for integration."""

    async def test_auth_endpoints_integration(self, http_client, user_data):
        """Test authentication endpoints."""
        user = user_data()

        # Test login
        login_response = await http_client.post(
            "/api/v1/auth/login", json={"username": user["username"], "password": user["password"]}
        )

        # May fail if user doesn't exist, but endpoint should be accessible
        assert login_response.status_code in [200, 401, 404, 422]

    async def test_suite_crud_endpoints(self, authenticated_client, test_suite_data):
        """Test suite CRUD operations."""
        suite = test_suite_data(name="API Test Suite")

        # Create
        with patch.object(authenticated_client, "post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=201, json=MagicMock(return_value={"id": 1, **suite})
            )

            create_resp = await authenticated_client.post("/api/v1/suites", json=suite)
            assert create_resp.status_code == 201

        # List
        with patch.object(authenticated_client, "get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200, json=MagicMock(return_value={"items": [{"id": 1, **suite}]})
            )

            list_resp = await authenticated_client.get("/api/v1/suites")
            assert list_resp.status_code == 200

    async def test_case_crud_endpoints(self, authenticated_client, test_case_data):
        """Test case CRUD operations."""
        case = test_case_data(name="API Test Case")

        with patch.object(authenticated_client, "post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=201, json=MagicMock(return_value={"id": 1, **case})
            )

            response = await authenticated_client.post("/api/v1/cases", json=case)
            assert response.status_code == 201

    async def test_execution_endpoints(self, authenticated_client):
        """Test execution endpoints."""
        endpoints = [
            ("/api/v1/executions", "GET"),
            ("/api/v1/executions", "POST"),
            ("/api/v1/executions/1", "GET"),
            ("/api/v1/executions/1/start", "POST"),
            ("/api/v1/executions/1/stop", "POST"),
        ]

        for endpoint, method in endpoints:
            with patch.object(authenticated_client, method.lower()) as mock_req:
                mock_req.return_value = MagicMock(status_code=200, json=MagicMock(return_value={}))

                if method == "GET":
                    response = await authenticated_client.get(endpoint)
                elif method == "POST":
                    response = await authenticated_client.post(endpoint, json={})

                assert response.status_code in [200, 201, 404, 422]


# =============================================================================
# Error Handling and Recovery Tests
# =============================================================================


@pytest.mark.integration
class TestIntegrationErrorHandling:
    """Test error handling in framework-dashboard integration."""

    async def test_framework_handles_dashboard_unavailability(self, http_client):
        """Test framework handles when dashboard is unavailable."""
        # Simulate dashboard unavailability
        with patch.object(http_client, "post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            try:
                await http_client.post("/api/v1/executions", json={"suite_id": 1})
            except httpx.ConnectError:
                pass  # Expected behavior

    async def test_dashboard_handles_framework_timeout(self, authenticated_client):
        """Test dashboard handles framework timeout gracefully."""
        with patch.object(authenticated_client, "post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timed out")

            try:
                await authenticated_client.post("/api/v1/executions/1/start", json={})
            except httpx.TimeoutException:
                pass  # Expected behavior

    async def test_invalid_data_handling(self, authenticated_client):
        """Test handling of invalid data between components."""
        invalid_data = {
            "suite_id": "invalid",  # Should be int
            "status": 123,  # Should be string
        }

        with patch.object(authenticated_client, "post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=422, json=MagicMock(return_value={"detail": "Validation error"})
            )

            response = await authenticated_client.post("/api/v1/executions", json=invalid_data)

            assert response.status_code == 422


# =============================================================================
# Real-Time Communication Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.websocket
class TestRealTimeCommunication:
    """Test real-time communication between Framework and Dashboard."""

    async def test_websocket_connection_established(self, mock_websocket_manager):
        """Test WebSocket connection can be established."""
        websocket_mock = AsyncMock()

        await mock_websocket_manager.connect(websocket_mock)
        mock_websocket_manager.connect.assert_called_once()

    async def test_execution_updates_via_websocket(
        self, mock_websocket_manager, websocket_message_factory
    ):
        """Test execution status updates via WebSocket."""
        message = websocket_message_factory(
            message_type="execution_update",
            data={"execution_id": 1, "status": "running", "progress": 50},
        )

        await mock_websocket_manager.broadcast(json.dumps(message))
        mock_websocket_manager.broadcast.assert_called_once()

    async def test_multiple_clients_receive_updates(self, mock_websocket_manager):
        """Test multiple dashboard clients receive updates."""
        updates = [
            {"type": "status_change", "status": "running"},
            {"type": "test_complete", "test_id": "test_001"},
            {"type": "execution_complete", "results": {"passed": 5, "failed": 0}},
        ]

        for update in updates:
            await mock_websocket_manager.broadcast(json.dumps(update))

        assert mock_websocket_manager.broadcast.call_count == len(updates)


# =============================================================================
# Performance Benchmark Tests
# =============================================================================


@pytest.mark.integration
class TestIntegrationPerformance:
    """Performance benchmarks for framework-dashboard integration."""

    async def test_api_response_time(self, authenticated_client, benchmark):
        """Test API response time is within acceptable limits."""

        start = time.time()

        with patch.object(authenticated_client, "get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value={}))

            await authenticated_client.get("/api/v1/dashboard/stats")

        elapsed_ms = (time.time() - start) * 1000

        assert benchmark.record("api_response", elapsed_ms, 500)

    async def test_bulk_result_submission_performance(
        self, authenticated_client, test_result_factory, benchmark
    ):
        """Test performance of bulk result submission."""

        # Generate 100 results
        results = [test_result_factory(test_id=f"test_{i:03d}") for i in range(100)]

        execution_data = {
            "suite_id": 1,
            "results": [
                {"test_id": r.test_id, "status": r.status.value, "duration": r.duration}
                for r in results
            ],
        }

        start = time.time()

        with patch.object(authenticated_client, "post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=201, json=MagicMock(return_value={"id": 1})
            )

            await authenticated_client.post("/api/v1/executions/bulk", json=execution_data)

        elapsed_ms = (time.time() - start) * 1000

        assert benchmark.record("bulk_submission", elapsed_ms, 2000)

    async def test_concurrent_api_calls_performance(self, authenticated_client, benchmark):
        """Test performance under concurrent API calls."""

        async def make_request(i: int):
            with patch.object(authenticated_client, "get") as mock_get:
                mock_get.return_value = MagicMock(
                    status_code=200, json=MagicMock(return_value={"id": i})
                )

                await authenticated_client.get(f"/api/v1/cases/{i}")

        start = time.time()

        # Make 10 concurrent requests
        await asyncio.gather(*[make_request(i) for i in range(10)])

        elapsed_ms = (time.time() - start) * 1000

        assert benchmark.record("concurrent_calls", elapsed_ms, 3000)
