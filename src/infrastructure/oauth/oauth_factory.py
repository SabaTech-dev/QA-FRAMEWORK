"""OAuth Provider Factory."""

from domain.auth.interfaces import OAuthProvider
from domain.auth.value_objects import AuthProvider

from .github_oauth import GitHubOAuthProvider
from .google_oauth import GoogleOAuthProvider


class OAuthProviderFactory:
    """Factory for creating OAuth provider instances."""

    _providers: dict[AuthProvider, type[OAuthProvider]] = {
        AuthProvider.GOOGLE: GoogleOAuthProvider,
        AuthProvider.GITHUB: GitHubOAuthProvider,
    }

    @classmethod
    def create(cls, provider: AuthProvider) -> OAuthProvider:
        """Create an OAuth provider instance.

        Args:
            provider: The authentication provider type

        Returns:
            OAuthProvider instance

        Raises:
            ValueError: If provider is not supported
        """
        provider_class = cls._providers.get(provider)
        if provider_class is None:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        return provider_class()

    @classmethod
    def create_from_string(cls, provider_name: str) -> OAuthProvider:
        """Create an OAuth provider from string name.

        Args:
            provider_name: Provider name (e.g., 'google', 'github')

        Returns:
            OAuthProvider instance

        Raises:
            ValueError: If provider is not supported
        """
        auth_provider = AuthProvider.from_string(provider_name)
        if auth_provider is None:
            raise ValueError(f"Unknown OAuth provider: {provider_name}")

        return cls.create(auth_provider)

    @classmethod
    def get_available_providers(cls) -> dict[AuthProvider, bool]:
        """Get all available providers and their configuration status.

        Returns:
            Dictionary mapping providers to their configured status
        """
        result = {}
        for auth_provider, provider_class in cls._providers.items():
            instance = provider_class()
            result[auth_provider] = instance.is_configured()
        return result

    @classmethod
    def register_provider(
        cls,
        provider: AuthProvider,
        provider_class: type[OAuthProvider],
    ) -> None:
        """Register a custom OAuth provider.

        Args:
            provider: The authentication provider type
            provider_class: The provider implementation class
        """
        cls._providers[provider] = provider_class

    @classmethod
    def is_supported(cls, provider_name: str) -> bool:
        """Check if provider is supported.

        Args:
            provider_name: Provider name to check

        Returns:
            True if provider is supported, False otherwise
        """
        return AuthProvider.from_string(provider_name) is not None
