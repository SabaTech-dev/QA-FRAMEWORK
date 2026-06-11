from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class UserType(str, Enum):
    standard = "standard"
    admin = "admin"
    superuser = "superuser"


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    is_active: bool = True


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    email: Optional[str] = Field(default=None, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    onboarding_completed: bool = False
    onboarding_state: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OnboardingStateUpdate(BaseModel):
    """Schema for updating onboarding progress"""
    current_step: Optional[int] = None
    steps: Optional[Dict[str, bool]] = None
    completed: Optional[bool] = None


class OnboardingStateResponse(BaseModel):
    """Schema for reading onboarding progress"""
    completed: bool
    current_step: int
    steps: Dict[str, bool]
    completed_at: Optional[datetime] = None


class TestSuiteBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    framework_type: str = "pytest"
    config: Optional[Dict[str, Any]] = {}


class TestSuiteCreate(TestSuiteBase):
    pass


class TestSuiteUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    framework_type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class TestSuiteResponse(TestSuiteBase):
    id: int
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestType(str, Enum):
    api = "api"
    ui = "ui"
    db = "db"
    security = "security"
    performance = "performance"
    mobile = "mobile"


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TestCaseBase(BaseModel):
    suite_id: int
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    test_code: str = Field(..., min_length=10)  # The actual test code
    test_type: TestType = TestType.api
    priority: Priority = Priority.medium
    tags: Optional[List[str]] = []


class TestCaseCreate(TestCaseBase):
    pass


class TestCaseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    test_code: Optional[str] = Field(default=None, min_length=10)
    test_type: Optional[TestType] = None
    priority: Optional[Priority] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class TestCaseResponse(TestCaseBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExecutionStatus(str, Enum):
    running = "running"
    passed = "passed"
    failed = "failed"
    skipped = "skipped"
    error = "error"


class ExecutionType(str, Enum):
    manual = "manual"
    scheduled = "scheduled"
    ci = "ci"


class TestExecutionBase(BaseModel):
    suite_id: int
    execution_type: ExecutionType = ExecutionType.manual
    environment: str = "production"


class TestExecutionCreate(TestExecutionBase):
    pass


class TestExecutionUpdate(BaseModel):
    status: Optional[ExecutionStatus] = None
    ended_at: Optional[datetime] = None
    duration: Optional[int] = None
    total_tests: Optional[int] = None
    passed_tests: Optional[int] = None
    failed_tests: Optional[int] = None
    skipped_tests: Optional[int] = None
    results_summary: Optional[Dict[str, Any]] = None


class TestExecutionResponse(TestExecutionBase):
    id: int
    executed_by: Optional[int] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration: Optional[int] = None
    status: ExecutionStatus = ExecutionStatus.running
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    results_summary: Optional[Dict[str, Any]] = None
    artifacts_path: Optional[str] = None

    class Config:
        from_attributes = True


class TestExecutionDetailBase(BaseModel):
    execution_id: int
    test_case_id: int
    status: ExecutionStatus = ExecutionStatus.running


class TestExecutionDetailCreate(TestExecutionDetailBase):
    pass


class TestExecutionDetailUpdate(BaseModel):
    status: Optional[ExecutionStatus] = None
    ended_at: Optional[datetime] = None
    duration: Optional[int] = None
    error_message: Optional[str] = None
    traceback: Optional[str] = None
    screenshot_path: Optional[str] = None
    logs: Optional[str] = None


class TestExecutionDetailResponse(TestExecutionDetailBase):
    id: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration: Optional[int] = None
    status: ExecutionStatus
    error_message: Optional[str] = None
    traceback: Optional[str] = None
    screenshot_path: Optional[str] = None
    logs: Optional[str] = None

    class Config:
        from_attributes = True


class ArtifactType(str, Enum):
    screenshot = "screenshot"
    video = "video"
    log = "log"
    report = "report"


class TestArtifactBase(BaseModel):
    execution_id: Optional[int] = None
    test_case_id: Optional[int] = None
    artifact_type: ArtifactType
    file_path: str
    file_size: Optional[int] = None


class TestArtifactCreate(TestArtifactBase):
    pass


class TestArtifactResponse(TestArtifactBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ScheduleBase(BaseModel):
    suite_id: int
    name: str = Field(..., min_length=1, max_length=100)
    cron_expression: str = Field(..., pattern=r'^(\*|[0-9]|1[0-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9]|\*\/[0-9]+) (\*|[0-9]|1[0-9]|2[0-3]|\*\/[0-9]+) (\*|[1-9]|1[0-9]|2[0-9]|3[0-1]|\*\/[0-9]+) (\*|[1-9]|1[0-2]|\*\/[0-9]+) ([0-6]|\*|\*\/[0-9]+)$')
    is_active: bool = True


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    cron_expression: Optional[str] = Field(default=None, pattern=r'^(\*|[0-9]|1[0-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9]|\*\/[0-9]+) (\*|[0-9]|1[0-9]|2[0-3]|\*\/[0-9]+) (\*|[1-9]|1[0-9]|2[0-9]|3[0-1]|\*\/[0-9]+) (\*|[1-9]|1[0-2]|\*\/[0-9]+) ([0-6]|\*|\*\/[0-9]+)$')
    is_active: Optional[bool] = None
    next_run: Optional[datetime] = None


class ScheduleResponse(ScheduleBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# OAuth Schemas
class OAuthProvider(str, Enum):
    google = "google"
    github = "github"


class OAuthLoginRequest(BaseModel):
    provider: OAuthProvider
    code: str
    state: Optional[str] = None


class OAuthUrlResponse(BaseModel):
    provider: OAuthProvider
    authorization_url: str
    state: str


# API Key Schemas
class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: Optional[List[str]] = ["read"]
    expires_at: Optional[datetime] = None


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key: str
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Feedback Schemas
class FeedbackType(str, Enum):
    bug = "bug"
    feature = "feature"
    general = "general"
    improvement = "improvement"


class FeedbackStatus(str, Enum):
    new = "new"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class FeedbackBase(BaseModel):
    feedback_type: FeedbackType
    category: Optional[str] = None
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    priority: Priority = Priority.medium
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    tags: Optional[List[str]] = []


class FeedbackCreate(FeedbackBase):
    page_url: Optional[str] = None
    browser_info: Optional[Dict[str, Any]] = None
    attachments: Optional[List[str]] = []


class FeedbackUpdate(BaseModel):
    feedback_type: Optional[FeedbackType] = None
    category: Optional[str] = None
    title: Optional[str] = Field(default=None, min_length=5, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10)
    priority: Optional[Priority] = None
    status: Optional[FeedbackStatus] = None
    assigned_to: Optional[int] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class FeedbackResponse(FeedbackBase):
    id: int
    user_id: Optional[int] = None
    status: FeedbackStatus = FeedbackStatus.new
    assigned_to: Optional[int] = None
    page_url: Optional[str] = None
    attachments: List[str] = []
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FeedbackListResponse(BaseModel):
    items: List[FeedbackResponse]
    total: int
    page: int
    page_size: int


# Beta Signup Schemas
class TeamSize(str, Enum):
    tiny = "1-5"
    small = "6-20"
    medium = "21-50"
    large = "50+"


class BetaSignupStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    onboarded = "onboarded"


class BetaSignupBase(BaseModel):
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    company: Optional[str] = Field(default=None, max_length=200)
    use_case: Optional[str] = None
    team_size: Optional[TeamSize] = None


class BetaSignupCreate(BetaSignupBase):
    source: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_source: Optional[str] = None


class BetaSignupUpdate(BaseModel):
    status: Optional[BetaSignupStatus] = None
    notes: Optional[str] = None
    feedback_score: Optional[int] = Field(default=None, ge=0, le=10)


class BetaSignupResponse(BetaSignupBase):
    id: int
    status: BetaSignupStatus = BetaSignupStatus.pending
    source: Optional[str] = None
    invite_sent_at: Optional[datetime] = None
    onboarded_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BetaSignupListResponse(BaseModel):
    items: List[BetaSignupResponse]
    total: int
    page: int
    page_size: int

# Waitlist Schemas
class WaitlistSignupStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class WaitlistSignupBase(BaseModel):
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    name: str = Field(..., min_length=1, max_length=200)
    role: Optional[str] = Field(default=None, max_length=100)
    company: Optional[str] = Field(default=None, max_length=200)
    use_case: Optional[str] = None


class WaitlistSignupCreate(WaitlistSignupBase):
    source: Optional[str] = None


class WaitlistSignupUpdate(BaseModel):
    status: Optional[WaitlistSignupStatus] = None
    notes: Optional[str] = None


class WaitlistSignupResponse(WaitlistSignupBase):
    id: int
    status: WaitlistSignupStatus = WaitlistSignupStatus.pending
    source: Optional[str] = None
    invite_sent_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class WaitlistSignupListResponse(BaseModel):
    items: List[WaitlistSignupResponse]
    total: int
    page: int
    page_size: int


class DashboardStats(BaseModel):
    """Dashboard statistics response model."""
    total_suites: int
    total_cases: int
    total_executions: int
    active_executions: int
    success_rate: float
    avg_duration: float
    last_24h_executions: int
    pending_executions: int


class TrendData(BaseModel):
    """Execution trend data for dashboard charts."""
    date: str
    executions: int
    passed: int
    failed: int
    success_rate: float


# Cron Job Schemas
from schemas.cron import (
    CronJobBase,
    CronJobCreate,
    CronJobResponse,
    CronJobStatus,
    CronExecutionBase,
    CronExecutionResponse,
    CronExecutionStatus,
    CronStats
)

# Search Schemas
from schemas.search import (
    SearchQuery,
    SearchResponse,
    SearchResults,
    SuiteSearchResult,
    CaseSearchResult,
    ExecutionSearchResult,
    UserSearchResult,
    SearchSuggestions
)


# Bulk Operation Schemas
class BulkOperationBase(BaseModel):
    """Base schema for bulk operations."""
    suite_ids: List[int] = Field(..., min_items=1, max_items=100)


class BulkDeleteRequest(BulkOperationBase):
    """Request schema for bulk delete operation."""
    pass


class BulkExecuteRequest(BaseModel):
    """Request schema for bulk execute operation."""
    suite_ids: List[int] = Field(..., min_items=1, max_items=50)
    execution_type: str = Field(default="manual", pattern="^(manual|scheduled|ci)$")
    environment: str = Field(default="production", pattern="^(dev|staging|production)$")


class BulkArchiveRequest(BulkOperationBase):
    """Request schema for bulk archive operation."""
    pass


class BulkOperationResult(BaseModel):
    """Response schema for bulk operations."""
    total_requested: int
    successful: List[Dict[str, Any]]
    failed: List[Dict[str, Any]]
    not_found: List[Dict[str, Any]]


class BulkDeleteResponse(BulkOperationResult):
    """Response schema for bulk delete operation."""
    pass


class BulkExecuteResponse(BulkOperationResult):
    """Response schema for bulk execute operation."""
    pass


class BulkArchiveResponse(BaseModel):
    """Response schema for bulk archive operation."""
    total_requested: int
    successful: List[Dict[str, Any]]
    failed: List[Dict[str, Any]]
    not_found: List[Dict[str, Any]]
    already_archived: List[Dict[str, Any]]


# Browser-Use Schemas
from schemas.browser_use import (
    BrowserUseOptions,
    BrowserUseExecuteRequest,
    BrowserUseExecuteResponse,
    BrowserUseStep,
    BrowserUseStatusResponse,
    BrowserUseResultsResponse,
)
