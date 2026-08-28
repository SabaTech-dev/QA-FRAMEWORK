"""
Services Module

Provides all business logic services for the QA-Framework Dashboard.
"""

from services.auth_service import (
    hash_password,
    verify_password,
    PasswordTooLongError,
    create_access_token,
    authenticate_user,
    get_current_user,
    login_for_access_token,
)
from services.user_service import (
    create_user_service,
    list_users_service,
    get_user_by_id,
    update_user_service,
    delete_user_service,
)
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
    start_execution_service,
    stop_execution_service,
    list_executions_service,
    get_execution_by_id,
)
from services.dashboard_service import (
    get_stats_service,
    get_trends_service,
    get_recent_service,
    get_test_types_distribution,
    get_performance_metrics,
)
from services.email_service import (
    email_service,
    send_beta_invitation,
    send_welcome_email,
    send_test_report,
    send_password_reset,
)
from services.analytics_service import (
    get_analytics_service,
    get_user_analytics,
    get_test_analytics,
    get_revenue_analytics,
    get_feature_usage_analytics,
    get_dashboard_summary,
)

__all__ = [
    # Auth
    "hash_password",
    "verify_password",
    "PasswordTooLongError",
    "create_access_token",
    "authenticate_user",
    "get_current_user",
    "login_for_access_token",
    # User
    "create_user_service",
    "list_users_service",
    "get_user_by_id",
    "update_user_service",
    "delete_user_service",
    # Suite
    "create_suite_service",
    "list_suites_service",
    "get_suite_by_id",
    "update_suite_service",
    "delete_suite_service",
    # Case
    "create_case_service",
    "list_cases_service",
    "get_case_by_id",
    "update_case_service",
    "delete_case_service",
    # Execution
    "create_execution_service",
    "start_execution_service",
    "stop_execution_service",
    "list_executions_service",
    "get_execution_by_id",
    # Dashboard
    "get_stats_service",
    "get_trends_service",
    "get_recent_service",
    "get_test_types_distribution",
    "get_performance_metrics",
    # Email
    "email_service",
    "send_beta_invitation",
    "send_welcome_email",
    "send_test_report",
    "send_password_reset",
    # Analytics
    "get_analytics_service",
    "get_user_analytics",
    "get_test_analytics",
    "get_revenue_analytics",
    "get_feature_usage_analytics",
    "get_dashboard_summary",
]
