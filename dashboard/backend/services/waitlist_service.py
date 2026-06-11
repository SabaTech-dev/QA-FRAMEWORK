"""
Waitlist Service

Business logic for waitlist signup and management.
Handles public signup, admin listing, approval, and email sending.
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from models import WaitlistSignup
from schemas import (
    WaitlistSignupCreate,
    WaitlistSignupUpdate,
    WaitlistSignupResponse,
    WaitlistSignupStatus,
)
from services.email_service import EmailService


async def create_waitlist_signup(
    db: AsyncSession,
    signup_data: WaitlistSignupCreate,
) -> WaitlistSignup:
    """Create a new waitlist signup."""
    signup = WaitlistSignup(
        email=signup_data.email,
        name=signup_data.name,
        role=signup_data.role,
        company=signup_data.company,
        use_case=signup_data.use_case,
        source=signup_data.source,
        status=WaitlistSignupStatus.pending.value,
    )
    db.add(signup)
    await db.commit()
    await db.refresh(signup)
    return signup


async def get_waitlist_signup_by_id(
    db: AsyncSession, signup_id: int
) -> Optional[WaitlistSignup]:
    """Get waitlist signup by ID."""
    result = await db.execute(
        select(WaitlistSignup).where(WaitlistSignup.id == signup_id)
    )
    return result.scalar_one_or_none()


async def get_waitlist_signup_by_email(
    db: AsyncSession, email: str
) -> Optional[WaitlistSignup]:
    """Get waitlist signup by email."""
    result = await db.execute(
        select(WaitlistSignup).where(WaitlistSignup.email == email)
    )
    return result.scalar_one_or_none()


async def list_waitlist_signups(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    status: Optional[WaitlistSignupStatus] = None,
    role: Optional[str] = None,
) -> tuple[List[WaitlistSignup], int]:
    """List waitlist signups with filters."""
    query = select(WaitlistSignup)

    # Apply filters
    filters = []
    if status:
        filters.append(WaitlistSignup.status == status.value)
    if role:
        filters.append(WaitlistSignup.role == role)

    if filters:
        query = query.where(and_(*filters))

    # Get total count
    count_query = select(func.count()).select_from(WaitlistSignup)
    if filters:
        count_query = count_query.where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.order_by(WaitlistSignup.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    signups = result.scalars().all()

    return list(signups), total


async def update_waitlist_signup(
    db: AsyncSession,
    signup_id: int,
    signup_data: WaitlistSignupUpdate,
) -> Optional[WaitlistSignup]:
    """Update waitlist signup."""
    signup = await get_waitlist_signup_by_id(db, signup_id)
    if not signup:
        return None

    update_data = signup_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(signup, field):
            setattr(signup, field, value)

    # Auto-set timestamps based on status
    new_status = update_data.get("status")
    if new_status == WaitlistSignupStatus.approved and not signup.invite_sent_at:
        signup.invite_sent_at = datetime.utcnow()
        signup.approved_at = datetime.utcnow()
    elif new_status == WaitlistSignupStatus.rejected and not signup.rejected_at:
        signup.rejected_at = datetime.utcnow()

    await db.commit()
    await db.refresh(signup)
    return signup


async def approve_waitlist_signup(
    db: AsyncSession, signup_id: int
) -> Optional[WaitlistSignup]:
    """Approve a waitlist signup and send welcome email."""
    signup = await update_waitlist_signup(
        db,
        signup_id,
        WaitlistSignupUpdate(status=WaitlistSignupStatus.approved),
    )

    if signup:
        # Send welcome email with beta access
        try:
            email_service = EmailService()
            await email_service.send_waitlist_approved(
                email=signup.email,
                name=signup.name,
            )
        except Exception as e:
            # Log but don't fail the approval
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send approval email to {signup.email}: {e}")

    return signup


async def get_waitlist_stats(db: AsyncSession) -> dict:
    """Get waitlist statistics."""
    # Total count
    total_result = await db.execute(select(func.count()).select_from(WaitlistSignup))
    total = total_result.scalar()

    # By status
    status_query = (
        select(WaitlistSignup.status, func.count().label("count"))
        .group_by(WaitlistSignup.status)
    )
    status_result = await db.execute(status_query)
    by_status = {row.status: row.count for row in status_result}

    # By role
    role_query = (
        select(WaitlistSignup.role, func.count().label("count"))
        .where(WaitlistSignup.role.isnot(None))
        .group_by(WaitlistSignup.role)
    )
    role_result = await db.execute(role_query)
    by_role = {row.role: row.count for row in role_result}

    # By source
    source_query = (
        select(WaitlistSignup.source, func.count().label("count"))
        .where(WaitlistSignup.source.isnot(None))
        .group_by(WaitlistSignup.source)
    )
    source_result = await db.execute(source_query)
    by_source = {row.source: row.count for row in source_result}

    # Conversion rate
    approved = by_status.get(WaitlistSignupStatus.approved.value, 0)
    conversion_rate = (approved / total * 100) if total > 0 else 0

    return {
        "total": total,
        "by_status": by_status,
        "by_role": by_role,
        "by_source": by_source,
        "conversion_rate": round(conversion_rate, 2),
    }
