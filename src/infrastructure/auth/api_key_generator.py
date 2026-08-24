"""API Key generation and validation utilities."""

import hashlib
import hmac
import secrets
from datetime import datetime
from uuid import UUID

from src.domain.auth.entities import APIKey


class APIKeyGenerator:
    """Generator for secure API keys.

    Format: qa_{prefix}_{random}
    - prefix: identifying prefix (e.g., 'live', 'test')
    - random: 32 bytes of randomness (URL-safe base64)

    Keys are stored as SHA-256 hashes, never plaintext.
    """

    KEY_PREFIX = "qa"
    KEY_VERSION = "1"
    RANDOM_BYTES = 32

    def __init__(self, prefix: str = "live"):
        """Initialize API key generator.

        Args:
            prefix: Key prefix identifier (live, test, dev)
        """
        self._prefix = prefix

    def generate_api_key(
        self,
        user_id: UUID,
        name: str,
        scopes: list[str],
        tenant_id: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[APIKey, str]:
        """Generate a new API key.

        Args:
            user_id: User identifier
            name: Key name/description
            scopes: List of permission scopes
            tenant_id: Optional tenant identifier
            expires_at: Optional expiration datetime

        Returns:
            Tuple of (APIKey entity, plaintext key for one-time display)
        """
        # Generate secure random token
        random_part = secrets.token_urlsafe(self.RANDOM_BYTES)

        # Construct full key: qa_{version}_{prefix}_{random}
        plaintext_key = f"{self.KEY_PREFIX}_{self.KEY_VERSION}_{self._prefix}_{random_part}"

        # Hash for storage
        key_hash = self.hash_api_key(plaintext_key)

        # Create entity
        api_key = APIKey(
            key_hash=key_hash,
            name=name,
            user_id=user_id,
            tenant_id=tenant_id,
            scopes=scopes,
            expires_at=expires_at,
            is_active=True,
        )

        return api_key, plaintext_key

    @staticmethod
    def hash_api_key(plaintext_key: str) -> str:
        """Hash an API key using SHA-256.

        Args:
            plaintext_key: Plaintext API key

        Returns:
            SHA-256 hash of the key
        """
        return hashlib.sha256(plaintext_key.encode("utf-8")).hexdigest()

    @staticmethod
    def verify_api_key(plaintext_key: str, stored_hash: str) -> bool:
        """Verify a plaintext key against stored hash.

        Args:
            plaintext_key: Provided API key
            stored_hash: Stored hash

        Returns:
            True if key matches
        """
        computed_hash = APIKeyGenerator.hash_api_key(plaintext_key)
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(computed_hash, stored_hash)

    @staticmethod
    def extract_key_id(plaintext_key: str) -> str | None:
        """Extract identifying portion from API key.

        Args:
            plaintext_key: Full API key

        Returns:
            Key ID prefix for identification
        """
        parts = plaintext_key.split("_")
        if len(parts) >= 4:
            # Return qa_v1_live_{first_8_chars}
            return f"{parts[0]}_{parts[1]}_{parts[2]}_{parts[3][:8]}..."
        return None

    @classmethod
    def validate_key_format(cls, key: str) -> bool:
        """Validate API key format.

        Args:
            key: API key to validate

        Returns:
            True if format is valid
        """
        if not key:
            return False

        parts = key.split("_")
        if len(parts) < 4:
            return False

        if parts[0] != cls.KEY_PREFIX:
            return False

        if parts[1] != cls.KEY_VERSION:
            return False

        return True
