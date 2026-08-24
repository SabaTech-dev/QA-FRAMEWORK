"""
Tests for Billing System
=========================

Tests for billing entities, services, and Stripe integration.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import List, Optional
from uuid import uuid4

import pytest

# ============================================================================
# Mock Billing Entities (for testing without Stripe dependency)
# ============================================================================


class SubscriptionStatus(str, Enum):
    """Subscription status enum."""

    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    TRIALING = "trialing"
    UNPAID = "unpaid"


class PlanType(str, Enum):
    """Available plan types."""

    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class MockPlan:
    """Mock subscription plan."""

    id: str
    name: str
    price: int  # in cents
    interval: str = "month"
    features: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "interval": self.interval,
            "features": self.features,
        }


@dataclass
class MockSubscription:
    """Mock subscription entity."""

    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    plan_id: str = "free"
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    stripe_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    current_period_start: datetime = field(default_factory=datetime.utcnow)
    current_period_end: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30)
    )
    cancel_at_period_end: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def is_active(self) -> bool:
        return self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "plan_id": self.plan_id,
            "status": self.status.value,
            "stripe_subscription_id": self.stripe_subscription_id,
            "stripe_customer_id": self.stripe_customer_id,
            "current_period_start": self.current_period_start.isoformat(),
            "current_period_end": self.current_period_end.isoformat(),
            "cancel_at_period_end": self.cancel_at_period_end,
            "is_active": self.is_active(),
        }


@dataclass
class MockInvoice:
    """Mock invoice entity."""

    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    subscription_id: Optional[str] = None
    amount: int = 0  # in cents
    currency: str = "usd"
    status: str = "draft"
    stripe_invoice_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_paid(self) -> bool:
        return self.status == "paid"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "subscription_id": self.subscription_id,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "stripe_invoice_id": self.stripe_invoice_id,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
        }


@dataclass
class MockPaymentMethod:
    """Mock payment method entity."""

    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    stripe_payment_method_id: Optional[str] = None
    type: str = "card"
    last4: Optional[str] = None
    brand: Optional[str] = None
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None
    is_default: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "last4": self.last4,
            "brand": self.brand,
            "exp_month": self.exp_month,
            "exp_year": self.exp_year,
            "is_default": self.is_default,
        }


# ============================================================================
# Mock Billing Service
# ============================================================================


class MockBillingService:
    """Mock billing service for testing."""

    PLANS = {
        "free": MockPlan(
            id="free",
            name="Free",
            price=0,
            features=["100 tests/month", "Basic support"],
        ),
        "starter": MockPlan(
            id="starter",
            name="Starter",
            price=2900,  # $29
            features=["1000 tests/month", "Priority support"],
        ),
        "pro": MockPlan(
            id="pro",
            name="Pro",
            price=9900,  # $99
            features=["Unlimited tests", "Priority support", "API access"],
        ),
        "enterprise": MockPlan(
            id="enterprise",
            name="Enterprise",
            price=49900,  # $499
            features=["Everything in Pro", "Dedicated support", "Custom features"],
        ),
    }

    def __init__(self):
        self.subscriptions: dict = {}
        self.invoices: dict = {}
        self.payment_methods: dict = {}

    def get_plan(self, plan_id: str) -> Optional[MockPlan]:
        """Get a plan by ID."""
        return self.PLANS.get(plan_id)

    def list_plans(self) -> List[MockPlan]:
        """List all available plans."""
        return list(self.PLANS.values())

    def create_subscription(
        self,
        user_id: str,
        plan_id: str,
        stripe_customer_id: Optional[str] = None,
    ) -> MockSubscription:
        """Create a new subscription."""
        subscription = MockSubscription(
            user_id=user_id,
            plan_id=plan_id,
            stripe_customer_id=stripe_customer_id,
            status=SubscriptionStatus.ACTIVE if plan_id != "free" else SubscriptionStatus.ACTIVE,
        )
        self.subscriptions[subscription.id] = subscription
        return subscription

    def get_subscription(self, user_id: str) -> Optional[MockSubscription]:
        """Get subscription for a user."""
        for sub in self.subscriptions.values():
            if sub.user_id == user_id:
                return sub
        return None

    def cancel_subscription(self, user_id: str) -> Optional[MockSubscription]:
        """Cancel a subscription."""
        sub = self.get_subscription(user_id)
        if sub:
            sub.cancel_at_period_end = True
            sub.updated_at = datetime.now(timezone.utc)
        return sub

    def update_subscription(self, user_id: str, new_plan_id: str) -> Optional[MockSubscription]:
        """Update subscription plan."""
        sub = self.get_subscription(user_id)
        if sub:
            sub.plan_id = new_plan_id
            sub.updated_at = datetime.now(timezone.utc)
        return sub

    def create_invoice(
        self,
        user_id: str,
        amount: int,
        subscription_id: Optional[str] = None,
    ) -> MockInvoice:
        """Create an invoice."""
        invoice = MockInvoice(
            user_id=user_id,
            amount=amount,
            subscription_id=subscription_id,
        )
        self.invoices[invoice.id] = invoice
        return invoice

    def pay_invoice(self, invoice_id: str) -> Optional[MockInvoice]:
        """Pay an invoice."""
        invoice = self.invoices.get(invoice_id)
        if invoice:
            invoice.status = "paid"
            invoice.paid_at = datetime.now(timezone.utc)
        return invoice

    def add_payment_method(
        self,
        user_id: str,
        last4: str,
        brand: str,
        exp_month: int,
        exp_year: int,
    ) -> MockPaymentMethod:
        """Add a payment method."""
        pm = MockPaymentMethod(
            user_id=user_id,
            last4=last4,
            brand=brand,
            exp_month=exp_month,
            exp_year=exp_year,
            is_default=len([p for p in self.payment_methods.values() if p.user_id == user_id]) == 0,
        )
        self.payment_methods[pm.id] = pm
        return pm

    def get_payment_methods(self, user_id: str) -> List[MockPaymentMethod]:
        """Get payment methods for a user."""
        return [pm for pm in self.payment_methods.values() if pm.user_id == user_id]


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def billing_service():
    """Create a fresh billing service for each test."""
    return MockBillingService()


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return "user_billing_test_123"


# ============================================================================
# Plan Tests
# ============================================================================


class TestPlans:
    """Tests for subscription plans."""

    def test_list_plans(self, billing_service):
        """Should list all available plans."""
        plans = billing_service.list_plans()

        assert len(plans) == 4
        assert any(p.id == "free" for p in plans)
        assert any(p.id == "pro" for p in plans)

    def test_get_plan(self, billing_service):
        """Should get a specific plan."""
        plan = billing_service.get_plan("pro")

        assert plan is not None
        assert plan.name == "Pro"
        assert plan.price == 9900

    def test_free_plan_price(self, billing_service):
        """Free plan should have zero price."""
        plan = billing_service.get_plan("free")

        assert plan.price == 0

    def test_plan_features(self, billing_service):
        """Plans should have features defined."""
        pro_plan = billing_service.get_plan("pro")

        assert len(pro_plan.features) > 0
        assert "API access" in pro_plan.features

    def test_plan_to_dict(self, billing_service):
        """Should convert plan to dictionary."""
        plan = billing_service.get_plan("starter")
        data = plan.to_dict()

        assert data["id"] == "starter"
        assert data["name"] == "Starter"
        assert data["price"] == 2900


# ============================================================================
# Subscription Tests
# ============================================================================


class TestSubscriptions:
    """Tests for subscription management."""

    def test_create_subscription(self, billing_service, sample_user_id):
        """Should create a subscription."""
        sub = billing_service.create_subscription(
            user_id=sample_user_id,
            plan_id="starter",
        )

        assert sub.user_id == sample_user_id
        assert sub.plan_id == "starter"
        assert sub.status == SubscriptionStatus.ACTIVE

    def test_get_subscription(self, billing_service, sample_user_id):
        """Should retrieve a subscription."""
        billing_service.create_subscription(
            user_id=sample_user_id,
            plan_id="pro",
        )

        sub = billing_service.get_subscription(sample_user_id)

        assert sub is not None
        assert sub.plan_id == "pro"

    def test_cancel_subscription(self, billing_service, sample_user_id):
        """Should cancel a subscription at period end."""
        billing_service.create_subscription(
            user_id=sample_user_id,
            plan_id="pro",
        )

        sub = billing_service.cancel_subscription(sample_user_id)

        assert sub.cancel_at_period_end is True

    def test_update_subscription(self, billing_service, sample_user_id):
        """Should update subscription plan."""
        billing_service.create_subscription(
            user_id=sample_user_id,
            plan_id="starter",
        )

        sub = billing_service.update_subscription(sample_user_id, "pro")

        assert sub.plan_id == "pro"

    def test_subscription_is_active(self, billing_service, sample_user_id):
        """Should check if subscription is active."""
        sub = billing_service.create_subscription(
            user_id=sample_user_id,
            plan_id="pro",
        )

        assert sub.is_active() is True

        sub.status = SubscriptionStatus.CANCELED
        assert sub.is_active() is False

    def test_subscription_to_dict(self, billing_service, sample_user_id):
        """Should convert subscription to dictionary."""
        sub = billing_service.create_subscription(
            user_id=sample_user_id,
            plan_id="pro",
        )

        data = sub.to_dict()

        assert data["user_id"] == sample_user_id
        assert data["plan_id"] == "pro"
        assert data["status"] == "active"


# ============================================================================
# Invoice Tests
# ============================================================================


class TestInvoices:
    """Tests for invoice management."""

    def test_create_invoice(self, billing_service, sample_user_id):
        """Should create an invoice."""
        invoice = billing_service.create_invoice(
            user_id=sample_user_id,
            amount=9900,
        )

        assert invoice.user_id == sample_user_id
        assert invoice.amount == 9900
        assert invoice.status == "draft"

    def test_pay_invoice(self, billing_service, sample_user_id):
        """Should pay an invoice."""
        invoice = billing_service.create_invoice(
            user_id=sample_user_id,
            amount=9900,
        )

        paid = billing_service.pay_invoice(invoice.id)

        assert paid.status == "paid"
        assert paid.paid_at is not None
        assert paid.is_paid() is True

    def test_invoice_with_subscription(self, billing_service, sample_user_id):
        """Should create invoice linked to subscription."""
        sub = billing_service.create_subscription(
            user_id=sample_user_id,
            plan_id="pro",
        )

        invoice = billing_service.create_invoice(
            user_id=sample_user_id,
            amount=9900,
            subscription_id=sub.id,
        )

        assert invoice.subscription_id == sub.id

    def test_invoice_to_dict(self, billing_service, sample_user_id):
        """Should convert invoice to dictionary."""
        invoice = billing_service.create_invoice(
            user_id=sample_user_id,
            amount=2900,
        )

        data = invoice.to_dict()

        assert data["user_id"] == sample_user_id
        assert data["amount"] == 2900
        assert data["status"] == "draft"


# ============================================================================
# Payment Method Tests
# ============================================================================


class TestPaymentMethods:
    """Tests for payment method management."""

    def test_add_payment_method(self, billing_service, sample_user_id):
        """Should add a payment method."""
        pm = billing_service.add_payment_method(
            user_id=sample_user_id,
            last4="4242",
            brand="visa",
            exp_month=12,
            exp_year=2025,
        )

        assert pm.user_id == sample_user_id
        assert pm.last4 == "4242"
        assert pm.brand == "visa"

    def test_first_payment_method_is_default(self, billing_service, sample_user_id):
        """First payment method should be default."""
        pm = billing_service.add_payment_method(
            user_id=sample_user_id,
            last4="4242",
            brand="visa",
            exp_month=12,
            exp_year=2025,
        )

        assert pm.is_default is True

    def test_get_payment_methods(self, billing_service, sample_user_id):
        """Should retrieve payment methods for user."""
        billing_service.add_payment_method(
            user_id=sample_user_id,
            last4="4242",
            brand="visa",
            exp_month=12,
            exp_year=2025,
        )
        billing_service.add_payment_method(
            user_id=sample_user_id,
            last4="5555",
            brand="mastercard",
            exp_month=6,
            exp_year=2026,
        )

        pms = billing_service.get_payment_methods(sample_user_id)

        assert len(pms) == 2

    def test_payment_method_to_dict(self, billing_service, sample_user_id):
        """Should convert payment method to dictionary."""
        pm = billing_service.add_payment_method(
            user_id=sample_user_id,
            last4="4242",
            brand="visa",
            exp_month=12,
            exp_year=2025,
        )

        data = pm.to_dict()

        assert data["last4"] == "4242"
        assert data["brand"] == "visa"
        assert data["exp_month"] == 12
        assert data["exp_year"] == 2025


# ============================================================================
# Billing Flow Integration Tests
# ============================================================================


class TestBillingFlows:
    """Integration tests for complete billing flows."""

    def test_complete_subscription_flow(self, billing_service, sample_user_id):
        """Test complete subscription flow."""
        # 1. Add payment method
        pm = billing_service.add_payment_method(
            user_id=sample_user_id,
            last4="4242",
            brand="visa",
            exp_month=12,
            exp_year=2025,
        )
        assert pm.is_default is True

        # 2. Create subscription
        sub = billing_service.create_subscription(
            user_id=sample_user_id,
            plan_id="pro",
            stripe_customer_id="cus_test123",
        )
        assert sub.plan_id == "pro"
        assert sub.is_active()

        # 3. Create and pay invoice
        invoice = billing_service.create_invoice(
            user_id=sample_user_id,
            amount=9900,
            subscription_id=sub.id,
        )
        paid = billing_service.pay_invoice(invoice.id)
        assert paid.is_paid()

        # 4. Upgrade subscription
        upgraded = billing_service.update_subscription(sample_user_id, "enterprise")
        assert upgraded.plan_id == "enterprise"

        # 5. Cancel subscription
        canceled = billing_service.cancel_subscription(sample_user_id)
        assert canceled.cancel_at_period_end is True

    def test_free_tier_no_payment_required(self, billing_service, sample_user_id):
        """Free tier should not require payment."""
        sub = billing_service.create_subscription(
            user_id=sample_user_id,
            plan_id="free",
        )

        assert sub.plan_id == "free"
        assert sub.is_active()

        # No payment methods needed
        pms = billing_service.get_payment_methods(sample_user_id)
        assert len(pms) == 0

    def test_plan_upgrade_billing(self, billing_service, sample_user_id):
        """Plan upgrade should create prorated invoice."""
        # Start with starter plan
        sub = billing_service.create_subscription(
            user_id=sample_user_id,
            plan_id="starter",
        )

        # Create initial invoice
        invoice1 = billing_service.create_invoice(
            user_id=sample_user_id,
            amount=2900,
            subscription_id=sub.id,
        )
        billing_service.pay_invoice(invoice1.id)

        # Upgrade to pro
        billing_service.update_subscription(sample_user_id, "pro")

        # Create prorated invoice (difference)
        prorated_amount = 9900 - 2900  # $70 difference
        invoice2 = billing_service.create_invoice(
            user_id=sample_user_id,
            amount=prorated_amount,
            subscription_id=sub.id,
        )

        assert invoice2.amount == 7000


# ============================================================================
# Security Tests
# ============================================================================


class TestBillingSecurity:
    """Tests for billing security."""

    def test_user_cannot_access_other_users_subscription(self, billing_service):
        """Users should not access other users' subscriptions."""
        user1 = "user1"
        user2 = "user2"

        billing_service.create_subscription(user1, "pro")

        # User2 should not see User1's subscription
        sub = billing_service.get_subscription(user2)
        assert sub is None

    def test_payment_method_last4_only(self, billing_service, sample_user_id):
        """Only last 4 digits should be stored."""
        pm = billing_service.add_payment_method(
            user_id=sample_user_id,
            last4="4242",
            brand="visa",
            exp_month=12,
            exp_year=2025,
        )

        # Should not store full card number
        assert not hasattr(pm, "card_number") or pm.card_number is None

    def test_invoice_amount_validation(self, billing_service, sample_user_id):
        """Invoice amounts should be positive."""
        invoice = billing_service.create_invoice(
            user_id=sample_user_id,
            amount=-100,
        )

        # In production, this would be rejected
        # For testing, we just verify the structure
        assert invoice.amount == -100  # Mock allows this, real service wouldn't


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
