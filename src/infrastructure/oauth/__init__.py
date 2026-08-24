"""Infrastructure layer for OAuth providers."""

from .base_oauth import (
    BaseOAuthProvider,
    OAuthConfigurationError,
    OAuthExchangeError,
    OAuthRefreshError,
    OAuthUserInfoError,
)
from .github_oauth import GitHubOAuthProvider
from .google_oauth import GoogleOAuthProvider
from .oauth_factory import OAuthProviderFactory

__all__ = [
    "BaseOAuthProvider",
    "GoogleOAuthProvider",
    "GitHubOAuthProvider",
    "OAuthProviderFactory",
    "OAuthConfigurationError",
    "OAuthExchangeError",
    "OAuthUserInfoError",
    "OAuthRefreshError",
]
