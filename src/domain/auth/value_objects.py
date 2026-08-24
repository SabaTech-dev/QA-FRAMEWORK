"""Auth domain value objects."""

import re
from enum import Enum
from typing import List, Optional, Tuple


class AuthProvider(Enum):
    """Enumeration of supported authentication providers."""

    GOOGLE = "google"
    GITHUB = "github"
    EMAIL = "email"

    @classmethod
    def from_string(cls, value: str) -> Optional["AuthProvider"]:
        """Create AuthProvider from string value (case-insensitive)."""
        try:
            return cls(value.lower())
        except ValueError:
            return None

    @property
    def display_name(self) -> str:
        """Human-readable provider name."""
        return self.value.title()

    def __str__(self) -> str:
        return self.value


class TokenStatus(Enum):
    """Token status enumeration."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    USED = "used"


class Password:
    """Password value object with validation."""

    MIN_LENGTH = 8
    MAX_LENGTH = 128

    def __init__(self, plain_text: str):
        """Initialize password with plain text."""
        self._plain_text = plain_text

    @staticmethod
    def validate_strength(password: str) -> Tuple[bool, List[str]]:
        """
        Validate password strength.

        Requirements:
        - Min 8 characters
        - 1 uppercase letter
        - 1 lowercase letter
        - 1 number
        - 1 special character

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if len(password) < Password.MIN_LENGTH:
            errors.append(f"Password must be at least {Password.MIN_LENGTH} characters")

        if len(password) > Password.MAX_LENGTH:
            errors.append(f"Password must not exceed {Password.MAX_LENGTH} characters")

        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")

        if not re.search(r"\d", password):
            errors.append("Password must contain at least one number")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-=+\[\]/\\`~]', password):
            errors.append("Password must contain at least one special character")

        return len(errors) == 0, errors

    @property
    def value(self) -> str:
        """Get plain text password (for hashing - never store this!)."""
        return self._plain_text

    def __eq__(self, other):
        """Check equality with another password."""
        if isinstance(other, Password):
            return self._plain_text == other._plain_text
        return False

    def __repr__(self):
        """String representation (hides actual password)."""
        return "Password(******)"


class EmailVerificationToken:
    """Email verification token value object."""

    def __init__(self, token: str, user_id: str):
        """Initialize email verification token."""
        self._token = token
        self._user_id = user_id

    @property
    def token(self) -> str:
        """Get token value."""
        return self._token

    @property
    def user_id(self) -> str:
        """Get associated user ID."""
        return self._user_id


class Scope:
    """API scope value object."""

    AVAILABLE_SCOPES = {
        "read:tests": "Read test results",
        "write:tests": "Create and update tests",
        "delete:tests": "Delete tests",
        "read:reports": "Read reports",
        "write:reports": "Generate reports",
        "read:executions": "Read test executions",
        "write:executions": "Trigger test executions",
        "admin": "Full administrative access",
        "*": "All scopes (use with caution)",
    }

    def __init__(self, name: str):
        """Initialize scope."""
        if name not in self.AVAILABLE_SCOPES and name != "*":
            raise ValueError(f"Invalid scope: {name}")
        self._name = name

    @property
    def name(self) -> str:
        """Get scope name."""
        return self._name

    @property
    def description(self) -> str:
        """Get scope description."""
        return self.AVAILABLE_SCOPES.get(self._name, "Unknown scope")

    @classmethod
    def validate_scopes(cls, scopes: List[str]) -> Tuple[bool, List[str]]:
        """Validate a list of scopes."""
        invalid = [s for s in scopes if s not in cls.AVAILABLE_SCOPES]
        if invalid:
            return False, invalid
        return True, []
