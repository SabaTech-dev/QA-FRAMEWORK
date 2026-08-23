"""
Tests for Usage Tracking System
================================

Tests for usage tracking entities and services.
"""

import pytest

from src.domain.usage.entities import (
    BillingPeriod,
    ResourceType,
    UsageRecord,
    UsageSummary,
    get_plan_limits,
)
from src.infrastructure.usage.usage_tracker import UsageTracker, get_usage_tracker

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def usage_tracker():
    """Create a fresh UsageTracker instance for each test."""
    return UsageTracker()


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return "user_test_123"


# ============================================================================
# UsageRecord Tests
# ============================================================================


class TestUsageRecord:
    """Tests for UsageRecord entity."""

    def test_create_usage_record(self):
        """Should create a usage record with default values."""
        record = UsageRecord(
            user_id="user123",
            resource_type=ResourceType.API_CALLS,
        )

        assert record.user_id == "user123"
        assert record.resource_type == ResourceType.API_CALLS
        assert record.quantity == 0.0
        assert record.id is not None
        assert record.timestamp is not None

    def test_usage_record_to_dict(self):
        """Should convert usage record to dictionary."""
        record = UsageRecord(
            user_id="user123",
            resource_type=ResourceType.TEST_EXECUTIONS,
            quantity=5.0,
            unit="executions",
        )

        data = record.to_dict()

        assert data["user_id"] == "user123"
        assert data["resource_type"] == "test_executions"
        assert data["quantity"] == 5.0
        assert data["unit"] == "executions"

    def test_usage_record_with_metadata(self):
        """Should store metadata in usage record."""
        metadata = {"test_id": "test_456", "browser": "chrome"}
        record = UsageRecord(
            user_id="user123",
            resource_type=ResourceType.TEST_EXECUTIONS,
            metadata=metadata,
        )

        assert record.metadata == metadata


# ============================================================================
# UsageSummary Tests
# ============================================================================


class TestUsageSummary:
    """Tests for UsageSummary entity."""

    def test_create_usage_summary(self):
        """Should create a usage summary with default values."""
        summary = UsageSummary(user_id="user123")

        assert summary.user_id == "user123"
        assert summary.api_calls == 0
        assert summary.test_executions == 0
        assert summary.total_cost == 0

    def test_calculate_total(self):
        """Should calculate total cost correctly."""
        summary = UsageSummary(
            user_id="user123",
            api_calls_cost=100,
            test_executions_cost=50,
            ai_generations_cost=25,
            storage_cost=10,
            bandwidth_cost=5,
        )

        total = summary.calculate_total()

        assert total == 190
        assert summary.total_cost == 190

    def test_usage_summary_to_dict(self):
        """Should convert usage summary to dictionary."""
        summary = UsageSummary(
            user_id="user123",
            api_calls=100,
            test_executions=50,
        )

        data = summary.to_dict()

        assert data["user_id"] == "user123"
        assert data["api_calls"] == 100
        assert data["test_executions"] == 50


# ============================================================================
# UsageLimit Tests
# ============================================================================


class TestUsageLimit:
    """Tests for UsageLimit entity."""

    def test_free_plan_limits(self):
        """Should have correct limits for free plan."""
        limits = get_plan_limits("free")

        assert limits.plan_name == "free"
        assert limits.max_api_calls == 1000
        assert limits.max_test_executions == 100
        assert limits.max_ai_generations == 10

    def test_pro_plan_limits(self):
        """Should have correct limits for pro plan."""
        limits = get_plan_limits("pro")

        assert limits.plan_name == "pro"
        assert limits.max_api_calls == 100000
        assert limits.max_test_executions == 10000

    def test_enterprise_plan_unlimited(self):
        """Enterprise plan should have unlimited (-1) limits."""
        limits = get_plan_limits("enterprise")

        assert limits.plan_name == "enterprise"
        assert limits.max_api_calls == -1
        assert limits.max_test_executions == -1

    def test_get_limit_by_resource_type(self):
        """Should get limit for specific resource type."""
        limits = get_plan_limits("starter")

        assert limits.get_limit(ResourceType.API_CALLS) == 10000
        assert limits.get_limit(ResourceType.TEST_EXECUTIONS) == 1000

    def test_get_price_by_resource_type(self):
        """Should get price for specific resource type."""
        limits = get_plan_limits("free")

        assert limits.get_price(ResourceType.API_CALLS) == 1
        assert limits.get_price(ResourceType.AI_GENERATIONS) == 50

    def test_unknown_plan_defaults_to_free(self):
        """Unknown plan should default to free limits."""
        limits = get_plan_limits("unknown_plan")

        assert limits.plan_name == "free"


# ============================================================================
# UsageTracker Tests
# ============================================================================


class TestUsageTracker:
    """Tests for UsageTracker service."""

    def test_track_api_call(self, usage_tracker, sample_user_id):
        """Should track an API call."""
        record = usage_tracker.track_usage(
            user_id=sample_user_id,
            resource_type=ResourceType.API_CALLS,
            quantity=1.0,
        )

        assert record.user_id == sample_user_id
        assert record.resource_type == ResourceType.API_CALLS
        assert record.quantity == 1.0

    def test_track_test_execution(self, usage_tracker, sample_user_id):
        """Should track a test execution."""
        record = usage_tracker.track_usage(
            user_id=sample_user_id,
            resource_type=ResourceType.TEST_EXECUTIONS,
            quantity=1.0,
            metadata={"test_name": "login_test"},
        )

        assert record.resource_type == ResourceType.TEST_EXECUTIONS
        assert record.metadata["test_name"] == "login_test"

    def test_get_usage_records(self, usage_tracker, sample_user_id):
        """Should retrieve usage records for a user."""
        # Track some usage
        usage_tracker.track_usage(sample_user_id, ResourceType.API_CALLS, 1.0)
        usage_tracker.track_usage(sample_user_id, ResourceType.API_CALLS, 1.0)
        usage_tracker.track_usage(sample_user_id, ResourceType.TEST_EXECUTIONS, 1.0)

        records = usage_tracker.get_usage(sample_user_id)

        assert len(records) == 3

    def test_get_usage_filtered_by_type(self, usage_tracker, sample_user_id):
        """Should filter usage records by resource type."""
        usage_tracker.track_usage(sample_user_id, ResourceType.API_CALLS, 1.0)
        usage_tracker.track_usage(sample_user_id, ResourceType.TEST_EXECUTIONS, 1.0)

        records = usage_tracker.get_usage(
            sample_user_id,
            resource_type=ResourceType.API_CALLS,
        )

        assert len(records) == 1
        assert records[0].resource_type == ResourceType.API_CALLS

    def test_get_usage_summary(self, usage_tracker, sample_user_id):
        """Should aggregate usage into a summary."""
        # Track various usage
        for _ in range(10):
            usage_tracker.track_usage(sample_user_id, ResourceType.API_CALLS, 1.0)
        for _ in range(5):
            usage_tracker.track_usage(sample_user_id, ResourceType.TEST_EXECUTIONS, 1.0)

        summary = usage_tracker.get_usage_summary(sample_user_id)

        assert summary.api_calls == 10
        assert summary.test_executions == 5

    def test_calculate_costs(self, usage_tracker, sample_user_id):
        """Should calculate costs based on plan pricing."""
        # Track usage within free plan limits
        for _ in range(100):
            usage_tracker.track_usage(sample_user_id, ResourceType.API_CALLS, 1.0)

        summary = usage_tracker.get_usage_summary(sample_user_id)
        summary_with_costs = usage_tracker.calculate_costs(summary, "free")

        # Within limits, should have no overage cost
        assert summary_with_costs.api_calls_cost == 0
        assert summary_with_costs.total_cost == 0

    def test_calculate_overage_costs(self, usage_tracker, sample_user_id):
        """Should calculate overage costs when exceeding limits."""
        # Track usage exceeding free plan limits
        for _ in range(1500):  # Free limit is 1000
            usage_tracker.track_usage(sample_user_id, ResourceType.API_CALLS, 1.0)

        summary = usage_tracker.get_usage_summary(sample_user_id)
        summary_with_costs = usage_tracker.calculate_costs(summary, "free")

        # 500 overage * $0.01 = 500 cents
        assert summary_with_costs.api_calls_cost == 500
        assert summary_with_costs.total_cost == 500

    def test_check_usage_limit_within_limit(self, usage_tracker, sample_user_id):
        """Should report when usage is within limits."""
        for _ in range(50):
            usage_tracker.track_usage(sample_user_id, ResourceType.API_CALLS, 1.0)

        status = usage_tracker.check_usage_limit(
            sample_user_id,
            ResourceType.API_CALLS,
            "free",
        )

        assert status["is_within_limit"] is True
        assert status["current_usage"] == 50
        assert status["remaining"] == 950
        assert status["percentage_used"] == 5.0

    def test_check_usage_limit_exceeded(self, usage_tracker, sample_user_id):
        """Should report when usage exceeds limits."""
        for _ in range(1500):
            usage_tracker.track_usage(sample_user_id, ResourceType.API_CALLS, 1.0)

        status = usage_tracker.check_usage_limit(
            sample_user_id,
            ResourceType.API_CALLS,
            "free",
        )

        assert status["is_within_limit"] is False
        assert status["current_usage"] == 1500
        assert status["remaining"] == 0
        # Percentage is capped at 100 in the implementation
        assert status["percentage_used"] == 100

    def test_check_usage_limit_unlimited(self, usage_tracker, sample_user_id):
        """Enterprise plan should report unlimited."""
        for _ in range(10000):
            usage_tracker.track_usage(sample_user_id, ResourceType.API_CALLS, 1.0)

        status = usage_tracker.check_usage_limit(
            sample_user_id,
            ResourceType.API_CALLS,
            "enterprise",
        )

        assert status["is_within_limit"] is True
        assert status["is_unlimited"] is True
        assert status["limit"] == -1

    def test_get_usage_report(self, usage_tracker, sample_user_id):
        """Should generate a comprehensive usage report."""
        usage_tracker.track_usage(sample_user_id, ResourceType.API_CALLS, 1.0)
        usage_tracker.track_usage(sample_user_id, ResourceType.TEST_EXECUTIONS, 1.0)

        report = usage_tracker.get_usage_report(sample_user_id, "free")

        assert report["user_id"] == sample_user_id
        assert report["plan_name"] == "free"
        assert "usage" in report
        assert "limits" in report
        assert "limit_status" in report


# ============================================================================
# ResourceType Tests
# ============================================================================


class TestResourceType:
    """Tests for ResourceType enum."""

    def test_resource_type_values(self):
        """Should have expected resource types."""
        assert ResourceType.API_CALLS.value == "api_calls"
        assert ResourceType.TEST_EXECUTIONS.value == "test_executions"
        assert ResourceType.AI_GENERATIONS.value == "ai_generations"
        assert ResourceType.STORAGE_MB.value == "storage_mb"
        assert ResourceType.BANDWIDTH_MB.value == "bandwidth_mb"


# ============================================================================
# BillingPeriod Tests
# ============================================================================


class TestBillingPeriod:
    """Tests for BillingPeriod enum."""

    def test_billing_period_values(self):
        """Should have expected billing periods."""
        assert BillingPeriod.DAILY.value == "daily"
        assert BillingPeriod.WEEKLY.value == "weekly"
        assert BillingPeriod.MONTHLY.value == "monthly"
        assert BillingPeriod.YEARLY.value == "yearly"


# ============================================================================
# Singleton Tests
# ============================================================================


class TestUsageTrackerSingleton:
    """Tests for UsageTracker singleton pattern."""

    def test_get_usage_tracker_singleton(self):
        """Should return the same instance."""
        tracker1 = get_usage_tracker()
        tracker2 = get_usage_tracker()

        assert tracker1 is tracker2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
