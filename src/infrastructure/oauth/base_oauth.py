"""Base OAuth Provider Implementation — with OWASP SSRF Protection."""
from abc import abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Set
import os
import logging

import httpx

from domain.auth.interfaces import OAuthProvider
from domain.auth.entities import OAuthUser, Token
from src.core.security.url_validator import (
    validate_url,
    DEFAULT_ALLOWED_DOMAINS,
    URLValidationError,
)


logger = logging.getLogger(__name__)


class OAuthError(Exception):
    """Base exception for OAuth errors."""
    pass


class OAuthConfigurationError(OAuthError):
    """Raised when OAuth provider is not properly configured."""
    pass


class OAuthExchangeError(OAuthError):
    """Raised when code exchange fails."""
    pass


class OAuthUserInfoError(OAuthError):
    """Raised when fetching user info fails."""
    pass


class OAuthRefreshError(OAuthError):
    """Raised when token refresh fails."""
    pass


# Default OAuth-specific allowed domains (extends the standard allowlist)
OAUTH_ALLOWED_DOMAINS: Set[str] = DEFAULT_ALLOWED_DOMAINS | {
    "accounts.google.com",
    "github.com",
    "api.github.com",
    "login.microsoftonline.com",
    "login.live.com",
    "graph.microsoft.com",
    "appleid.apple.com",
    "api.twitter.com",
    "api.linkedin.com",
    "www.linkedin.com",
    "apis.google.com",
    "oauth2.googleapis.com",
    "www.googleapis.com",
    "accounts.spotify.com",
    "api.spotify.com",
    "slack.com",
    "api.slack.com",
    "discord.com",
    "discordapp.com",
    "api.discord.com",
}


class BaseOAuthProvider(OAuthProvider):
    """Base implementation for OAuth 2.0 providers.
    
    Provides common functionality for OAuth 2.0 authorization code flow.
    Subclasses must implement provider-specific methods.
    
    SSRF Protection:
        All outbound HTTP requests are validated against an OAuth-specific
        allowlist to prevent Server-Side Request Forgery (OWASP A01).
    """
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        ssrf_enabled: bool = True,
        allowed_domains: Optional[Set[str]] = None,
    ):
        """Initialize OAuth provider with optional SSRF protection.
        
        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            redirect_uri: OAuth redirect URI
            ssrf_enabled: Enable/disable SSRF URL validation
            allowed_domains: Custom allowlist of trusted OAuth domains
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._http_client: Optional[httpx.AsyncClient] = None
        self._ssrf_enabled = ssrf_enabled
        self._allowed_domains = allowed_domains if allowed_domains is not None else OAUTH_ALLOWED_DOMAINS
    
    @property
    def client_id(self) -> str:
        """Get client ID from config or environment."""
        return self._client_id or os.getenv(f"{self.name.upper()}_CLIENT_ID", "")
    
    @property
    def client_secret(self) -> str:
        """Get client secret from config or environment."""
        return self._client_secret or os.getenv(f"{self.name.upper()}_CLIENT_SECRET", "")
    
    @property
    def redirect_uri(self) -> str:
        """Get redirect URI from config or environment."""
        default = f"http://localhost:3000/auth/{self.name}/callback"
        return self._redirect_uri or os.getenv(f"{self.name.upper()}_REDIRECT_URI", default)
    
    def is_configured(self) -> bool:
        """Check if provider has valid credentials."""
        return bool(self.client_id and self.client_secret)
    
    def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True
            )
        return self._http_client
    
    def _validate_url(self, url: str) -> None:
        """
        Validate a URL against the OAuth SSRF allowlist.
        
        Args:
            url: The URL to validate.
            
        Raises:
            URLValidationError: If the URL is not in the allowlist and SSRF is enabled.
        """
        if not self._ssrf_enabled:
            return
        validate_url(url, allowed_domains=self._allowed_domains)
    
    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Make HTTP request with SSRF validation and error handling."""
        # SSRF protection: validate the target URL before making the request
        self._validate_url(url)
        
        client = self._get_http_client()
        
        try:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                if json_data:
                    response = await client.post(url, headers=headers, json=json_data)
                else:
                    response = await client.post(url, headers=headers, data=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            return response
        except httpx.RequestError as e:
            raise OAuthError(f"HTTP request failed: {e}") from e
    
    def _build_url(self, base_url: str, params: Dict[str, str]) -> str:
        """Build URL with query parameters."""
        from urllib.parse import urlencode
        query = urlencode(params)
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}{query}"
    
    def _parse_token_response(self, data: Dict[str, Any]) -> Token:
        """Parse OAuth token response."""
        expires_in = data.get("expires_in")
        expires_at = None
        if expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        return Token(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
            token_type=data.get("token_type", "Bearer").title(),
        )
    
    async def get_authorization_url(
        self,
        state: str,
        redirect_uri: Optional[str] = None,
    ) -> str:
        """Get OAuth authorization URL."""
        if not self.is_configured():
            raise OAuthConfigurationError(f"{self.name} OAuth provider not configured")
        
        uri = redirect_uri or self.redirect_uri
        
        # Validate redirect URI against the allowlist
        if self._ssrf_enabled and not uri.startswith("http://localhost"):
            self._validate_url(uri)
        
        params = self._get_authorization_params(state, uri)
        return self._build_url(self._authorization_url, params)
    
    async def exchange_code(
        self,
        code: str,
        redirect_uri: Optional[str] = None,
    ) -> Token:
        """Exchange authorization code for token."""
        if not self.is_configured():
            raise OAuthConfigurationError(f"{self.name} OAuth provider not configured")
        
        uri = redirect_uri or self.redirect_uri
        
        try:
            response = await self._exchange_code_impl(code, uri)
            data = response.json()
            
            if response.status_code != 200:
                error = data.get("error", "unknown_error")
                error_desc = data.get("error_description", "No description")
                raise OAuthExchangeError(f"Token exchange failed: {error} - {error_desc}")
            
            return self._parse_token_response(data)
            
        except httpx.RequestError as e:
            raise OAuthExchangeError(f"Token exchange request failed: {e}") from e
    
    async def refresh_token(self, refresh_token: str) -> Token:
        """Refresh access token."""
        if not self.is_configured():
            raise OAuthConfigurationError(f"{self.name} OAuth provider not configured")
        
        try:
            response = await self._refresh_token_impl(refresh_token)
            data = response.json()
            
            if response.status_code != 200:
                error = data.get("error", "unknown_error")
                raise OAuthRefreshError(f"Token refresh failed: {error}")
            
            return self._parse_token_response(data)
            
        except httpx.RequestError as e:
            raise OAuthRefreshError(f"Token refresh request failed: {e}") from e
    
    async def close(self):
        """Close HTTP client connections."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
    
    # Provider-specific implementations (to be overridden)
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable provider name."""
        pass
    
    @property
    @abstractmethod
    def _authorization_url(self) -> str:
        """OAuth authorization endpoint URL."""
        pass
    
    @property
    @abstractmethod
    def _token_url(self) -> str:
        """OAuth token endpoint URL."""
        pass
    
    @abstractmethod
    def _get_authorization_params(self, state: str, redirect_uri: str) -> Dict[str, str]:
        """Build authorization URL parameters."""
        pass
    
    @abstractmethod
    async def _exchange_code_impl(
        self,
        code: str,
        redirect_uri: str,
    ) -> httpx.Response:
        """Implement the actual token exchange HTTP call."""
        pass
    
    @abstractmethod
    async def _refresh_token_impl(self, refresh_token: str) -> httpx.Response:
        """Implement the actual token refresh HTTP call."""
        pass
    
    @abstractmethod
    async def get_user_info(self, token: Token) -> OAuthUser:
        """Fetch user info using the access token."""
        pass
