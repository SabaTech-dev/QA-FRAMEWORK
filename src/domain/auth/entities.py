"""OAuth Domain Entities."""

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class OAuthUser:
    """Entity representing an OAuth user."""

    id: str
    email: str
    name: str | None = None
    avatar: str | None = None
    provider: str = ""
    provider_id: str = ""

    def __post_init__(self):
        """Validate required fields."""
        if not self.id:
            raise ValueError("OAuthUser.id is required")
        if not self.email:
            raise ValueError("OAuthUser.email is required")


@dataclass(frozen=True)
class Token:
    """Entity representing OAuth tokens."""

    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None
    token_type: str = "Bearer"

    def __post_init__(self):
        """Set defaults."""
        if not self.access_token:
            raise ValueError("Token.access_token is required")

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) >= self.expires_at

    @property
    def expires_in(self) -> int | None:
        """Get seconds until expiration."""
        if self.expires_at is None:
            return None
        delta = self.expires_at - datetime.now(UTC)
        return max(0, int(delta.total_seconds()))
