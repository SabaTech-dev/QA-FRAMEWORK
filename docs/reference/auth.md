# Authentication System Documentation

**Last Updated:** 2026-02-24
**Version:** 1.0.0
**Sprint:** 2.2 - Authentication & Authorization

---

## Overview

QA-FRAMEWORK SaaS provides a comprehensive authentication system supporting multiple authentication methods:

- **Email/Password** - Traditional credentials-based authentication
- **Google OAuth 2.0** - Social login with Google
- **GitHub OAuth 2.0** - Social login with GitHub
- **API Keys** - Programmatic access for automation

---

## Architecture

### Domain Layer

Located in `src/domain/auth/`:

```
src/domain/auth/
├── __init__.py          # Module exports
├── entities.py          # User, OAuthUser, Token, Session, APIKey
├── interfaces.py        # Abstract interfaces
└── value_objects.py     # AuthProvider, TokenStatus, Email, Password
```

#### Entities

| Entity | Purpose |
|--------|---------|
| `User` | Base user entity with email, password hash, tenant association |
| `OAuthUser` | OAuth-specific user data from social providers |
| `Token` | Access and refresh tokens with expiration |
| `Session` | User session with device info and activity tracking |
| `APIKey` | API key for programmatic access with scopes |

#### Value Objects

| Value Object | Purpose |
|--------------|---------|
| `AuthProvider` | Enum: GOOGLE, GITHUB, EMAIL, API_KEY |
| `TokenStatus` | Enum: ACTIVE, EXPIRED, REVOKED, USED |
| `Email` | Validated email address |
| `Password` | Password with strength validation |

### Infrastructure Layer

Located in `src/infrastructure/oauth/`:

```
src/infrastructure/oauth/
├── __init__.py           # Module exports
├── base_oauth.py         # BaseOAuthProvider with common OAuth flow
├── google_oauth.py       # Google OAuth implementation
├── github_oauth.py       # GitHub OAuth implementation
└── oauth_factory.py      # Factory for creating providers
```

---

## Configuration

### Environment Variables

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# JWT Settings
JWT_SECRET_KEY=your_secure_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

### OAuth Provider Setup

#### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 credentials
3. Add authorized redirect URIs:
   - `https://your-domain.com/auth/google/callback`
   - `http://localhost:8000/auth/google/callback` (development)
4. Enable required APIs (People API)

#### GitHub OAuth Setup

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Create new OAuth App
3. Set callback URL:
   - `https://your-domain.com/auth/github/callback`
   - `http://localhost:8000/auth/github/callback` (development)

---

## API Endpoints

### Authentication Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/providers` | GET | List available auth providers |
| `/auth/register` | POST | Register new user with email/password |
| `/auth/login` | POST | Login with email/password |
| `/auth/verify-email` | POST | Verify email address |
| `/auth/forgot-password` | POST | Request password reset |
| `/auth/reset-password` | POST | Reset password with token |
| `/auth/change-password` | POST | Change password (authenticated) |

### OAuth Endpoints

| Endpoint | Method | Provider | Description |
|----------|--------|----------|-------------|
| `/auth/google` | GET | Google | Initiate Google OAuth flow |
| `/auth/google/callback` | GET | Google | Handle Google OAuth callback |
| `/auth/github` | GET | GitHub | Initiate GitHub OAuth flow |
| `/auth/github/callback` | GET | GitHub | Handle GitHub OAuth callback |

### API Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/api-keys` | GET | List user's API keys |
| `/auth/api-keys` | POST | Create new API key |
| `/auth/api-keys/{id}` | DELETE | Revoke API key |
| `/auth/api-keys/{id}/regenerate` | POST | Regenerate API key |
| `/auth/api-keys/scopes` | GET | List available scopes |

### Session Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/sessions` | GET | List active sessions |
| `/auth/sessions/current` | GET | Get current session info |
| `/auth/sessions/{id}` | DELETE | Revoke specific session |
| `/auth/sessions` | DELETE | Revoke all other sessions |

---

## Usage Examples

### Email/Password Registration

```bash
curl -X POST https://api.qaframework.io/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "name": "John Doe"
  }'
```

### Email/Password Login

```bash
curl -X POST https://api.qaframework.io/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "rt_abc123...",
  "user_id": "uuid-here"
}
```

### Google OAuth Flow

1. **Initiate OAuth:**
```bash
curl "https://api.qaframework.io/auth/google?redirect_uri=https://app.qaframework.io/callback"
```

2. **User redirected to Google consent screen**

3. **Google redirects back with code:**
```
https://app.qaframework.io/callback?code=abc123&state=xyz789
```

4. **Exchange code for token:**
```bash
curl "https://api.qaframework.io/auth/google/callback?code=abc123&state=xyz789"
```

### Create API Key

```bash
curl -X POST https://api.qaframework.io/auth/api-keys \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CI/CD Pipeline",
    "scopes": ["read:tests", "write:tests"],
    "expires_in_days": 90
  }'
```

Response (key shown only once!):
```json
{
  "id": "uuid-here",
  "name": "CI/CD Pipeline",
  "key": "qa_1a2b3c4d5e6f...",
  "scopes": ["read:tests", "write:tests"],
  "created_at": "2026-02-24T21:00:00Z",
  "expires_at": "2026-05-25T21:00:00Z"
}
```

### Using API Key

```bash
curl https://api.qaframework.io/api/v1/tests \
  -H "X-API-Key: qa_1a2b3c4d5e6f..."
```

---

## Password Requirements

Passwords must meet the following criteria:

- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 number
- At least 1 special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

---

## API Key Scopes

| Scope | Description |
|-------|-------------|
| `read:tests` | Read test results |
| `write:tests` | Create and update tests |
| `delete:tests` | Delete tests |
| `read:reports` | Read reports |
| `write:reports` | Generate reports |
| `admin` | Full administrative access |
| `*` | All scopes (use with caution) |

---

## Security Best Practices

1. **Never store API keys in code** - Use environment variables
2. **Rotate API keys regularly** - Every 90 days recommended
3. **Use minimal scopes** - Grant only necessary permissions
4. **Monitor session activity** - Revoke suspicious sessions
5. **Enable 2FA** - When available (future feature)
6. **Use HTTPS everywhere** - Never transmit tokens over HTTP

---

## Rate Limiting

| Endpoint Type | Rate Limit |
|---------------|------------|
| Login | 5 attempts / 15 minutes |
| API requests | 1000 / hour (varies by plan) |
| OAuth | 10 requests / minute |

---

## Error Handling

### Common Error Codes

| Code | Description |
|------|-------------|
| 400 | Invalid request (check password requirements) |
| 401 | Invalid credentials or expired token |
| 403 | Insufficient permissions |
| 409 | Email already registered |
| 429 | Rate limit exceeded |

---

## Multi-Tenant Isolation

All authentication is tenant-aware:

- Users belong to a specific tenant
- Sessions are isolated per tenant
- API keys are scoped to tenant
- OAuth flows maintain tenant context

---

## Future Enhancements

- [ ] Two-Factor Authentication (2FA)
- [ ] Single Sign-On (SSO) with SAML
- [ ] Magic link authentication
- [ ] Biometric authentication
- [ ] Passwordless login
- [ ] Session analytics dashboard

---

## Support

For authentication issues:
- Email: support@qaframework.io
- Discord: discord.gg/qaframework
- Docs: docs.qaframework.io/auth
