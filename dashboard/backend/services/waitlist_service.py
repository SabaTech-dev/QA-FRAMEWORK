"""
Waitlist Service

Business logic for waitlist entry management.
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from models import WaitlistEntry
from schemas import (
    WaitlistEntryCreate,
    WaitlistEntryUpdate,
    WaitlistEntryResponse,
    WaitlistStatus,
)


async def create_waitlist_entry(
    db: AsyncSession,
    entry_data: WaitlistEntryCreate,
) -> WaitlistEntry:
    """Create a new waitlist entry."""
    entry = WaitlistEntry(
        email=entry_data.email,
        name=entry_data.name,
        source=entry_data.source,
        status=WaitlistStatus.pending.value,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def get_waitlist_entry_by_id(db: AsyncSession, entry_id: int) -> Optional[WaitlistEntry]:
    """Get waitlist entry by ID."""
    result = await db.execute(
        select(WaitlistEntry).where(WaitlistEntry.id == entry_id)
    )
    return result.scalar_one_or_none()


async def get_waitlist_entry_by_email(db: AsyncSession, email: str) -> Optional[WaitlistEntry]:
    """Get waitlist entry by email."""
    result = await db.execute(
        select(WaitlistEntry).where(WaitlistEntry.email == email)
    )
    return result.scalar_one_or_none()


async def list_waitlist_entries(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    status: Optional[WaitlistStatus] = None,
) -> tuple[List[WaitlistEntry], int]:
    """List waitlist entries with optional filters."""
    query = select(WaitlistEntry)

    filters = []
    if status:
        filters.append(WaitlistEntry.status == status.value)

    if filters:
        query = query.where(and_(*filters))

    # Total count
    count_query = select(func.count()).select_from(WaitlistEntry)
    if filters:
        count_query = count_query.where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginated results
    query = query.order_by(WaitlistEntry.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    entries = result.scalars().all()

    return list(entries), total


async def update_waitlist_entry(
    db: AsyncSession,
    entry_id: int,
    entry_data: WaitlistEntryUpdate,
) -> Optional[WaitlistEntry]:
    """Update waitlist entry."""
    entry = await get_waitlist_entry_by_id(db, entry_id)
    if not entry:
        return None

    update_data = entry_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(entry, field):
            setattr(entry, field, value)

    await db.commit()
    await db.refresh(entry)
    return entry


async def delete_waitlist_entry(db: AsyncSession, entry_id: int) -> bool:
    """Delete waitlist entry."""
    entry = await get_waitlist_entry_by_id(db, entry_id)
    if not entry:
        return False

    await db.delete(entry)
    await db.commit()
    return True


async def get_waitlist_stats(db: AsyncSession) -> dict:
    """Get waitlist statistics."""
    total_result = await db.execute(select(func.count()).select_from(WaitlistEntry))
    total = total_result.scalar()

    status_query = (
        select(WaitlistEntry.status, func.count().label("count"))
        .group_by(WaitlistEntry.status)
    )
    status_result = await db.execute(status_query)
    by_status = {row.status: row.count for row in status_result}

    return {
        "total": total,
        "by_status": by_status,
        "pending": by_status.get(WaitlistStatus.pending.value, 0),
        "contacted": by_status.get(WaitlistStatus.contacted.value, 0),
        "converted": by_status.get(WaitlistStatus.converted.value, 0),
    }
