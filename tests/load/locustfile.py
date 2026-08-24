"""
Load Testing Suite for QA-FRAMEWORK using Locust.

Target: 100 concurrent users, <200ms response time (p95)

Usage:
    # Local testing
    locust -f tests/load/locustfile.py --host http://localhost:8000
    
    # Production testing (CAUTION!)
    locust -f tests/load/locustfile.py --host https://qa-framework-backend.railway.app
    
    # Headless mode (CI/CD)
    locust -f tests/load/locustfile.py --host http://localhost:8000 \
        --users 100 --spawn-rate 10 --run-time 5m --headless --html load-test-report.html
"""

import random

from faker import Faker
from locust import HttpUser, between, task


class QAFrameworkUser(HttpUser):
    """Simulates a typical QA-FRAMEWORK user behavior."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    fake = Faker()

    def on_start(self):
        """Initialize user session - login and get auth token."""
        self.tenant_id = self.fake.uuid4()
        self.api_key = None
        # Note: In production, implement actual login flow
        # For now, we test public endpoints

    @task(10)
    def health_check(self):
        """Test health endpoint - HIGH PRIORITY."""
        self.client.get("/health", name="/health")

    @task(5)
    def api_docs(self):
        """Test API documentation endpoint."""
        self.client.get("/docs", name="/docs")

    @task(3)
    def openapi_schema(self):
        """Test OpenAPI schema endpoint."""
        self.client.get("/openapi.json", name="/openapi.json")

    @task(8)
    def create_test_run(self):
        """Test creating a new test run - CORE FEATURE."""
        payload = {
            "test_id": self.fake.uuid4(),
            "name": self.fake.sentence(nb_words=4),
            "status": random.choice(["running", "pending"]),
            "metadata": {
                "browser": random.choice(["chrome", "firefox", "safari"]),
                "environment": random.choice(["staging", "production"]),
            },
        }
        self.client.post("/api/v1/test-runs", json=payload, name="/api/v1/test-runs [POST]")

    @task(7)
    def get_test_runs(self):
        """Test listing test runs - CORE FEATURE."""
        self.client.get(
            "/api/v1/test-runs", params={"limit": 20, "offset": 0}, name="/api/v1/test-runs [GET]"
        )

    @task(6)
    def get_test_results(self):
        """Test getting test results - CORE FEATURE."""
        test_id = self.fake.uuid4()
        self.client.get(
            f"/api/v1/test-runs/{test_id}/results", name="/api/v1/test-runs/{id}/results [GET]"
        )

    @task(4)
    def create_project(self):
        """Test creating a new project."""
        payload = {"name": self.fake.company(), "description": self.fake.text(max_nb_chars=200)}
        self.client.post("/api/v1/projects", json=payload, name="/api/v1/projects [POST]")

    @task(5)
    def get_projects(self):
        """Test listing projects."""
        self.client.get("/api/v1/projects", name="/api/v1/projects [GET]")

    @task(3)
    def generate_test_report(self):
        """Test report generation."""
        test_id = self.fake.uuid4()
        self.client.get(
            f"/api/v1/test-runs/{test_id}/report",
            params={"format": "html"},
            name="/api/v1/test-runs/{id}/report [GET]",
        )


class TenantAdminUser(HttpUser):
    """Simulates a tenant admin user - heavier operations."""

    wait_time = between(2, 5)
    fake = Faker()

    @task(5)
    def get_tenant_stats(self):
        """Test tenant statistics endpoint."""
        self.client.get("/api/v1/tenant/stats", name="/api/v1/tenant/stats [GET]")

    @task(4)
    def manage_team_members(self):
        """Test team management."""
        payload = {"email": self.fake.email(), "role": random.choice(["admin", "member", "viewer"])}
        self.client.post("/api/v1/team/invite", json=payload, name="/api/v1/team/invite [POST]")

    @task(3)
    def check_usage_limits(self):
        """Test usage limits check."""
        self.client.get("/api/v1/usage", name="/api/v1/usage [GET]")


class APIConsumer(HttpUser):
    """Simulates external API consumer - API key based access."""

    wait_time = between(0.5, 2)  # Faster requests
    fake = Faker()

    @task(10)
    def trigger_test_webhook(self):
        """Test webhook trigger."""
        payload = {
            "event": "test.completed",
            "test_id": self.fake.uuid4(),
            "status": random.choice(["passed", "failed"]),
            "timestamp": self.fake.iso8601(),
        }
        self.client.post(
            "/api/v1/webhooks/trigger", json=payload, name="/api/v1/webhooks/trigger [POST]"
        )

    @task(8)
    def query_test_history(self):
        """Test historical data query."""
        self.client.get(
            "/api/v1/test-runs/history",
            params={"start_date": "2026-01-01", "end_date": "2026-03-10", "status": "passed"},
            name="/api/v1/test-runs/history [GET]",
        )


# Stress test scenarios
class StressTestUser(HttpUser):
    """Stress test - aggressive request patterns."""

    wait_time = between(0.1, 0.5)  # Very fast requests

    @task
    def rapid_fire(self):
        """Rapid fire requests to test rate limiting."""
        self.client.get("/health", name="/health [STRESS]")
