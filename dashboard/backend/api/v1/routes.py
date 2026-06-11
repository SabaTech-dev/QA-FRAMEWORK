"""
API Routes with Structured Logging

Provides API endpoints with comprehensive logging for QA-Framework Dashboard.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from database import get_db_session as get_db
from schemas import (
    TokenResponse,
    TestSuiteCreate,
    TestSuiteResponse,
    TestSuiteUpdate,
    TestCaseCreate,
    TestCaseResponse,
    TestCaseUpdate,
    TestExecutionCreate,
    TestExecutionResponse,
    TestExecutionUpdate,
    DashboardStats,
    TrendData,
    UserCreate,
    UserResponse,
    UserUpdate,
    LoginRequest,
    OAuthLoginRequest,
    OAuthUrlResponse,
    ApiKeyCreate,
    ApiKeyResponse,
)
from services.auth_service import get_current_user, login_for_access_token
from api.v1 import auth_routes, billing_routes, feedback_routes, beta_routes, analytics_routes, email_routes, cron_routes, bulk_routes, browser_use_routes, onboarding_routes, waitlist_routes
from api.v1.scan import router as scan_routes
from services.auth_service import get_current_user, login_for_access_token
from services.suite_service import (
    create_suite_service,
    list_suites_service,
    get_suite_by_id,
    update_suite_service,
    delete_suite_service,
)
from services.case_service import (
    create_case_service,
    list_cases_service,
    get_case_by_id,
    update_case_service,
    delete_case_service,
)
from services.execution_service import (
    create_execution_service,
    list_executions_service,
    get_execution_by_id,
    start_execution_service,
    stop_execution_service,
)
from services.user_service import (
    create_user_service,
    list_users_service,
    get_user_by_id,
    update_user_service,
    delete_user_service,
)
from core.logging_config import get_logger, set_request_id, clear_request_id

# Initialize logger
logger = get_logger(__name__)

# Include auth routes
router = APIRouter(tags=["v1"])
router.include_router(auth_routes.router)
router.include_router(billing_routes.router)
router.include_router(feedback_routes.router)
router.include_router(beta_routes.router)
router.include_router(analytics_routes.router)
router.include_router(email_routes.router)
router.include_router(cron_routes.router)
router.include_router(bulk_routes.router)
router.include_router(browser_use_routes.router)
router.include_router(onboarding_routes.router)
router.include_router(scan_routes)
router.include_router(waitlist_routes.router)


# @router.middleware("http")
# async def logging_middleware(request: Request, call_next):
#     """Middleware to add request ID to all logs."""
#     request_id = str(uuid.uuid4())
#     set_request_id(request_id)

#     logger.info(
#         "Request started",
#         method=request.method,
#         url=str(request.url),
#         client_ip=request.client.host if request.client else None,
#         request_id=request_id,
#     )

#     start_time = datetime.utcnow()

#     try:
#         response = await call_next(request)
#         duration = (datetime.utcnow() - start_time).total_seconds()

#         logger.info(
#             "Request completed",
#             method=request.method,
#             url=str(request.url),
#             status_code=response.status_code,
#             duration_ms=round(duration * 1000, 2),
#             request_id=request_id,
#         )

#         return response
#     except Exception as e:
#         duration = (datetime.utcnow() - start_time).total_seconds()
#         logger.error(
#             "Request failed",
#             method=request.method,
#             url=str(request.url),
#             error=str(e),
#             duration_ms=round(duration * 1000, 2),
#             request_id=request_id,
#             exc_info=True,
#         )
#         raise
#     finally:
#         clear_request_id()


# ==================== Dashboard Routes ====================


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get dashboard statistics.

    Retrieves comprehensive dashboard statistics including total counts
    of suites, cases, executions, success rates, and active executions.

    Args:
        db: Database session (injected)

    Returns:
        DashboardStats containing:
        - total_suites: Total number of test suites
        - total_cases: Total number of test cases
        - total_executions: Total number of executions
        - active_executions: Currently running executions
        - success_rate: Overall success percentage
        - avg_duration: Average execution duration in seconds
        - last_24h_executions: Executions in last 24 hours
        - pending_executions: Queued/pending executions

    Example:
        GET /api/v1/dashboard/stats

        Response:
        {
            "total_suites": 15,
            "total_cases": 450,
            "total_executions": 1250,
            "active_executions": 3,
            "success_rate": 94.5,
            "avg_duration": 245.5,
            "last_24h_executions": 45,
            "pending_executions": 2
        }
    """
    logger.info("Getting dashboard stats")
    try:
        from services.dashboard_service import get_stats_service as get_stats

        stats = await get_stats(db)
        logger.info("Dashboard stats retrieved successfully")
        return stats
    except Exception as e:
        logger.error("Failed to get dashboard stats", error=str(e))
        raise


@router.get("/dashboard/trends")
async def get_trends(
    days: int = 30, 
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get execution trends over time.

    Retrieves historical execution statistics for trend analysis,
    including daily execution counts, pass/fail rates, and success rates.

    Args:
        days: Number of days to include in trend analysis (default: 30, max: 365)
        db: Database session (injected)

    Returns:
        List of trend data points, each containing:
        - date: Date string (YYYY-MM-DD)
        - executions: Total executions that day
        - passed: Number of passed executions
        - failed: Number of failed executions
        - success_rate: Success percentage for that day

    Example:
        GET /api/v1/dashboard/trends?days=7

        Response:
        [
            {
                "date": "2024-01-01",
                "executions": 15,
                "passed": 14,
                "failed": 1,
                "success_rate": 93.3
            }
        ]
    """
    logger.info("Getting execution trends", days=days)
    try:
        from services.dashboard_service import get_trends_service as get_trends

        trends = await get_trends(db, days)
        logger.info(
            "Execution trends retrieved successfully",
            days=days,
            data_points=len(trends) if trends else 0,
        )
        return trends
    except Exception as e:
        logger.error("Failed to get execution trends", days=days, error=str(e))
        raise


# ==================== Suite Routes ====================


@router.post(
    "/suites", response_model=TestSuiteResponse, status_code=status.HTTP_201_CREATED
)
async def create_suite(
    suite_data: TestSuiteCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create a new test suite.

    Creates a test suite to organize related test cases. Requires authentication.

    Args:
        suite_data: TestSuiteCreate containing suite configuration
        db: Database session (injected)
        current_user: Authenticated user (injected)

    Returns:
        TestSuiteResponse with created suite details

    Raises:
        HTTPException 401: Authentication required
        HTTPException 422: Validation error in request data

    Example:
        POST /api/v1/suites
        Authorization: Bearer <token>
        {
            "name": "API Integration Tests",
            "description": "Comprehensive API testing suite",
            "framework_type": "pytest",
            "config": {
                "parallel_workers": 4,
                "timeout": 300
            }
        }

        Response (201 Created):
        {
            "id": 1,
            "name": "API Integration Tests",
            "description": "Comprehensive API testing suite",
            "framework_type": "pytest",
            "config": {"parallel_workers": 4, "timeout": 300},
            "is_active": true,
            "created_by": 1,
            "created_at": "2024-01-15T10:30:45.123456Z",
            "updated_at": "2024-01-15T10:30:45.123456Z"
        }
    """
    logger.info(
        "Creating test suite",
        suite_name=suite_data.name,
        framework_type=suite_data.framework_type,
        user_id=current_user.id,
    )
    try:
        suite = await create_suite_service(suite_data, current_user.id, db)
        logger.info(
            "Test suite created successfully via API",
            suite_id=suite.id,
            name=suite.name,
        )
        return suite
    except HTTPException as e:
        logger.error(
            "Failed to create test suite", error=e.detail, status_code=e.status_code
        )
        raise


@router.get("/suites", response_model=List[TestSuiteResponse])
async def list_suites(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    List all test suites with pagination.

    Retrieves a paginated list of all test suites in the system.

    Args:
        skip: Number of items to skip (default: 0)
        limit: Maximum number of items to return (default: 100, max: 1000)
        db: Database session (injected)

    Returns:
        List[TestSuiteResponse] containing suite details

    Example:
        GET /api/v1/suites?skip=0&limit=10

        Response:
        [
            {
                "id": 1,
                "name": "API Integration Tests",
                "description": "Comprehensive API testing suite",
                "framework_type": "pytest",
                "config": {"parallel_workers": 4},
                "is_active": true,
                "created_by": 1,
                "created_at": "2024-01-15T10:30:45.123456Z",
                "updated_at": "2024-01-15T10:30:45.123456Z"
            }
        ]
    """
    logger.info("Listing test suites via API", skip=skip, limit=limit)
    try:
        suites = await list_suites_service(skip, limit, db)
        logger.info("Test suites listed successfully via API", count=len(suites))
        return suites
    except Exception as e:
        logger.error("Failed to list test suites", error=str(e))
        raise


@router.get("/suites/{suite_id}", response_model=TestSuiteResponse)
async def get_suite(
    suite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get a test suite by ID.

    Retrieves detailed information about a specific test suite.

    Args:
        suite_id: Unique identifier of the test suite
        db: Database session (injected)

    Returns:
        TestSuiteResponse with suite details

    Raises:
        HTTPException 404: Test suite not found

    Example:
        GET /api/v1/suites/1

        Response:
        {
            "id": 1,
            "name": "API Integration Tests",
            "description": "Comprehensive API testing suite",
            "framework_type": "pytest",
            "config": {"parallel_workers": 4},
            "is_active": true,
            "created_by": 1,
            "created_at": "2024-01-15T10:30:45.123456Z",
            "updated_at": "2024-01-15T10:30:45.123456Z"
        }
    """
    logger.info("Getting test suite via API", suite_id=suite_id)
    try:
        suite = await get_suite_by_id(suite_id, db)
        logger.info("Test suite retrieved successfully via API", suite_id=suite_id)
        return suite
    except HTTPException as e:
        logger.error("Failed to get test suite", suite_id=suite_id, error=e.detail)
        raise


@router.put("/suites/{suite_id}", response_model=TestSuiteResponse)
async def update_suite(
    suite_id: int,
    suite_update: TestSuiteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Update a test suite.

    Updates an existing test suite's information. Requires authentication.

    Args:
        suite_id: Unique identifier of the test suite to update
        suite_update: TestSuiteUpdate containing fields to update
        db: Database session (injected)
        current_user: Authenticated user (injected)

    Returns:
        TestSuiteResponse with updated suite details

    Raises:
        HTTPException 401: Authentication required
        HTTPException 404: Test suite not found
        HTTPException 422: Validation error in request data

    Example:
        PUT /api/v1/suites/1
        Authorization: Bearer <token>
        {
            "name": "Updated Suite Name",
            "description": "Updated description",
            "config": {"parallel_workers": 8}
        }

        Response:
        {
            "id": 1,
            "name": "Updated Suite Name",
            "description": "Updated description",
            "framework_type": "pytest",
            "config": {"parallel_workers": 8},
            "is_active": true,
            "created_by": 1,
            "created_at": "2024-01-15T10:30:45.123456Z",
            "updated_at": "2024-01-15T12:00:00.000000Z"
        }
    """
    logger.info(
        "Updating test suite via API", suite_id=suite_id, user_id=current_user.id
    )
    try:
        suite = await update_suite_service(suite_id, suite_update, db)
        logger.info("Test suite updated successfully via API", suite_id=suite_id)
        return suite
    except HTTPException as e:
        logger.error("Failed to update test suite", suite_id=suite_id, error=e.detail)
        raise


@router.delete("/suites/{suite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_suite(
    suite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Delete a test suite (soft delete).

    Soft deletes a test suite by setting is_active to false.
    The suite and its cases are retained in the database but marked as inactive.
    Requires authentication.

    Args:
        suite_id: Unique identifier of the test suite to delete
        db: Database session (injected)
        current_user: Authenticated user (injected)

    Returns:
        None (204 No Content)

    Raises:
        HTTPException 401: Authentication required
        HTTPException 404: Test suite not found

    Example:
        DELETE /api/v1/suites/1
        Authorization: Bearer <token>

        Response: 204 No Content
    """
    logger.info(
        "Deleting test suite via API", suite_id=suite_id, user_id=current_user.id
    )
    try:
        await delete_suite_service(suite_id, db)
        logger.info("Test suite deleted successfully via API", suite_id=suite_id)
    except HTTPException as e:
        logger.error("Failed to delete test suite", suite_id=suite_id, error=e.detail)
        raise


# ==================== Case Routes ====================


@router.post(
    "/cases", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED
)
async def create_case(
    case_data: TestCaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create a new test case.

    Creates a test case within a specified test suite. Requires authentication.

    Args:
        case_data: TestCaseCreate containing case configuration
        db: Database session (injected)
        current_user: Authenticated user (injected)

    Returns:
        TestCaseResponse with created case details

    Raises:
        HTTPException 401: Authentication required
        HTTPException 404: Test suite not found
        HTTPException 422: Validation error in request data

    Example:
        POST /api/v1/cases
        Authorization: Bearer <token>
        {
            "suite_id": 1,
            "name": "Test User Login",
            "description": "Verify user can login",
            "test_code": "def test_login(): assert True",
            "test_type": "api",
            "priority": "high",
            "tags": ["smoke", "auth"]
        }

        Response (201 Created):
        {
            "id": 1,
            "suite_id": 1,
            "name": "Test User Login",
            "description": "Verify user can login",
            "test_code": "def test_login(): assert True",
            "test_type": "api",
            "priority": "high",
            "tags": ["smoke", "auth"],
            "is_active": true,
            "created_at": "2024-01-15T10:35:00.123456Z",
            "updated_at": "2024-01-15T10:35:00.123456Z"
        }
    """
    logger.info(
        "Creating test case via API",
        suite_id=case_data.suite_id,
        case_name=case_data.name,
        user_id=current_user.id,
    )
    try:
        case = await create_case_service(case_data, db)
        logger.info(
            "Test case created successfully via API", case_id=case.id, name=case.name
        )
        return case
    except HTTPException as e:
        logger.error(
            "Failed to create test case", error=e.detail, status_code=e.status_code
        )
        raise


@router.get("/cases", response_model=List[TestCaseResponse])
async def list_cases(
    suite_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    List test cases with optional filtering.

    Retrieves a paginated list of test cases, optionally filtered by suite.

    Args:
        suite_id: Optional filter by test suite ID
        skip: Number of items to skip (default: 0)
        limit: Maximum number of items to return (default: 100)
        db: Database session (injected)

    Returns:
        List[TestCaseResponse] containing case details

    Example:
        GET /api/v1/cases?suite_id=1&skip=0&limit=10

        Response:
        [
            {
                "id": 1,
                "suite_id": 1,
                "name": "Test User Login",
                "description": "Verify user can login",
                "test_code": "def test_login(): assert True",
                "test_type": "api",
                "priority": "high",
                "tags": ["smoke", "auth"],
                "is_active": true,
                "created_at": "2024-01-15T10:35:00.123456Z",
                "updated_at": "2024-01-15T10:35:00.123456Z"
            }
        ]
    """
    logger.info("Listing test cases via API", suite_id=suite_id, skip=skip, limit=limit)
    try:
        cases = await list_cases_service(suite_id, skip, limit, db)
        logger.info("Test cases listed successfully via API", count=len(cases))
        return cases
    except Exception as e:
        logger.error("Failed to list test cases", error=str(e))
        raise


@router.get("/cases/{case_id}", response_model=TestCaseResponse)
async def get_case(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get a test case by ID.

    Retrieves detailed information about a specific test case.

    Args:
        case_id: Unique identifier of the test case
        db: Database session (injected)

    Returns:
        TestCaseResponse with case details

    Raises:
        HTTPException 404: Test case not found

    Example:
        GET /api/v1/cases/1

        Response:
        {
            "id": 1,
            "suite_id": 1,
            "name": "Test User Login",
            "description": "Verify user can login",
            "test_code": "def test_login(): assert True",
            "test_type": "api",
            "priority": "high",
            "tags": ["smoke", "auth"],
            "is_active": true,
            "created_at": "2024-01-15T10:35:00.123456Z",
            "updated_at": "2024-01-15T10:35:00.123456Z"
        }
    """
    logger.info("Getting test case via API", case_id=case_id)
    try:
        case = await get_case_by_id(case_id, db)
        logger.info("Test case retrieved successfully via API", case_id=case_id)
        return case
    except HTTPException as e:
        logger.error("Failed to get test case", case_id=case_id, error=e.detail)
        raise


@router.put("/cases/{case_id}", response_model=TestCaseResponse)
async def update_case(
    case_id: int,
    case_update: TestCaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Update a test case.

    Updates an existing test case's information. Requires authentication.

    Args:
        case_id: Unique identifier of the test case to update
        case_update: TestCaseUpdate containing fields to update
        db: Database session (injected)
        current_user: Authenticated user (injected)

    Returns:
        TestCaseResponse with updated case details

    Raises:
        HTTPException 401: Authentication required
        HTTPException 404: Test case not found
        HTTPException 422: Validation error in request data

    Example:
        PUT /api/v1/cases/1
        Authorization: Bearer <token>
        {
            "name": "Updated Test Name",
            "priority": "critical",
            "tags": ["smoke", "auth", "regression"]
        }

        Response:
        {
            "id": 1,
            "suite_id": 1,
            "name": "Updated Test Name",
            "description": "Verify user can login",
            "test_code": "def test_login(): assert True",
            "test_type": "api",
            "priority": "critical",
            "tags": ["smoke", "auth", "regression"],
            "is_active": true,
            "created_at": "2024-01-15T10:35:00.123456Z",
            "updated_at": "2024-01-15T12:00:00.000000Z"
        }
    """
    logger.info("Updating test case via API", case_id=case_id, user_id=current_user.id)
    try:
        case = await update_case_service(case_id, case_update, db)
        logger.info("Test case updated successfully via API", case_id=case_id)
        return case
    except HTTPException as e:
        logger.error("Failed to update test case", case_id=case_id, error=e.detail)
        raise


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Delete a test case (soft delete).

    Soft deletes a test case by setting is_active to false.
    Requires authentication.

    Args:
        case_id: Unique identifier of the test case to delete
        db: Database session (injected)
        current_user: Authenticated user (injected)

    Returns:
        None (204 No Content)

    Raises:
        HTTPException 401: Authentication required
        HTTPException 404: Test case not found

    Example:
        DELETE /api/v1/cases/1
        Authorization: Bearer <token>

        Response: 204 No Content
    """
    logger.info("Deleting test case via API", case_id=case_id, user_id=current_user.id)
    try:
        await delete_case_service(case_id, db)
        logger.info("Test case deleted successfully via API", case_id=case_id)
    except HTTPException as e:
        logger.error("Failed to delete test case", case_id=case_id, error=e.detail)
        raise


# ==================== Execution Routes ====================


@router.post(
    "/executions",
    response_model=TestExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_execution(
    execution_data: TestExecutionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create a new test execution.

    Creates a test execution record for running tests from a suite.
    Use POST /executions/{id}/start to actually begin the execution.
    Requires authentication.

    Args:
        execution_data: TestExecutionCreate containing execution configuration
        db: Database session (injected)
        current_user: Authenticated user (injected)

    Returns:
        TestExecutionResponse with created execution details

    Raises:
        HTTPException 401: Authentication required
        HTTPException 404: Test suite not found
        HTTPException 422: Validation error in request data

    Example:
        POST /api/v1/executions
        Authorization: Bearer <token>
        {
            "suite_id": 1,
            "execution_type": "manual",
            "environment": "staging"
        }

        Response (201 Created):
        {
            "id": 1,
            "suite_id": 1,
            "execution_type": "manual",
            "environment": "staging",
            "executed_by": 1,
            "started_at": "2024-01-15T10:40:00.123456Z",
            "ended_at": null,
            "duration": null,
            "status": "running",
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0,
            "results_summary": null,
            "artifacts_path": null
        }
    """
    logger.info(
        "Creating test execution via API",
        suite_id=execution_data.suite_id,
        execution_type=execution_data.execution_type,
        user_id=current_user.id,
    )
    try:
        execution = await create_execution_service(execution_data, current_user.id, db)
        logger.info(
            "Test execution created successfully via API",
            execution_id=execution.id,
            suite_id=execution.suite_id,
        )
        return execution
    except HTTPException as e:
        logger.error(
            "Failed to create test execution", error=e.detail, status_code=e.status_code
        )
        raise


@router.get("/executions", response_model=List[TestExecutionResponse])
async def list_executions(
    suite_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    List test executions with optional filtering.

    Retrieves a paginated list of test executions, optionally filtered
    by suite and/or status.

    Args:
        suite_id: Optional filter by test suite ID
        status_filter: Optional filter by status (running, passed, failed, skipped, error)
        skip: Number of items to skip (default: 0)
        limit: Maximum number of items to return (default: 100)
        db: Database session (injected)

    Returns:
        List[TestExecutionResponse] containing execution details

    Example:
        GET /api/v1/executions?suite_id=1&status_filter=passed&limit=10

        Response:
        [
            {
                "id": 1,
                "suite_id": 1,
                "execution_type": "manual",
                "environment": "staging",
                "executed_by": 1,
                "started_at": "2024-01-15T10:40:00.123456Z",
                "ended_at": "2024-01-15T10:45:30.123456Z",
                "duration": 330,
                "status": "passed",
                "total_tests": 50,
                "passed_tests": 48,
                "failed_tests": 2,
                "skipped_tests": 0,
                "results_summary": {"success_rate": 96.0},
                "artifacts_path": "/executions/1"
            }
        ]
    """
    logger.info(
        "Listing test executions via API",
        suite_id=suite_id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )
    try:
        executions = await list_executions_service(
            suite_id, status_filter, skip, limit, db
        )
        logger.info(
            "Test executions listed successfully via API", count=len(executions)
        )
        return executions
    except Exception as e:
        logger.error("Failed to list test executions", error=str(e))
        raise


@router.get("/executions/{execution_id}", response_model=TestExecutionResponse)
async def get_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get a test execution by ID.

    Retrieves detailed information about a specific test execution,
    including results and statistics.

    Args:
        execution_id: Unique identifier of the test execution
        db: Database session (injected)

    Returns:
        TestExecutionResponse with execution details

    Raises:
        HTTPException 404: Test execution not found

    Example:
        GET /api/v1/executions/1

        Response:
        {
            "id": 1,
            "suite_id": 1,
            "execution_type": "manual",
            "environment": "staging",
            "executed_by": 1,
            "started_at": "2024-01-15T10:40:00.123456Z",
            "ended_at": "2024-01-15T10:45:30.123456Z",
            "duration": 330,
            "status": "passed",
            "total_tests": 50,
            "passed_tests": 48,
            "failed_tests": 2,
            "skipped_tests": 0,
            "results_summary": {
                "success_rate": 96.0,
                "avg_duration": 6.6,
                "slowest_tests": ["test_large_data_export"]
            },
            "artifacts_path": "/executions/1"
        }
    """
    logger.info("Getting test execution via API", execution_id=execution_id)
    try:
        execution = await get_execution_by_id(execution_id, db)
        logger.info(
            "Test execution retrieved successfully via API", execution_id=execution_id
        )
        return execution
    except HTTPException as e:
        logger.error(
            "Failed to get test execution", execution_id=execution_id, error=e.detail
        )
        raise


@router.post("/executions/{execution_id}/start")
async def start_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Start a test execution.

    Initiates the execution of tests for the specified execution record.
    The execution must be in a valid state to start.
    Requires authentication.

    Args:
        execution_id: Unique identifier of the test execution to start
        db: Database session (injected)
        current_user: Authenticated user (injected)

    Returns:
        Dict containing message, execution_id, status, and started_at timestamp

    Raises:
        HTTPException 401: Authentication required
        HTTPException 404: Test execution not found
        HTTPException 409: Execution already running or completed

    Example:
        POST /api/v1/executions/1/start
        Authorization: Bearer <token>

        Response:
        {
            "message": "Execution started successfully",
            "execution_id": 1,
            "status": "running",
            "started_at": "2024-01-15T10:40:00.123456Z"
        }
    """
    logger.info(
        "Starting test execution via API",
        execution_id=execution_id,
        user_id=current_user.id,
    )
    try:
        result = await start_execution_service(execution_id, db)
        logger.info(
            "Test execution started successfully via API", execution_id=execution_id
        )
        return result
    except HTTPException as e:
        logger.error(
            "Failed to start test execution", execution_id=execution_id, error=e.detail
        )
        raise


@router.post("/executions/{execution_id}/stop")
async def stop_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Stop a running test execution.

    Stops an actively running test execution. The execution will be marked
    as failed/stopped and partial results will be saved.
    Requires authentication.

    Args:
        execution_id: Unique identifier of the test execution to stop
        db: Database session (injected)
        current_user: Authenticated user (injected)

    Returns:
        Dict containing message, execution_id, status, and duration

    Raises:
        HTTPException 401: Authentication required
        HTTPException 404: Test execution not found
        HTTPException 409: Execution not currently running

    Example:
        POST /api/v1/executions/1/stop
        Authorization: Bearer <token>

        Response:
        {
            "message": "Execution stopped successfully",
            "execution_id": 1,
            "status": "failed",
            "duration": 180
        }
    """
    logger.info(
        "Stopping test execution via API",
        execution_id=execution_id,
        user_id=current_user.id,
    )
    try:
        result = await stop_execution_service(execution_id, db)
        logger.info(
            "Test execution stopped successfully via API", execution_id=execution_id
        )
        return result
    except HTTPException as e:
        logger.error(
            "Failed to stop test execution", execution_id=execution_id, error=e.detail
        )
        raise


# ==================== User Routes ====================


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new user account.

    Creates a new user with the provided credentials. The username and email
    must be unique. Passwords are securely hashed before storage.

    Args:
        user_data: UserCreate containing user registration details
        db: Database session (injected)

    Returns:
        UserResponse with created user details (excluding password)

    Raises:
        HTTPException 400: Username or email already exists
        HTTPException 422: Validation error in request data

    Example:
        POST /api/v1/users
        {
            "username": "john_doe",
            "email": "john.doe@example.com",
            "password": "SecurePass123!",
            "is_active": true
        }

        Response (201 Created):
        {
            "id": 2,
            "username": "john_doe",
            "email": "john.doe@example.com",
            "is_active": true,
            "is_superuser": false,
            "created_at": "2024-01-15T10:50:00.123456Z",
            "updated_at": "2024-01-15T10:50:00.123456Z"
        }
    """
    logger.info(
        "Creating user via API", username=user_data.username, email=user_data.email
    )
    try:
        user = await create_user_service(user_data, db)
        logger.info(
            "User created successfully via API", user_id=user.id, username=user.username
        )
        return user
    except HTTPException as e:
        logger.error("Failed to create user", error=e.detail, status_code=e.status_code)
        raise


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    List all users with pagination.

    Retrieves a paginated list of all user accounts. Requires authentication.

    Args:
        skip: Number of items to skip (default: 0)
        limit: Maximum number of items to return (default: 100)
        db: Database session (injected)
        current_user: Authenticated user (injected)

    Returns:
        List[UserResponse] containing user details (excluding passwords)

    Raises:
        HTTPException 401: Authentication required

    Example:
        GET /api/v1/users?skip=0&limit=10
        Authorization: Bearer <token>

        Response:
        [
            {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "is_active": true,
                "is_superuser": true,
                "created_at": "2024-01-15T09:00:00.123456Z",
                "updated_at": "2024-01-15T09:00:00.123456Z"
            }
        ]
    """
    logger.info(
        "Listing users via API", skip=skip, limit=limit, requesting_user=current_user.id
    )
    try:
        users = await list_users_service(skip, limit, db)
        logger.info("Users listed successfully via API", count=len(users))
        return users
    except Exception as e:
        logger.error("Failed to list users", error=str(e))
        raise


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get a user by ID.

    Retrieves detailed information about a specific user account.
    Requires authentication.

    Args:
        user_id: Unique identifier of the user
        db: Database session (injected)
        current_user: Authenticated user (injected)

    Returns:
        UserResponse with user details (excluding password)

    Raises:
        HTTPException 401: Authentication required
        HTTPException 404: User not found

    Example:
        GET /api/v1/users/1
        Authorization: Bearer <token>

        Response:
        {
            "id": 1,
            "username": "admin",
            "email": "admin@example.com",
            "is_active": true,
            "is_superuser": true,
            "created_at": "2024-01-15T09:00:00.123456Z",
            "updated_at": "2024-01-15T09:00:00.123456Z"
        }
    """
    logger.info(
        "Getting user via API", user_id=user_id, requesting_user=current_user.id
    )
    try:
        user = await get_user_by_id(user_id, db)
        logger.info("User retrieved successfully via API", user_id=user_id)
        return user
    except HTTPException as e:
        logger.error("Failed to get user", user_id=user_id, error=e.detail)
        raise


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Update a user account.

    Updates an existing user's information. Requires authentication.

    Args:
        user_id: Unique identifier of the user to update
        user_update: UserUpdate containing fields to update
        db: Database session (injected)
        current_user: Authenticated user (injected)

    Returns:
        UserResponse with updated user details

    Raises:
        HTTPException 401: Authentication required
        HTTPException 404: User not found
        HTTPException 422: Validation error in request data

    Example:
        PUT /api/v1/users/1
        Authorization: Bearer <token>
        {
            "email": "new.email@example.com",
            "is_active": false
        }

        Response:
        {
            "id": 1,
            "username": "admin",
            "email": "new.email@example.com",
            "is_active": false,
            "is_superuser": true,
            "created_at": "2024-01-15T09:00:00.123456Z",
            "updated_at": "2024-01-15T12:00:00.000000Z"
        }
    """
    logger.info(
        "Updating user via API", user_id=user_id, requesting_user=current_user.id
    )
    try:
        user = await update_user_service(user_id, user_update, db)
        logger.info("User updated successfully via API", user_id=user_id)
        return user
    except HTTPException as e:
        logger.error("Failed to update user", user_id=user_id, error=e.detail)
        raise


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Delete a user account (soft delete).

    Soft deletes a user by setting is_active to false.
    The user account is retained in the database but marked as inactive.
    Requires authentication.

    Args:
        user_id: Unique identifier of the user to delete
        db: Database session (injected)
        current_user: Authenticated user (injected)

    Returns:
        None (204 No Content)

    Raises:
        HTTPException 401: Authentication required
        HTTPException 404: User not found
        HTTPException 403: Cannot delete own account or insufficient permissions

    Example:
        DELETE /api/v1/users/2
        Authorization: Bearer <token>

        Response: 204 No Content
    """
    logger.info(
        "Deleting user via API", user_id=user_id, requesting_user=current_user.id
    )
    try:
        await delete_user_service(user_id, db)
        logger.info("User deleted successfully via API", user_id=user_id)
    except HTTPException as e:
        logger.error("Failed to delete user", user_id=user_id, error=e.detail)
        raise
