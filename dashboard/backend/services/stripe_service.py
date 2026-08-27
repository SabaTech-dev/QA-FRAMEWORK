"""
Stripe Service - Subscription and Billing Management

This module handles all Stripe-related operations including:
- Customer management
- Subscription lifecycle
- Payment processing
- Webhook handling
"""

import stripe
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User
from core.logging_config import get_logger
from config import settings

logger = get_logger(__name__)

# Configure Stripe API key
stripe.api_key = settings.STRIPE_API_KEY.get_secret_value() if settings.STRIPE_API_KEY else None


# Pricing Plans - Uses Stripe Price IDs from config
PRICING_PLANS = {
    "free": {
        "name": "Free",
        "price": 0,
        "price_id": settings.STRIPE_PRICE_FREE,
        "product_id": settings.STRIPE_PRODUCT_FREE,
        "features": {
            "max_suites": 3,
            "max_cases_per_suite": 10,
            "max_executions_per_month": 100,
            "ai_healing": False,
            "api_access": False,
            "priority_support": False,
        },
    },
    "pro": {
        "name": "Pro",
        "price": 29,
        "price_id": settings.STRIPE_PRICE_PRO,
        "product_id": settings.STRIPE_PRODUCT_PRO,
        "features": {
            "max_suites": 50,
            "max_cases_per_suite": 100,
            "max_executions_per_month": 10000,
            "ai_healing": True,
            "api_access": True,
            "priority_support": False,
        },
    },
    "enterprise": {
        "name": "Enterprise",
        "price": 99,
        "price_id": settings.STRIPE_PRICE_ENTERPRISE,
        "product_id": settings.STRIPE_PRODUCT_ENTERPRISE,
        "features": {
            "max_suites": -1,  # Unlimited
            "max_cases_per_suite": -1,  # Unlimited
            "max_executions_per_month": -1,  # Unlimited
            "ai_healing": True,
            "api_access": True,
            "priority_support": True,
        },
    },
}


async def create_stripe_customer(
    db: AsyncSession, user: User, payment_method_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a Stripe customer for a user

    Args:
        db: Database session
        user: User to create customer for
        payment_method_id: Optional payment method to attach

    Returns:
        Stripe customer object
    """
    logger.info("Creating Stripe customer", user_id=user.id, email=user.email)

    try:
        # Create customer in Stripe
        customer_data = {
            "email": user.email,
            "name": user.username,
            "metadata": {
                "user_id": str(user.id),
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            },
        }

        customer = stripe.Customer.create(**customer_data)

        # Attach payment method if provided
        if payment_method_id:
            stripe.PaymentMethod.attach(payment_method_id, customer=customer.id)
            stripe.Customer.modify(
                customer.id, invoice_settings={"default_payment_method": payment_method_id}
            )

        # Update user with Stripe customer ID
        user.stripe_customer_id = customer.id
        user.subscription_plan = "free"
        await db.commit()

        logger.info("Stripe customer created successfully", customer_id=customer.id)
        return customer

    except stripe.error.StripeError as e:
        logger.error("Failed to create Stripe customer", error=str(e))
        raise Exception(f"Failed to create customer: {str(e)}")


async def create_subscription(
    db: AsyncSession, user: User, plan_id: str, payment_method_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a subscription for a user

    Args:
        db: Database session
        user: User to create subscription for
        plan_id: Plan ID (free, pro, enterprise)
        payment_method_id: Payment method ID

    Returns:
        Stripe subscription object
    """
    logger.info("Creating subscription", user_id=user.id, plan_id=plan_id)

    if plan_id not in PRICING_PLANS:
        raise ValueError(f"Invalid plan ID: {plan_id}")

    plan = PRICING_PLANS[plan_id]

    # Free tier doesn't need Stripe subscription
    if plan_id == "free":
        user.subscription_plan = "free"
        user.subscription_status = "active"
        await db.commit()
        return {"status": "active", "plan": "free"}

    # Ensure customer exists
    if not user.stripe_customer_id:
        await create_stripe_customer(db, user, payment_method_id)

    try:
        # Create subscription in Stripe
        subscription = stripe.Subscription.create(
            customer=user.stripe_customer_id,
            items=[{"price": plan["price_id"]}],
            payment_behavior="default_incomplete",
            expand=["latest_invoice.payment_intent"],
        )

        # Update user subscription info
        user.subscription_plan = plan_id
        user.subscription_status = subscription.status
        user.stripe_subscription_id = subscription.id
        user.subscription_current_period_start = datetime.fromtimestamp(
            subscription.current_period_start
        )
        user.subscription_current_period_end = datetime.fromtimestamp(
            subscription.current_period_end
        )
        await db.commit()

        logger.info(
            "Subscription created successfully", subscription_id=subscription.id, plan_id=plan_id
        )

        return {
            "subscription_id": subscription.id,
            "status": subscription.status,
            "client_secret": subscription.latest_invoice.payment_intent.client_secret,
        }

    except stripe.error.StripeError as e:
        logger.error("Failed to create subscription", error=str(e))
        raise Exception(f"Failed to create subscription: {str(e)}")


async def cancel_subscription(
    db: AsyncSession, user: User, immediately: bool = False
) -> Dict[str, Any]:
    """
    Cancel a user's subscription

    Args:
        db: Database session
        user: User to cancel subscription for
        immediately: Cancel immediately or at period end

    Returns:
        Cancellation result
    """
    logger.info("Cancelling subscription", user_id=user.id, immediately=immediately)

    if not user.stripe_subscription_id:
        logger.warning("No active subscription to cancel", user_id=user.id)
        return {"status": "no_subscription"}

    try:
        if immediately:
            subscription = stripe.Subscription.delete(user.stripe_subscription_id)
        else:
            subscription = stripe.Subscription.modify(
                user.stripe_subscription_id, cancel_at_period_end=True
            )

        user.subscription_status = "canceled" if immediately else "canceling"
        await db.commit()

        logger.info("Subscription cancelled", subscription_id=user.stripe_subscription_id)
        return {"status": subscription.status}

    except stripe.error.StripeError as e:
        logger.error("Failed to cancel subscription", error=str(e))
        raise Exception(f"Failed to cancel subscription: {str(e)}")


async def update_subscription(db: AsyncSession, user: User, new_plan_id: str) -> Dict[str, Any]:
    """
    Update a user's subscription to a new plan

    Args:
        db: Database session
        user: User to update subscription for
        new_plan_id: New plan ID

    Returns:
        Updated subscription
    """
    logger.info("Updating subscription", user_id=user.id, new_plan_id=new_plan_id)

    if new_plan_id not in PRICING_PLANS:
        raise ValueError(f"Invalid plan ID: {new_plan_id}")

    if not user.stripe_subscription_id:
        # No existing subscription, create new one
        return await create_subscription(db, user, new_plan_id)

    new_plan = PRICING_PLANS[new_plan_id]

    try:
        # Get current subscription
        subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)

        # Update subscription item
        stripe.Subscription.modify(
            user.stripe_subscription_id,
            items=[{"id": subscription["items"]["data"][0].id, "price": new_plan["price_id"]}],
        )

        user.subscription_plan = new_plan_id
        await db.commit()

        logger.info("Subscription updated successfully", new_plan_id=new_plan_id)
        return {"status": "updated", "plan": new_plan_id}

    except stripe.error.StripeError as e:
        logger.error("Failed to update subscription", error=str(e))
        raise Exception(f"Failed to update subscription: {str(e)}")


async def handle_webhook_event(db: AsyncSession, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle Stripe webhook events

    Args:
        db: Database session
        event: Stripe event object

    Returns:
        Processing result
    """
    event_type = event["type"]
    logger.info("Processing Stripe webhook", event_type=event_type)

    try:
        if event_type == "invoice.payment_succeeded":
            return await _handle_payment_succeeded(db, event)
        elif event_type == "invoice.payment_failed":
            return await _handle_payment_failed(db, event)
        elif event_type == "customer.subscription.updated":
            return await _handle_subscription_updated(db, event)
        elif event_type == "customer.subscription.deleted":
            return await _handle_subscription_deleted(db, event)
        else:
            logger.info("Unhandled webhook event type", event_type=event_type)
            return {"status": "ignored"}

    except Exception as e:
        logger.error("Failed to process webhook", event_type=event_type, error=str(e))
        raise


async def _handle_payment_succeeded(db: AsyncSession, event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle successful payment"""
    invoice = event["data"]["object"]
    customer_id = invoice["customer"]

    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()

    if user:
        user.subscription_status = "active"
        await db.commit()
        logger.info("Payment succeeded", user_id=user.id)

    return {"status": "processed"}


async def _handle_payment_failed(db: AsyncSession, event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle failed payment"""
    invoice = event["data"]["object"]
    customer_id = invoice["customer"]

    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()

    if user:
        user.subscription_status = "past_due"
        await db.commit()
        logger.warning("Payment failed", user_id=user.id)

    return {"status": "processed"}


async def _handle_subscription_updated(db: AsyncSession, event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle subscription update"""
    subscription = event["data"]["object"]
    customer_id = subscription["customer"]

    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()

    if user:
        user.subscription_status = subscription["status"]
        user.subscription_current_period_start = datetime.fromtimestamp(
            subscription["current_period_start"]
        )
        user.subscription_current_period_end = datetime.fromtimestamp(
            subscription["current_period_end"]
        )
        await db.commit()
        logger.info("Subscription updated", user_id=user.id)

    return {"status": "processed"}


async def _handle_subscription_deleted(db: AsyncSession, event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle subscription deletion"""
    subscription = event["data"]["object"]
    customer_id = subscription["customer"]

    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()

    if user:
        user.subscription_plan = "free"
        user.subscription_status = "canceled"
        user.stripe_subscription_id = None
        await db.commit()
        logger.info("Subscription deleted, downgraded to free", user_id=user.id)

    return {"status": "processed"}


def get_plan_features(plan_id: str) -> Dict[str, Any]:
    """Get features for a specific plan"""
    if plan_id not in PRICING_PLANS:
        raise ValueError(f"Invalid plan ID: {plan_id}")
    return PRICING_PLANS[plan_id]["features"]


def get_all_plans() -> List[Dict[str, Any]]:
    """Get all available plans"""
    return [
        {"id": plan_id, "name": plan["name"], "price": plan["price"], "features": plan["features"]}
        for plan_id, plan in PRICING_PLANS.items()
    ]
