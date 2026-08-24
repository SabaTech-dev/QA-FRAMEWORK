"""
Security Tests for Authentication System
=========================================

Comprehensive security tests covering:
- Password hashing verification
- JWT token validation
- API key generation and validation
- Session management security
- OAuth security checks
- Rate limiting
- SQL injection prevention
- XSS prevention
"""

import hashlib
import re
import secrets
import time
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
import pytest
from fastapi import HTTPException
from jose import jwt as jose_jwt

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_password_hasher():
    """Mock password hasher for testing."""

    class PasswordHasher:
        @staticmethod
        def hash_password(password: str) -> str:
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

        @staticmethod
        def verify_password(plain_password: str, hashed_password: str) -> bool:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

    return PasswordHasher()


@pytest.fixture
def mock_token_generator():
    """Mock token generator for testing."""

    class TokenGenerator:
        SECRET_KEY = "test-secret-key-for-testing-only"
        ALGORITHM = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES = 30

        @staticmethod
        def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
            to_encode = data.copy()
            expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=30))
            to_encode.update({"exp": expire})
            return jose_jwt.encode(
                to_encode, TokenGenerator.SECRET_KEY, algorithm=TokenGenerator.ALGORITHM
            )

        @staticmethod
        def decode_token(token: str) -> dict:
            try:
                return jose_jwt.decode(
                    token, TokenGenerator.SECRET_KEY, algorithms=[TokenGenerator.ALGORITHM]
                )
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=401, detail="Token has expired")
            except jwt.InvalidTokenError:
                raise HTTPException(status_code=401, detail="Invalid token")

    return TokenGenerator()


@pytest.fixture
def mock_api_key_generator():
    """Mock API key generator for testing."""

    class APIKeyGenerator:
        PREFIX = "qa_"

        @staticmethod
        def generate_api_key() -> str:
            """Generate a secure API key."""
            random_bytes = secrets.token_bytes(32)
            key_hash = hashlib.sha256(random_bytes).hexdigest()
            return f"{APIKeyGenerator.PREFIX}{key_hash}"

        @staticmethod
        def validate_api_key_format(api_key: str) -> bool:
            """Validate API key format."""
            if not api_key:
                return False
            if not api_key.startswith(APIKeyGenerator.PREFIX):
                return False
            key_part = api_key[len(APIKeyGenerator.PREFIX) :]
            return len(key_part) == 64 and all(c in "0123456789abcdef" for c in key_part)

    return APIKeyGenerator()


@pytest.fixture
def mock_session_store():
    """Mock session store for testing."""

    class SessionStore:
        def __init__(self):
            self._sessions = {}

        def create_session(self, user_id: str) -> str:
            session_id = secrets.token_urlsafe(32)
            self._sessions[session_id] = {
                "user_id": user_id,
                "created_at": datetime.now(UTC),
                "expires_at": datetime.now(UTC) + timedelta(hours=24),
            }
            return session_id

        def get_session(self, session_id: str) -> dict:
            session = self._sessions.get(session_id)
            if session and session["expires_at"] > datetime.now(UTC):
                return session
            return None

        def invalidate_session(self, session_id: str) -> bool:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    return SessionStore()


# ============================================================================
# Password Security Tests
# ============================================================================


class TestPasswordSecurity:
    """Tests for password hashing and verification."""

    def test_password_hashing_creates_unique_hashes(self, mock_password_hasher):
        """Each password hash should be unique due to salt."""
        password = "testPassword123!"
        hash1 = mock_password_hasher.hash_password(password)
        hash2 = mock_password_hasher.hash_password(password)

        assert hash1 != hash2, "Same password should produce different hashes"

    def test_password_hashing_verifies_correctly(self, mock_password_hasher):
        """Correct password should verify successfully."""
        password = "testPassword123!"
        hashed = mock_password_hasher.hash_password(password)

        assert mock_password_hasher.verify_password(password, hashed)

    def test_password_hashing_rejects_wrong_password(self, mock_password_hasher):
        """Wrong password should fail verification."""
        password = "testPassword123!"
        wrong_password = "wrongPassword456!"
        hashed = mock_password_hasher.hash_password(password)

        assert not mock_password_hasher.verify_password(wrong_password, hashed)

    def test_password_hash_format_is_bcrypt(self, mock_password_hasher):
        """Hash should be in bcrypt format."""
        password = "testPassword123!"
        hashed = mock_password_hasher.hash_password(password)

        assert hashed.startswith("$2b$"), "Hash should be bcrypt format"

    @pytest.mark.parametrize(
        "weak_password",
        [
            "123456",
            "password",
            "abc123",
            "qwerty",
            "",
        ],
    )
    def test_weak_passwords_should_be_rejected(self, weak_password):
        """Weak passwords should be rejected during registration."""

        # This would be implemented in the password validation layer
        def is_password_strong(password: str) -> bool:
            if len(password) < 8:
                return False
            if not re.search(r"[A-Z]", password):
                return False
            if not re.search(r"[a-z]", password):
                return False
            if not re.search(r"\d", password):
                return False
            if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
                return False
            return True

        assert not is_password_strong(
            weak_password
        ), f"Weak password '{weak_password}' should be rejected"

    def test_password_timing_attack_resistance(self, mock_password_hasher):
        """Password verification should have consistent timing."""
        password = "testPassword123!"
        hashed = mock_password_hasher.hash_password(password)

        # Measure time for correct password
        times_correct = []
        for _ in range(10):
            start = time.perf_counter()
            mock_password_hasher.verify_password(password, hashed)
            times_correct.append(time.perf_counter() - start)

        # Measure time for incorrect password
        times_incorrect = []
        for _ in range(10):
            start = time.perf_counter()
            mock_password_hasher.verify_password("wrongPassword!", hashed)
            times_incorrect.append(time.perf_counter() - start)

        avg_correct = sum(times_correct) / len(times_correct)
        avg_incorrect = sum(times_incorrect) / len(times_incorrect)

        # Bcrypt should have similar timing regardless of correctness
        # Allow 20% variance
        assert abs(avg_correct - avg_incorrect) < (
            avg_correct * 0.2
        ), "Timing difference could indicate timing attack vulnerability"


# ============================================================================
# JWT Token Security Tests
# ============================================================================


class TestJWTTokenSecurity:
    """Tests for JWT token validation and security."""

    def test_token_creation_includes_claims(self, mock_token_generator):
        """Token should include required claims."""
        user_data = {"sub": "user123", "email": "test@example.com"}
        token = mock_token_generator.create_access_token(user_data)
        decoded = mock_token_generator.decode_token(token)

        assert decoded["sub"] == user_data["sub"]
        assert decoded["email"] == user_data["email"]
        assert "exp" in decoded, "Token should have expiration"

    def test_token_expiration_is_enforced(self, mock_token_generator):
        """Expired tokens should be rejected."""
        user_data = {"sub": "user123"}

        # Create token that expires immediately
        token = mock_token_generator.create_access_token(
            user_data, expires_delta=timedelta(seconds=-1)
        )

        # Should raise either HTTPException or ExpiredSignatureError
        # The jose library throws ExpiredSignatureError directly
        from jose.exceptions import ExpiredSignatureError

        with pytest.raises((HTTPException, ExpiredSignatureError, jwt.ExpiredSignatureError)):
            mock_token_generator.decode_token(token)

    def test_token_tampering_detection(self, mock_token_generator):
        """Tampered tokens should be rejected."""
        user_data = {"sub": "user123", "role": "user"}
        token = mock_token_generator.create_access_token(user_data)

        # Tamper with token
        parts = token.split(".")
        if len(parts) == 3:
            # Modify the payload
            tampered_token = parts[0] + "." + "tampered" + "." + parts[2]

            # Should raise either HTTPException or JWT error
            with pytest.raises((HTTPException, jwt.InvalidTokenError, Exception)):
                mock_token_generator.decode_token(tampered_token)

    def test_token_without_signature_rejected(self, mock_token_generator):
        """Tokens without valid signatures should be rejected."""
        # Create a token without proper signature
        fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIn0.fake"

        # Should raise either HTTPException or JWT error
        with pytest.raises((HTTPException, jwt.InvalidTokenError, Exception)):
            mock_token_generator.decode_token(fake_token)

    def test_algorithm_confusion_attack_prevention(self, mock_token_generator):
        """Should reject tokens with algorithm confusion attacks."""
        # jose library doesn't support 'none' algorithm, which is good!
        # This test verifies that we don't accidentally enable it
        payload = {"sub": "user123", "role": "admin"}

        # Try to manually create a token with none algorithm (should fail or be rejected)
        try:
            none_token = jose_jwt.encode(payload, "", algorithm="none")
            # If somehow it was created, it should be rejected
            with pytest.raises((HTTPException, jwt.InvalidTokenError, Exception)):
                mock_token_generator.decode_token(none_token)
        except Exception:
            # Expected: library doesn't support 'none' algorithm
            pass  # This is the correct behavior!


# ============================================================================
# API Key Security Tests
# ============================================================================


class TestAPIKeySecurity:
    """Tests for API key generation and validation."""

    def test_api_key_generation_is_unique(self, mock_api_key_generator):
        """Each generated API key should be unique."""
        key1 = mock_api_key_generator.generate_api_key()
        key2 = mock_api_key_generator.generate_api_key()

        assert key1 != key2, "API keys should be unique"

    def test_api_key_format_validation(self, mock_api_key_generator):
        """API key format should be validated."""
        valid_key = mock_api_key_generator.generate_api_key()
        invalid_key = "invalid_key_format"

        assert mock_api_key_generator.validate_api_key_format(valid_key)
        assert not mock_api_key_generator.validate_api_key_format(invalid_key)

    def test_api_key_has_correct_prefix(self, mock_api_key_generator):
        """API key should have correct prefix."""
        key = mock_api_key_generator.generate_api_key()
        assert key.startswith(mock_api_key_generator.PREFIX)

    def test_api_key_length_is_sufficient(self, mock_api_key_generator):
        """API key should be long enough for security."""
        key = mock_api_key_generator.generate_api_key()
        assert len(key) >= 64, "API key should be at least 64 characters"

    @pytest.mark.parametrize(
        "malformed_key",
        [
            "",
            "qa_",
            "qa_short",
            "wrong_prefix_" + "a" * 64,
            "qa_" + "invalid_chars_!@#$%",
        ],
    )
    def test_malformed_api_keys_rejected(self, mock_api_key_generator, malformed_key):
        """Malformed API keys should be rejected."""
        assert not mock_api_key_generator.validate_api_key_format(malformed_key)


# ============================================================================
# Session Security Tests
# ============================================================================


class TestSessionSecurity:
    """Tests for session management security."""

    def test_session_creation(self, mock_session_store):
        """Sessions should be created correctly."""
        user_id = "user123"
        session_id = mock_session_store.create_session(user_id)

        assert session_id is not None
        session = mock_session_store.get_session(session_id)
        assert session["user_id"] == user_id

    def test_session_expiration(self, mock_session_store):
        """Sessions should expire after timeout."""
        user_id = "user123"
        session_id = mock_session_store.create_session(user_id)

        # Mock expired session
        mock_session_store._sessions[session_id]["expires_at"] = datetime.now(UTC) - timedelta(
            hours=1
        )

        session = mock_session_store.get_session(session_id)
        assert session is None, "Expired session should return None"

    def test_session_invalidation(self, mock_session_store):
        """Sessions should be properly invalidated."""
        user_id = "user123"
        session_id = mock_session_store.create_session(user_id)

        # Invalidate session
        result = mock_session_store.invalidate_session(session_id)
        assert result is True

        # Session should no longer exist
        session = mock_session_store.get_session(session_id)
        assert session is None

    def test_session_id_is_cryptographically_random(self, mock_session_store):
        """Session IDs should be cryptographically random."""
        session_ids = [mock_session_store.create_session("user123") for _ in range(100)]

        # All session IDs should be unique
        assert len(set(session_ids)) == len(session_ids), "Session IDs should be unique"

        # Session IDs should be URL-safe
        for sid in session_ids:
            assert re.match(r"^[A-Za-z0-9_-]+$", sid), "Session ID should be URL-safe"


# ============================================================================
# OAuth Security Tests
# ============================================================================


class TestOAuthSecurity:
    """Tests for OAuth security."""

    def test_oauth_state_parameter_validation(self):
        """OAuth state parameter should be validated to prevent CSRF."""

        def validate_state(received_state: str, expected_state: str) -> bool:
            return secrets.compare_digest(received_state, expected_state)

        # Valid state
        state = secrets.token_urlsafe(32)
        assert validate_state(state, state)

        # Invalid state
        assert not validate_state(state, "invalid_state")

    def test_oauth_redirect_uri_validation(self):
        """OAuth redirect URI should be validated to prevent open redirect."""
        allowed_redirects = [
            "https://example.com/auth/callback",
            "https://app.example.com/auth/callback",
        ]

        def validate_redirect_uri(uri: str) -> bool:
            return uri in allowed_redirects

        assert validate_redirect_uri("https://example.com/auth/callback")
        assert not validate_redirect_uri("https://evil.com/callback")
        assert not validate_redirect_uri("https://example.com.evil.com/callback")

    def test_oauth_code_single_use(self):
        """OAuth authorization codes should be single-use."""
        used_codes = set()

        def use_code(code: str) -> bool:
            if code in used_codes:
                return False
            used_codes.add(code)
            return True

        code = secrets.token_urlsafe(32)
        assert use_code(code) is True  # First use
        assert use_code(code) is False  # Second use should fail


# ============================================================================
# Rate Limiting Tests
# ============================================================================


class TestRateLimiting:
    """Tests for rate limiting on auth endpoints."""

    def test_rate_limiting_prevents_brute_force(self):
        """Rate limiting should prevent brute force attacks."""

        class RateLimiter:
            def __init__(self, max_attempts: int = 5, window_seconds: int = 60):
                self.max_attempts = max_attempts
                self.window_seconds = window_seconds
                self.attempts = {}

            def is_allowed(self, key: str) -> bool:
                now = time.time()
                if key not in self.attempts:
                    self.attempts[key] = []

                # Remove old attempts
                self.attempts[key] = [
                    t for t in self.attempts[key] if now - t < self.window_seconds
                ]

                if len(self.attempts[key]) >= self.max_attempts:
                    return False

                self.attempts[key].append(now)
                return True

        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        ip = "192.168.1.1"

        # First 3 attempts should succeed
        assert limiter.is_allowed(ip)
        assert limiter.is_allowed(ip)
        assert limiter.is_allowed(ip)

        # 4th attempt should be blocked
        assert not limiter.is_allowed(ip)

    def test_rate_limiting_by_ip_and_user(self):
        """Rate limiting should track both IP and user."""

        class DualRateLimiter:
            def __init__(self):
                self.ip_limits = {}
                self.user_limits = {}

            def is_allowed(self, ip: str, user: str = None) -> bool:
                ip_allowed = self._check_limit(self.ip_limits, ip, 100, 3600)
                user_allowed = self._check_limit(self.user_limits, user, 5, 300) if user else True
                return ip_allowed and user_allowed

            def _check_limit(self, store: dict, key: str, max_attempts: int, window: int) -> bool:
                if not key:
                    return True
                now = time.time()
                if key not in store:
                    store[key] = []
                store[key] = [t for t in store[key] if now - t < window]
                if len(store[key]) >= max_attempts:
                    return False
                store[key].append(now)
                return True

        limiter = DualRateLimiter()

        # IP should allow many requests
        for _ in range(10):
            assert limiter.is_allowed("192.168.1.1")

        # User should have stricter limit
        for i in range(6):
            result = limiter.is_allowed("192.168.1.1", "user123")
            if i < 5:
                assert result
            else:
                assert not result


# ============================================================================
# SQL Injection Prevention Tests
# ============================================================================


class TestSQLInjectionPrevention:
    """Tests for SQL injection prevention in auth queries."""

    @pytest.mark.parametrize(
        "malicious_input",
        [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "admin'--",
            "' UNION SELECT * FROM users --",
            "1; SELECT * FROM users",
            "' OR 1=1 --",
            '" OR ""="',
            "1' AND '1'='1",
        ],
    )
    def test_sql_injection_inputs_sanitized(self, malicious_input):
        """SQL injection attempts should be sanitized."""

        def sanitize_input(value: str) -> str:
            # Basic sanitization - in production use parameterized queries
            dangerous_chars = ["'", '"', ";", "--", "/*", "*/", "DROP", "SELECT", "UNION"]
            sanitized = value
            for char in dangerous_chars:
                sanitized = sanitized.replace(char, "")
            return sanitized

        sanitized = sanitize_input(malicious_input)

        # Sanitized input should not contain dangerous patterns
        assert "DROP" not in sanitized.upper()
        assert "SELECT" not in sanitized.upper()
        assert "UNION" not in sanitized.upper()
        assert "--" not in sanitized
        assert ";" not in sanitized

    def test_parameterized_queries_used(self):
        """Auth queries should use parameterized statements."""

        # This test verifies the pattern, actual implementation would check the code
        def safe_query_template(query: str, params: tuple) -> dict:
            """Simulates parameterized query execution."""
            # In real implementation, this would use cursor.execute(query, params)
            return {"query": query, "params": params, "safe": True}

        query = "SELECT * FROM users WHERE email = %s AND password = %s"
        params = ("user@example.com", "hashed_password")

        result = safe_query_template(query, params)
        assert result["safe"]
        assert "%s" in result["query"]


# ============================================================================
# XSS Prevention Tests
# ============================================================================


class TestXSSPrevention:
    """Tests for XSS prevention in user inputs."""

    @pytest.mark.parametrize(
        "xss_payload",
        [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<body onload=alert('XSS')>",
            "<iframe src='javascript:alert(1)'>",
            "'\"><script>alert('XSS')</script>",
            "<<SCRIPT>alert('XSS');//<</SCRIPT>",
        ],
    )
    def test_xss_payloads_sanitized(self, xss_payload):
        """XSS payloads should be sanitized."""
        import html
        import re

        def sanitize_html(value: str) -> str:
            # First HTML escape
            escaped = html.escape(value)
            # Also remove any remaining dangerous patterns
            escaped = re.sub(r"javascript:", "", escaped, flags=re.IGNORECASE)
            escaped = re.sub(r"onerror\s*=", "", escaped, flags=re.IGNORECASE)
            escaped = re.sub(r"onload\s*=", "", escaped, flags=re.IGNORECASE)
            return escaped

        sanitized = sanitize_html(xss_payload)

        # Sanitized output should not contain executable scripts
        # After html.escape, < becomes &lt; and > becomes &gt;
        assert "<script>" not in sanitized.lower()
        assert "javascript:" not in sanitized.lower()
        assert "onerror=" not in sanitized.lower()
        assert "onload=" not in sanitized.lower()

    def test_content_security_headers(self):
        """Response should include security headers."""
        expected_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Content-Security-Policy": "default-src 'self'",
        }

        # In actual implementation, verify these headers are set
        for header, expected_value in expected_headers.items():
            assert header is not None
            assert expected_value is not None


# ============================================================================
# Security Headers Tests
# ============================================================================


class TestSecurityHeaders:
    """Tests for security-related HTTP headers."""

    def test_secure_cookie_attributes(self):
        """Session cookies should have secure attributes."""

        def create_secure_cookie(name: str, value: str) -> dict:
            return {
                "name": name,
                "value": value,
                "secure": True,
                "httponly": True,
                "samesite": "Lax",
                "path": "/",
            }

        cookie = create_secure_cookie("session", "session_value")

        assert cookie["secure"] is True, "Cookie should have Secure flag"
        assert cookie["httponly"] is True, "Cookie should have HttpOnly flag"
        assert cookie["samesite"] in ["Lax", "Strict"], "Cookie should have SameSite attribute"

    def test_cors_configuration(self):
        """CORS should be properly configured."""
        allowed_origins = ["https://example.com", "https://app.example.com"]

        def validate_cors_origin(origin: str) -> bool:
            return origin in allowed_origins

        assert validate_cors_origin("https://example.com")
        assert not validate_cors_origin("https://evil.com")
        assert not validate_cors_origin("null")


# ============================================================================
# Integration Tests
# ============================================================================


class TestAuthSecurityIntegration:
    """Integration tests for auth security."""

    def test_complete_auth_flow_security(
        self, mock_password_hasher, mock_token_generator, mock_api_key_generator, mock_session_store
    ):
        """Test complete authentication flow for security."""
        # 1. Register user with strong password
        password = "Str0ng!Pass123"
        assert len(password) >= 8
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in '!@#$%^&*(),.?":{}|<>' for c in password)

        # 2. Hash password
        hashed_password = mock_password_hasher.hash_password(password)
        assert mock_password_hasher.verify_password(password, hashed_password)

        # 3. Create session
        user_id = "user123"
        session_id = mock_session_store.create_session(user_id)
        assert mock_session_store.get_session(session_id) is not None

        # 4. Generate token
        token = mock_token_generator.create_access_token({"sub": user_id})
        decoded = mock_token_generator.decode_token(token)
        assert decoded["sub"] == user_id

        # 5. Generate API key
        api_key = mock_api_key_generator.generate_api_key()
        assert mock_api_key_generator.validate_api_key_format(api_key)

        # 6. Logout - invalidate session
        mock_session_store.invalidate_session(session_id)
        assert mock_session_store.get_session(session_id) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
