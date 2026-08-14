# API Reference - QA-FRAMEWORK SaaS

**Version:** 1.0.0  
**Base URL:** `https://qa-framework-production.up.railway.app/api/v1`  
**OpenAPI Docs:** https://qa-framework-production.up.railway.app/api/v1/docs

---

## Table of Contents

1. [Authentication](#authentication)
2. [Test Management](#test-management)
3. [Test Executions](#test-executions)
4. [User Management](#user-management)
5. [Dashboard & Analytics](#dashboard--analytics)
6. [Billing & Subscriptions](#billing--subscriptions)
7. [Feedback](#feedback)
8. [Beta Signup](#beta-signup)
9. [Email Services](#email-services)
10. [Integrations](#integrations)
11. [Cron Jobs](#cron-jobs)
12. [Health Checks](#health-checks)
13. [Error Handling](#error-handling)
14. [Rate Limiting](#rate-limiting)
15. [Webhooks](#webhooks)

---

## Authentication

All authenticated endpoints require the `Authorization` header:

```
Authorization: Bearer <access_token>
```

### POST /api/v1/auth/login

Login with username and password.

**Request Body:**
```json
{
  "username": "admin",
  "password": "secure_password123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors:**
- `401 Unauthorized`: Invalid credentials

---

### POST /api/v1/auth/register

Register a new user.

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "username": "johndoe",
  "password": "secure_password"
}
```

**Response (201):**
```json
{
  "id": 2,
  "username": "johndoe",
  "email": "newuser@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2024-01-15T10:50:00.123456Z",
  "updated_at": "2024-01-15T10:50:00.123456Z"
}
```

---

### POST /api/v1/auth/refresh

Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

### POST /api/v1/auth/logout

Logout current user.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Logout successful. Please discard your tokens."
}
```

---

### GET /api/v1/auth/oauth/{provider}/url

Get OAuth authorization URL for a provider.

**Path Parameters:**
- `provider` (string): OAuth provider (`google` or `github`)

**Response (200):**
```json
{
  "provider": "google",
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "random_state_token"
}
```

**Errors:**
- `400 Bad Request`: Unsupported provider

---

### POST /api/v1/auth/oauth/callback

Handle OAuth callback and authenticate user.

**Request Body:**
```json
{
  "provider": "google",
  "code": "authorization_code",
  "state": "state_token"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

### GET /api/v1/auth/providers

Get list of available OAuth providers.

**Response (200):**
```json
{
  "providers": [
    {
      "name": "google",
      "configured": true,
      "display_name": "Google"
    },
    {
      "name": "github",
      "configured": true,
      "display_name": "GitHub"
    }
  ]
}
```

---

### API Keys

#### GET /api/v1/auth/api-keys

List all API keys for the authenticated user.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
[
  {
    "id": "uuid",
    "name": "Production Key",
    "scopes": ["read:tests", "write:tests"],
    "last_used_at": "2024-01-15T10:00:00Z",
    "created_at": "2024-01-01T00:00:00Z",
    "expires_at": "2024-12-31T23:59:59Z",
    "is_active": true
  }
]
```

#### POST /api/v1/auth/api-keys

Create a new API key.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "CI/CD Key",
  "scopes": ["read:tests", "write:tests"],
  "expires_in_days": 90
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "name": "CI/CD Key",
  "key": "sk_live_xxxxxxxxxxxxxxxxx",  // Only shown once!
  "scopes": ["read:tests", "write:tests"],
  "created_at": "2024-01-15T10:00:00Z",
  "expires_at": "2024-04-15T10:00:00Z"
}
```

#### DELETE /api/v1/auth/api-keys/{key_id}

Revoke an API key.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "API key revoked successfully"
}
```

#### GET /api/v1/auth/api-keys/scopes

List available API key scopes.

**Response (200):**
```json
{
  "scopes": [
    {"name": "read:tests", "description": "Read test results"},
    {"name": "write:tests", "description": "Create and update tests"},
    {"name": "delete:tests", "description": "Delete tests"},
    {"name": "read:reports", "description": "Read reports"},
    {"name": "write:reports", "description": "Generate reports"},
    {"name": "admin", "description": "Full administrative access"},
    {"name": "*", "description": "All scopes (use with caution)"}
  ]
}
```

---

## Test Management

### POST /api/v1/suites

Create a new test suite.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "API Integration Tests",
  "description": "Comprehensive API testing suite",
  "framework_type": "pytest",
  "config": {
    "parallel_workers": 4,
    "timeout": 300
  }
}
```

**Response (201):**
```json
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
```

---

### GET /api/v1/suites

List all test suites with pagination.

**Query Parameters:**
- `skip` (int, default: 0): Number of items to skip
- `limit` (int, default: 100): Maximum items to return

**Response (200):**
```json
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
```

---

### GET /api/v1/suites/{suite_id}

Get a test suite by ID.

**Response (200):**
```json
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
```

**Errors:**
- `404 Not Found`: Test suite not found

---

### PUT /api/v1/suites/{suite_id}

Update a test suite.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "Updated Suite Name",
  "description": "Updated description",
  "config": {"parallel_workers": 8}
}
```

**Response (200):**
```json
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
```

---

### DELETE /api/v1/suites/{suite_id}

Delete a test suite (soft delete).

**Headers:** `Authorization: Bearer <token>`

**Response (204):** No content

---

### POST /api/v1/cases

Create a new test case.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "suite_id": 1,
  "name": "Test User Login",
  "description": "Verify user can login",
  "test_code": "def test_login(): assert True",
  "test_type": "api",
  "priority": "high",
  "tags": ["smoke", "auth"]
}
```

**Response (201):**
```json
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
```

---

### GET /api/v1/cases

List test cases with optional filtering.

**Query Parameters:**
- `suite_id` (int, optional): Filter by test suite ID
- `skip` (int, default: 0): Number of items to skip
- `limit` (int, default: 100): Maximum items to return

**Response (200):**
```json
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
```

---

### GET /api/v1/cases/{case_id}

Get a test case by ID.

**Response (200):**
```json
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
```

---

### PUT /api/v1/cases/{case_id}

Update a test case.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "Updated Test Name",
  "priority": "critical",
  "tags": ["smoke", "auth", "regression"]
}
```

**Response (200):** Updated TestCaseResponse

---

### DELETE /api/v1/cases/{case_id}

Delete a test case (soft delete).

**Headers:** `Authorization: Bearer <token>`

**Response (204):** No content

---

## Test Executions

### POST /api/v1/executions

Create a new test execution.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "suite_id": 1,
  "execution_type": "manual",
  "environment": "staging"
}
```

**Response (201):**
```json
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
```

---

### GET /api/v1/executions

List test executions with optional filtering.

**Query Parameters:**
- `suite_id` (int, optional): Filter by test suite ID
- `status_filter` (string, optional): Filter by status (`running`, `passed`, `failed`, `skipped`, `error`)
- `skip` (int, default: 0): Number of items to skip
- `limit` (int, default: 100): Maximum items to return

**Response (200):**
```json
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
```

---

### GET /api/v1/executions/{execution_id}

Get a test execution by ID.

**Response (200):**
```json
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
```

---

### POST /api/v1/executions/{execution_id}/start

Start a test execution.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Execution started successfully",
  "execution_id": 1,
  "status": "running",
  "started_at": "2024-01-15T10:40:00.123456Z"
}
```

**Errors:**
- `409 Conflict`: Execution already running or completed

---

### POST /api/v1/executions/{execution_id}/stop

Stop a running test execution.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Execution stopped successfully",
  "execution_id": 1,
  "status": "failed",
  "duration": 180
}
```

---

## User Management

### POST /api/v1/users

Create a new user account.

**Request Body:**
```json
{
  "username": "john_doe",
  "email": "john.doe@example.com",
  "password": "SecurePass123!",
  "is_active": true
}
```

**Response (201):**
```json
{
  "id": 2,
  "username": "john_doe",
  "email": "john.doe@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2024-01-15T10:50:00.123456Z",
  "updated_at": "2024-01-15T10:50:00.123456Z"
}
```

---

### GET /api/v1/users

List all users with pagination.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `skip` (int, default: 0): Number of items to skip
- `limit` (int, default: 100): Maximum items to return

**Response (200):** Array of UserResponse

---

### GET /api/v1/users/{user_id}

Get a user by ID.

**Headers:** `Authorization: Bearer <token>`

**Response (200):** UserResponse

---

### PUT /api/v1/users/{user_id}

Update a user account.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "email": "new.email@example.com",
  "is_active": false
}
```

**Response (200):** Updated UserResponse

---

### DELETE /api/v1/users/{user_id}

Delete a user account (soft delete).

**Headers:** `Authorization: Bearer <token>`

**Response (204):** No content

---

## Dashboard & Analytics

### GET /api/v1/dashboard/stats

Get dashboard statistics.

**Response (200):**
```json
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
```

---

### GET /api/v1/dashboard/trends

Get execution trends over time.

**Query Parameters:**
- `days` (int, default: 30): Number of days for trend analysis

**Response (200):**
```json
[
  {
    "date": "2024-01-01",
    "executions": 15,
    "passed": 14,
    "failed": 1,
    "success_rate": 93.3
  }
]
```

---

### GET /api/v1/analytics/dashboard

Get comprehensive dashboard analytics.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "success": true,
  "data": {
    "summary": {
      "total_users": 350,
      "total_executions": 12500,
      "mrr": 12450,
      "subscribers": 180
    },
    "trends": {
      "signups": [...],
      "executions": [...],
      "revenue": [...]
    },
    "features": {
      "self_healing": {"usage": 45},
      "ai_generation": {"usage": 32}
    },
    "top_projects": [...]
  }
}
```

---

### GET /api/v1/analytics/users

Get user analytics.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `start_date` (string, optional): Start date (ISO format)
- `end_date` (string, optional): End date (ISO format)

**Response (200):**
```json
{
  "success": true,
  "data": {
    "total_users": 350,
    "new_signups": 45,
    "active_users": 250,
    "churned_users": 5,
    "signup_trend": [...],
    "active_trend": [...]
  }
}
```

---

### GET /api/v1/analytics/tests

Get test execution analytics.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `user_id` (int, optional): Filter by user ID
- `start_date` (string, optional): Start date (ISO format)
- `end_date` (string, optional): End date (ISO format)

**Response (200):**
```json
{
  "success": true,
  "data": {
    "total_executions": 12500,
    "passed": 11875,
    "failed": 625,
    "success_rate": 95.0,
    "avg_duration": 245.5,
    "executions_trend": [...],
    "top_projects": [...]
  }
}
```

---

### GET /api/v1/analytics/revenue

Get revenue and subscription analytics (Admin only).

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `start_date` (string, optional): Start date (ISO format)
- `end_date` (string, optional): End date (ISO format)

**Response (200):**
```json
{
  "success": true,
  "data": {
    "mrr": 12450,
    "arr": 149400,
    "total_subscribers": 180,
    "subscribers_by_plan": {
      "pro": 120,
      "enterprise": 60
    },
    "revenue_trend": [...],
    "ltv_estimate": 1494
  }
}
```

**Errors:**
- `403 Forbidden`: Admin access required

---

### GET /api/v1/analytics/features

Get feature usage analytics.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `start_date` (string, optional): Start date (ISO format)
- `end_date` (string, optional): End date (ISO format)

**Response (200):**
```json
{
  "success": true,
  "data": {
    "feature_usage": {
      "self_healing": {"users": 150, "usage_rate": 0.43},
      "ai_generation": {"users": 120, "usage_rate": 0.34}
    },
    "adoption_rates": {...},
    "total_users": 350
  }
}
```

---

### GET /api/v1/analytics/export

Export analytics report.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `report_type` (string, required): Type of report (`dashboard`, `users`, `tests`, `revenue`, `features`)
- `format` (string, default: `json`): Export format (`json` or `csv`)
- `start_date` (string, optional): Start date (ISO format)
- `end_date` (string, optional): End date (ISO format)

**Response (200):**
```json
{
  "success": true,
  "format": "json",
  "data": {...}
}
```

---

## Billing & Subscriptions

### GET /api/v1/billing/plans

Get all available subscription plans.

**Response (200):**
```json
{
  "plans": [
    {
      "name": "free",
      "price": 0,
      "currency": "usd",
      "interval": "month",
      "features": ["1,000 API calls/month", "1 test suite", "Basic support"],
      "limits": {
        "api_calls": 1000,
        "test_suites": 1,
        "storage_mb": 100
      }
    },
    {
      "name": "pro",
      "price": 99,
      "currency": "usd",
      "interval": "month",
      "features": [
        "10,000 API calls/month",
        "10 test suites",
        "Priority support",
        "AI test generation",
        "Self-healing tests"
      ],
      "limits": {
        "api_calls": 10000,
        "test_suites": 10,
        "storage_mb": 1000
      }
    },
    {
      "name": "enterprise",
      "price": 499,
      "currency": "usd",
      "interval": "month",
      "features": [
        "Unlimited API calls",
        "Unlimited test suites",
        "24/7 dedicated support",
        "Advanced AI features",
        "Custom integrations"
      ],
      "limits": {
        "api_calls": -1,
        "test_suites": -1,
        "storage_mb": 10000
      }
    }
  ]
}
```

---

### GET /api/v1/billing/subscription

Get current user's subscription details.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "plan": {
    "name": "pro",
    "price": 99,
    "currency": "usd"
  },
  "status": "active",
  "current_period_start": "2024-02-01T00:00:00Z",
  "current_period_end": "2024-03-01T00:00:00Z",
  "features": ["10,000 API calls/month", "Priority support", "AI features"]
}
```

---

### POST /api/v1/billing/subscribe

Create a new subscription.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "plan_id": "pro",
  "payment_method_id": "pm_card_visa"
}
```

**Response (200):**
```json
{
  "success": true,
  "subscription_id": "sub_123456789",
  "status": "active",
  "plan": "pro"
}
```

---

### POST /api/v1/billing/cancel

Cancel current subscription.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "immediately": false
}
```

**Response (200):**
```json
{
  "success": true,
  "subscription_id": "sub_123456789",
  "status": "canceled",
  "cancel_at_period_end": true
}
```

---

### POST /api/v1/billing/upgrade

Upgrade or downgrade subscription.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "plan_id": "enterprise"
}
```

**Response (200):**
```json
{
  "success": true,
  "subscription_id": "sub_123456789",
  "status": "active",
  "plan": "enterprise"
}
```

---

### POST /api/v1/billing/customer

Create a Stripe customer for the current user.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "customer_id": "cus_123456789",
  "exists": false
}
```

---

### POST /api/v1/billing/webhook

Handle Stripe webhook events.

**Headers:**
- `Stripe-Signature`: Webhook signature

**Request Body:** Stripe webhook payload

**Response (200):**
```json
{
  "status": "success"
}
```

---

## Feedback

### POST /api/v1/feedback

Submit feedback (anonymous or authenticated).

**Request Body:**
```json
{
  "type": "bug",
  "category": "dashboard",
  "rating": 3,
  "message": "The download button doesn't work on Firefox",
  "tags": ["firefox", "download"],
  "priority": "medium",
  "anonymous": false
}
```

**Response (201):**
```json
{
  "id": 1,
  "type": "bug",
  "category": "dashboard",
  "rating": 3,
  "message": "The download button doesn't work on Firefox",
  "tags": ["firefox", "download"],
  "status": "new",
  "created_at": "2024-01-15T10:00:00Z"
}
```

---

### GET /api/v1/feedback

List feedback with pagination and filters.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `page` (int, default: 1): Page number
- `page_size` (int, default: 20): Items per page
- `status_filter` (string, optional): Filter by status
- `feedback_type` (string, optional): Filter by type
- `priority` (string, optional): Filter by priority

**Response (200):**
```json
{
  "items": [...],
  "total": 25,
  "page": 1,
  "page_size": 20
}
```

---

### GET /api/v1/feedback/stats

Get feedback statistics.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "total_feedback": 150,
  "by_status": {
    "new": 45,
    "in_progress": 30,
    "resolved": 60,
    "closed": 15
  },
  "by_type": {
    "bug": 80,
    "feature": 40,
    "general": 20,
    "improvement": 10
  },
  "average_rating": 4.2
}
```

---

### GET /api/v1/feedback/{feedback_id}

Get feedback by ID.

**Headers:** `Authorization: Bearer <token>`

**Response (200):** FeedbackResponse

---

### PATCH /api/v1/feedback/{feedback_id}

Update feedback.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "status": "in_progress",
  "assigned_to": "user_id"
}
```

**Response (200):** Updated FeedbackResponse

---

### DELETE /api/v1/feedback/{feedback_id}

Delete feedback (admin only).

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "success": true,
  "message": "Feedback deleted successfully"
}
```

---

## Beta Signup

### POST /api/v1/beta/signup

Sign up for beta program (public endpoint).

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "team_size": 10,
  "use_case": "ecommerce_testing"
}
```

**Response (201):**
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "team_size": 10,
  "use_case": "ecommerce_testing",
  "status": "pending",
  "created_at": "2024-01-15T10:00:00Z"
}
```

**Errors:**
- `409 Conflict`: Email already registered

---

### GET /api/v1/beta

List beta signups (admin only).

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `page` (int, default: 1): Page number
- `page_size` (int, default: 20): Items per page
- `status_filter` (string, optional): Filter by status
- `source` (string, optional): Filter by source

**Response (200):**
```json
{
  "items": [...],
  "total": 500,
  "page": 1,
  "page_size": 20
}
```

---

### GET /api/v1/beta/stats

Get beta signup statistics (admin only).

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "total_signups": 500,
  "approved": 450,
  "pending": 30,
  "rejected": 20,
  "conversion_rate": 0.90,
  "avg_team_size": 8
}
```

---

### GET /api/v1/beta/check/{email}

Check if email is already registered.

**Response (200):**
```json
{
  "registered": true
}
```

---

### POST /api/v1/beta/{signup_id}/approve

Approve a beta signup (admin only).

**Headers:** `Authorization: Bearer <token>`

**Response (200):** Updated BetaSignupResponse

---

### POST /api/v1/beta/{signup_id}/reject

Reject a beta signup (admin only).

**Headers:** `Authorization: Bearer <token>`

**Response (200):** Updated BetaSignupResponse

---

## Email Services

### POST /api/v1/email/beta-invitation

Send beta tester invitation email.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "email": "user@example.com",
  "name": "John Doe",
  "referral_code": "BETA123",
  "accept_url": "https://example.com/accept"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Beta invitation email queued for user@example.com"
}
```

---

### POST /api/v1/email/welcome

Send welcome email to new user.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "email": "user@example.com",
  "name": "John Doe"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Welcome email queued for user@example.com"
}
```

---

### POST /api/v1/email/test-report

Send test execution report email.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "email": "user@example.com",
  "project_name": "E-commerce API",
  "execution_date": "2024-01-15T10:00:00Z",
  "total_tests": 100,
  "passed": 95,
  "failed": 5,
  "duration": "2m 30s",
  "report_url": "https://dashboard.example.com/reports/123",
  "failed_tests": [
    {"name": "test_payment", "error": "Timeout"}
  ]
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Test report email queued for user@example.com"
}
```

---

### POST /api/v1/email/password-reset

Send password reset email (public endpoint).

**Request Body:**
```json
{
  "email": "user@example.com",
  "name": "John Doe",
  "reset_token": "abc123...",
  "expires_in": 24
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Password reset email queued for user@example.com"
}
```

---

### POST /api/v1/email/bulk

Send bulk emails (admin only).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "emails": ["user1@example.com", "user2@example.com"],
  "subject": "Monthly Update",
  "template": "welcome",
  "template_data": {"name": "User"}
}
```

**Response (200):**
```json
{
  "success": true,
  "queued_count": 2,
  "total_recipients": 2,
  "message": "Bulk emails queued: 2/2"
}
```

---

### GET /api/v1/email/templates

List available email templates.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "success": true,
  "templates": [
    {
      "name": "beta_invitation",
      "description": "Beta tester invitation email",
      "required_fields": ["name", "referral_code"],
      "optional_fields": ["accept_url"]
    }
  ]
}
```

---

### POST /api/v1/email/preview/{template_name}

Preview email template with sample data.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com"
}
```

**Response (200):**
```json
{
  "success": true,
  "template_name": "beta_invitation",
  "html": "<html>...</html>"
}
```

---

## Integrations

### GET /api/v1/integrations/providers

Get list of all available integration providers.

**Response (200):**
```json
{
  "providers": [
    {
      "name": "jira",
      "display_name": "Jira",
      "configured": false
    },
    {
      "name": "testrail",
      "display_name": "TestRail",
      "configured": true
    }
  ]
}
```

---

### GET /api/v1/integrations/configured

Get list of currently configured integrations.

**Response (200):**
```json
{
  "configured": [
    {
      "provider": "jira",
      "connected": true,
      "last_sync": "2024-01-15T10:00:00Z"
    }
  ]
}
```

---

### POST /api/v1/integrations/configure

Configure an integration provider.

**Request Body:**
```json
{
  "provider": "jira",
  "config": {
    "url": "https://company.atlassian.net",
    "api_token": "xxx",
    "email": "user@example.com"
  }
}
```

**Response (200):**
```json
{
  "status": "success",
  "provider": "jira",
  "configured": true
}
```

---

### DELETE /api/v1/integrations/configure/{provider}

Remove an integration.

**Response (200):**
```json
{
  "status": "success",
  "provider": "jira",
  "removed": true
}
```

---

### POST /api/v1/integrations/{provider}/connect

Connect to an integration provider.

**Response (200):**
```json
{
  "provider": "jira",
  "connected": true
}
```

---

### POST /api/v1/integrations/{provider}/disconnect

Disconnect from an integration provider.

**Response (200):**
```json
{
  "provider": "jira",
  "disconnected": true
}
```

---

### GET /api/v1/integrations/{provider}/health

Check health status of an integration.

**Response (200):**
```json
{
  "provider": "jira",
  "health": {
    "status": "healthy",
    "last_check": "2024-01-15T10:00:00Z"
  }
}
```

---

### GET /api/v1/integrations/health/all

Check health status of all integrations.

**Response (200):**
```json
{
  "health_status": {
    "jira": {"status": "healthy"},
    "testrail": {"status": "healthy"}
  }
}
```

---

### POST /api/v1/integrations/sync

Synchronize test results to integration providers.

**Request Body:**
```json
{
  "results": [
    {
      "test_id": "test_1",
      "status": "passed",
      "duration_ms": 150
    }
  ],
  "providers": ["jira", "testrail"],
  "project_key": "PROJ",
  "cycle_name": "Sprint 1"
}
```

**Response (200):**
```json
{
  "sync_results": {
    "jira": {
      "success": true,
      "synced_count": 1,
      "failed_count": 0
    }
  }
}
```

---

### POST /api/v1/integrations/{provider}/test-cases

Create a test case in the specified provider.

**Request Body:**
```json
{
  "name": "Test User Login",
  "description": "Verify user can login",
  "project_key": "PROJ",
  "folder": "Authentication",
  "labels": ["smoke", "auth"]
}
```

**Response (200):**
```json
{
  "test_case": {
    "id": "TC-123",
    "name": "Test User Login",
    "url": "https://jira.example.com/browse/TC-123"
  }
}
```

---

### GET /api/v1/integrations/{provider}/test-cases

Get test cases from the specified provider.

**Query Parameters:**
- `project_key` (string, required): Project key
- `folder` (string, optional): Folder filter
- `status` (string, optional): Status filter

**Response (200):**
```json
{
  "test_cases": [
    {
      "id": "TC-123",
      "name": "Test User Login",
      "status": "pass"
    }
  ]
}
```

---

### POST /api/v1/integrations/{provider}/bugs

Create a bug in the specified provider.

**Request Body:**
```json
{
  "title": "Login button not working",
  "description": "The login button fails to submit",
  "project_key": "PROJ",
  "severity": "high",
  "priority": "critical",
  "labels": ["bug", "auth"]
}
```

**Response (200):**
```json
{
  "bug": {
    "id": "BUG-456",
    "key": "PROJ-456",
    "url": "https://jira.example.com/browse/PROJ-456"
  }
}
```

---

### GET /api/v1/integrations/{provider}/bugs

Get bugs from the specified provider.

**Query Parameters:**
- `project_key` (string, required): Project key
- `status` (string, optional): Status filter
- `assigned_to` (string, optional): Assignee filter

**Response (200):**
```json
{
  "bugs": [...]
}
```

---

### GET /api/v1/integrations/{provider}/projects

Get projects from the specified provider.

**Response (200):**
```json
{
  "projects": [
    {
      "key": "PROJ",
      "name": "Main Project"
    }
  ]
}
```

---

## Cron Jobs

### GET /api/v1/cron/jobs

Get all active cron jobs.

**Response (200):**
```json
[
  {
    "id": 1,
    "name": "cleanup_old_executions",
    "schedule": "0 2 * * *",
    "is_active": true,
    "last_run": "2024-01-15T02:00:00Z",
    "next_run": "2024-01-16T02:00:00Z"
  }
]
```

---

### GET /api/v1/cron/jobs/{job_id}

Get a specific cron job by ID.

**Response (200):** CronJobResponse

**Errors:**
- `404 Not Found`: Job not found

---

### GET /api/v1/cron/jobs/{job_id}/executions

Get execution history for a specific job.

**Query Parameters:**
- `limit` (int, default: 50, max: 500): Maximum executions to return

**Response (200):**
```json
[
  {
    "id": 1,
    "job_id": 1,
    "status": "completed",
    "started_at": "2024-01-15T02:00:00Z",
    "completed_at": "2024-01-15T02:05:00Z",
    "duration_ms": 300000
  }
]
```

---

### POST /api/v1/cron/jobs/{job_id}/run

Trigger manual execution of a cron job.

**Response (200):**
```json
{
  "execution_id": 123,
  "status": "started",
  "message": "Job execution started"
}
```

---

### GET /api/v1/cron/stats

Get overall cron job statistics.

**Response (200):**
```json
{
  "total_jobs": 10,
  "active_jobs": 8,
  "total_executions_today": 45,
  "success_rate": 0.98
}
```

---

## Health Checks

### GET /api/v1/health/live

Kubernetes liveness probe.

**Response (200):**
```json
{
  "status": "alive",
  "timestamp": "2024-01-15T10:00:00Z",
  "uptime_seconds": 86400
}
```

---

### GET /api/v1/health/ready

Kubernetes readiness probe.

**Response (200):**
```json
{
  "status": "ready",
  "timestamp": "2024-01-15T10:00:00Z",
  "checks": {
    "database": {"status": "healthy", "response_time_ms": 5.2},
    "redis": {"status": "healthy", "response_time_ms": 2.1},
    "qa_framework": {"status": "healthy", "response_time_ms": 150.5}
  }
}
```

**Errors:**
- `503 Service Unavailable`: One or more checks failed

---

### GET /api/v1/health/startup

Kubernetes startup probe.

**Response (200):**
```json
{
  "status": "started",
  "startup_time": "2024-01-15T09:00:00Z",
  "startup_duration_seconds": 5.2
}
```

---

### GET /api/v1/health/status

Detailed health status with all system information.

**Response (200):**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:00:00Z",
  "system": {
    "platform": "Linux-5.15.0",
    "python_version": "3.11.0",
    "cpu_percent": 25.5,
    "memory_percent": 45.2,
    "disk_usage_percent": 60.1
  },
  "application": {
    "uptime_seconds": 86400,
    "start_time": "2024-01-15T09:00:00Z"
  },
  "services": {
    "database": {"status": "healthy"},
    "redis": {"status": "healthy"},
    "qa_framework": {"status": "healthy"}
  }
}
```

---

### GET /api/v1/health/metrics

Prometheus metrics endpoint.

**Response (200):** Plain text Prometheus metrics

---

## Error Handling

All errors follow a consistent format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

For validation errors:

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "Invalid email format",
      "type": "value_error.email"
    }
  ]
}
```

### Common HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| `200 OK` | Request successful |
| `201 Created` | Resource created successfully |
| `204 No Content` | Request successful, no content to return |
| `400 Bad Request` | Invalid request or validation error |
| `401 Unauthorized` | Authentication required |
| `403 Forbidden` | Insufficient permissions |
| `404 Not Found` | Resource not found |
| `409 Conflict` | Conflict with existing resource |
| `422 Unprocessable Entity` | Validation failed |
| `429 Too Many Requests` | Rate limit exceeded |
| `500 Internal Server Error` | Server error |
| `503 Service Unavailable` | Service temporarily unavailable |

---

## Rate Limiting

| Endpoint Type | Rate Limit |
|---------------|------------|
| Auth endpoints | 100 requests/minute |
| Public endpoints | 1000 requests/minute |
| User endpoints | 1000 requests/minute |
| Admin endpoints | 500 requests/minute |

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 2024-01-15T11:00:00Z
```

---

## Webhooks

### Available Webhook Events

| Event | Description |
|-------|-------------|
| `subscription.created` | New subscription created |
| `subscription.updated` | Subscription updated |
| `subscription.cancelled` | Subscription cancelled |
| `subscription.payment_failed` | Payment failed |
| `test.run.completed` | Test execution completed |
| `test.run.started` | Test execution started |
| `test.run.failed` | Test execution failed |

### Webhook Payload Example

```json
{
  "event": "subscription.updated",
  "data": {
    "subscription_id": "sub_123456789",
    "plan": "pro",
    "status": "active",
    "previous_plan": "free"
  },
  "timestamp": "2024-01-15T10:00:00Z",
  "signature": "sha256=abc123..."
}
```

### Stripe Webhook

**Endpoint:** `POST /api/v1/billing/webhook`

**Headers:**
- `Stripe-Signature`: Webhook signature from Stripe

---

## API Versioning

The API uses URL-based versioning. The current version is `v1`.

**Base URL:** `/api/v1/`

Future versions will be available at `/api/v2/`, etc.

---

**Last Updated:** 2026-03-04  
**Maintained by:** QA-FRAMEWORK Team

---

## Endpoint Summary

| Category | Endpoints |
|----------|-----------|
| **Authentication** | 13 endpoints |
| **Test Suites** | 5 endpoints |
| **Test Cases** | 5 endpoints |
| **Test Executions** | 5 endpoints |
| **Users** | 5 endpoints |
| **Dashboard** | 2 endpoints |
| **Analytics** | 6 endpoints |
| **Billing** | 7 endpoints |
| **Feedback** | 6 endpoints |
| **Beta Signup** | 6 endpoints |
| **Email** | 7 endpoints |
| **Integrations** | 15 endpoints |
| **Cron Jobs** | 4 endpoints |
| **Health Checks** | 5 endpoints |
| **Total** | **91 endpoints** |
