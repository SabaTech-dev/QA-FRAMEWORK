"""
Performance Test Configuration for QA-FRAMEWORK Dashboard

This module contains all configuration settings for Locust performance tests,
including performance thresholds, test scenarios, and environment settings.
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class TestEnvironment(Enum):
    """Test environment types"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class PerformanceThresholds:
    """
    Performance thresholds for API endpoints.
    All times are in milliseconds.
    """

    # General thresholds
    p50_max: int = 200  # 50th percentile (median)
    p95_max: int = 500  # 95th percentile
    p99_max: int = 1000  # 99th percentile

    # Specific endpoint thresholds
    auth_p50: int = 300
    auth_p95: int = 800
    auth_p99: int = 1500

    dashboard_p50: int = 150
    dashboard_p95: int = 400
    dashboard_p99: int = 800

    suite_crud_p50: int = 200
    suite_crud_p95: int = 600
    suite_crud_p99: int = 1200

    case_crud_p50: int = 200
    case_crud_p95: int = 600
    case_crud_p99: int = 1200

    execution_p50: int = 250
    execution_p95: int = 700
    execution_p99: int = 1400

    # Error rate thresholds (percentage)
    max_error_rate: float = 1.0  # 1% max error rate
    max_failure_rate: float = 0.5  # 0.5% max failure rate

    # Throughput thresholds (requests per second)
    min_rps: float = 10.0
    target_rps: float = 50.0


@dataclass
class LoadTestConfig:
    """Configuration for different load test scenarios"""

    # User counts
    min_users: int = 10
    max_users: int = 200
    target_users: int = 100

    # Spawn rates (users per second)
    spawn_rate: float = 5.0
    ramp_up_time: int = 60  # seconds

    # Test duration
    test_duration: int = 300  # 5 minutes default
    steady_state_duration: int = 180  # 3 minutes

    # Wait times between requests (seconds)
    min_wait: float = 1.0
    max_wait: float = 5.0


@dataclass
class StressTestConfig:
    """Configuration for stress testing"""

    # Initial load
    initial_users: int = 50

    # Stress ramp
    stress_increment: int = 25
    stress_steps: int = 6  # Will reach 50 + (25 * 6) = 200 users
    step_duration: int = 120  # 2 minutes per step

    # Breaking point detection
    max_response_time: int = 5000  # 5 seconds
    max_error_rate: float = 10.0  # 10%


@dataclass
class SoakTestConfig:
    """Configuration for soak/endurance testing"""

    duration: int = 3600  # 1 hour
    users: int = 50
    spawn_rate: float = 2.0


@dataclass
class SpikeTestConfig:
    """Configuration for spike testing"""

    baseline_users: int = 20
    spike_users: int = 200
    spike_duration: int = 60  # 1 minute spike
    recovery_duration: int = 300  # 5 minutes recovery


class TestConfig:
    """Main test configuration class"""

    def __init__(self):
        # Environment
        self.environment = TestEnvironment(os.getenv("PERF_TEST_ENV", "development"))

        # Base URL
        self.base_url = os.getenv("PERF_TEST_BASE_URL", "http://localhost:8000")

        # API prefix
        self.api_prefix = "/api/v1"

        # Authentication
        self.test_username = os.getenv("PERF_TEST_USERNAME", "testuser")
        self.test_password = os.getenv("PERF_TEST_PASSWORD", "testpass123")

        # Thresholds
        self.thresholds = PerformanceThresholds()

        # Test configurations
        self.load_test = LoadTestConfig()
        self.stress_test = StressTestConfig()
        self.soak_test = SoakTestConfig()
        self.spike_test = SpikeTestConfig()

        # Output settings
        self.results_dir = os.path.join(os.path.dirname(__file__), "results")
        self.html_report = True
        self.csv_stats = True
        self.log_metrics = True

        # Host configuration for distributed testing
        self.master_host = os.getenv("LOCUST_MASTER_HOST", "localhost")
        self.master_port = int(os.getenv("LOCUST_MASTER_PORT", "5557"))

    def get_full_url(self, endpoint: str) -> str:
        """Get full URL for an endpoint"""
        return f"{self.base_url}{self.api_prefix}{endpoint}"

    def get_auth_headers(self, token: str) -> Dict[str, str]:
        """Get authentication headers"""
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# Default configuration instance
config = TestConfig()

# API Endpoints
ENDPOINTS = {
    # Auth
    "auth_login": "/auth/login",
    # Dashboard
    "dashboard_stats": "/dashboard/stats",
    "dashboard_trends": "/dashboard/trends",
    # Suites
    "suites_list": "/suites",
    "suite_create": "/suites",
    "suite_get": "/suites/{id}",
    "suite_update": "/suites/{id}",
    "suite_delete": "/suites/{id}",
    # Cases
    "cases_list": "/cases",
    "case_create": "/cases",
    "case_get": "/cases/{id}",
    "case_update": "/cases/{id}",
    "case_delete": "/cases/{id}",
    # Executions
    "executions_list": "/executions",
    "execution_create": "/executions",
    "execution_get": "/executions/{id}",
    "execution_start": "/executions/{id}/start",
    "execution_stop": "/executions/{id}/stop",
    # Users
    "users_list": "/users",
    "user_create": "/auth/register",
    "user_get": "/users/{id}",
}

# Test data templates
TEST_DATA = {
    "suite": {
        "name": "Performance Test Suite {timestamp}",
        "description": "Suite created during performance testing",
        "framework_type": "pytest",
        "config": {"parallel": True, "workers": 4},
    },
    "case": {
        "name": "Performance Test Case {timestamp}",
        "description": "Test case created during performance testing",
        "test_code": "def test_example():\n    assert True",
        "test_type": "api",
        "priority": "medium",
        "tags": ["performance", "automated"],
    },
    "execution": {"execution_type": "manual", "environment": "production"},
    "user": {
        "username": "perfuser_{timestamp}",
        "email": "perfuser_{timestamp}@example.com",
        "password": "TestPass123!",
        "is_active": True,
    },
}

# Weighted task distribution (higher = more frequent)
TASK_WEIGHTS = {
    "dashboard_viewer": 40,  # High - everyone views dashboard
    "suite_manager": 20,  # Medium - CRUD operations
    "case_manager": 20,  # Medium - CRUD operations
    "execution_runner": 15,  # Lower - less frequent
    "authenticated_user": 5,  # Lowest - auth operations
}

# Performance baseline expectations
PERFORMANCE_BASELINES = {
    "concurrent_users": 100,
    "requests_per_second": 50,
    "avg_response_time_ms": 200,
    "p95_response_time_ms": 500,
    "error_rate_percent": 1.0,
    "availability_percent": 99.9,
}
