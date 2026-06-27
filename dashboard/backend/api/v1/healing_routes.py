"""
Self-Healing API Routes

CRUD endpoints for healing selectors, the heal action and session/result
inspection. Every endpoint requires JWT authentication via get_current_user.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session as get_db
from schemas.self_healing import (
    HealingSelectorCreate,
    HealingSelectorResponse,
    HealingSelectorUpdate,
    HealingSessionResponse,
    HealingResultResponse,
    HealResponse,
)
from services.auth_service import get_current_user
from services.healing_service import (
    create_selector_service,
    list_selectors_service,
    get_selector_by_id,
    update_selector_service,
    delete_selector_service,
    heal_selector_service,
    list_sessions_service,
    get_session_by_id,
    list_results_service,
)
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/healing", tags=["self-healing"])


# ─── Selectors ────────────────────────────────────────────────────
@router.get(
    "/selectors",
    response_model=List[HealingSelectorResponse],
    summary="List healing selectors",
)
async def list_selectors(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return a paginated list of active healing selectors."""
    logger.info("Listing healing selectors via API", skip=skip, limit=limit)
    return await list_selectors_service(skip=skip, limit=limit, db=db)


@router.post(
    "/selectors",
    response_model=HealingSelectorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a healing selector",
)
async def create_selector(
    selector_data: HealingSelectorCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Register a new selector to track for self-healing."""
    logger.info(
        "Creating healing selector via API",
        value=selector_data.value,
        user_id=current_user.id,
    )
    return await create_selector_service(selector_data, db)


@router.get(
    "/selectors/{selector_id}",
    response_model=HealingSelectorResponse,
    summary="Get a healing selector",
)
async def get_selector(
    selector_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return a single healing selector by id."""
    logger.info("Getting healing selector via API", selector_id=selector_id)
    return await get_selector_by_id(selector_id, db)


@router.put(
    "/selectors/{selector_id}",
    response_model=HealingSelectorResponse,
    summary="Update a healing selector",
)
async def update_selector(
    selector_id: int,
    selector_update: HealingSelectorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update editable fields of a healing selector."""
    logger.info("Updating healing selector via API", selector_id=selector_id)
    return await update_selector_service(selector_id, selector_update, db)


@router.delete(
    "/selectors/{selector_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a healing selector",
)
async def delete_selector(
    selector_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Soft delete a healing selector."""
    logger.info("Deleting healing selector via API", selector_id=selector_id)
    await delete_selector_service(selector_id, db)
    return None


@router.post(
    "/selectors/{selector_id}/heal",
    response_model=HealResponse,
    summary="Heal a selector",
)
async def heal_selector(
    selector_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Trigger self-healing for a single selector and return the result."""
    logger.info("Healing selector via API", selector_id=selector_id, user_id=current_user.id)
    return await heal_selector_service(selector_id, db)


# ─── Sessions ─────────────────────────────────────────────────────
@router.get(
    "/sessions",
    response_model=List[HealingSessionResponse],
    summary="List healing sessions",
)
async def list_sessions(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return a paginated list of healing sessions."""
    logger.info("Listing healing sessions via API", skip=skip, limit=limit)
    return await list_sessions_service(skip=skip, limit=limit, db=db)


@router.get(
    "/sessions/{session_id}",
    response_model=HealingSessionResponse,
    summary="Get a healing session",
)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return a single healing session by id."""
    logger.info("Getting healing session via API", session_id=session_id)
    return await get_session_by_id(session_id, db)


# ─── Results ──────────────────────────────────────────────────────
@router.get(
    "/results",
    response_model=List[HealingResultResponse],
    summary="List healing results",
)
async def list_results(
    selector_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return healing results, optionally filtered by selector."""
    logger.info("Listing healing results via API", selector_id=selector_id)
    return await list_results_service(selector_id=selector_id, skip=skip, limit=limit, db=db)
