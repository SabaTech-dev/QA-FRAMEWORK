"""
Dashboard Service

Provides dashboard statistics, trends, and analytics functionality with Redis caching.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from sqlalchemy.orm import selectinload

from models import TestExecution, TestSuite, TestCase
from core.cache import cache_manager, CacheManager


async def get_stats_service(db: AsyncSession) -> Dict[str, Any]:
    """Get dashboard statistics (cached)"""
    cache_key = cache_manager.get_dashboard_stats_key()

    # Try to get from cache
    cached_stats = await cache_manager.async_get(cache_key)
    if cached_stats is not None:
        return cached_stats

    # Total executions
    total_executions_result = await db.execute(select(func.count(TestExecution.id)))
    total_executions = total_executions_result.scalar() or 0

    # Executions last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_executions_result = await db.execute(
        select(func.count(TestExecution.id)).where(TestExecution.started_at >= yesterday)
    )
    last_24h_executions = recent_executions_result.scalar() or 0

    # Successful executions. The model uses status="passed" (never "completed"),
    # so success_rate must be computed against "passed".
    passed_result = await db.execute(
        select(func.count(TestExecution.id)).where(TestExecution.status == "passed")
    )
    passed_executions = passed_result.scalar() or 0

    # Active (currently running) and pending (queued) executions.
    active_result = await db.execute(
        select(func.count(TestExecution.id)).where(TestExecution.status == "running")
    )
    active_executions = active_result.scalar() or 0
    # The model has no explicit "queued/pending" lifecycle state, so this is 0
    # unless such a status is introduced.
    pending_executions = 0

    # Total test cases
    total_cases_result = await db.execute(
        select(func.count(TestCase.id)).where(TestCase.is_active == True)
    )
    total_cases = total_cases_result.scalar()

    # Total suites
    total_suites_result = await db.execute(
        select(func.count(TestSuite.id)).where(TestSuite.is_active == True)
    )
    total_suites = total_suites_result.scalar()

    # Average execution time (over successful runs)
    avg_duration_result = await db.execute(
        select(func.avg(TestExecution.duration)).where(TestExecution.status == "passed")
    )
    avg_duration = avg_duration_result.scalar() or 0

    stats = {
        # Field names MUST match the DashboardStats response schema, otherwise
        # FastAPI raises a response validation error (HTTP 500).
        "total_suites": total_suites,
        "total_cases": total_cases,
        "total_executions": total_executions,
        "active_executions": active_executions,
        "success_rate": round(
            (passed_executions / total_executions * 100) if total_executions > 0 else 0,
            2,
        ),
        "avg_duration": round(avg_duration, 2) if avg_duration else 0,
        "last_24h_executions": last_24h_executions,
        "pending_executions": pending_executions,
    }

    # Cache the results with short TTL since stats change frequently
    await cache_manager.async_set(cache_key, stats, ttl=CacheManager.SHORT_TTL)

    return stats


async def get_trends_service(db: AsyncSession, days: int = 30) -> List[Dict[str, Any]]:
    """Get execution trends over time (cached)"""
    cache_key = cache_manager.get_dashboard_trends_key(days)

    # Try to get from cache
    cached_trends = await cache_manager.async_get(cache_key)
    if cached_trends is not None:
        return cached_trends

    start_date = datetime.utcnow() - timedelta(days=days)

    # Get daily execution counts
    result = await db.execute(
        select(
            func.date(TestExecution.started_at).label("date"),
            func.count(TestExecution.id).label("total"),
            func.sum(case((TestExecution.status == "completed", 1), else_=0)).label("passed"),
            func.sum(case((TestExecution.status == "failed", 1), else_=0)).label("failed"),
        )
        .where(TestExecution.started_at >= start_date)
        .group_by(func.date(TestExecution.started_at))
        .order_by(func.date(TestExecution.started_at))
    )

    trends = []
    for row in result:
        trends.append(
            {
                "date": row.date.isoformat(),
                "total": row.total,
                "passed": row.passed or 0,
                "failed": row.failed or 0,
            }
        )

    # Cache the results with short TTL
    await cache_manager.async_set(cache_key, trends, ttl=CacheManager.SHORT_TTL)

    return trends


async def get_recent_service(db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent test executions (cached)"""
    cache_key = cache_manager.get_dashboard_recent_key(limit)

    # Try to get from cache
    cached_executions = await cache_manager.async_get(cache_key)
    if cached_executions is not None:
        return cached_executions

    result = await db.execute(
        select(TestExecution)
        .options(selectinload(TestExecution.suite))
        .order_by(TestExecution.started_at.desc())
        .limit(limit)
    )

    executions = []
    for execution in result.scalars().all():
        executions.append(
            {
                "id": execution.id,
                "suite_name": execution.suite.name,
                "status": execution.status,
                "started_at": execution.started_at.isoformat(),
                "duration": execution.duration,
                "total_tests": execution.total_tests,
                "passed": execution.passed_tests,
                "failed": execution.failed_tests,
                "environment": execution.environment,
            }
        )

    # Cache the results with very short TTL since recent executions change frequently
    await cache_manager.async_set(cache_key, executions, ttl=CacheManager.SHORT_TTL)

    return executions


async def get_test_types_distribution(db: AsyncSession) -> Dict[str, int]:
    """Get distribution of test types (cached)"""
    cache_key = "dashboard:test_types_distribution"

    # Try to get from cache
    cached_distribution = await cache_manager.async_get(cache_key)
    if cached_distribution is not None:
        return cached_distribution

    result = await db.execute(
        select(TestCase.test_type, func.count(TestCase.id).label("count"))
        .where(TestCase.is_active == True)
        .group_by(TestCase.test_type)
    )

    distribution = {}
    for row in result:
        distribution[row.test_type] = row.count

    # Cache the results with medium TTL
    await cache_manager.async_set(cache_key, distribution, ttl=CacheManager.MEDIUM_TTL)

    return distribution


async def get_performance_metrics(db: AsyncSession) -> Dict[str, Any]:
    """Get performance metrics (cached)"""
    cache_key = "dashboard:performance_metrics"

    # Try to get from cache
    cached_metrics = await cache_manager.async_get(cache_key)
    if cached_metrics is not None:
        return cached_metrics

    # Average test duration
    avg_duration_result = await db.execute(
        select(func.avg(TestExecution.duration)).where(TestExecution.status == "completed")
    )
    avg_duration = avg_duration_result.scalar() or 0

    # Fastest execution
    fastest_result = await db.execute(
        select(TestExecution)
        .where(TestExecution.status == "completed")
        .order_by(TestExecution.duration.asc())
        .limit(1)
    )
    fastest = fastest_result.scalar_one_or_none()

    # Slowest execution
    slowest_result = await db.execute(
        select(TestExecution)
        .where(TestExecution.status == "completed")
        .order_by(TestExecution.duration.desc())
        .limit(1)
    )
    slowest = slowest_result.scalar_one_or_none()

    metrics = {
        "average_duration": round(avg_duration, 2) if avg_duration else 0,
        "fastest_execution": {
            "id": fastest.id if fastest else None,
            "duration": fastest.duration if fastest else 0,
            "suite_name": fastest.suite.name if fastest and fastest.suite else None,
        }
        if fastest
        else None,
        "slowest_execution": {
            "id": slowest.id if slowest else None,
            "duration": slowest.duration if slowest else 0,
            "suite_name": slowest.suite.name if slowest and slowest.suite else None,
        }
        if slowest
        else None,
    }

    # Cache the results with short TTL
    await cache_manager.async_set(cache_key, metrics, ttl=CacheManager.SHORT_TTL)

    return metrics
