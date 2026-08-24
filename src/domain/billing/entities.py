"""
Billing Domain Entities

Core domain entities for the billing system.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from .value_objects import Money, UsageLimit


class PlanType(Enum):
    """Types of subscription plans"""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(Enum):
    """Subscription status"""

    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    CANCELING = "canceling"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    UNPAID = "unpaid"
    PAUSED = "paused"


@dataclass
class Plan:
    """
    Represents a subscription plan.

    This is a domain entity that defines the available plans
    and their pricing/feature structure.
    """

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    plan_type: PlanType = PlanType.FREE
    price: Money = field(default_factory=lambda: Money(0))
    stripe_price_id: str | None = None
    stripe_product_id: str | None = None
    features: list[str] = field(default_factory=list)
    limits: UsageLimit = field(default_factory=UsageLimit)
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Initialize default timestamps"""
        if self.created_at is None:
            self.created_at = datetime.now(UTC)
        if self.updated_at is None:
            self.updated_at = datetime.now(UTC)

    def is_free(self) -> bool:
        """Check if this is a free plan"""
        return self.price.is_zero() or self.plan_type == PlanType.FREE

    def is_paid(self) -> bool:
        """Check if this is a paid plan"""
        return not self.is_free()

    def has_feature(self, feature: str) -> bool:
        """Check if plan includes a feature"""
        return feature in self.features

    def check_limit(self, metric: str, value: int) -> bool:
        """Check if value is within plan limits"""
        return self.limits.exceeds_limit(metric, value)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "plan_type": self.plan_type.value,
            "price": str(self.price) if self.price else "$0.00",
            "price_amount": float(self.price.amount) if self.price else 0,
            "features": self.features,
            "limits": {
                "max_tests_per_month": self.limits.max_tests_per_month,
                "max_users": self.limits.max_users,
                "max_suites": self.limits.max_suites,
                "max_cases_per_suite": self.limits.max_cases_per_suite,
                "ai_features": self.limits.ai_features,
                "api_access": self.limits.api_access,
                "priority_support": self.limits.priority_support,
            },
            "is_active": self.is_active,
        }


@dataclass
class Subscription:
    """
    Represents a user's subscription.

    This entity tracks subscription state and metadata.
    """

    id: UUID = field(default_factory=uuid4)
    tenant_id: UUID | None = None
    user_id: UUID | None = None
    plan_id: UUID | None = None
    plan_type: PlanType = PlanType.FREE
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    status: SubscriptionStatus = SubscriptionStatus.INCOMPLETE
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    canceled_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize default timestamps"""
        if self.created_at is None:
            self.created_at = datetime.now(UTC)
        if self.updated_at is None:
            self.updated_at = datetime.now(UTC)

    def is_active(self) -> bool:
        """Check if subscription is active"""
        return self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]

    def is_paid(self) -> bool:
        """Check if subscription is paid"""
        return self.plan_type != PlanType.FREE

    def is_in_trial(self) -> bool:
        """Check if subscription is in trial period"""
        return self.status == SubscriptionStatus.TRIALING

    def cancel(self, at_period_end: bool = True) -> None:
        """Mark subscription for cancellation"""
        self.cancel_at_period_end = at_period_end
        self.canceled_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)
        self.status = SubscriptionStatus.CANCELING

    def activate(self) -> None:
        """Activate subscription"""
        self.status = SubscriptionStatus.ACTIVE
        self.updated_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "plan_type": self.plan_type.value,
            "status": self.status.value,
            "is_active": self.is_active(),
            "current_period_start": (
                self.current_period_start.isoformat() if self.current_period_start else None
            ),
            "current_period_end": (
                self.current_period_end.isoformat() if self.current_period_end else None
            ),
            "cancel_at_period_end": self.cancel_at_period_end,
        }


@dataclass
class Usage:
    """
    Represents resource usage for a tenant.

    Tracks actual consumption against plan limits.
    """

    id: UUID = field(default_factory=uuid4)
    tenant_id: UUID | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    tests_executed: int = 0
    users_active: int = 0
    suites_created: int = 0
    cases_created: int = 0
    ai_feature_calls: int = 0
    storage_used_gb: float = 0.0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Initialize default timestamps"""
        if self.created_at is None:
            self.created_at = datetime.now(UTC)
        if self.updated_at is None:
            self.updated_at = datetime.now(UTC)
        if self.period_start is None:
            self.period_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0)

    def increment_tests(self, count: int = 1) -> None:
        """Increment test execution count"""
        self.tests_executed += count
        self.updated_at = datetime.now(UTC)

    def increment_ai_calls(self, count: int = 1) -> None:
        """Increment AI feature usage"""
        self.ai_feature_calls += count
        self.updated_at = datetime.now(UTC)

    def check_against_limits(self, plan: Plan) -> dict[str, bool]:
        """
        Check current usage against plan limits.

        Returns dict of metric -> is_within_limit
        """
        return {
            "tests_executed": self.tests_executed <= plan.limits.max_tests_per_month
            or plan.limits.max_tests_per_month == -1,
            "users_active": self.users_active <= plan.limits.max_users
            or plan.limits.max_users == -1,
            "suites_created": self.suites_created <= plan.limits.max_suites
            or plan.limits.max_suites == -1,
            "cases_created": self.cases_created <= plan.limits.max_cases_per_suite
            or plan.limits.max_cases_per_suite == -1,
            "storage_used_gb": self.storage_used_gb <= plan.limits.storage_gb
            or plan.limits.storage_gb == -1,
        }
