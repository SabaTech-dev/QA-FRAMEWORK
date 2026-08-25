# Changelog

All notable changes to the QA-Framework Dashboard project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
#### Refresh Token Rotation (card 3ae2e5c1, F-2 / OWASP API2)
- **Rotating refresh tokens with reuse detection**: `services/auth_service.py`
  mints refresh tokens with a unique `jti` and a `fam` (family) claim via
  the new vendored `src/infrastructure/refresh_tokens` store (Redis-backed
  jti denylist + family tombstones; parity-guarded against the repo-level
  module)
  - `POST /auth/refresh` now ROTATES: returns a new access + refresh pair,
    atomically consumes the old `jti` (SET NX EX, TTL = remaining lifetime)
  - REUSE DETECTION: replaying a consumed token returns 401, revokes the
    entire token family and logs a SECURITY alarm; members of a revoked
    family are always rejected
  - New `POST /auth/revoke`: explicit server-side logout (RFC 7009-style,
    idempotent; invalid/expired tokens still return 200)
  - Fail-closed: refresh answers 503 when Redis is unavailable (the
    denylist can never be bypassed by an outage)
  - Legacy tokens without `jti` are upgraded once and expire naturally
  - `tests/conftest.py`: the global redis mock now keeps
    `redis.exceptions` importable (also un-breaks 10 pre-existing
    `test_test_cache.py` failures)
  - Redis credentials come only from env (`REDIS_HOST`/`REDIS_PORT`/
    `REDIS_PASSWORD`); tests use local `127.0.0.1:6379` DB 15 with a
    dedicated prefix and skip when Redis is absent

#### Secrets Remediation
- **Removed hardcoded Railway Redis credentials from the repository**: the
  production credential was embedded in test fixtures and docs
  - `backend/tests/conftest.py`: REDIS_URL fallback now uses local Redis
    (`redis://127.0.0.1:6379/0`); redis stays mocked in tests, so no real
    connection is attempted
  - `backend/tests/infrastructure/test_test_cache.py` and
    `test_test_cache_backup.py`: fixture default switched to local Redis
  - `backend/TEST_FIX_PROMPT.md`: example REDIS_URL switched to local Redis
  - NOTE: the credential remains in git history prior to this change and must
    be rotated on the Railway side

### Fixed
#### Dependencies
- **Bumped FastAPI 0.115.4 -> 0.122.0 with Starlette >= 0.42**: FastAPI <= 0.121
  returns 403 Forbidden (instead of 401 Unauthorized) when `HTTPBearer` finds
  no credentials; 0.122.0 introduced `HTTPBase.make_not_authenticated_error()`
  answering 401 with `WWW-Authenticate`
  - Unblocked `test_accuracy_mounted_rejects_unauthenticated` and
    `test_accuracy_mount_with_provider_env_assembles` (wiring suite back to 6/6)

### Changed
#### CI
- **Dashboard wiring suites now run in PR checks**: the
  `dashboard-middleware-tests` job (required check) additionally runs
  `test_accuracy_wiring.py`, `test_qa_visual_wiring.py` and
  `test_qa_visual_feature_flag.py` and uploads their JUnit report

## [0.3.0] - 2026-02-13

### Fixed
#### Testing Infrastructure
- **Fixed pytest-asyncio segmentation fault**: Downgraded from 0.25.0 to 0.24.0
  - Recreated virtual environment with compatible versions
  - File: `backend/recreate_venv.sh`

- **Fixed bcrypt compatibility issue**: Downgraded from 5.0.0 to 4.1.2
  - bcrypt 5.0.0 removed `__about__` attribute needed by passlib
  - Reinstalled with compatible version

- **Fixed AsyncMock configuration**: Corrected mock setup for async functions
  - Changed `mock.return_value` to `Mock(return_value=...)` for sync methods
  - Changed `mock.all.return_value` to `mock.all = Mock(return_value=...)`
  - Differentiated between sync and async mock calls

- **Fixed Pydantic validation**: Corrected test data to match schema
  - Changed `test_type='unit'` to `test_type='api'` (valid enum)
  - Added proper validation for TestCaseCreate schema

- **Fixed password length issues**: Truncated passwords to < 72 bytes
  - bcrypt has a maximum password length of 72 bytes
  - Updated test passwords to shorter versions

### Added
#### Testing
- **Complete Unit Test Coverage**: 53 tests created and passing
  - **Auth Service**: 10 tests (authentication, JWT, password hashing)
  - **Suite Service**: 10 tests (CRUD, soft delete, validation)
  - **Case Service**: 13 tests (CRUD, filtering, pagination)
  - **Execution Service**: 17 tests (CRUD, status management, filtering)
  - **User Service**: 3 tests (creation, validation)
  - Files: `backend/tests/unit/test_*.py`

- **Coverage Reports**: Generated HTML and terminal reports
  - Total coverage: 82.59% (superado el objetivo de 80%)
  - Directory: `backend/htmlcov/`

#### Documentation
- **Updated Progress Status**: Comprehensive status update
  - File: `PROGRESS_STATUS.md`
  - Added test metrics and achievements
  - Updated phase completion percentages

- **Script for Virtual Environment Recreation**: Automated script
  - File: `backend/recreate_venv.sh`
  - Handles dependency installation and verification

### Changed
#### Testing
- **Improved Mock Configuration**: Better separation of sync/async mocks
  - `scalar_one_or_none` now uses `Mock(return_value=...)` (sync)
  - `execute` uses `AsyncMock(return_value=...)` (async)
  - `scalars().all()` properly mocked with sync Mock

- **Test Data Validation**: Ensured all test data matches Pydantic schemas
  - Valid enum values for `test_type`, `priority`, etc.
  - Proper field types and constraints

#### Infrastructure
- **Virtual Environment**: Recreated with correct dependencies
  - Python 3.12
  - pytest 8.3.3
  - pytest-asyncio 0.24.0
  - bcrypt 4.1.2
  - structlog (added)

### Technical Details
#### Coverage by Service
- `services/auth_service.py`: 83% coverage
- `services/case_service.py`: 97% coverage
- `services/suite_service.py`: 93% coverage
- `services/execution_service.py`: 65% coverage
- `services/user_service.py`: 27% coverage (pending improvement)
- `models/`: 100% coverage
- `schemas/`: 100% coverage

#### Test Organization
- **Total Tests**: 53 unit tests
- **Passing**: 53 (100%)
- **Failing**: 0
- **Warnings**: 41 (mostly deprecation warnings, non-critical)

---

## [0.2.0] - 2026-02-12

### Added
#### Security
- **Rate Limiting Middleware**: Implemented rate limiting to protect against abuse
  - Login attempts: 5 requests/minute
  - API endpoints: 100 requests/minute
  - Test executions: 10 requests/minute
  - Module: `backend/middleware/rate_limiting.py`

#### Testing
- **Unit Tests for Auth Service**: 12 comprehensive tests
  - Password hashing and verification
  - JWT token creation and validation
  - User authentication
  - Token refresh functionality
  - File: `backend/tests/unit/test_auth_service.py`

- **Unit Tests for Suite Service**: 10 comprehensive tests
  - CRUD operations for test suites
  - Soft delete functionality
  - Data validation
  - Error handling
  - File: `backend/tests/unit/test_suite_service.py`

- **Pytest Configuration**: Configured testing framework
  - Coverage minimum: 80%
  - HTML and terminal reports
  - Async test support
  - Test markers (unit, integration, slow)
  - File: `backend/pytest.ini`

#### Frontend
- **Error Boundary Component**: Global error handling
  - Graceful error catching
  - User-friendly fallback UI
  - Error reset functionality
  - File: `frontend/src/components/ErrorBoundary.tsx`

- **Performance Optimizations**:
  - React Query cache configuration (5min stale, 10min cache)
  - Suspense for lazy loading
  - Optimized loading states
  - Improved error handling in main.tsx

#### Documentation
- **Improvement Plan**: Detailed 3-phase improvement plan
  - PLAN → BUILD → TEST workflow
  - Sprint planning
  - Success metrics
  - File: `IMPROVEMENT_PLAN.md`

- **Improvements Tracker**: Progress tracking document
  - Current status
  - Completed tasks
  - Pending tasks
  - File: `IMPROVEMENTS_COMPLETED.md`

### Changed
- **Enhanced Main Entry Point**: Improved `frontend/src/main.tsx`
  - Added ErrorBoundary wrapper
  - Implemented Suspense for lazy loading
  - Optimized React Query configuration
  - Better loading states

- **Backend Requirements**: Updated `backend/requirements.txt`
  - Added pytest and testing dependencies
  - Added slowapi for rate limiting
  - Updated package versions

### Security
- **Rate Limiting**: Protection against brute force and API abuse
- **Input Validation**: Enhanced Pydantic validators
- **Error Handling**: Better error messages without sensitive data

## [0.1.0] - 2026-02-12

### Added
#### Backend Core
- **FastAPI Application**: Complete REST API backend
  - 30+ API endpoints
  - JWT authentication
  - Async/await support
  - CORS middleware
  - File: `backend/main.py`

- **Database Models**: SQLAlchemy ORM models
  - User model with authentication
  - TestSuite model
  - TestCase model
  - TestExecution model
  - TestExecutionDetail model
  - TestArtifact model
  - Schedule model
  - File: `backend/models/__init__.py`

- **Pydantic Schemas**: Data validation schemas
  - User schemas (create, update, response)
  - TestSuite schemas
  - TestCase schemas
  - Execution schemas
  - Dashboard schemas
  - File: `backend/schemas/__init__.py`

- **Business Services**: Core business logic
  - `auth_service.py`: JWT authentication, password hashing
  - `user_service.py`: User CRUD operations
  - `suite_service.py`: Test suite management
  - `case_service.py`: Test case management
  - `execution_service.py`: Test execution orchestration
  - `dashboard_service.py`: Statistics and analytics
  - Directory: `backend/services/`

- **API Routes**: RESTful endpoints
  - Authentication routes
  - User management routes
  - Suite management routes
  - Case management routes
  - Execution routes
  - Dashboard routes
  - File: `backend/api/v1/routes.py`

- **QA-FRAMEWORK Integration**: Integration with existing framework
  - Client for connecting to QA-FRAMEWORK
  - Remote test execution
  - Result retrieval
  - File: `backend/integration/qa_framework_client.py`

#### Frontend Core
- **React Application**: Modern React with TypeScript
  - Vite build system
  - TypeScript strict mode
  - Material-UI dark theme
  - File: `frontend/src/main.tsx`

- **Routing**: React Router with protected routes
  - Dashboard route
  - Login route
  - TestSuites route
  - TestCases route
  - Executions route
  - File: `frontend/src/App.tsx`

- **Layout Component**: Main application layout
  - Responsive sidebar
  - Header with user info
  - Navigation menu
  - File: `frontend/src/components/Layout.tsx`

- **Dashboard Page**: Main dashboard with KPIs
  - Statistics cards
  - Execution trends chart
  - Test types distribution
  - Recent executions list
  - File: `frontend/src/pages/Dashboard.tsx`

- **Login Page**: User authentication
  - Username/password form
  - JWT token handling
  - Error handling
  - File: `frontend/src/pages/Login.tsx`

- **TestSuites Page**: Suite management
  - Suite listing
  - CRUD operations
  - Execution triggering
  - File: `frontend/src/pages/TestSuites.tsx`

- **TestCases Page**: Case management
  - Case listing with filtering
  - Code editor
  - Priority and tags
  - File: `frontend/src/pages/TestCases.tsx`

- **Executions Page**: Execution history
  - Execution listing
  - Status tracking
  - Start/stop controls
  - File: `frontend/src/pages/Executions.tsx`

- **State Management**: Zustand stores
  - Auth store with persistence
  - Token management
  - File: `frontend/src/stores/authStore.ts`

- **API Client**: Axios HTTP client
  - JWT interceptors
  - Error handling
  - API functions for all endpoints
  - File: `frontend/src/api/client.ts`

#### Infrastructure
- **Docker Compose**: Complete orchestration
  - Backend service
  - Frontend service
  - PostgreSQL database
  - Redis cache
  - File: `docker-compose.yml`

- **Dockerfiles**: Container definitions
  - Backend Dockerfile
  - Frontend Dockerfile
  - Multi-stage builds
  - Directory: `backend/Dockerfile`, `frontend/Dockerfile`

- **Configuration Files**:
  - TypeScript configuration
  - Vite configuration
  - ESLint configuration
  - Environment variables template
  - Files: `frontend/tsconfig.json`, `frontend/vite.config.ts`, etc.

#### Documentation
- **README**: Complete project documentation
  - Installation guide
  - Architecture overview
  - API documentation
  - Development guide
  - File: `README.md`

- **Project Summary**: Project overview
  - Features list
  - Metrics
  - Next steps
  - File: `PROJECT_SUMMARY.md`

- **Dashboard Investigation**: Market research
  - Competitor analysis
  - Technical proposal
  - File: `QA_FRAMEWORK_DASHBOARD_INVESTIGATION.md`

### Technical Details
- **Backend**: Python 3.11, FastAPI, SQLAlchemy, PostgreSQL, Redis
- **Frontend**: React 18, TypeScript, Material-UI, React Query, Chart.js
- **Architecture**: Clean Architecture, SOLID principles
- **Testing**: Pytest, Vitest, Playwright (planned)
- **CI/CD**: GitHub Actions (planned)

## [Unreleased]

### Planned
- Integration tests for API
- E2E tests with Playwright
- Performance optimizations
- CI/CD pipeline
- API documentation (OpenAPI/Swagger)
- Contribution guide

### Completed (v0.3.0)
- ✅ Execution service tests (15 tests)
- ✅ Case service tests (15 tests)
- ✅ Structured logging with structlog
- ✅ Core logging configuration module
- ✅ Absolute imports throughout services
- ✅ Improved error handling in all services

---

## [0.3.0] - 2026-02-13

### Added
- **Execution Service Tests**: 15 comprehensive tests
  - CRUD operations for test executions
  - Start/stop execution functionality
  - Filtering and pagination
  - Edge cases and error handling
  - File: `backend/tests/unit/test_execution_service.py`

- **Case Service Tests**: 15 comprehensive tests
  - CRUD operations for test cases
  - Partial updates support
  - Soft delete functionality
  - Edge cases with special characters
  - File: `backend/tests/unit/test_case_service.py`

- **Structured Logging**: Complete logging implementation
  - JSON-formatted logs for production
  - Context-aware logging with request IDs
  - Log levels per environment
  - Module: `backend/core/logging_config.py`

- **Service Integration**: Logs added to all services
  - `services/execution_service.py`: 10+ log statements
  - `services/case_service.py`: 10+ log statements
  - Detailed audit trail for all operations

### Changed
- **Imports**: Changed to absolute imports throughout
  - `backend/services/__init__.py`
  - `backend/services/user_service.py`
  - Better compatibility with pytest

- **Database Configuration**: Fixed async engine compatibility
  - Removed QueuePool (incompatible with asyncio)
  - Better connection pool management
  - File: `backend/database.py`

### Fixed
- **Test Configuration**: Pydantic v2 compatibility
  - Changed `regex` to `pattern` in Field validators
  - Updated schema definitions
  - File: `backend/schemas/__init__.py`

### Documentation
- **Autonomous Work Plan**: Complete night-time work plan
  - FASE 1: Testing Backend
  - FASE 2: Logging Implementation
  - FASE 3: Documentation
  - File: `QA-FRAMEWORK-DASHBOARD/AUTONOMOUS_WORK_PLAN.md`

- **Nightly Progress Reports**: Real-time progress tracking
  - Work completed
  - Blockers detected
  - Next steps
  - File: `backend/NIGHTLY_PROGRESS_REPORT.md`

---

## Version History

- **[0.3.0]** - 2026-02-13: Testing, Logging, and Observability improvements
- **[0.2.0]** - 2026-02-12: Security, Testing, and Performance improvements
- **[0.1.0]** - 2026-02-12: Initial release with complete dashboard

---

## Migration Guide

### From 0.1.0 to 0.2.0

1. **Install new dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Run tests**:
   ```bash
   pytest tests/unit/
   ```

3. **Update frontend**:
   ```bash
   cd frontend
   npm install
   ```

4. **Verify rate limiting**:
   - Check `backend/middleware/rate_limiting.py` configuration
   - Adjust limits if needed

---

## Contributing

Please read the contribution guidelines before submitting pull requests.

## License

This project is licensed under the MIT License.