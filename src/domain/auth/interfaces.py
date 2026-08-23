"""OAuth Domain Interface."""

from abc import ABC, abstractmethod
from typing import Optional

from .entities import OAuthUser, Token


class OAuthProvider(ABC):
    """Abstract interface for OAuth providers.

    This interface defines the contract that all OAuth provider
    implementations must follow.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g., 'google', 'github')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable provider name."""
        pass

    @abstractmethod
    async def get_authorization_url(self, state: str, redirect_uri: Optional[str] = None) -> str:
        """Generate OAuth authorization URL.

        Args:
            state: CSRF protection state parameter
            redirect_uri: Optional custom redirect URI (overrides default)

        Returns:
            Complete authorization URL for user redirect

        Raises:
            OAuthConfigurationError: If provider is not properly configured
        """
        pass

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: Optional[str] = None) -> Token:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Optional custom redirect URI (must match auth request)

        Returns:
            Token object with access and refresh tokens

        Raises:
            OAuthExchangeError: If code exchange fails
        """
        pass

    @abstractmethod
    async def get_user_info(self, token: Token) -> OAuthUser:
        """Get user information from OAuth provider.

        Args:
            token: Valid access token

        Returns:
            OAuthUser entity with provider user data

        Raises:
            OAuthUserInfoError: If user info fetch fails
        """
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Token:
        """Refresh an expired access token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New token with updated access token

        Raises:
            OAuthRefreshError: If token refresh fails
        """
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured with credentials.

        Returns:
            True if provider has valid credentials, False otherwise
        """
        pass
