"""Token generation utilities using JWT."""

import hashlib
import secrets
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from jose import JWTError, jwt


class TokenGenerator(ABC):
    """Abstract interface for token generation."""

    @abstractmethod
    def generate_access_token(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        scopes: Optional[list] = None,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate an access token.

        Args:
            user_id: User identifier
            tenant_id: Optional tenant identifier
            scopes: Optional list of scopes
            extra_claims: Optional additional claims

        Returns:
            Access token string
        """
        pass

    @abstractmethod
    def generate_refresh_token(self, user_id: str) -> str:
        """Generate a refresh token.

        Args:
            user_id: User identifier

        Returns:
            Refresh token string
        """
        pass

    @abstractmethod
    def generate_verification_token(self, user_id: str) -> str:
        """Generate an email verification token.

        Args:
            user_id: User identifier

        Returns:
            Verification token string
        """
        pass

    @abstractmethod
    def generate_password_reset_token(self, user_id: str) -> str:
        """Generate a password reset token.

        Args:
            user_id: User identifier

        Returns:
            Reset token string
        """
        pass

    @abstractmethod
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate a token.

        Args:
            token: Token to decode

        Returns:
            Decoded token payload or None if invalid
        """
        pass


class JWTokenGenerator(TokenGenerator):
    """JWT token generator implementation."""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 60,
        refresh_token_expire_days: int = 7,
        verification_token_expire_hours: int = 24,
        password_reset_token_expire_hours: int = 1,
    ):
        """Initialize JWT token generator.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm (default: HS256)
            access_token_expire_minutes: Access token expiry
            refresh_token_expire_days: Refresh token expiry
            verification_token_expire_hours: Email verification token expiry
            password_reset_token_expire_hours: Password reset token expiry
        """
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_token_expire = timedelta(minutes=access_token_expire_minutes)
        self._refresh_token_expire = timedelta(days=refresh_token_expire_days)
        self._verification_token_expire = timedelta(hours=verification_token_expire_hours)
        self._password_reset_token_expire = timedelta(hours=password_reset_token_expire_hours)

    def generate_access_token(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        scopes: Optional[list] = None,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate JWT access token."""
        now = datetime.now(timezone.utc)
        expire = now + self._access_token_expire

        claims = {
            "sub": str(user_id),
            "iat": now,
            "exp": expire,
            "type": "access",
            "jti": str(uuid4()),  # Unique token ID for revocation
        }

        if tenant_id:
            claims["tenant_id"] = str(tenant_id)

        if scopes:
            claims["scopes"] = scopes

        if extra_claims:
            # Prevent overwriting reserved claims
            for key in ["sub", "iat", "exp", "type", "jti"]:
                extra_claims.pop(key, None)
            claims.update(extra_claims)

        return jwt.encode(claims, self._secret_key, algorithm=self._algorithm)

    def generate_refresh_token(self, user_id: str) -> str:
        """Generate JWT refresh token."""
        now = datetime.now(timezone.utc)
        expire = now + self._refresh_token_expire

        claims = {
            "sub": str(user_id),
            "iat": now,
            "exp": expire,
            "type": "refresh",
            "jti": str(uuid4()),
        }

        return jwt.encode(claims, self._secret_key, algorithm=self._algorithm)

    def generate_verification_token(self, user_id: str) -> str:
        """Generate email verification token (URL-safe random string)."""
        # Use cryptographically secure random token
        _random_bytes = secrets.token_bytes(32)
        token = secrets.token_urlsafe(32)
        # Include user ID hash for validation
        user_hash = hashlib.sha256(user_id.encode()).hexdigest()[:16]
        return f"{token}.{user_hash}"

    def generate_password_reset_token(self, user_id: str) -> str:
        """Generate password reset token."""
        now = datetime.now(timezone.utc)
        expire = now + self._password_reset_token_expire

        claims = {
            "sub": str(user_id),
            "iat": now,
            "exp": expire,
            "type": "password_reset",
            "jti": str(uuid4()),
        }

        return jwt.encode(claims, self._secret_key, algorithm=self._algorithm)

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
            return payload
        except JWTError:
            return None

    def verify_verification_token(self, token: str, user_id: str) -> bool:
        """Verify email verification token."""
        try:
            parts = token.split(".")
            if len(parts) != 2:
                return False

            # Verify user hash matches
            expected_hash = hashlib.sha256(user_id.encode()).hexdigest()[:16]
            return parts[1] == expected_hash
        except Exception:
            return False

    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """Get token expiration datetime."""
        payload = self.decode_token(token)
        if payload and "exp" in payload:
            return datetime.utcfromtimestamp(payload["exp"])
        return None

    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired."""
        expiry = self.get_token_expiry(token)
        if expiry:
            return datetime.now(timezone.utc) > expiry
        return True


# Default token generator instance
_default_token_generator: Optional[JWTokenGenerator] = None


def get_token_generator(secret_key: Optional[str] = None) -> JWTokenGenerator:
    """Get or create default token generator."""
    global _default_token_generator
    if _default_token_generator is None:
        if secret_key is None:
            raise ValueError("Secret key required for token generator")
        _default_token_generator = JWTokenGenerator(secret_key=secret_key)
    return _default_token_generator
