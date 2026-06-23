"""
Waitlist Routes

API endpoints for waitlist signup and management.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from database import get_db_session as get_db
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import (
    WaitlistEntryCreate,
    WaitlistEntryUpdate,
    WaitlistEntryResponse,
    WaitlistListResponse,
    WaitlistStatus,
    ApiResponse,
)
from services.waitlist_service import (
    create_waitlist_entry,
    get_waitlist_entry_by_id,
    get_waitlist_entry_by_email,
    list_waitlist_entries,
    update_waitlist_entry,
    delete_waitlist_entry,
    get_waitlist_stats,
)
from services.auth_service import get_current_user
from models import User

router = APIRouter(prefix="/waitlist", tags=["Waitlist"])


@router.post(
    "/join",
    response_model=WaitlistEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join waitlist",
    description="Sign up for the waitlist. Public endpoint.",
)
async def join_waitlist(
    entry_data: WaitlistEntryCreate,
    db: AsyncSession = Depends(get_db),
):
    """Join waitlist (public endpoint)."""
    # Check for duplicate email
    existing = await get_waitlist_entry_by_email(db, entry_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already on waitlist",
        )

    entry = await create_waitlist_entry(db, entry_data)
    return entry


@router.get(
    "/check",
    summary="Check waitlist status",
    description="Check if an email is on the waitlist and its status.",
)
async def check_waitlist_status(
    email: str,
    db: AsyncSession = Depends(get_db),
):
    """Check waitlist status (public endpoint)."""
    existing = await get_waitlist_entry_by_email(db, email)
    if not existing:
        return {"registered": False, "status": None}
    return {"registered": True, "status": existing.status}


@router.get(
    "",
    response_model=WaitlistListResponse,
    summary="List waitlist entries",
    description="List all waitlist entries with pagination. Admin only.",
)
async def list_waitlist(
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[WaitlistStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List waitlist entries (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view waitlist",
        )

    skip = (page - 1) * page_size
    entries, total = await list_waitlist_entries(
        db=db, skip=skip, limit=page_size, status=status_filter
    )
    return WaitlistListResponse(
        items=[WaitlistEntryResponse.model_validate(e) for e in entries],
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
    """Get waitlist statistics (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view waitlist stats",
        )
    return await get_waitlist_stats(db)


@router.get(
    "/{entry_id}",
    response_model=WaitlistEntryResponse,
    summary="Get waitlist entry by ID",
    description="Get a specific waitlist entry. Admin only.",
)
async def get_waitlist_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get waitlist entry by ID (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view waitlist entries",
        )

    entry = await get_waitlist_entry_by_id(db, entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist entry not found",
        )
    return entry


@router.patch(
    "/{entry_id}",
    response_model=WaitlistEntryResponse,
    summary="Update waitlist entry",
    description="Update waitlist entry status or notes. Admin only.",
)
async def update_waitlist_entry_endpoint(
    entry_id: int,
    entry_data: WaitlistEntryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update waitlist entry (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update waitlist entries",
        )

    entry = await update_waitlist_entry(db, entry_id, entry_data)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist entry not found",
        )
    return entry


@router.delete(
    "/{entry_id}",
    response_model=ApiResponse,
    summary="Delete waitlist entry",
    description="Delete a waitlist entry. Admin only.",
)
async def delete_waitlist_entry_endpoint(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete waitlist entry (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete waitlist entries",
        )

    deleted = await delete_waitlist_entry(db, entry_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist entry not found",
        )
    return ApiResponse(success=True, message="Waitlist entry deleted")
