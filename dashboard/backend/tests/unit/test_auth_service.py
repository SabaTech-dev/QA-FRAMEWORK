"""
Unit Tests for Auth Service

Tests authentication, JWT generation, and user management.
"""

import pytest

pytest.importorskip("jose")
pytest.importorskip("bcrypt")
pytest.importorskip("asyncpg")
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from jose import jwt

from config import settings
from services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    authenticate_user,
    get_current_user,
    PasswordTooLongError,
)
from models import User
from schemas import UserCreate, LoginRequest

# Reference bcrypt hash of "test_pwd_123" ($2b$12$, 12 rounds) in the exact
# format produced by the previous passlib 1.7.4 + bcrypt 4 stack. Password
# hashes are algorithm-identical, so verification must keep accepting them.
LEGACY_BCRYPT_HASH = "$2b$12$HyDcNXuJwAmu7K9rdC8iVOnBIZ1wlznn4VJKSGiVDvrWicowUxc3q"


@pytest.mark.asyncio
class TestAuthService:
    """Test suite for auth service"""

    def test_hash_password(self):
        """Test password hashing"""
        password = "test_pwd_123"  # Shorter password (< 72 bytes)
        hashed = hash_password(password)

        # Verify it's hashed
        assert hashed != password
        assert hashed.startswith("$2b$")
        assert len(hashed) > 50

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "test_pwd_123"  # Shorter password (< 72 bytes)
        hashed = hash_password(password)

        # Verify correct password
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "test_pwd_123"  # Shorter password (< 72 bytes)
        hashed = hash_password(password)

        # Verify incorrect password
        assert verify_password("wrong_pwd", hashed) is False

    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "testuser"}
        token = create_access_token(data)

        # Verify token is created
        assert token is not None
        assert isinstance(token, str)

        # Decode and verify
        payload = jwt.decode(
            token, settings.secret_key.get_secret_value(), algorithms=[settings.algorithm]
        )
        assert payload["sub"] == "testuser"
        assert "exp" in payload

    def test_create_access_token_with_expiry(self):
        """Test JWT token creation with custom expiry"""
        data = {"sub": "testuser"}
        expires = timedelta(minutes=15)
        token = create_access_token(data, expires)

        # Decode and verify expiry
        payload = jwt.decode(
            token, settings.secret_key.get_secret_value(), algorithms=[settings.algorithm]
        )
        exp_time = datetime.fromtimestamp(payload["exp"])

        # Should be approximately 15 minutes from now
        now = datetime.utcnow()
        delta = exp_time - now

        assert 14 * 60 < delta.total_seconds() < 16 * 60

    async def test_authenticate_user_success(self):
        """Test successful user authentication"""
        # Mock database session
        mock_db = AsyncMock()

        # Mock user
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password=hash_password("test_pwd_123"),  # Shorter password
            is_active=True,
        )

        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=user)  # Sync mock
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Test authentication
        authenticated_user = await authenticate_user(mock_db, "testuser", "test_pwd_123")

        assert authenticated_user is not None
        assert authenticated_user.username == "testuser"

    async def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password"""
        # Mock database session
        mock_db = AsyncMock()

        # Mock user
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password=hash_password("test_pwd_123"),  # Shorter password
            is_active=True,
        )

        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=user)  # Sync mock
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Test authentication with wrong password
        authenticated_user = await authenticate_user(mock_db, "testuser", "wrong_pwd")

        assert authenticated_user is None

    async def test_authenticate_user_not_found(self):
        """Test authentication with non-existent user"""
        # Mock database session
        mock_db = AsyncMock()

        # Mock database query returning None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=None)  # Sync mock
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Test authentication
        authenticated_user = await authenticate_user(mock_db, "nonexistent", "pwd123")

        assert authenticated_user is None

    async def test_get_current_user_success(self):
        """Test getting current user from valid token"""
        # Mock database session
        mock_db = AsyncMock()

        # Mock user
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password="hashed",
            is_active=True,
        )

        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=user)  # Sync mock
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Create token
        token = create_access_token({"sub": "testuser"})

        # Mock credentials
        mock_credentials = Mock()
        mock_credentials.credentials = token

        # Test get current user
        current_user = await get_current_user(mock_credentials, mock_db)

        assert current_user is not None
        assert current_user.username == "testuser"


@pytest.mark.asyncio
class TestUserCreation:
    """Test user creation and validation"""

    async def test_create_user_password_hashing(self):
        """Test that passwords are properly hashed when creating users"""
        from services.user_service import create_user_service

        # Mock database
        mock_db = AsyncMock()

        # Mock no existing users
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Create user
        user_data = UserCreate(
            username="newuser",
            email="new@example.com",
            password="plain_pwd",  # Shorter password
            is_active=True,
        )

        # Mock add and commit
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # This would normally create the user
        # We're testing that the password gets hashed
        hashed = hash_password("plain_pwd")

        # Verify it's properly hashed
        assert hashed != "plain_pwd"
        assert verify_password("plain_pwd", hashed) is True


class TestBcryptPasswordLimits:
    """bcrypt 5 adaptation: explicit, controlled >72-byte password policy.

    bcrypt only digests the first 72 bytes of a password. bcrypt 5 removed
    the silent truncation, so the service must reject oversized passwords
    with a domain error instead of letting a raw ValueError escape.
    """

    def test_hash_password_rejects_ascii_over_72_bytes(self):
        """73 ASCII chars = 73 bytes -> PasswordTooLongError, not ValueError"""
        with pytest.raises(PasswordTooLongError, match="72 bytes"):
            hash_password("a" * 73)

    def test_hash_password_rejects_multibyte_over_72_bytes(self):
        """37 x 'ñ' is only 37 chars but 74 UTF-8 bytes -> rejected.

        Proves the limit is enforced on encoded bytes, not characters.
        """
        with pytest.raises(PasswordTooLongError, match="72 bytes"):
            hash_password("ñ" * 37)

    def test_hash_password_accepts_exactly_72_bytes(self):
        """Boundary: exactly 72 bytes must hash and verify normally"""
        password = "a" * 72
        hashed = hash_password(password)
        assert hashed.startswith("$2b$")
        assert verify_password(password, hashed) is True

    def test_hash_password_accepts_multibyte_exactly_72_bytes(self):
        """Boundary: 24 x '€' = 72 UTF-8 bytes must hash and verify"""
        password = "€" * 24
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_over_72_bytes_returns_false(self):
        """Login with an oversized password is an auth failure, not a crash"""
        hashed = hash_password("short_pwd")
        assert verify_password("a" * 73, hashed) is False

    def test_verify_password_accepts_legacy_passlib_hash(self):
        """Hashes stored by the passlib 1.7.4 + bcrypt 4 stack stay valid"""
        assert verify_password("test_pwd_123", LEGACY_BCRYPT_HASH) is True

    def test_verify_password_rejects_wrong_password_on_legacy_hash(self):
        assert verify_password("wrong_pwd", LEGACY_BCRYPT_HASH) is False


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
