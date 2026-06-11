from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON
from typing import Optional

from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

# Import cron job models (moved to migration files directly)
# from cron import CronJob, CronExecution

Base = declarative_base()

# Export relationship for use in models
__all__ = [
    'Base', 'Column', 'Integer', 'String', 'DateTime', 'Boolean',
    'Text', 'ForeignKey', 'JSON', 'Optional', 'func', 'relationship',
    'datetime', 'CronJob', 'CronExecution'
]


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Multi-tenant
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    
    # OAuth
    oauth_provider = Column(String, nullable=True)
    oauth_provider_id = Column(String, nullable=True)
    
    # Subscription & Billing
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True)
    subscription_plan = Column(String, default="free")  # free, pro, enterprise
    subscription_status = Column(String, default="active")  # active, past_due, canceled, canceling
    subscription_current_period_start = Column(DateTime, nullable=True)
    subscription_current_period_end = Column(DateTime, nullable=True)
    
    # Onboarding
    onboarding_completed = Column(Boolean, default=False)
    onboarding_state = Column(JSON, default=dict)  # {"current_step": 0, "steps": {"welcome": true, ...}}
    onboarding_completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    test_executions = relationship("TestExecution", back_populates="user")
    api_keys = relationship("ApiKey", back_populates="user")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    hashed_key = Column(String, unique=True, nullable=False)
    scopes = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")


class TestSuite(Base):
    __tablename__ = "test_suites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    framework_type = Column(String, default="pytest")  # pytest, unittest, etc.
    config = Column(JSON)  # Configuration parameters
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    tests = relationship("TestCase", back_populates="suite")
    executions = relationship("TestExecution", back_populates="suite")


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    suite_id = Column(Integer, ForeignKey("test_suites.id"), nullable=False)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    test_code = Column(Text, nullable=False)  # The actual test code
    test_type = Column(String, default="api")  # api, ui, db, security, etc.
    priority = Column(String, default="medium")  # low, medium, high, critical
    tags = Column(JSON)  # ["smoke", "regression", "performance"]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    suite = relationship("TestSuite", back_populates="tests")
    executions = relationship("TestExecutionDetail", back_populates="test_case")


class TestExecution(Base):
    __tablename__ = "test_executions"

    id = Column(Integer, primary_key=True, index=True)
    suite_id = Column(Integer, ForeignKey("test_suites.id"), nullable=False)
    executed_by = Column(Integer, ForeignKey("users.id"))
    execution_type = Column(String, default="manual")  # manual, scheduled, ci
    environment = Column(String, default="production")  # dev, staging, production
    started_at = Column(DateTime, default=func.now())
    ended_at = Column(DateTime)
    duration = Column(Integer)  # Duration in seconds
    status = Column(String, default="running")  # running, passed, failed, skipped, error
    total_tests = Column(Integer, default=0)
    passed_tests = Column(Integer, default=0)
    failed_tests = Column(Integer, default=0)
    skipped_tests = Column(Integer, default=0)
    results_summary = Column(JSON)  # Summary of results
    artifacts_path = Column(String)  # Path to artifacts like screenshots, logs

    # Relationships
    suite = relationship("TestSuite", back_populates="executions")
    user = relationship("User", back_populates="test_executions")
    details = relationship("TestExecutionDetail", back_populates="execution")


class TestExecutionDetail(Base):
    __tablename__ = "test_execution_details"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("test_executions.id"), nullable=False)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False)
    started_at = Column(DateTime, default=func.now())
    ended_at = Column(DateTime)
    duration = Column(Integer)  # Duration in seconds
    status = Column(String, default="running")  # passed, failed, skipped, error
    error_message = Column(Text)
    traceback = Column(Text)
    screenshot_path = Column(String)  # Path to screenshot if UI test failed
    logs = Column(Text)  # Execution logs

    # Relationships
    execution = relationship("TestExecution", back_populates="details")
    test_case = relationship("TestCase", back_populates="executions")


class TestArtifact(Base):
    __tablename__ = "test_artifacts"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("test_executions.id"))
    test_case_id = Column(Integer, ForeignKey("test_cases.id"))
    artifact_type = Column(String, nullable=False)  # screenshot, video, log, report
    file_path = Column(String, nullable=False)
    file_size = Column(Integer)
    created_at = Column(DateTime, default=func.now())


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    suite_id = Column(Integer, ForeignKey("test_suites.id"), nullable=False)
    name = Column(String, nullable=False)
    cron_expression = Column(String, nullable=False)  # Cron expression for scheduling
    is_active = Column(Boolean, default=True)
    next_run = Column(DateTime)
    last_run = Column(DateTime)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    suite = relationship("TestSuite")
    creator = relationship("User")


class TenantModel(Base):
    """SQLAlchemy model for Tenant entity (multi-tenancy support)"""
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, index=True)  # UUID as string
    name = Column(String, nullable=False, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    plan = Column(String, nullable=False, default="free")  # free, pro, enterprise
    status = Column(String, nullable=False, default="trial")  # active, suspended, trial
    settings = Column(JSON, default={})
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Feedback(Base):
    """Model for user feedback collection"""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional for anonymous
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    
    # Feedback content
    feedback_type = Column(String, nullable=False)  # bug, feature, general, improvement
    category = Column(String, nullable=True)  # ui, ux, performance, documentation, etc.
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String, default="medium")  # low, medium, high, critical
    
    # Context
    page_url = Column(String(500), nullable=True)  # URL where feedback was submitted
    user_agent = Column(String, nullable=True)
    browser_info = Column(JSON, nullable=True)  # Browser, OS, screen size, etc.
    
    # Status tracking
    status = Column(String, default="new")  # new, in_progress, resolved, closed
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Rating (optional)
    rating = Column(Integer, nullable=True)  # 1-5 stars
    
    # Metadata
    tags = Column(JSON, default=list)  # ["ui", "dashboard", "critical"]
    attachments = Column(JSON, default=list)  # List of attachment URLs/paths
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    assignee = relationship("User", foreign_keys=[assigned_to])


class BetaSignup(Base):
    """Model for beta tester signups"""
    __tablename__ = "beta_signups"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    company = Column(String(200), nullable=True)
    use_case = Column(Text, nullable=True)
    team_size = Column(String, nullable=True)  # 1-5, 6-20, 21-50, 50+
    
    # Status
    status = Column(String, default="pending")  # pending, approved, rejected, onboarded
    invite_sent_at = Column(DateTime, nullable=True)
    onboarded_at = Column(DateTime, nullable=True)
    
    # Tracking
    source = Column(String, nullable=True)  # landing_page, referral, social, etc.
    utm_campaign = Column(String, nullable=True)
    utm_source = Column(String, nullable=True)
    
    # Metadata
    notes = Column(Text, nullable=True)
    feedback_score = Column(Integer, nullable=True)  # NPS score 0-10
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class WaitlistSignup(Base):
    """Model for waitlist signups (beta access waitlist)"""
    __tablename__ = "waitlist_signups"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    role = Column(String(100), nullable=True)  # QA Engineer, Developer, DevOps, etc.
    company = Column(String(200), nullable=True)
    use_case = Column(Text, nullable=True)

    # Status
    status = Column(String, default="pending")  # pending, approved, rejected
    invite_sent_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)

    # Tracking
    source = Column(String, nullable=True)  # landing_page, referral, social, etc.

    # Metadata
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Project(Base):
    """Project model for organizing test suites."""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Subscription(Base):
    """Subscription model for billing analytics."""
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_type = Column(String, default="free")  # free, pro, enterprise
    status = Column(String, default="active")  # active, past_due, canceled, cancelled
    stripe_subscription_id = Column(String, nullable=True)
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class UsageRecord(Base):
    """Usage tracking for feature analytics."""
    __tablename__ = "usage_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    feature_name = Column(String, nullable=False)  # ai_test_generation, self_healing, etc.
    usage_count = Column(Integer, default=1)
    extra_data = Column(JSON, nullable=True)  # Changed from 'metadata' (reserved word)
    
    created_at = Column(DateTime, default=func.now())


# Browser-Use Task Model
from models.browser_use_task import BrowserUseTask, TaskStatus
