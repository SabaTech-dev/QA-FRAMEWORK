# QA-Framework Dashboard API Guide

Complete guide for integrating with the QA-Framework Dashboard API.

## Table of Contents

- [Overview](#overview)
- [Base URL](#base-url)
- [Authentication](#authentication)
- [Common Patterns](#common-patterns)
- [Best Practices](#best-practices)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [API Versioning](#api-versioning)

---

## Overview

The QA-Framework Dashboard API provides a comprehensive RESTful interface for managing test suites, test cases, test executions, and user management. Built with FastAPI, it offers:

- **RESTful Architecture**: Standard HTTP methods and status codes
- **JSON Format**: All requests and responses use JSON
- **Async Support**: Full async/await support for optimal performance
- **Type Safety**: Pydantic models for request/response validation
- **Auto-generated Documentation**: Interactive Swagger UI at `/api/v1/docs` (development only — disabled when `ENVIRONMENT=production`)
- **Structured Logging**: Every request is logged with unique request IDs

### Key Features

| Feature | Description |
|---------|-------------|
| Test Suite Management | Create, update, delete, and organize test suites |
| Test Case Operations | Manage individual test cases with metadata |
| Execution Control | Start, stop, and monitor test executions |
| Dashboard Analytics | Real-time statistics and trend analysis |
| User Management | Multi-user support with role-based access |
| Caching | Redis-based caching for optimal performance |

---

## Base URL

```
Development: http://localhost:8000/api/v1
Production:  https://your-domain.com/api/v1
```

### API Endpoints Overview

```
Authentication
├── POST /auth/login              # Obtain access token

Dashboard
├── GET  /dashboard/stats         # Dashboard statistics
├── GET  /dashboard/trends        # Execution trends

Test Suites
├── POST   /suites                # Create suite
├── GET    /suites                # List suites
├── GET    /suites/{id}           # Get suite
├── PUT    /suites/{id}           # Update suite
├── DELETE /suites/{id}           # Delete suite

Test Cases
├── POST   /cases                 # Create case
├── GET    /cases                 # List cases
├── GET    /cases/{id}            # Get case
├── PUT    /cases/{id}            # Update case
├── DELETE /cases/{id}            # Delete case

Executions
├── POST   /executions            # Create execution
├── GET    /executions            # List executions
├── GET    /executions/{id}       # Get execution
├── POST   /executions/{id}/start # Start execution
├── POST   /executions/{id}/stop  # Stop execution

Users
├── POST   /users                 # Create user
├── GET    /users                 # List users
├── GET    /users/{id}            # Get user
├── PUT    /users/{id}            # Update user
├── DELETE /users/{id}            # Delete user
```

---

## Authentication

The API uses **JWT (JSON Web Tokens)** for authentication. All protected endpoints require a valid Bearer token in the Authorization header.

### Obtaining a Token

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Using the Token

Include the token in the Authorization header for all subsequent requests:

```http
GET /api/v1/suites
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Expiration

- Tokens expire after **30 minutes** by default
- You'll receive a `401 Unauthorized` response when the token expires
- Re-authenticate using the `/auth/login` endpoint to obtain a new token

### Authentication Flow

```
┌─────────────┐                    ┌─────────────┐
│   Client    │─── POST /login ───▶│    API      │
│             │                    │             │
│             │◀── Token (JWT) ────│             │
│             │                    │             │
│             │── Authenticated ───▶│             │
│             │   Requests +       │   Validate  │
│             │   Bearer Token     │   Token     │
└─────────────┘                    └─────────────┘
```

---

## Common Patterns

### Request/Response Format

All API requests and responses use JSON format with UTF-8 encoding.

**Request Headers:**
```http
Content-Type: application/json
Authorization: Bearer <token>
Accept: application/json
```

### CRUD Operations

| Operation | HTTP Method | Endpoint Pattern | Status Code |
|-----------|-------------|------------------|-------------|
| Create | POST | `/resource` | 201 Created |
| Read All | GET | `/resource` | 200 OK |
| Read One | GET | `/resource/{id}` | 200 OK |
| Update | PUT | `/resource/{id}` | 200 OK |
| Delete | DELETE | `/resource/{id}` | 204 No Content |

### Pagination

List endpoints support pagination with `skip` and `limit` parameters:

```http
GET /api/v1/suites?skip=0&limit=20
```

**Parameters:**
- `skip` (int): Number of items to skip (default: 0)
- `limit` (int): Maximum items to return (default: 100, max: 1000)

**Response Pattern:**
```json
[
  {
    "id": 1,
    "name": "Suite Name",
    ...
  },
  {
    "id": 2,
    "name": "Another Suite",
    ...
  }
]
```

### Filtering

Many list endpoints support filtering:

```http
# Filter cases by suite
GET /api/v1/cases?suite_id=1

# Filter executions by suite and status
GET /api/v1/executions?suite_id=1&status_filter=passed

# Get trends for specific period
GET /api/v1/dashboard/trends?days=7
```

### DateTime Format

All datetime fields use **ISO 8601 format** in UTC:

```
2024-01-15T10:30:45.123456Z
```

### Enum Values

The API uses enums for specific fields. Always use valid enum values:

**Test Types:** `api`, `ui`, `db`, `security`, `performance`, `mobile`

**Priority Levels:** `low`, `medium`, `high`, `critical`

**Execution Status:** `running`, `passed`, `failed`, `skipped`, `error`

**Execution Types:** `manual`, `scheduled`, `ci`

---

## Best Practices

### 1. Error Handling

Always check HTTP status codes and handle errors appropriately:

```python
import requests

response = requests.get("/api/v1/suites/999")
if response.status_code == 404:
    print("Suite not found")
elif response.status_code == 401:
    print("Authentication required - refresh token")
```

### 2. Pagination Handling

When fetching large datasets, implement pagination:

```python
def fetch_all_suites():
    all_suites = []
    skip = 0
    limit = 100
    
    while True:
        response = requests.get(f"/api/v1/suites?skip={skip}&limit={limit}")
        suites = response.json()
        
        if not suites:
            break
            
        all_suites.extend(suites)
        skip += limit
    
    return all_suites
```

### 3. Idempotency

For create operations, consider implementing idempotency keys to prevent duplicate creation on network retries.

### 4. Caching

The API implements Redis caching. Cache TTL values:
- **1 minute**: Execution data, rapidly changing stats
- **10 minutes**: Suite/case lists, test configurations
- **1 hour**: User profiles, reference data

### 5. Request Timeouts

Set appropriate timeouts for different operations:
- **Read operations**: 10 seconds
- **Write operations**: 30 seconds
- **Execution start/stop**: 60 seconds

### 6. Connection Pooling

Use connection pooling for optimal performance:

```python
import requests

session = requests.Session()
# Reuse session for multiple requests
response = session.get("/api/v1/suites")
```

### 7. Structured Logging

Every API request is automatically logged with:
- Unique request ID
- Method and URL
- Client IP
- Duration
- Status code

Include the request ID in your client logs for debugging:

```http
X-Request-ID: <your-request-id>
```

---

## Rate Limiting

The API implements rate limiting to ensure fair usage and system stability.

### Current Limits

| Endpoint Category | Limit | Window |
|------------------|-------|--------|
| Authentication | 5 requests | 1 minute |
| General API | 100 requests | 1 minute |
| Dashboard Stats | 30 requests | 1 minute |
| Execution Start/Stop | 10 requests | 1 minute |

### Rate Limit Headers

When rate limiting is active, responses include:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

### Handling Rate Limits

When you receive a `429 Too Many Requests` response:

1. Check the `Retry-After` header
2. Implement exponential backoff
3. Cache responses when appropriate

**Example Backoff Strategy:**

```python
import time
import random

def exponential_backoff(attempt, max_delay=60):
    """Calculate delay with exponential backoff and jitter."""
    delay = min(2 ** attempt, max_delay)
    jitter = random.uniform(0, 1)
    return delay + jitter

# Usage
for attempt in range(5):
    response = requests.get("/api/v1/suites")
    if response.status_code == 429:
        delay = exponential_backoff(attempt)
        time.sleep(delay)
    else:
        break
```

### Optimizing Requests

To avoid hitting rate limits:

1. **Batch Operations**: Use bulk endpoints when available
2. **Cache Aggressively**: Store frequently accessed data locally
3. **Use Webhooks**: For real-time updates instead of polling
4. **Implement Local Caching**: Cache immutable data (e.g., suite configurations)

---

## Error Handling

### HTTP Status Codes

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 204 | No Content | Request successful, no body returned |
| 400 | Bad Request | Invalid request format or parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Valid auth but insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Service temporarily unavailable |

### Error Response Format

All errors follow a consistent format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Validation Error Example:**

```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

### Common Error Scenarios

**Authentication Errors:**
```json
{ "detail": "Invalid authentication credentials" }
```

**Not Found:**
```json
{ "detail": "Test suite not found" }
```

**Validation Error:**
```json
{ "detail": "Invalid email format" }
```

**Conflict (Duplicate):**
```json
{ "detail": "Username already exists" }
```

---

## API Versioning

The API uses URL versioning (`/api/v1/`). When breaking changes are introduced, a new version will be released.

### Version History

| Version | Status | Release Date |
|---------|--------|--------------|
| v1 | Current | 2024-01-15 |

### Deprecation Policy

- API versions are supported for at least 12 months after deprecation
- Deprecated versions return a `Sunset` header with the end-of-life date
- Major changes are announced 3 months in advance

### Migration Guide

When migrating to a new API version:

1. Review the changelog for breaking changes
2. Update your base URL
3. Test all integrations in a staging environment
4. Update client libraries if applicable
5. Monitor for deprecation warnings

---

## Additional Resources

- **Interactive API Docs**: `/api/v1/docs` (Swagger UI)
- **Alternative Docs**: `/api/v1/redoc` (ReDoc)
- **OpenAPI Schema**: `/api/v1/openapi.json`
- **Examples**: See [api-examples.md](api-examples.md)
- **Architecture**: See [architecture.md](architecture.md)
- **Troubleshooting**: See [troubleshooting.md](troubleshooting.md)

---

## Comprehensive Error Codes Reference

### HTTP Status Codes

#### Success Codes

| Status Code | Meaning | When Returned |
|-------------|---------|---------------|
| 200 | OK | GET, PUT requests successful |
| 201 | Created | POST requests creating new resources |
| 204 | No Content | DELETE requests successful |

#### Client Error Codes

| Status Code | Meaning | Common Causes |
|-------------|---------|---------------|
| 400 | Bad Request | Malformed JSON, missing required fields |
| 401 | Unauthorized | Missing or invalid JWT token |
| 403 | Forbidden | Valid token but insufficient permissions |
| 404 | Not Found | Resource ID doesn't exist |
| 405 | Method Not Allowed | HTTP method not supported on endpoint |
| 408 | Request Timeout | Request took too long to process |
| 409 | Conflict | Resource already exists, state conflict |
| 410 | Gone | Resource permanently deleted |
| 413 | Payload Too Large | Request body exceeds limit |
| 415 | Unsupported Media Type | Content-Type not application/json |
| 422 | Unprocessable Entity | Validation error, invalid field values |
| 423 | Locked | Resource temporarily locked |
| 429 | Too Many Requests | Rate limit exceeded |
| 451 | Unavailable For Legal Reasons | Content blocked |

#### Server Error Codes

| Status Code | Meaning | Common Causes |
|-------------|---------|---------------|
| 500 | Internal Server Error | Unexpected server error |
| 501 | Not Implemented | Feature not yet implemented |
| 502 | Bad Gateway | Upstream service error |
| 503 | Service Unavailable | Service temporarily down or overloaded |
| 504 | Gateway Timeout | Upstream service timeout |

### Detailed Error Messages

#### Authentication Errors

```json
// 401 - Missing Authorization Header
{
  "detail": "Not authenticated"
}

// 401 - Invalid Token Format
{
  "detail": "Invalid authentication credentials"
}

// 401 - Expired Token
{
  "detail": "Token has expired"
}

// 401 - Invalid Credentials
{
  "detail": "Incorrect username or password"
}
```

#### Authorization Errors

```json
// 403 - Insufficient Permissions
{
  "detail": "Not enough permissions"
}

// 403 - Cannot Delete Own Account
{
  "detail": "Cannot delete your own account"
}
```

#### Resource Errors

```json
// 404 - Test Suite Not Found
{
  "detail": "Test suite not found"
}

// 404 - Test Case Not Found
{
  "detail": "Test case not found"
}

// 404 - Test Execution Not Found
{
  "detail": "Test execution not found"
}

// 404 - User Not Found
{
  "detail": "User not found"
}
```

#### Validation Errors

```json
// 400 - Duplicate Username
{
  "detail": "Username already exists"
}

// 400 - Duplicate Email
{
  "detail": "Email already registered"
}

// 422 - Field Validation Error
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}

// 422 - Min Length Violation
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "ensure this value has at least 8 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}

// 422 - Required Field Missing
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}

// 422 - Invalid Enum Value
{
  "detail": [
    {
      "loc": ["body", "priority"],
      "msg": "value is not a valid enumeration member",
      "type": "type_error.enum"
    }
  ]
}
```

#### Conflict Errors

```json
// 409 - Execution Already Running
{
  "detail": "Execution is already running"
}

// 409 - Execution Already Completed
{
  "detail": "Execution has already completed"
}

// 409 - Execution Not Running
{
  "detail": "Execution is not currently running"
}
```

#### Rate Limit Errors

```json
// 429 - Rate Limit Exceeded
{
  "detail": "Rate limit exceeded"
}

// 429 - Too Many Login Attempts
{
  "detail": "Too many login attempts. Please try again later."
}
```

#### Server Errors

```json
// 500 - Database Connection Error
{
  "detail": "Internal server error"
}

// 500 - Unexpected Error
{
  "detail": "An unexpected error occurred"
}

// 503 - Service Unavailable
{
  "detail": "Service temporarily unavailable"
}
```

### Error Code Quick Reference by Endpoint

#### Authentication Endpoints

| Endpoint | Possible Errors | Status Codes |
|----------|----------------|--------------|
| `POST /auth/login` | Invalid credentials, validation | 401, 422 |

#### Dashboard Endpoints

| Endpoint | Possible Errors | Status Codes |
|----------|----------------|--------------|
| `GET /dashboard/stats` | None | 200 |
| `GET /dashboard/trends` | Invalid days parameter | 400, 422 |

#### Suite Endpoints

| Endpoint | Possible Errors | Status Codes |
|----------|----------------|--------------|
| `POST /suites` | Auth required, validation | 401, 422 |
| `GET /suites` | None | 200 |
| `GET /suites/{id}` | Not found | 404 |
| `PUT /suites/{id}` | Auth required, not found, validation | 401, 404, 422 |
| `DELETE /suites/{id}` | Auth required, not found | 401, 404 |

#### Case Endpoints

| Endpoint | Possible Errors | Status Codes |
|----------|----------------|--------------|
| `POST /cases` | Auth required, suite not found, validation | 401, 404, 422 |
| `GET /cases` | None | 200 |
| `GET /cases/{id}` | Not found | 404 |
| `PUT /cases/{id}` | Auth required, not found, validation | 401, 404, 422 |
| `DELETE /cases/{id}` | Auth required, not found | 401, 404 |

#### Execution Endpoints

| Endpoint | Possible Errors | Status Codes |
|----------|----------------|--------------|
| `POST /executions` | Auth required, suite not found, validation | 401, 404, 422 |
| `GET /executions` | None | 200 |
| `GET /executions/{id}` | Not found | 404 |
| `POST /executions/{id}/start` | Auth required, not found, already running | 401, 404, 409 |
| `POST /executions/{id}/stop` | Auth required, not found, not running | 401, 404, 409 |

#### User Endpoints

| Endpoint | Possible Errors | Status Codes |
|----------|----------------|--------------|
| `POST /users` | Duplicate user, validation | 400, 422 |
| `GET /users` | Auth required | 401 |
| `GET /users/{id}` | Auth required, not found | 401, 404 |
| `PUT /users/{id}` | Auth required, not found, validation | 401, 404, 422 |
| `DELETE /users/{id}` | Auth required, not found, self-delete | 401, 403, 404 |

---

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Authentication Issues

**Problem:** "Not authenticated" or "Invalid authentication credentials"

**Solutions:**
```bash
# 1. Verify token is being sent correctly
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/suites

# 2. Check token hasn't expired - login again to get fresh token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'

# 3. Verify token format (should start with 'eyJ')
echo $TOKEN | cut -d'.' -f1 | base64 -d 2>/dev/null
```

**Problem:** "Token has expired"

**Solution:**
```python
# Re-authenticate to get a new token
import requests

response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"username": "admin", "password": "secure_password123"}
)
token = response.json()["access_token"]
```

#### 2. 404 Not Found Errors

**Problem:** Resource returns 404 even though ID seems correct

**Solutions:**
```bash
# 1. Verify the resource exists
# List all resources to find valid IDs
curl http://localhost:8000/api/v1/suites

# 2. Check for soft-deleted resources
curl http://localhost:8000/api/v1/suites/1
# Response: {"detail": "Test suite not found"}
# Resource may have been soft-deleted

# 3. Verify you're using the correct endpoint
# Wrong: /api/v1/suite/1 (singular)
# Correct: /api/v1/suites/1 (plural)
```

#### 3. Validation Errors (422)

**Problem:** "field required" or validation errors

**Solutions:**
```bash
# 1. Check required fields in request body
# Required: name, email, password (for user creation)
# Required: suite_id, name, test_code (for case creation)

# 2. Verify data types
curl -X POST http://localhost:8000/api/v1/suites \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Test Suite",           # String, required
    "description": "Description",   # String, optional
    "framework_type": "pytest"      # String, optional (default: pytest)
  }'

# 3. Check field constraints
# - username: min 3, max 50 characters
# - password: min 8 characters
# - email: valid email format
# - suite_id: must be positive integer
```

#### 4. Rate Limiting (429)

**Problem:** "Rate limit exceeded"

**Solutions:**
```python
import time
import random

def make_request_with_backoff(url, headers, max_retries=5):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code == 429:
            # Exponential backoff with jitter
            delay = min(2 ** attempt, 60) + random.uniform(0, 1)
            print(f"Rate limited. Waiting {delay:.1f}s...")
            time.sleep(delay)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")

# Use connection pooling to reduce requests
session = requests.Session()
session.headers.update({'Authorization': f'Bearer {token}'})
```

#### 5. CORS Errors (Browser/Frontend)

**Problem:** CORS policy blocks requests from browser

**Solutions:**
```javascript
// 1. Ensure correct headers
fetch('http://localhost:8000/api/v1/suites', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  credentials: 'include'  // If using cookies
});

// 2. Check server CORS configuration
// Backend must include your origin in allow_origins
// See backend/main.py CORS middleware configuration
```

#### 6. Database Connection Issues

**Problem:** 500 errors or slow responses

**Solutions:**
```bash
# 1. Check database connectivity
psql -h localhost -U postgres -d qa_framework -c "SELECT 1"

# 2. Verify environment variables
echo $DATABASE_URL
# Should be: postgresql+asyncpg://user:pass@localhost/qa_framework

# 3. Check server logs
docker-compose logs backend

# 4. Restart services
docker-compose restart backend
```

#### 7. Test Execution Failures

**Problem:** Execution stuck in "running" state or fails immediately

**Solutions:**
```bash
# 1. Check execution status
curl http://localhost:8000/api/v1/executions/1

# 2. Stop stuck execution
curl -X POST http://localhost:8000/api/v1/executions/1/stop \
  -H "Authorization: Bearer $TOKEN"

# 3. Verify suite has test cases
curl "http://localhost:8000/api/v1/cases?suite_id=1"

# 4. Check execution environment is valid
# Valid values: "production", "staging", "development"
```

#### 8. Pagination Issues

**Problem:** Not getting all expected results

**Solutions:**
```python
# 1. Use pagination correctly
all_suites = []
skip = 0
limit = 100

while True:
    response = requests.get(
        f"http://localhost:8000/api/v1/suites?skip={skip}&limit={limit}",
        headers=headers
    )
    suites = response.json()
    
    if not suites:
        break
    
    all_suites.extend(suites)
    skip += limit

print(f"Total suites: {len(all_suites)}")

# 2. Check default limits
# Default limit: 100
# Maximum limit: 1000
```

### Debugging Checklist

When encountering API issues:

- [ ] **Check Authentication**
  - Token is included in Authorization header
  - Token hasn't expired
  - Format: `Bearer <token>`

- [ ] **Verify Request Format**
  - Content-Type: `application/json`
  - Valid JSON in request body
  - Required fields are present

- [ ] **Check Resource IDs**
  - Resource exists (not soft-deleted)
  - ID is positive integer
  - Using correct endpoint URL

- [ ] **Review Rate Limits**
  - Not exceeding 100 requests/minute
  - Implement backoff on 429 errors

- [ ] **Inspect Server Logs**
  - Check for detailed error messages
  - Look for stack traces
  - Verify request ID for tracing

- [ ] **Validate Data**
  - Field types match schema
  - String lengths within limits
  - Enum values are valid

### Getting Help

If issues persist:

1. **Check Request ID**: Every response includes a request ID in logs
   ```
   X-Request-ID: 123e4567-e89b-12d3-a456-426614174000
   ```

2. **Enable Debug Logging**:
   ```bash
   export LOG_LEVEL=DEBUG
   ```

3. **Test with cURL**: Isolate client vs server issues
   ```bash
   curl -v http://localhost:8000/api/v1/suites
   ```

4. **Check API Health**:
   ```bash
   curl http://localhost:8000/health
   ```

---

## Support

For API support:
- Check the troubleshooting guide first
- Review example code in the documentation
- Open an issue in the project repository
- Include the request ID for faster debugging
