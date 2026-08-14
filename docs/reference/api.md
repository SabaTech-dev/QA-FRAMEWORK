# API Reference

## Overview

QA-Framework provides a comprehensive REST API for managing test suites, test cases, executions, and reports.

**Base URL:** `http://localhost:8000/api/v1`

**Authentication:** JWT Bearer Token

**Content-Type:** `application/json`

## Authentication

### Register User

```http
POST /auth/register
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123",
  "full_name": "John Doe"
}
```

**Response:** `201 Created`
```json
{
  "id": "user_123",
  "email": "user@example.com",
  "full_name": "John Doe",
  "created_at": "2026-02-20T10:00:00Z"
}
```

### Login

```http
POST /auth/login
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Refresh Token

```http
POST /auth/refresh
```

**Headers:** `Authorization: Bearer {token}`

**Response:** `200 OK`
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## Test Suites

### List Test Suites

```http
GET /suites
```

**Query Parameters:**
- `skip` (int): Number of records to skip (default: 0)
- `limit` (int): Maximum records to return (default: 100)
- `tags` (string): Filter by tags (comma-separated)
- `search` (string): Search in name/description

**Response:** `200 OK`
```json
{
  "total": 50,
  "items": [
    {
      "id": "suite_123",
      "name": "Login Tests",
      "description": "Authentication tests",
      "tags": ["smoke", "auth"],
      "test_count": 10,
      "created_at": "2026-02-20T10:00:00Z",
      "updated_at": "2026-02-20T12:00:00Z",
      "status": "active"
    }
  ]
}
```

### Create Test Suite

```http
POST /suites
```

**Request Body:**
```json
{
  "name": "My Test Suite",
  "description": "Suite description",
  "tags": ["tag1", "tag2"],
  "priority": "high"
}
```

**Response:** `201 Created`
```json
{
  "id": "suite_124",
  "name": "My Test Suite",
  "description": "Suite description",
  "tags": ["tag1", "tag2"],
  "test_count": 0,
  "created_at": "2026-02-20T13:00:00Z",
  "status": "active"
}
```

### Get Test Suite

```http
GET /suites/{suite_id}
```

**Response:** `200 OK`
```json
{
  "id": "suite_123",
  "name": "Login Tests",
  "description": "Authentication tests",
  "tags": ["smoke", "auth"],
  "test_count": 10,
  "created_at": "2026-02-20T10:00:00Z",
  "test_cases": [
    {
      "id": "case_1",
      "name": "Valid Login",
      "status": "passed"
    }
  ]
}
```

### Update Test Suite

```http
PUT /suites/{suite_id}
```

**Request Body:**
```json
{
  "name": "Updated Suite Name",
  "description": "Updated description",
  "tags": ["new-tag"]
}
```

**Response:** `200 OK`

### Delete Test Suite

```http
DELETE /suites/{suite_id}
```

**Response:** `204 No Content`

## Test Cases

### List Test Cases

```http
GET /suites/{suite_id}/cases
```

**Response:** `200 OK`
```json
{
  "total": 10,
  "items": [
    {
      "id": "case_1",
      "name": "Valid Login",
      "description": "Test valid user login",
      "status": "active",
      "priority": "high",
      "steps": [
        "Navigate to login page",
        "Enter valid credentials",
        "Click submit"
      ],
      "expected_result": "User logged in successfully"
    }
  ]
}
```

### Create Test Case

```http
POST /suites/{suite_id}/cases
```

**Request Body:**
```json
{
  "name": "Test Case Name",
  "description": "Test case description",
  "priority": "medium",
  "steps": [
    "Step 1",
    "Step 2"
  ],
  "expected_result": "Expected outcome"
}
```

**Response:** `201 Created`

### Get Test Case

```http
GET /suites/{suite_id}/cases/{case_id}
```

**Response:** `200 OK`

### Update Test Case

```http
PUT /suites/{suite_id}/cases/{case_id}
```

**Response:** `200 OK`

### Delete Test Case

```http
DELETE /suites/{suite_id}/cases/{case_id}
```

**Response:** `204 No Content`

## Test Executions

### Run Test Suite

```http
POST /suites/{suite_id}/run
```

**Request Body:**
```json
{
  "environment": "staging",
  "tags": ["smoke"],
  "parallel": true,
  "workers": 4
}
```

**Response:** `202 Accepted`
```json
{
  "execution_id": "exec_123",
  "suite_id": "suite_123",
  "status": "running",
  "started_at": "2026-02-20T14:00:00Z",
  "estimated_duration": 300
}
```

### Get Execution Status

```http
GET /executions/{execution_id}
```

**Response:** `200 OK`
```json
{
  "execution_id": "exec_123",
  "suite_id": "suite_123",
  "status": "completed",
  "started_at": "2026-02-20T14:00:00Z",
  "completed_at": "2026-02-20T14:05:00Z",
  "duration": 300,
  "summary": {
    "total": 10,
    "passed": 8,
    "failed": 1,
    "skipped": 1
  }
}
```

### List Executions

```http
GET /executions
```

**Query Parameters:**
- `suite_id` (string): Filter by suite ID
- `status` (string): Filter by status (running, completed, failed)
- `start_date` (string): Filter from date (ISO 8601)
- `end_date` (string): Filter to date (ISO 8601)

**Response:** `200 OK`
```json
{
  "total": 100,
  "items": [
    {
      "execution_id": "exec_123",
      "suite_id": "suite_123",
      "status": "completed",
      "started_at": "2026-02-20T14:00:00Z",
      "summary": {
        "total": 10,
        "passed": 8,
        "failed": 1,
        "skipped": 1
      }
    }
  ]
}
```

### Cancel Execution

```http
POST /executions/{execution_id}/cancel
```

**Response:** `200 OK`
```json
{
  "execution_id": "exec_123",
  "status": "cancelled",
  "message": "Execution cancelled successfully"
}
```

## Test Results

### Get Execution Results

```http
GET /executions/{execution_id}/results
```

**Response:** `200 OK`
```json
{
  "execution_id": "exec_123",
  "results": [
    {
      "case_id": "case_1",
      "name": "Valid Login",
      "status": "passed",
      "duration": 2.5,
      "started_at": "2026-02-20T14:00:00Z",
      "completed_at": "2026-02-20T14:00:02Z",
      "error": null
    },
    {
      "case_id": "case_2",
      "name": "Invalid Login",
      "status": "failed",
      "duration": 1.8,
      "started_at": "2026-02-20T14:00:03Z",
      "completed_at": "2026-02-20T14:00:05Z",
      "error": "AssertionError: Expected error message not found"
    }
  ]
}
```

## Reports

### Generate HTML Report

```http
GET /executions/{execution_id}/reports/html
```

**Response:** `200 OK` (HTML content)

### Generate JSON Report

```http
GET /executions/{execution_id}/reports/json
```

**Response:** `200 OK` (JSON content)

### Generate Allure Report

```http
GET /executions/{execution_id}/reports/allure
```

**Response:** `200 OK` (Allure JSON)

### Download Report

```http
GET /executions/{execution_id}/reports/download?format=html
```

**Response:** `200 OK` (File download)

## Integrations

### Jira Integration

#### Sync Test Case to Jira

```http
POST /integrations/jira/sync/{case_id}
```

**Response:** `200 OK`
```json
{
  "case_id": "case_1",
  "jira_key": "PROJ-123",
  "synced_at": "2026-02-20T15:00:00Z"
}
```

#### Get Jira Issues

```http
GET /integrations/jira/issues
```

**Query Parameters:**
- `project` (string): Jira project key
- `status` (string): Issue status

**Response:** `200 OK`

### Slack Integration

#### Send Notification

```http
POST /integrations/slack/notify
```

**Request Body:**
```json
{
  "channel": "#test-results",
  "execution_id": "exec_123",
  "message": "Test execution completed"
}
```

**Response:** `200 OK`

## Health & Monitoring

### Health Check

```http
GET /health
```

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "checks": {
    "database": "healthy",
    "redis": "healthy",
    "storage": "healthy"
  }
}
```

### Ready Check

```http
GET /ready
```

**Response:** `200 OK`

### Live Check

```http
GET /live
```

**Response:** `200 OK`

### Metrics (Prometheus)

```http
GET /metrics
```

**Response:** `200 OK` (Prometheus format)

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Invalid request body",
  "errors": [
    {
      "field": "name",
      "message": "Name is required"
    }
  ]
}
```

### 401 Unauthorized

```json
{
  "detail": "Could not validate credentials",
  "error": "invalid_token"
}
```

### 403 Forbidden

```json
{
  "detail": "Not enough permissions",
  "error": "forbidden"
}
```

### 404 Not Found

```json
{
  "detail": "Suite not found",
  "error": "not_found"
}
```

### 422 Unprocessable Entity

```json
{
  "detail": "Validation error",
  "errors": [
    {
      "field": "email",
      "message": "Invalid email format"
    }
  ]
}
```

### 429 Too Many Requests

```json
{
  "detail": "Rate limit exceeded",
  "error": "rate_limit",
  "retry_after": 60
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error",
  "error": "internal_error",
  "request_id": "req_123"
}
```

## Rate Limits

| Endpoint Type | Limit |
|---------------|-------|
| Auth endpoints | 5 requests/minute |
| Read operations | 200 requests/minute |
| Write operations | 50 requests/minute |
| Execution operations | 10 requests/minute |

Rate limit headers are included in all responses:
- `X-RateLimit-Limit`: Maximum requests per minute
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when the limit resets

## Pagination

All list endpoints support pagination:

**Query Parameters:**
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 100, max: 1000)

**Response Format:**
```json
{
  "total": 1000,
  "skip": 0,
  "limit": 100,
  "items": [...]
}
```

## Sorting

Most list endpoints support sorting:

**Query Parameters:**
- `sort_by`: Field to sort by
- `sort_order`: `asc` or `desc` (default: `desc`)

Example: `GET /suites?sort_by=created_at&sort_order=desc`

## Filtering

Most list endpoints support filtering:

**Query Parameters:**
- Various field-specific filters (see individual endpoints)

Example: `GET /suites?tags=smoke,regression&status=active`

## Versioning

The API uses URL-based versioning: `/api/v1/`

When breaking changes are introduced, a new version will be released (e.g., `/api/v2/`).

## SDKs

### Python SDK

```bash
pip install qa-framework-sdk
```

```python
from qa_framework import Client

client = Client(api_key="your-api-key")
suites = client.suites.list()
```

### JavaScript SDK

```bash
npm install qa-framework-sdk
```

```javascript
import { Client } from 'qa-framework-sdk';

const client = new Client({ apiKey: 'your-api-key' });
const suites = await client.suites.list();
```

---

For more information, see the [Getting Started](../getting-started.md) guide or [Architecture](../explanation/architecture.md) documentation.
