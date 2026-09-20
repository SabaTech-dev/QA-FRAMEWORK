"""
Test Execution Service

Provides test execution management and orchestration functionality with Redis caching.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import asyncio
import subprocess
import json

from models import TestExecution, TestExecutionDetail, TestSuite, TestCase
from schemas import TestExecutionCreate, TestExecutionUpdate
from config import settings
from core.logging_config import get_logger
from core.cache import cache_manager, CacheManager

# Initialize logger
logger = get_logger(__name__)


async def create_execution_service(
    execution_data: TestExecutionCreate, user_id: int, db: AsyncSession
) -> TestExecution:
    """Create a new test execution"""
    logger.info(
        "Creating new test execution",
        user_id=user_id,
        suite_id=execution_data.suite_id,
        execution_type=execution_data.execution_type,
        environment=execution_data.environment,
    )

    # Verify suite exists
    result = await db.execute(
        select(TestSuite)
        .where(TestSuite.id == execution_data.suite_id)
        .options(selectinload(TestSuite.tests))
    )
    suite = result.scalar_one_or_none()

    if not suite:
        logger.error("Test suite not found", suite_id=execution_data.suite_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test suite not found")

    # Create execution
    db_execution = TestExecution(
        suite_id=execution_data.suite_id,
        executed_by=user_id,
        execution_type=execution_data.execution_type,
        environment=execution_data.environment,
        total_tests=len(suite.tests),
        status="running",
    )

    db.add(db_execution)
    await db.commit()
    await db.refresh(db_execution)

    logger.info(
        "Test execution created successfully",
        execution_id=db_execution.id,
        suite_id=db_execution.suite_id,
        total_tests=db_execution.total_tests,
    )

    # Create execution details for each test case
    for test in suite.tests:
        if test.is_active:
            detail = TestExecutionDetail(
                execution_id=db_execution.id, test_case_id=test.id, status="pending"
            )
            db.add(detail)

    await db.commit()

    logger.info(
        "Execution details created for active tests",
        execution_id=db_execution.id,
        active_tests=len([t for t in suite.tests if t.is_active]),
    )

    # Invalidate execution cache
    await cache_manager.invalidate_execution_cache()
    await cache_manager.invalidate_dashboard_cache()

    return db_execution


async def start_execution_service(execution_id: int, db: AsyncSession) -> dict:
    """Start a test execution"""
    logger.info("Starting test execution", execution_id=execution_id)

    execution = await get_execution_by_id(execution_id, db)

    if execution.status != "running":
        logger.error(
            "Execution not in running state",
            execution_id=execution_id,
            current_status=execution.status,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Execution already completed or not in running state",
        )

    # Start execution asynchronously
    asyncio.create_task(run_tests(execution_id, db))

    logger.info("Execution started successfully", execution_id=execution_id)

    return {"message": "Execution started", "execution_id": execution_id}


async def run_tests(execution_id: int, db: AsyncSession):
    """Run tests in background"""
    logger.info("Starting test execution in background", execution_id=execution_id)

    try:
        # Get execution
        result = await db.execute(
            select(TestExecution)
            .where(TestExecution.id == execution_id)
            .options(selectinload(TestExecution.details))
        )
        execution = result.scalar_one()

        logger.info(
            "Test execution retrieved",
            execution_id=execution_id,
            total_tests=len(execution.details),
        )

        # Run each test
        passed = 0
        failed = 0
        skipped = 0

        for detail in execution.details:
            test_case = await db.execute(select(TestCase).where(TestCase.id == detail.test_case_id))
            test = test_case.scalar_one()

            logger.info(
                "Running test case",
                execution_id=execution_id,
                test_case_id=detail.test_case_id,
                test_name=test.name,
            )

            # Execute test (simplified - in reality would use pytest or similar)
            try:
                # Simulate test execution
                detail.status = "running"
                detail.started_at = datetime.utcnow()
                await db.commit()

                logger.info(
                    "Test case started",
                    execution_id=execution_id,
                    test_case_id=detail.test_case_id,
                    status="running",
                )

                # In real implementation, would execute test code
                await asyncio.sleep(1)  # Simulate test execution

                # Simulate result
                detail.status = "passed"
                detail.ended_at = datetime.utcnow()
                detail.duration = 1
                passed += 1

                logger.info(
                    "Test case completed successfully",
                    execution_id=execution_id,
                    test_case_id=detail.test_case_id,
                    status="passed",
                )

            except Exception as e:
                detail.status = "failed"
                detail.error_message = str(e)
                failed += 1

                logger.error(
                    "Test case failed",
                    execution_id=execution_id,
                    test_case_id=detail.test_case_id,
                    error=str(e),
                )

            await db.commit()

        # Anti false-green meta-check: "never ran" is a failure, not a pass.
        # A suite that executed 0 assertions (empty suite, all tests inactive,
        # or everything skipped) must fail explicitly instead of reporting a
        # green completion (card a34a1b5c, Anthropic 0/0-parser postmortem class).
        executed = passed + failed
        if executed == 0:
            execution.status = "failed"
            execution.ended_at = datetime.utcnow()
            execution.duration = int((execution.ended_at - execution.started_at).total_seconds())
            execution.passed_tests = passed
            execution.failed_tests = failed
            execution.skipped_tests = skipped
            execution.results_summary = {
                "total": execution.total_tests,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "error": (
                    "QA meta-check failed: 0 assertions executed "
                    f"(passed={passed}, failed={failed}, skipped={skipped}, "
                    f"total={execution.total_tests}). "
                    "Suite never ran — this is NOT a pass."
                ),
            }

            await db.commit()

            await cache_manager.invalidate_execution_cache(execution_id)
            await cache_manager.invalidate_dashboard_cache()

            logger.error(
                "Test execution rejected: 0 assertions executed",
                execution_id=execution_id,
                total_tests=execution.total_tests,
                skipped=skipped,
            )
            return

        # Update execution summary
        execution.status = "completed"
        execution.ended_at = datetime.utcnow()
        execution.duration = int((execution.ended_at - execution.started_at).total_seconds())
        execution.passed_tests = passed
        execution.failed_tests = failed
        execution.skipped_tests = skipped
        execution.results_summary = {
            "total": execution.total_tests,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }

        await db.commit()

        # Invalidate execution and dashboard cache after completion
        await cache_manager.invalidate_execution_cache(execution_id)
        await cache_manager.invalidate_dashboard_cache()

        logger.info(
            "Test execution completed",
            execution_id=execution_id,
            total_tests=len(execution.details),
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration=execution.duration,
        )

    except Exception as e:
        logger.error(
            "Error running tests",
            execution_id=execution_id,
            error=str(e),
            exc_info=True,
        )


async def stop_execution_service(execution_id: int, db: AsyncSession) -> dict:
    """Stop a running execution"""
    logger.info("Stopping test execution", execution_id=execution_id)

    execution = await get_execution_by_id(execution_id, db)

    if execution.status != "running":
        logger.error(
            "Execution not in running state",
            execution_id=execution_id,
            current_status=execution.status,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Execution not in running state",
        )

    execution.status = "stopped"
    execution.ended_at = datetime.utcnow()
    execution.duration = int((execution.ended_at - execution.started_at).total_seconds())

    await db.commit()

    # Invalidate execution and dashboard cache
    await cache_manager.invalidate_execution_cache(execution_id)
    await cache_manager.invalidate_dashboard_cache()

    logger.info(
        "Execution stopped successfully",
        execution_id=execution_id,
        duration=execution.duration,
    )

    return {"message": "Execution stopped", "execution_id": execution_id}


async def list_executions_service(
    suite_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = None,
) -> List[TestExecution]:
    """List test executions with optional filters (cached)"""
    logger.info(
        "Listing test executions",
        suite_id=suite_id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )

    # Generate cache key
    cache_key = cache_manager.get_execution_list_key(suite_id, status_filter, skip, limit)

    # Try to get from cache
    cached_executions = await cache_manager.async_get(cache_key)
    if cached_executions is not None:
        logger.info("Test executions retrieved from cache", count=len(cached_executions))
        return cached_executions

    # Fetch from database
    query = select(TestExecution)

    if suite_id:
        query = query.where(TestExecution.suite_id == suite_id)
    if status_filter:
        query = query.where(TestExecution.status == status_filter)

    result = await db.execute(
        query.options(selectinload(TestExecution.suite))
        .offset(skip)
        .limit(limit)
        .order_by(TestExecution.started_at.desc())
    )
    executions = result.scalars().all()

    # Cache the results with short TTL since executions change frequently
    await cache_manager.async_set(cache_key, executions, ttl=CacheManager.SHORT_TTL)

    logger.info(
        "Executions listed successfully",
        count=len(executions),
        suite_id=suite_id,
        status_filter=status_filter,
    )

    return executions


async def get_execution_by_id(execution_id: int, db: AsyncSession) -> TestExecution:
    """Get a test execution by ID (cached)"""
    logger.info("Getting execution by ID", execution_id=execution_id)

    # Generate cache key
    cache_key = cache_manager.get_execution_key(execution_id)

    # Try to get from cache
    cached_execution = await cache_manager.async_get(cache_key)
    if cached_execution is not None:
        logger.debug("Test execution retrieved from cache", execution_id=execution_id)
        return cached_execution

    # Fetch from database
    result = await db.execute(
        select(TestExecution)
        .where(TestExecution.id == execution_id)
        .options(selectinload(TestExecution.suite), selectinload(TestExecution.details))
    )
    execution = result.scalar_one_or_none()

    if not execution:
        logger.error("Test execution not found", execution_id=execution_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test execution not found"
        )

    # Cache the result with short TTL
    await cache_manager.async_set(cache_key, execution, ttl=CacheManager.SHORT_TTL)

    logger.info(
        "Execution retrieved successfully",
        execution_id=execution_id,
        status=execution.status,
    )

    return execution
