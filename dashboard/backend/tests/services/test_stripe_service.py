"""
Unit Tests for Stripe Service

Tests subscription and billing management with comprehensive mocking.
"""
import pytest
pytest.importorskip('fastapi')
pytest.importorskip('asyncpg')
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from fastapi import HTTPException

from services.stripe_service import (
    create_stripe_customer,
    create_subscription,
    cancel_subscription,
    update_subscription,
    handle_webhook_event,
    get_plan_features,
    get_all_plans,
    PRICING_PLANS
)
from models import User


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """Mock user instance"""
    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed",
        stripe_customer_id=None,
        stripe_subscription_id=None,
        subscription_plan="free",
        subscription_status="active"
    )
    return user


@pytest.fixture
def mock_stripe_customer():
    """Mock Stripe customer object"""
    customer = Mock()
    customer.id = "cus_test123"
    return customer


@pytest.fixture
def mock_stripe_subscription():
    """Mock Stripe subscription object"""
    subscription = Mock()
    subscription.id = "sub_test123"
    subscription.status = "active"
    subscription.current_period_start = 1704067200  # 2024-01-01
    subscription.current_period_end = 1706745600  # 2024-02-01
    
    # Mock latest_invoice with payment_intent
    invoice = Mock()
    payment_intent = Mock()
    payment_intent.client_secret = "pi_secret_test"
    invoice.payment_intent = payment_intent
    subscription.latest_invoice = invoice
    
    # Mock items
    item = Mock()
    item.id = "si_test123"
    subscription.items = {"data": [item]}
    
    return subscription


class TestCreateStripeCustomer:
    """Tests for create_stripe_customer function"""
    
    @pytest.mark.asyncio
    async def test_create_customer_success(self, mock_db, mock_user, mock_stripe_customer):
        """Test successful customer creation"""
        with patch('services.stripe_service.stripe.Customer') as mock_customer_api:
            mock_customer_api.create.return_value = mock_stripe_customer
            
            result = await create_stripe_customer(mock_db, mock_user)
            
            # Verify Stripe API called with correct params
            mock_customer_api.create.assert_called_once()
            call_args = mock_customer_api.create.call_args[1]
            assert call_args["email"] == mock_user.email
            assert call_args["name"] == mock_user.username
            assert call_args["metadata"]["user_id"] == str(mock_user.id)
            
            # Verify user updated
            assert mock_user.stripe_customer_id == "cus_test123"
            assert mock_user.subscription_plan == "free"
            mock_db.commit.assert_called_once()
            
            # Verify result
            assert result.id == "cus_test123"
    
    @pytest.mark.asyncio
    async def test_create_customer_with_payment_method(self, mock_db, mock_user, mock_stripe_customer):
        """Test customer creation with payment method attachment"""
        with patch('services.stripe_service.stripe.Customer') as mock_customer_api, \
             patch('services.stripe_service.stripe.PaymentMethod') as mock_pm_api:
            
            mock_customer_api.create.return_value = mock_stripe_customer
            mock_pm_api.attach = Mock()
            mock_customer_api.modify = Mock()
            
            result = await create_stripe_customer(mock_db, mock_user, "pm_test123")
            
            # Verify payment method attached
            mock_pm_api.attach.assert_called_once_with(
                "pm_test123",
                customer="cus_test123"
            )
            
            # Verify customer modified with default payment method
            mock_customer_api.modify.assert_called_once_with(
                "cus_test123",
                invoice_settings={"default_payment_method": "pm_test123"}
            )
            
            assert result.id == "cus_test123"
    
    @pytest.mark.asyncio
    async def test_create_customer_stripe_error(self, mock_db, mock_user):
        """Test customer creation with Stripe error"""
        import stripe
        
        with patch('services.stripe_service.stripe.Customer') as mock_customer_api:
            mock_customer_api.create.side_effect = stripe.error.StripeError("API error")
            
            with pytest.raises(Exception) as exc_info:
                await create_stripe_customer(mock_db, mock_user)
            
            assert "Failed to create customer" in str(exc_info.value)


class TestCreateSubscription:
    """Tests for create_subscription function"""
    
    @pytest.mark.asyncio
    async def test_create_subscription_free_plan(self, mock_db, mock_user):
        """Test creating free plan subscription"""
        result = await create_subscription(mock_db, mock_user, "free")
        
        # Verify user updated for free tier
        assert mock_user.subscription_plan == "free"
        assert mock_user.subscription_status == "active"
        mock_db.commit.assert_called_once()
        
        # Verify result
        assert result["status"] == "active"
        assert result["plan"] == "free"
    
    @pytest.mark.asyncio
    async def test_create_subscription_invalid_plan(self, mock_db, mock_user):
        """Test creating subscription with invalid plan"""
        with pytest.raises(ValueError) as exc_info:
            await create_subscription(mock_db, mock_user, "invalid_plan")
        
        assert "Invalid plan ID" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_create_subscription_pro_plan(self, mock_db, mock_user, mock_stripe_subscription):
        """Test creating pro plan subscription"""
        mock_user.stripe_customer_id = "cus_test123"
        
        with patch('services.stripe_service.stripe.Subscription') as mock_sub_api:
            mock_sub_api.create.return_value = mock_stripe_subscription
            
            result = await create_subscription(mock_db, mock_user, "pro")
            
            # Verify Stripe API called
            mock_sub_api.create.assert_called_once()
            call_args = mock_sub_api.create.call_args[1]
            assert call_args["customer"] == "cus_test123"
            assert call_args["items"][0]["price"] == "price_pro_monthly"
            
            # Verify user updated
            assert mock_user.subscription_plan == "pro"
            assert mock_user.subscription_status == "active"
            assert mock_user.stripe_subscription_id == "sub_test123"
            
            # Verify result
            assert result["subscription_id"] == "sub_test123"
            assert result["status"] == "active"
            assert result["client_secret"] == "pi_secret_test"
    
    @pytest.mark.asyncio
    async def test_create_subscription_creates_customer_if_needed(self, mock_db, mock_user, mock_stripe_customer, mock_stripe_subscription):
        """Test subscription creates customer if not exists"""
        mock_user.stripe_customer_id = None
        
        with patch('services.stripe_service.stripe.Customer') as mock_customer_api, \
             patch('services.stripe_service.stripe.Subscription') as mock_sub_api:
            
            mock_customer_api.create.return_value = mock_stripe_customer
            mock_sub_api.create.return_value = mock_stripe_subscription
            
            result = await create_subscription(mock_db, mock_user, "pro")
            
            # Verify customer created first
            mock_customer_api.create.assert_called_once()
            
            # Verify subscription created
            mock_sub_api.create.assert_called_once()
            
            assert result["subscription_id"] == "sub_test123"
    
    @pytest.mark.asyncio
    async def test_create_subscription_stripe_error(self, mock_db, mock_user):
        """Test subscription creation with Stripe error"""
        import stripe
        
        mock_user.stripe_customer_id = "cus_test123"
        
        with patch('services.stripe_service.stripe.Subscription') as mock_sub_api:
            mock_sub_api.create.side_effect = stripe.error.StripeError("API error")
            
            with pytest.raises(Exception) as exc_info:
                await create_subscription(mock_db, mock_user, "pro")
            
            assert "Failed to create subscription" in str(exc_info.value)


class TestCancelSubscription:
    """Tests for cancel_subscription function"""
    
    @pytest.mark.asyncio
    async def test_cancel_subscription_no_subscription(self, mock_db, mock_user):
        """Test canceling when no subscription exists"""
        mock_user.stripe_subscription_id = None
        
        result = await cancel_subscription(mock_db, mock_user)
        
        assert result["status"] == "no_subscription"
    
    @pytest.mark.asyncio
    async def test_cancel_subscription_immediately(self, mock_db, mock_user, mock_stripe_subscription):
        """Test immediate subscription cancellation"""
        mock_user.stripe_subscription_id = "sub_test123"
        
        with patch('services.stripe_service.stripe.Subscription') as mock_sub_api:
            mock_sub_api.delete.return_value = mock_stripe_subscription
            
            result = await cancel_subscription(mock_db, mock_user, immediately=True)
            
            # Verify Stripe API called
            mock_sub_api.delete.assert_called_once_with("sub_test123")
            
            # Verify user updated
            assert mock_user.subscription_status == "canceled"
            mock_db.commit.assert_called()
            
            assert result["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_cancel_subscription_at_period_end(self, mock_db, mock_user, mock_stripe_subscription):
        """Test subscription cancellation at period end"""
        mock_user.stripe_subscription_id = "sub_test123"
        
        with patch('services.stripe_service.stripe.Subscription') as mock_sub_api:
            mock_sub_api.modify.return_value = mock_stripe_subscription
            
            result = await cancel_subscription(mock_db, mock_user, immediately=False)
            
            # Verify Stripe API called
            mock_sub_api.modify.assert_called_once_with(
                "sub_test123",
                cancel_at_period_end=True
            )
            
            # Verify user updated
            assert mock_user.subscription_status == "canceling"
            
            assert result["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_cancel_subscription_stripe_error(self, mock_db, mock_user):
        """Test cancellation with Stripe error"""
        import stripe
        
        mock_user.stripe_subscription_id = "sub_test123"
        
        with patch('services.stripe_service.stripe.Subscription') as mock_sub_api:
            mock_sub_api.delete.side_effect = stripe.error.StripeError("API error")
            
            with pytest.raises(Exception) as exc_info:
                await cancel_subscription(mock_db, mock_user, immediately=True)
            
            assert "Failed to cancel subscription" in str(exc_info.value)


class TestUpdateSubscription:
    """Tests for update_subscription function"""
    
    @pytest.mark.asyncio
    async def test_update_subscription_invalid_plan(self, mock_db, mock_user):
        """Test updating to invalid plan"""
        with pytest.raises(ValueError) as exc_info:
            await update_subscription(mock_db, mock_user, "invalid_plan")
        
        assert "Invalid plan ID" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update_subscription_creates_new_if_none(self, mock_db, mock_user, mock_stripe_customer, mock_stripe_subscription):
        """Test update creates new subscription if none exists"""
        mock_user.stripe_subscription_id = None
        
        with patch('services.stripe_service.create_subscription') as mock_create:
            mock_create.return_value = {"subscription_id": "sub_new", "status": "active"}
            
            result = await update_subscription(mock_db, mock_user, "pro")
            
            # Verify create_subscription called
            mock_create.assert_called_once_with(mock_db, mock_user, "pro")
            assert result["subscription_id"] == "sub_new"
    
    @pytest.mark.asyncio
    async def test_update_subscription_success(self, mock_db, mock_user):
        """Test successful subscription update"""
        mock_user.stripe_subscription_id = "sub_test123"
        
        # Create a subscription mock that behaves like a dict
        mock_subscription = Mock()
        mock_subscription.id = "sub_test123"
        mock_subscription.status = "active"
        
        # Mock the subscription item
        mock_item = Mock()
        mock_item.id = "si_test123"
        
        # Make subscription subscriptable for ["items"]["data"][0].id
        mock_subscription.__getitem__ = Mock(side_effect=lambda key: {
            "items": {
                "data": [mock_item]
            }
        }[key])
        
        with patch('services.stripe_service.stripe.Subscription') as mock_sub_api:
            mock_sub_api.retrieve.return_value = mock_subscription
            mock_sub_api.modify.return_value = mock_subscription
            
            result = await update_subscription(mock_db, mock_user, "enterprise")
            
            # Verify retrieve called
            mock_sub_api.retrieve.assert_called_once_with("sub_test123")
            
            # Verify modify called
            mock_sub_api.modify.assert_called_once()
            call_args = mock_sub_api.modify.call_args[1]
            assert call_args["items"][0]["id"] == "si_test123"
            assert call_args["items"][0]["price"] == "price_enterprise_monthly"
            
            # Verify user updated
            assert mock_user.subscription_plan == "enterprise"
            mock_db.commit.assert_called()
            
            assert result["status"] == "updated"
            assert result["plan"] == "enterprise"
    
    @pytest.mark.asyncio
    async def test_update_subscription_stripe_error(self, mock_db, mock_user):
        """Test update with Stripe error"""
        import stripe
        
        mock_user.stripe_subscription_id = "sub_test123"
        
        # Create a subscription mock that behaves like a dict
        mock_subscription = Mock()
        mock_item = Mock()
        mock_item.id = "si_test123"
        mock_subscription.__getitem__ = Mock(side_effect=lambda key: {
            "items": {
                "data": [mock_item]
            }
        }[key])
        
        with patch('services.stripe_service.stripe.Subscription') as mock_sub_api:
            mock_sub_api.retrieve.return_value = mock_subscription
            mock_sub_api.modify.side_effect = stripe.error.StripeError("API error")
            
            with pytest.raises(Exception) as exc_info:
                await update_subscription(mock_db, mock_user, "pro")
            
            assert "Failed to update subscription" in str(exc_info.value)


class TestHandleWebhookEvent:
    """Tests for handle_webhook_event function"""
    
    @pytest.mark.asyncio
    async def test_handle_payment_succeeded(self, mock_db, mock_user):
        """Test handling payment succeeded event"""
        event = {
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    "customer": "cus_test123"
                }
            }
        }
        
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_user)
        mock_db.execute.return_value = mock_result
        mock_user.stripe_customer_id = "cus_test123"
        
        result = await handle_webhook_event(mock_db, event)
        
        assert result["status"] == "processed"
        assert mock_user.subscription_status == "active"
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_payment_failed(self, mock_db, mock_user):
        """Test handling payment failed event"""
        event = {
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "customer": "cus_test123"
                }
            }
        }
        
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_user)
        mock_db.execute.return_value = mock_result
        mock_user.stripe_customer_id = "cus_test123"
        
        result = await handle_webhook_event(mock_db, event)
        
        assert result["status"] == "processed"
        assert mock_user.subscription_status == "past_due"
    
    @pytest.mark.asyncio
    async def test_handle_subscription_updated(self, mock_db, mock_user):
        """Test handling subscription updated event"""
        event = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "customer": "cus_test123",
                    "status": "active",
                    "current_period_start": 1704067200,
                    "current_period_end": 1706745600
                }
            }
        }
        
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_user)
        mock_db.execute.return_value = mock_result
        mock_user.stripe_customer_id = "cus_test123"
        
        result = await handle_webhook_event(mock_db, event)
        
        assert result["status"] == "processed"
        assert mock_user.subscription_status == "active"
    
    @pytest.mark.asyncio
    async def test_handle_subscription_deleted(self, mock_db, mock_user):
        """Test handling subscription deleted event"""
        event = {
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "customer": "cus_test123"
                }
            }
        }
        
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_user)
        mock_db.execute.return_value = mock_result
        mock_user.stripe_customer_id = "cus_test123"
        mock_user.stripe_subscription_id = "sub_test123"
        
        result = await handle_webhook_event(mock_db, event)
        
        assert result["status"] == "processed"
        assert mock_user.subscription_plan == "free"
        assert mock_user.subscription_status == "canceled"
        assert mock_user.stripe_subscription_id is None
    
    @pytest.mark.asyncio
    async def test_handle_unhandled_event(self, mock_db):
        """Test handling unhandled event type"""
        event = {
            "type": "unknown.event",
            "data": {"object": {}}
        }
        
        result = await handle_webhook_event(mock_db, event)
        
        assert result["status"] == "ignored"
    
    @pytest.mark.asyncio
    async def test_handle_webhook_user_not_found(self, mock_db):
        """Test webhook when user not found"""
        event = {
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    "customer": "cus_unknown"
                }
            }
        }
        
        # Mock database query returning None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result
        
        result = await handle_webhook_event(mock_db, event)
        
        # Should still return processed
        assert result["status"] == "processed"
        # But no commit should happen
        mock_db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_webhook_error(self, mock_db):
        """Test webhook handling with error"""
        event = {
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    "customer": "cus_test123"
                }
            }
        }
        
        # Mock database error
        mock_db.execute.side_effect = Exception("Database error")
        
        with pytest.raises(Exception):
            await handle_webhook_event(mock_db, event)


class TestPlanFeatures:
    """Tests for plan feature functions"""
    
    def test_get_plan_features_free(self):
        """Test getting free plan features"""
        features = get_plan_features("free")
        
        assert features["max_suites"] == 3
        assert features["max_cases_per_suite"] == 10
        assert features["ai_healing"] is False
        assert features["api_access"] is False
    
    def test_get_plan_features_pro(self):
        """Test getting pro plan features"""
        features = get_plan_features("pro")
        
        assert features["max_suites"] == 50
        assert features["ai_healing"] is True
        assert features["api_access"] is True
    
    def test_get_plan_features_enterprise(self):
        """Test getting enterprise plan features"""
        features = get_plan_features("enterprise")
        
        assert features["max_suites"] == -1  # Unlimited
        assert features["priority_support"] is True
    
    def test_get_plan_features_invalid(self):
        """Test getting invalid plan features"""
        with pytest.raises(ValueError) as exc_info:
            get_plan_features("invalid")
        
        assert "Invalid plan ID" in str(exc_info.value)
    
    def test_get_all_plans(self):
        """Test getting all plans"""
        plans = get_all_plans()
        
        assert len(plans) == 3
        
        # Verify each plan has required fields
        for plan in plans:
            assert "id" in plan
            assert "name" in plan
            assert "price" in plan
            assert "features" in plan
        
        # Verify specific plans
        plan_ids = [p["id"] for p in plans]
        assert "free" in plan_ids
        assert "pro" in plan_ids
        assert "enterprise" in plan_ids


class TestPricingPlans:
    """Tests for pricing plans configuration"""
    
    def test_pricing_plans_structure(self):
        """Test pricing plans have correct structure"""
        for plan_id, plan in PRICING_PLANS.items():
            assert "name" in plan
            assert "price" in plan
            assert "price_id" in plan
            assert "features" in plan
            
            # Verify features
            features = plan["features"]
            assert "max_suites" in features
            assert "max_cases_per_suite" in features
            assert "max_executions_per_month" in features
            assert "ai_healing" in features
            assert "api_access" in features
            assert "priority_support" in features
    
    def test_free_tier_no_stripe_price(self):
        """Test free tier has no Stripe price"""
        assert PRICING_PLANS["free"]["price_id"] is None
        assert PRICING_PLANS["free"]["price"] == 0
    
    def test_paid_tiers_have_stripe_price(self):
        """Test paid tiers have Stripe price IDs"""
        assert PRICING_PLANS["pro"]["price_id"] is not None
        assert PRICING_PLANS["enterprise"]["price_id"] is not None


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=services/stripe_service", "--cov-report=term-missing"])
