"""Password hashing utilities using bcrypt."""

from abc import ABC, abstractmethod
from typing import Optional

import bcrypt

from src.domain.auth.value_objects import Password


class PasswordHasher(ABC):
    """Abstract interface for password hashing."""

    @abstractmethod
    def hash(self, password: str) -> str:
        """Hash a plain text password.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        pass

    @abstractmethod
    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hash.

        Args:
            plain_password: Plain text password
            hashed_password: Stored hash

        Returns:
            True if password matches, False otherwise
        """
        pass

    @abstractmethod
    def needs_rehash(self, hashed_password: str) -> bool:
        """Check if password needs to be rehashed (e.g., algorithm update).

        Args:
            hashed_password: Stored hash

        Returns:
            True if rehashing is recommended
        """
        pass


class BCryptPasswordHasher(PasswordHasher):
    """BCrypt password hasher implementation.

    Uses bcrypt with configurable rounds (cost factor).
    Default rounds: 12 (adjustable based on security/performance needs)
    """

    def __init__(self, rounds: int = 12):
        """Initialize bcrypt hasher.

        Args:
            rounds: Number of bcrypt rounds (4-31, higher = slower)
        """
        self._rounds = rounds

    def hash(self, password: str) -> str:
        """Hash password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            BCrypt hash string (includes salt)
        """
        # Generate salt with configured rounds
        salt = bcrypt.gensalt(rounds=self._rounds)
        # Hash password
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against bcrypt hash.

        Args:
            plain_password: Plain text password
            hashed_password: BCrypt hash

        Returns:
            True if passwords match
        """
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            return False

    def needs_rehash(self, hashed_password: str) -> bool:
        """Check if password needs rehashing.

        Checks if the stored hash was created with fewer rounds
        than currently configured.

        Args:
            hashed_password: Stored BCrypt hash

        Returns:
            True if rehashing is recommended
        """
        try:
            # Extract rounds from hash prefix ($2b$rounds$)
            prefix_parts = hashed_password.split("$")
            if len(prefix_parts) >= 3:
                stored_rounds = int(prefix_parts[2])
                return stored_rounds < self._rounds
            return True
        except (ValueError, IndexError):
            return True

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, list[str]]:
        """Validate password meets strength requirements.

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        return Password.validate_strength(password)


# Global hasher instance (use this for all password operations)
_default_hasher: Optional[BCryptPasswordHasher] = None


def get_password_hasher() -> BCryptPasswordHasher:
    """Get default password hasher instance."""
    global _default_hasher
    if _default_hasher is None:
        _default_hasher = BCryptPasswordHasher(rounds=12)
    return _default_hasher


def hash_password(password: str) -> str:
    """Convenience function to hash a password."""
    return get_password_hasher().hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Convenience function to verify a password."""
    return get_password_hasher().verify(plain_password, hashed_password)


def check_password_strength(password: str) -> tuple[bool, list[str]]:
    """Convenience function to check password strength."""
    return Password.validate_strength(password)
