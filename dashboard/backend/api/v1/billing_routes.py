"""
Billing Routes - Subscription and Payment Management

This module provides API endpoints for:
- Viewing available plans
- Creating subscriptions
- Managing subscriptions
- Handling webhooks
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import stripe
import json

from database import get_db_session
from services.auth_service import get_current_user
from services import stripe_service
from models import User
from schemas import ApiResponse
from config import settings
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


# Configure Stripe
stripe.api_key = settings.STRIPE_API_KEY


@router.get("/plans")
async def get_plans():
    """Get all available subscription plans"""
    logger.info("Fetching available plans")
    plans = stripe_service.get_all_plans()
    return {"plans": plans}


@router.get("/subscription")
async def get_subscription(
    current_user: User = Depends(get_current_user)
):
    """Get current user's subscription details"""
    logger.info("Fetching subscription details", user_id=current_user.id)
    
    return {
        "plan": current_user.subscription_plan,
        "status": current_user.subscription_status,
        "current_period_start": current_user.subscription_current_period_start,
        "current_period_end": current_user.subscription_current_period_end,
        "features": stripe_service.get_plan_features(current_user.subscription_plan)
    }


@router.post("/subscribe")
async def create_subscription(
    plan_request: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new subscription"""
    plan_id = plan_request.get("plan_id")
    payment_method_id = plan_request.get("payment_method_id")
    
    if not plan_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="plan_id is required"
        )
    
    logger.info("Creating subscription", user_id=current_user.id, plan_id=plan_id)
    
    try:
        result = await stripe_service.create_subscription(
            db, current_user, plan_id, payment_method_id
        )
        return result
    except Exception as e:
        logger.error("Failed to create subscription", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/cancel")
async def cancel_subscription(
    cancel_request: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Cancel current subscription"""
    immediately = cancel_request.get("immediately", False)
    
    logger.info("Cancelling subscription", user_id=current_user.id, immediately=immediately)
    
    try:
        result = await stripe_service.cancel_subscription(db, current_user, immediately)
        return result
    except Exception as e:
        logger.error("Failed to cancel subscription", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/upgrade")
async def upgrade_subscription(
    upgrade_request: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Upgrade or downgrade subscription"""
    new_plan_id = upgrade_request.get("plan_id")
    
    if not new_plan_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="plan_id is required"
        )
    
    logger.info("Updating subscription", user_id=current_user.id, new_plan_id=new_plan_id)
    
    try:
        result = await stripe_service.update_subscription(db, current_user, new_plan_id)
        return result
    except Exception as e:
        logger.error("Failed to update subscription", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Handle Stripe webhook events
    
    This endpoint receives events from Stripe and processes them accordingly.
    Events include: payment success/failure, subscription updates, etc.
    """
    logger.info("Received Stripe webhook")
    
    # Check if signature is present
    if not stripe_signature:
        logger.error("Missing Stripe-Signature header")
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error("Invalid payload", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error("Invalid signature", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error("Webhook construction failed", error=str(e))
        raise HTTPException(status_code=400, detail="Webhook validation failed")
    
    try:
        result = await stripe_service.handle_webhook_event(db, event)
        return result
    except Exception as e:
        logger.error("Failed to process webhook", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/customer")
async def create_customer(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a Stripe customer for the current user"""
    logger.info("Creating Stripe customer", user_id=current_user.id)
    
    if current_user.stripe_customer_id:
        return {"customer_id": current_user.stripe_customer_id, "exists": True}
    
    try:
        customer = await stripe_service.create_stripe_customer(db, current_user)
        return {"customer_id": customer.id, "exists": False}
    except Exception as e:
        logger.error("Failed to create customer", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
