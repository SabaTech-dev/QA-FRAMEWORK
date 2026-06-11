"""
Waitlist Routes

API endpoints for waitlist signup and management for beta access.
Provides public signup, admin listing, and approval flow.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session as get_db
from schemas import (
    WaitlistSignupCreate,
    WaitlistSignupUpdate,
    WaitlistSignupResponse,
    WaitlistSignupListResponse,
    WaitlistSignupStatus,
    ApiResponse,
)
from services.waitlist_service import (
    create_waitlist_signup,
    get_waitlist_signup_by_id,
    get_waitlist_signup_by_email,
    list_waitlist_signups,
    update_waitlist_signup,
    approve_waitlist_signup,
    get_waitlist_stats,
)
from services.auth_service import get_current_user
from models import User

router = APIRouter(prefix="/waitlist", tags=["Waitlist"])


@router.post(
    "/signup",
    response_model=WaitlistSignupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join the waitlist",
    description="Sign up for the waitlist. Public endpoint.",
)
async def signup_for_waitlist(
    signup_data: WaitlistSignupCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Join the waitlist (public endpoint). Requires email, name, and role."""
    # Check if email already exists
    existing = await get_waitlist_signup_by_email(db, signup_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered on the waitlist",
        )

    signup = await create_waitlist_signup(db, signup_data)
    return signup


@router.get(
    "/list",
    response_model=WaitlistSignupListResponse,
    summary="List waitlist signups",
    description="List all waitlist signups with optional filters. Admin only.",
)
async def get_waitlist_list(
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[WaitlistSignupStatus] = None,
    role_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List waitlist signups (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view waitlist signups",
        )

    skip = (page - 1) * page_size
    signups, total = await list_waitlist_signups(
        db=db,
        skip=skip,
        limit=page_size,
        status=status_filter,
        role=role_filter,
    )
    return WaitlistSignupListResponse(
        items=[WaitlistSignupResponse.model_validate(s) for s in signups],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/stats",
    summary="Get waitlist statistics",
    description="Get aggregated waitlist statistics. Admin only.",
)
async def get_waitlist_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get waitlist statistics."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view waitlist statistics",
        )
    stats = await get_waitlist_stats(db)
    return stats


@router.get(
    "/check/{email}",
    summary="Check if email is on waitlist",
    description="Check if an email is already registered on the waitlist.",
)
async def check_waitlist_email(
    email: str,
    db: AsyncSession = Depends(get_db),
):
    """Check if email is already registered."""
    existing = await get_waitlist_signup_by_email(db, email)
    return {"registered": existing is not None}


@router.get(
    "/{signup_id}",
    response_model=WaitlistSignupResponse,
    summary="Get waitlist signup by ID",
    description="Get a specific waitlist signup by ID. Admin only.",
)
async def get_waitlist_signup(
    signup_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get waitlist signup by ID."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view waitlist signups",
        )

    signup = await get_waitlist_signup_by_id(db, signup_id)
    if not signup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist signup not found",
        )
    return signup


@router.patch(
    "/{signup_id}",
    response_model=WaitlistSignupResponse,
    summary="Update waitlist signup",
    description="Update waitlist signup status or notes. Admin only.",
)
async def update_waitlist_signup_endpoint(
    signup_id: int,
    signup_data: WaitlistSignupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update waitlist signup."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update waitlist signups",
        )

    signup = await update_waitlist_signup(db, signup_id, signup_data)
    if not signup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist signup not found",
        )
    return signup


@router.post(
    "/approve/{signup_id}",
    response_model=WaitlistSignupResponse,
    summary="Approve waitlist signup",
    description="Approve a waitlist signup and send invite. Admin only.",
)
async def approve_waitlist_signup_endpoint(
    signup_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve waitlist signup and send welcome email."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can approve waitlist signups",
        )

    signup = await approve_waitlist_signup(db, signup_id)
    if not signup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist signup not found",
        )

    return signup


@router.delete(
    "/{signup_id}",
    response_model=ApiResponse,
    summary="Delete waitlist signup",
    description="Delete waitlist signup. Admin only.",
)
async def delete_waitlist_signup_endpoint(
    signup_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete waitlist signup (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete waitlist signups",
        )

    signup = await get_waitlist_signup_by_id(db, signup_id)
    if not signup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist signup not found",
        )

    await db.delete(signup)
    await db.commit()
    return ApiResponse(success=True, message="Waitlist signup deleted successfully")
