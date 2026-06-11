"""
Locust Performance Tests for QA-FRAMEWORK Dashboard

This module implements comprehensive performance testing scenarios including:
- Load testing with various user behaviors
- Stress testing to find breaking points
- Spike testing for sudden traffic increases
- Soak testing for endurance validation

Test Scenarios:
1. Auth flow (login, token refresh)
2. Suite CRUD operations
3. Case CRUD operations
4. Execution workflows
5. Dashboard stats retrieval
6. Concurrent user simulations
"""

import json
import random
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

from locust import HttpUser, task, between, events
from locust.runners import MasterRunner

from config import config, ENDPOINTS, TEST_DATA, TASK_WEIGHTS, PerformanceThresholds


# Global storage for test data
class TestDataStore:
    """Shared storage for test data across users"""

    suite_ids: List[int] = []
    case_ids: List[int] = []
    execution_ids: List[int] = []
    user_ids: List[int] = []
    auth_tokens: Dict[str, str] = {}


# Performance metrics tracking
class MetricsCollector:
    """Collect and track performance metrics"""

    response_times: Dict[str, List[float]] = {}
    error_counts: Dict[str, int] = {}
    request_counts: Dict[str, int] = {}

    @classmethod
    def record_response(cls, endpoint: str, response_time: float, success: bool):
        """Record a response metric"""
        if endpoint not in cls.response_times:
            cls.response_times[endpoint] = []
            cls.error_counts[endpoint] = 0
            cls.request_counts[endpoint] = 0

        cls.response_times[endpoint].append(response_time)
        cls.request_counts[endpoint] += 1
        if not success:
            cls.error_counts[endpoint] += 1

    @classmethod
    def get_statistics(cls) -> Dict[str, Any]:
        """Get collected statistics"""
        stats = {}
        for endpoint, times in cls.response_times.items():
            if times:
                sorted_times = sorted(times)
                count = len(sorted_times)
                stats[endpoint] = {
                    "count": count,
                    "avg_ms": round(sum(sorted_times) / count * 1000, 2),
                    "p50_ms": round(sorted_times[int(count * 0.5)] * 1000, 2),
                    "p95_ms": round(sorted_times[int(count * 0.95)] * 1000, 2),
                    "p99_ms": round(sorted_times[int(count * 0.99)] * 1000, 2),
                    "min_ms": round(min(sorted_times) * 1000, 2),
                    "max_ms": round(max(sorted_times) * 1000, 2),
                    "errors": cls.error_counts.get(endpoint, 0),
                    "error_rate": round(
                        cls.error_counts.get(endpoint, 0) / count * 100, 2
                    )
                    if count > 0
                    else 0,
                }
        return stats


# Locust events for setup and teardown
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts"""
    print(f"\n{'=' * 60}")
    print(f"QA-FRAMEWORK Performance Test Starting")
    print(f"Environment: {config.environment.value}")
    print(f"Base URL: {config.base_url}")
    print(f"{'=' * 60}\n")

    # Reset metrics
    MetricsCollector.response_times.clear()
    MetricsCollector.error_counts.clear()
    MetricsCollector.request_counts.clear()


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops"""
    print(f"\n{'=' * 60}")
    print(f"QA-FRAMEWORK Performance Test Completed")
    print(f"{'=' * 60}\n")

    # Print statistics
    stats = MetricsCollector.get_statistics()
    print("\nPerformance Statistics:")
    print("-" * 80)
    for endpoint, data in stats.items():
        print(f"\n{endpoint}:")
        print(f"  Requests: {data['count']}")
        print(f"  Avg: {data['avg_ms']}ms")
        print(f"  P50: {data['p50_ms']}ms")
        print(f"  P95: {data['p95_ms']}ms")
        print(f"  P99: {data['p99_ms']}ms")
        print(f"  Errors: {data['errors']} ({data['error_rate']}%)")

    # Check against thresholds
    thresholds = PerformanceThresholds()
    print("\n\nThreshold Analysis:")
    print("-" * 80)
    violations = []

    for endpoint, data in stats.items():
        if data["p95_ms"] > thresholds.p95_max:
            violations.append(
                f"{endpoint}: P95 {data['p95_ms']}ms > {thresholds.p95_max}ms"
            )
        if data["p99_ms"] > thresholds.p99_max:
            violations.append(
                f"{endpoint}: P99 {data['p99_ms']}ms > {thresholds.p99_max}ms"
            )
        if data["error_rate"] > thresholds.max_error_rate:
            violations.append(
                f"{endpoint}: Error rate {data['error_rate']}% > {thresholds.max_error_rate}%"
            )

    if violations:
        print("\n⚠️  THRESHOLD VIOLATIONS:")
        for v in violations:
            print(f"  - {v}")
    else:
        print("\n✅ All thresholds met!")


class BaseUser(HttpUser):
    """Base user class with common functionality"""

    abstract = True

    # Wait between 1-5 seconds between tasks
    wait_time = between(1, 5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token: Optional[str] = None
        self.user_id: Optional[int] = None
        self.created_suite_ids: List[int] = []
        self.created_case_ids: List[int] = []
        self.created_execution_ids: List[int] = []

    def on_start(self):
        """Called when a user starts"""
        self.login()

    def on_stop(self):
        """Called when a user stops - cleanup created resources"""
        self.cleanup()

    def login(self):
        """Authenticate and get token"""
        response = self.client.post(
            ENDPOINTS["auth_login"],
            json={"username": config.test_username, "password": config.test_password},
            name="auth_login",
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            # Get user info
            self._get_user_info()
        else:
            print(f"Login failed: {response.status_code} - {response.text}")

    def _get_user_info(self):
        """Get current user information"""
        if not self.token:
            return

        headers = config.get_auth_headers(self.token)
        response = self.client.get(
            "/api/v1/me", headers=headers, name="get_current_user"
        )

        if response.status_code == 200:
            data = response.json()
            self.user_id = data.get("id")

    def get_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        if not self.token:
            self.login()
        return config.get_auth_headers(self.token) if self.token else {}

    def cleanup(self):
        """Cleanup created resources"""
        headers = self.get_headers()

        # Delete created executions
        for exec_id in self.created_execution_ids:
            try:
                self.client.delete(
                    ENDPOINTS["execution_get"].format(id=exec_id),
                    headers=headers,
                    name="cleanup_execution",
                )
            except Exception:
                pass

        # Delete created cases
        for case_id in self.created_case_ids:
            try:
                self.client.delete(
                    ENDPOINTS["case_get"].format(id=case_id),
                    headers=headers,
                    name="cleanup_case",
                )
            except Exception:
                pass

        # Delete created suites
        for suite_id in self.created_suite_ids:
            try:
                self.client.delete(
                    ENDPOINTS["suite_get"].format(id=suite_id),
                    headers=headers,
                    name="cleanup_suite",
                )
            except Exception:
                pass


class DashboardViewer(BaseUser):
    """
    Simulates users who primarily view the dashboard.
    High frequency, read-only operations.
    """

    weight = TASK_WEIGHTS["dashboard_viewer"]

    @task(10)
    def get_dashboard_stats(self):
        """Get dashboard statistics"""
        headers = self.get_headers()
        response = self.client.get(
            ENDPOINTS["dashboard_stats"], headers=headers, name="dashboard_stats"
        )

        MetricsCollector.record_response(
            "dashboard_stats",
            response.elapsed.total_seconds(),
            response.status_code == 200,
        )

    @task(5)
    def get_dashboard_trends(self):
        """Get execution trends"""
        headers = self.get_headers()
        days = random.choice([7, 14, 30, 60, 90])
        response = self.client.get(
            f"{ENDPOINTS['dashboard_trends']}?days={days}",
            headers=headers,
            name="dashboard_trends",
        )

        MetricsCollector.record_response(
            "dashboard_trends",
            response.elapsed.total_seconds(),
            response.status_code == 200,
        )

    @task(3)
    def list_suites(self):
        """List all test suites"""
        headers = self.get_headers()
        skip = random.randint(0, 50)
        limit = random.randint(10, 50)
        response = self.client.get(
            f"{ENDPOINTS['suites_list']}?skip={skip}&limit={limit}",
            headers=headers,
            name="list_suites",
        )

        MetricsCollector.record_response(
            "list_suites", response.elapsed.total_seconds(), response.status_code == 200
        )

    @task(3)
    def list_cases(self):
        """List test cases"""
        headers = self.get_headers()
        skip = random.randint(0, 100)
        limit = random.randint(10, 50)

        url = f"{ENDPOINTS['cases_list']}?skip={skip}&limit={limit}"

        # Sometimes filter by suite
        if TestDataStore.suite_ids and random.random() > 0.5:
            suite_id = random.choice(TestDataStore.suite_ids)
            url += f"&suite_id={suite_id}"

        response = self.client.get(url, headers=headers, name="list_cases")

        MetricsCollector.record_response(
            "list_cases", response.elapsed.total_seconds(), response.status_code == 200
        )

    @task(2)
    def list_executions(self):
        """List test executions"""
        headers = self.get_headers()
        skip = random.randint(0, 50)
        limit = random.randint(10, 30)

        url = f"{ENDPOINTS['executions_list']}?skip={skip}&limit={limit}"

        # Sometimes filter by status
        if random.random() > 0.7:
            status = random.choice(["running", "passed", "failed", "completed"])
            url += f"&status={status}"

        response = self.client.get(url, headers=headers, name="list_executions")

        MetricsCollector.record_response(
            "list_executions",
            response.elapsed.total_seconds(),
            response.status_code == 200,
        )


class SuiteManager(BaseUser):
    """
    Simulates users who manage test suites.
    Medium frequency, CRUD operations on suites.
    """

    weight = TASK_WEIGHTS["suite_manager"]

    @task(5)
    def create_suite(self):
        """Create a new test suite"""
        headers = self.get_headers()
        timestamp = int(time.time() * 1000)

        data = {
            "name": f"Perf Suite {timestamp} - {self.user_id}",
            "description": "Created during performance testing",
            "framework_type": random.choice(["pytest", "unittest", "jest", "mocha"]),
            "config": {
                "parallel": random.choice([True, False]),
                "workers": random.randint(2, 8),
                "timeout": random.randint(30, 300),
            },
        }

        response = self.client.post(
            ENDPOINTS["suite_create"], headers=headers, json=data, name="create_suite"
        )

        if response.status_code == 201:
            suite_data = response.json()
            suite_id = suite_data.get("id")
            if suite_id:
                self.created_suite_ids.append(suite_id)
                TestDataStore.suite_ids.append(suite_id)

        MetricsCollector.record_response(
            "create_suite",
            response.elapsed.total_seconds(),
            response.status_code == 201,
        )

    @task(3)
    def get_suite(self):
        """Get a specific suite"""
        if not TestDataStore.suite_ids:
            return

        headers = self.get_headers()
        suite_id = random.choice(TestDataStore.suite_ids)

        response = self.client.get(
            ENDPOINTS["suite_get"].format(id=suite_id),
            headers=headers,
            name="get_suite",
        )

        MetricsCollector.record_response(
            "get_suite", response.elapsed.total_seconds(), response.status_code == 200
        )

    @task(2)
    def update_suite(self):
        """Update an existing suite"""
        if not self.created_suite_ids:
            return

        headers = self.get_headers()
        suite_id = random.choice(self.created_suite_ids)

        data = {
            "description": f"Updated at {datetime.now().isoformat()}",
            "config": {"parallel": True, "workers": 4},
        }

        response = self.client.put(
            ENDPOINTS["suite_update"].format(id=suite_id),
            headers=headers,
            json=data,
            name="update_suite",
        )

        MetricsCollector.record_response(
            "update_suite",
            response.elapsed.total_seconds(),
            response.status_code == 200,
        )

    @task(1)
    def delete_suite(self):
        """Delete a suite (soft delete)"""
        if not self.created_suite_ids:
            return

        headers = self.get_headers()
        suite_id = self.created_suite_ids.pop(0)

        response = self.client.delete(
            ENDPOINTS["suite_delete"].format(id=suite_id),
            headers=headers,
            name="delete_suite",
        )

        if response.status_code == 204 and suite_id in TestDataStore.suite_ids:
            TestDataStore.suite_ids.remove(suite_id)

        MetricsCollector.record_response(
            "delete_suite",
            response.elapsed.total_seconds(),
            response.status_code == 204,
        )


class CaseManager(BaseUser):
    """
    Simulates users who manage test cases.
    Medium frequency, CRUD operations on cases.
    """

    weight = TASK_WEIGHTS["case_manager"]

    @task(5)
    def create_case(self):
        """Create a new test case"""
        if not TestDataStore.suite_ids:
            return

        headers = self.get_headers()
        timestamp = int(time.time() * 1000)
        suite_id = random.choice(TestDataStore.suite_ids)

        data = {
            "suite_id": suite_id,
            "name": f"Perf Case {timestamp} - {self.user_id}",
            "description": "Created during performance testing",
            "test_code": self._generate_test_code(),
            "test_type": random.choice(["api", "ui", "db", "security", "performance"]),
            "priority": random.choice(["low", "medium", "high", "critical"]),
            "tags": random.sample(
                ["regression", "smoke", "integration", "e2e", "unit"],
                k=random.randint(1, 3),
            ),
        }

        response = self.client.post(
            ENDPOINTS["case_create"], headers=headers, json=data, name="create_case"
        )

        if response.status_code == 201:
            case_data = response.json()
            case_id = case_data.get("id")
            if case_id:
                self.created_case_ids.append(case_id)
                TestDataStore.case_ids.append(case_id)

        MetricsCollector.record_response(
            "create_case", response.elapsed.total_seconds(), response.status_code == 201
        )

    @task(3)
    def get_case(self):
        """Get a specific test case"""
        if not TestDataStore.case_ids:
            return

        headers = self.get_headers()
        case_id = random.choice(TestDataStore.case_ids)

        response = self.client.get(
            ENDPOINTS["case_get"].format(id=case_id), headers=headers, name="get_case"
        )

        MetricsCollector.record_response(
            "get_case", response.elapsed.total_seconds(), response.status_code == 200
        )

    @task(2)
    def update_case(self):
        """Update an existing test case"""
        if not self.created_case_ids:
            return

        headers = self.get_headers()
        case_id = random.choice(self.created_case_ids)

        data = {
            "description": f"Updated at {datetime.now().isoformat()}",
            "priority": random.choice(["low", "medium", "high", "critical"]),
            "tags": random.sample(
                ["regression", "smoke", "integration", "e2e", "unit"],
                k=random.randint(1, 3),
            ),
        }

        response = self.client.put(
            ENDPOINTS["case_update"].format(id=case_id),
            headers=headers,
            json=data,
            name="update_case",
        )

        MetricsCollector.record_response(
            "update_case", response.elapsed.total_seconds(), response.status_code == 200
        )

    @task(1)
    def delete_case(self):
        """Delete a test case"""
        if not self.created_case_ids:
            return

        headers = self.get_headers()
        case_id = self.created_case_ids.pop(0)

        response = self.client.delete(
            ENDPOINTS["case_delete"].format(id=case_id),
            headers=headers,
            name="delete_case",
        )

        if response.status_code == 204 and case_id in TestDataStore.case_ids:
            TestDataStore.case_ids.remove(case_id)

        MetricsCollector.record_response(
            "delete_case", response.elapsed.total_seconds(), response.status_code == 204
        )

    def _generate_test_code(self) -> str:
        """Generate sample test code"""
        templates = [
            """def test_api_endpoint():
    response = requests.get('/api/test')
    assert response.status_code == 200
    assert 'data' in response.json()""",
            """def test_database_connection():
    conn = get_db_connection()
    result = conn.execute('SELECT 1')
    assert result.scalar() == 1""",
            """def test_user_authentication():
    user = authenticate('test_user', 'password')
    assert user is not None
    assert user.is_active""",
            """def test_performance_threshold():
    start = time.time()
    response = make_request()
    duration = time.time() - start
    assert duration < 1.0  # 1 second threshold""",
        ]
        return random.choice(templates)


class ExecutionRunner(BaseUser):
    """
    Simulates users who run test executions.
    Lower frequency, execution workflow operations.
    """

    weight = TASK_WEIGHTS["execution_runner"]

    @task(3)
    def create_execution(self):
        """Create a new test execution"""
        if not TestDataStore.suite_ids:
            return

        headers = self.get_headers()
        suite_id = random.choice(TestDataStore.suite_ids)

        data = {
            "suite_id": suite_id,
            "execution_type": random.choice(["manual", "scheduled", "ci"]),
            "environment": random.choice(["production", "staging", "development"]),
        }

        response = self.client.post(
            ENDPOINTS["execution_create"],
            headers=headers,
            json=data,
            name="create_execution",
        )

        if response.status_code == 201:
            exec_data = response.json()
            execution_id = exec_data.get("id")
            if execution_id:
                self.created_execution_ids.append(execution_id)
                TestDataStore.execution_ids.append(execution_id)

        MetricsCollector.record_response(
            "create_execution",
            response.elapsed.total_seconds(),
            response.status_code == 201,
        )

    @task(2)
    def get_execution(self):
        """Get execution details"""
        if not TestDataStore.execution_ids:
            return

        headers = self.get_headers()
        execution_id = random.choice(TestDataStore.execution_ids)

        response = self.client.get(
            ENDPOINTS["execution_get"].format(id=execution_id),
            headers=headers,
            name="get_execution",
        )

        MetricsCollector.record_response(
            "get_execution",
            response.elapsed.total_seconds(),
            response.status_code == 200,
        )

    @task(2)
    def start_execution(self):
        """Start a test execution"""
        if not TestDataStore.execution_ids:
            return

        headers = self.get_headers()
        execution_id = random.choice(TestDataStore.execution_ids)

        response = self.client.post(
            ENDPOINTS["execution_start"].format(id=execution_id),
            headers=headers,
            name="start_execution",
        )

        MetricsCollector.record_response(
            "start_execution",
            response.elapsed.total_seconds(),
            response.status_code == 200,
        )

    @task(1)
    def stop_execution(self):
        """Stop a running execution"""
        if not TestDataStore.execution_ids:
            return

        headers = self.get_headers()
        execution_id = random.choice(TestDataStore.execution_ids)

        response = self.client.post(
            ENDPOINTS["execution_stop"].format(id=execution_id),
            headers=headers,
            name="stop_execution",
        )

        MetricsCollector.record_response(
            "stop_execution",
            response.elapsed.total_seconds(),
            response.status_code == 200,
        )


class AuthenticatedUser(BaseUser):
    """
    Simulates authentication operations.
    Lowest frequency - login/logout flows.
    """

    weight = TASK_WEIGHTS["authenticated_user"]
    wait_time = between(10, 30)  # Less frequent

    @task(5)
    def login_flow(self):
        """Perform login"""
        response = self.client.post(
            ENDPOINTS["auth_login"],
            json={"username": config.test_username, "password": config.test_password},
            name="auth_login",
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")

        MetricsCollector.record_response(
            "auth_login", response.elapsed.total_seconds(), response.status_code == 200
        )

    @task(1)
    def get_current_user(self):
        """Get current user info"""
        if not self.token:
            return

        headers = config.get_auth_headers(self.token)
        response = self.client.get(
            "/api/v1/me", headers=headers, name="get_current_user"
        )

        MetricsCollector.record_response(
            "get_current_user",
            response.elapsed.total_seconds(),
            response.status_code == 200,
        )


# ============================================================================
# Load Test Scenarios
# ============================================================================


class LoadTestUser(DashboardViewer, SuiteManager, CaseManager, ExecutionRunner):
    """
    Combined user for standard load testing.
    Represents realistic user behavior mix.
    """

    weight = 50
    wait_time = between(1, 3)  # Faster for load testing


class StressTestUser(HttpUser):
    """
    User for stress testing - rapidly increasing load.
    Tests system behavior under extreme conditions.
    """

    weight = 30
    wait_time = between(0.1, 0.5)  # Very fast requests

    def on_start(self):
        self.token = None
        self.login()

    def login(self):
        """Quick login"""
        response = self.client.post(
            ENDPOINTS["auth_login"],
            json={"username": config.test_username, "password": config.test_password},
            name="stress_auth_login",
        )

        if response.status_code == 200:
            self.token = response.json().get("access_token")

    def get_headers(self):
        if not self.token:
            self.login()
        return config.get_auth_headers(self.token) if self.token else {}

    @task(10)
    def stress_dashboard(self):
        """High frequency dashboard access"""
        headers = self.get_headers()
        self.client.get(
            ENDPOINTS["dashboard_stats"], headers=headers, name="stress_dashboard_stats"
        )

    @task(5)
    def stress_list_operations(self):
        """High frequency list operations"""
        headers = self.get_headers()
        self.client.get(
            f"{ENDPOINTS['suites_list']}?limit=100",
            headers=headers,
            name="stress_list_suites",
        )


class SpikeTestUser(HttpUser):
    """
    User for spike testing - sudden burst of activity.
    """

    weight = 20
    wait_time = between(0.5, 1.0)

    def on_start(self):
        self.token = None
        self.login()

    def login(self):
        response = self.client.post(
            ENDPOINTS["auth_login"],
            json={"username": config.test_username, "password": config.test_password},
            name="spike_auth_login",
        )

        if response.status_code == 200:
            self.token = response.json().get("access_token")

    @task(1)
    def spike_dashboard(self):
        """Burst of dashboard requests"""
        if not self.token:
            return

        headers = config.get_auth_headers(self.token)
        # Fire multiple requests rapidly
        for _ in range(5):
            self.client.get(
                ENDPOINTS["dashboard_stats"], headers=headers, name="spike_dashboard"
            )


# Default user class for simple load testing
class WebsiteUser(LoadTestUser):
    """Default user class"""

    pass
