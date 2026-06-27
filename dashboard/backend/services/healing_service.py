"""
Self-Healing Service

CRUD operations for self-healing selectors/sessions/results plus the
``heal_selector_service`` stub. The heal logic is deterministic (no external
calls): a selector with ``confidence_score >= 0.5`` is skipped, one below
``0.5`` is healed and a stable alternative selector is generated.

See ``docs/superpowers/specs/2026-06-27-self-healing-backend-design.md``.
"""

import time
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging_config import get_logger
from models.self_healing import HealingSelector, HealingSession, HealingResult
from schemas.self_healing import (
    HealingSelectorCreate,
    HealingSelectorUpdate,
)

logger = get_logger(__name__)

# Confidence thresholds (also used for the heal decision).
HIGH_THRESHOLD = 0.7
MEDIUM_THRESHOLD = 0.5
HEAL_THRESHOLD = 0.5  # selectors with confidence below this are healed


def classify_confidence(score: float) -> str:
    """Map a 0-1 confidence score to a qualitative level."""
    if score >= HIGH_THRESHOLD:
        return "high"
    if score >= MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def _enum_value(v):
    """Coerce a possibly-enum value to its underlying string value.

    Handles both real Pydantic enums (use ``.value``) and plain strings
    (used in tests) without triggering the ``str(Enum)`` repr change from
    Python 3.11.
    """
    if v is None:
        return None
    return v.value if hasattr(v, "value") else v


def _generate_healed_selector(selector: HealingSelector) -> str:
    """Generate a deterministic, stable alternative selector (healing stub).

    Prefers a ``data-testid`` based selector which is the most stable strategy
    for UI automation. The hint comes from the selector description or, when
    absent, from a sanitised version of the original value.
    """
    hint = getattr(selector, "description", None) or selector.value or "healed"
    normalised = "".join(c if c.isalnum() else "_" for c in hint).lower().strip("_")
    return f"[data-testid='{normalised or 'healed'}']"


# ─── Selectors CRUD ───────────────────────────────────────────────
async def create_selector_service(
    selector_data: HealingSelectorCreate, db: AsyncSession
) -> HealingSelector:
    """Create a new healing selector, auto-deriving the confidence level."""
    logger.info(
        "Creating healing selector",
        value=selector_data.value,
        selector_type=str(selector_data.selector_type),
    )

    score = float(selector_data.confidence_score)
    selector = HealingSelector(
        value=selector_data.value,
        selector_type=_enum_value(selector_data.selector_type),
        description=selector_data.description,
        confidence_score=score,
        confidence_level=classify_confidence(score),
        is_active=selector_data.is_active,
        usage_count=selector_data.usage_count,
        success_rate=float(selector_data.success_rate),
    )

    db.add(selector)
    await db.commit()
    await db.refresh(selector)

    logger.info(
        "Healing selector created",
        selector_id=selector.id,
        level=selector.confidence_level,
    )
    return selector


async def list_selectors_service(
    skip: int = 0, limit: int = 100, db: AsyncSession = None
) -> List[HealingSelector]:
    """List active healing selectors with pagination."""
    logger.debug("Listing healing selectors", skip=skip, limit=limit)
    result = await db.execute(
        select(HealingSelector)
        .where(HealingSelector.is_active == True)  # noqa: E712
        .offset(skip)
        .limit(limit)
        .order_by(HealingSelector.created_at.desc())
    )
    return list(result.scalars().all())


async def get_selector_by_id(selector_id: int, db: AsyncSession) -> HealingSelector:
    """Return a selector by id or raise 404."""
    logger.debug("Getting healing selector", selector_id=selector_id)
    result = await db.execute(select(HealingSelector).where(HealingSelector.id == selector_id))
    selector = result.scalar_one_or_none()
    if not selector:
        logger.error("Healing selector not found", selector_id=selector_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Healing selector not found",
        )
    return selector


async def update_selector_service(
    selector_id: int, selector_update: HealingSelectorUpdate, db: AsyncSession
) -> HealingSelector:
    """Update editable selector fields (soft, in-place)."""
    logger.info("Updating healing selector", selector_id=selector_id)
    selector = await get_selector_by_id(selector_id, db)

    if selector_update.value is not None:
        selector.value = selector_update.value
    if selector_update.selector_type is not None:
        selector.selector_type = _enum_value(selector_update.selector_type)
    if selector_update.description is not None:
        selector.description = selector_update.description
    if selector_update.confidence_score is not None:
        selector.confidence_score = float(selector_update.confidence_score)
        selector.confidence_level = classify_confidence(selector.confidence_score)
    elif selector_update.confidence_level is not None:
        selector.confidence_level = str(selector_update.confidence_level)
    if selector_update.is_active is not None:
        selector.is_active = selector_update.is_active
    if selector_update.success_rate is not None:
        selector.success_rate = float(selector_update.success_rate)

    await db.commit()
    await db.refresh(selector)
    return selector


async def delete_selector_service(selector_id: int, db: AsyncSession) -> None:
    """Soft delete a healing selector (matches the project's is_active pattern)."""
    logger.info("Soft deleting healing selector", selector_id=selector_id)
    selector = await get_selector_by_id(selector_id, db)
    selector.is_active = False
    await db.commit()


# ─── heal_selector (core stub) ────────────────────────────────────
async def heal_selector_service(selector_id: int, db: AsyncSession) -> HealingResult:
    """Attempt to heal a single selector.

    Creates a one-off :class:`HealingSession`, evaluates whether the selector
    needs healing (``confidence_score < HEAL_THRESHOLD``) and records a
    :class:`HealingResult`. Selector usage stats are updated afterwards.
    """
    selector = await get_selector_by_id(selector_id, db)
    start = time.perf_counter()

    session = HealingSession(status="running", total_selectors=1)
    db.add(session)
    await db.flush()  # populate session.id

    needs_heal = float(selector.confidence_score) < HEAL_THRESHOLD

    if needs_heal:
        healed_value = _generate_healed_selector(selector)
        result_status = "success"
        new_confidence = 0.8
        attempts = 3
        selector.confidence_score = new_confidence
        selector.confidence_level = classify_confidence(new_confidence)
    else:
        healed_value = None
        result_status = "skipped"
        new_confidence = float(selector.confidence_score)
        attempts = 1

    healing_time_ms = int((time.perf_counter() - start) * 1000)

    result = HealingResult(
        session_id=session.id,
        selector_id=selector.id,
        original_selector_value=selector.value,
        healed_selector_value=healed_value,
        status=result_status,
        confidence_score=new_confidence,
        confidence_level=classify_confidence(new_confidence),
        healing_time_ms=healing_time_ms,
        attempts=attempts,
    )
    db.add(result)

    # Session aggregates
    session.successful_heals = 1  # skipped counts as a successful evaluation
    session.failed_heals = 0
    session.success_rate = 1.0
    session.average_confidence = new_confidence
    session.status = "success"
    session.completed_at = datetime.now(timezone.utc)

    # Selector usage stats (running average)
    selector.usage_count = int(selector.usage_count or 0) + 1
    total = selector.usage_count
    selector.success_rate = (((float(selector.success_rate or 0.0)) * (total - 1)) + 1.0) / total

    await db.commit()
    await db.refresh(result)

    logger.info(
        "Healing completed",
        selector_id=selector.id,
        status=result_status,
        session_id=session.id,
    )
    return result


# ─── Sessions ─────────────────────────────────────────────────────
async def list_sessions_service(
    skip: int = 0, limit: int = 50, db: AsyncSession = None
) -> List[HealingSession]:
    """List healing sessions with pagination."""
    logger.debug("Listing healing sessions", skip=skip, limit=limit)
    result = await db.execute(
        select(HealingSession).offset(skip).limit(limit).order_by(HealingSession.started_at.desc())
    )
    return list(result.scalars().all())


async def get_session_by_id(session_id: int, db: AsyncSession) -> HealingSession:
    """Return a session by id or raise 404."""
    logger.debug("Getting healing session", session_id=session_id)
    result = await db.execute(select(HealingSession).where(HealingSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        logger.error("Healing session not found", session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Healing session not found",
        )
    return session


# ─── Results ──────────────────────────────────────────────────────
async def list_results_service(
    selector_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = None,
) -> List[HealingResult]:
    """List healing results, optionally filtered by selector."""
    logger.debug("Listing healing results", selector_id=selector_id)
    query = select(HealingResult)
    if selector_id is not None:
        query = query.where(HealingResult.selector_id == selector_id)
    query = query.offset(skip).limit(limit).order_by(HealingResult.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())
