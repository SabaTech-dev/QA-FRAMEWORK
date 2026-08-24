"""
Usage Tracking Domain Entities
==============================

Entities for tracking API usage, test executions, and resource consumption.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4


class ResourceType(str, Enum):
    """Types of resources that can be tracked."""

    API_CALLS = "api_calls"
    TEST_EXECUTIONS = "test_executions"
    AI_GENERATIONS = "ai_generations"
    STORAGE_MB = "storage_mb"
    BANDWIDTH_MB = "bandwidth_mb"


class BillingPeriod(str, Enum):
    """Billing period types."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass
class UsageRecord:
    """Single usage record for tracking resource consumption."""

    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    organization_id: Optional[str] = None
    resource_type: ResourceType = ResourceType.API_CALLS
    quantity: float = 0.0
    unit: str = "count"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "resource_type": self.resource_type.value,
            "quantity": self.quantity,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class UsageSummary:
    """Aggregated usage summary for a billing period."""

    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    organization_id: Optional[str] = None
    period_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    billing_period: BillingPeriod = BillingPeriod.MONTHLY

    # Resource usage counts
    api_calls: int = 0
    test_executions: int = 0
    ai_generations: int = 0
    storage_mb: float = 0.0
    bandwidth_mb: float = 0.0

    # Calculated costs (in cents)
    api_calls_cost: int = 0
    test_executions_cost: int = 0
    ai_generations_cost: int = 0
    storage_cost: int = 0
    bandwidth_cost: int = 0
    total_cost: int = 0

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def calculate_total(self) -> int:
        """Calculate total cost in cents."""
        self.total_cost = (
            self.api_calls_cost
            + self.test_executions_cost
            + self.ai_generations_cost
            + self.storage_cost
            + self.bandwidth_cost
        )
        return self.total_cost

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "billing_period": self.billing_period.value,
            "api_calls": self.api_calls,
            "test_executions": self.test_executions,
            "ai_generations": self.ai_generations,
            "storage_mb": self.storage_mb,
            "bandwidth_mb": self.bandwidth_mb,
            "api_calls_cost": self.api_calls_cost,
            "test_executions_cost": self.test_executions_cost,
            "ai_generations_cost": self.ai_generations_cost,
            "storage_cost": self.storage_cost,
            "bandwidth_cost": self.bandwidth_cost,
            "total_cost": self.total_cost,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class UsageLimit:
    """Usage limits for a subscription plan."""

    plan_name: str = "free"

    # Resource limits
    max_api_calls: int = 1000
    max_test_executions: int = 100
    max_ai_generations: int = 10
    max_storage_mb: int = 100
    max_bandwidth_mb: int = 1000

    # Pricing per unit (in cents)
    api_call_price: int = 1  # $0.01 per call
    test_execution_price: int = 5  # $0.05 per execution
    ai_generation_price: int = 50  # $0.50 per generation
    storage_price_per_mb: int = 10  # $0.10 per MB
    bandwidth_price_per_mb: int = 1  # $0.01 per MB

    def get_limit(self, resource_type: ResourceType) -> int:
        """Get the limit for a specific resource type."""
        limits = {
            ResourceType.API_CALLS: self.max_api_calls,
            ResourceType.TEST_EXECUTIONS: self.max_test_executions,
            ResourceType.AI_GENERATIONS: self.max_ai_generations,
            ResourceType.STORAGE_MB: self.max_storage_mb,
            ResourceType.BANDWIDTH_MB: self.max_bandwidth_mb,
        }
        return limits.get(resource_type, 0)

    def get_price(self, resource_type: ResourceType) -> int:
        """Get the price per unit for a specific resource type."""
        prices = {
            ResourceType.API_CALLS: self.api_call_price,
            ResourceType.TEST_EXECUTIONS: self.test_execution_price,
            ResourceType.AI_GENERATIONS: self.ai_generation_price,
            ResourceType.STORAGE_MB: self.storage_price_per_mb,
            ResourceType.BANDWIDTH_MB: self.bandwidth_price_per_mb,
        }
        return prices.get(resource_type, 0)

    def to_dict(self) -> dict:
        return {
            "plan_name": self.plan_name,
            "max_api_calls": self.max_api_calls,
            "max_test_executions": self.max_test_executions,
            "max_ai_generations": self.max_ai_generations,
            "max_storage_mb": self.max_storage_mb,
            "max_bandwidth_mb": self.max_bandwidth_mb,
            "api_call_price": self.api_call_price,
            "test_execution_price": self.test_execution_price,
            "ai_generation_price": self.ai_generation_price,
            "storage_price_per_mb": self.storage_price_per_mb,
            "bandwidth_price_per_mb": self.bandwidth_price_per_mb,
        }


# Plan definitions
PLAN_LIMITS = {
    "free": UsageLimit(
        plan_name="free",
        max_api_calls=1000,
        max_test_executions=100,
        max_ai_generations=10,
        max_storage_mb=100,
        max_bandwidth_mb=1000,
    ),
    "starter": UsageLimit(
        plan_name="starter",
        max_api_calls=10000,
        max_test_executions=1000,
        max_ai_generations=100,
        max_storage_mb=1000,
        max_bandwidth_mb=10000,
    ),
    "pro": UsageLimit(
        plan_name="pro",
        max_api_calls=100000,
        max_test_executions=10000,
        max_ai_generations=1000,
        max_storage_mb=10000,
        max_bandwidth_mb=100000,
    ),
    "enterprise": UsageLimit(
        plan_name="enterprise",
        max_api_calls=-1,  # Unlimited
        max_test_executions=-1,
        max_ai_generations=-1,
        max_storage_mb=-1,
        max_bandwidth_mb=-1,
    ),
}


def get_plan_limits(plan_name: str) -> UsageLimit:
    """Get usage limits for a plan."""
    return PLAN_LIMITS.get(plan_name, PLAN_LIMITS["free"])
