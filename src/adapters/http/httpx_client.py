"""HTTP Client adapter using HTTPX (async) — with OWASP SSRF protection"""

import logging
import os
from typing import Any, Dict, Optional, Set

import httpx

from src.core.interfaces import IHTTPClient
from src.core.security.url_validator import (
    validate_url,
    DEFAULT_ALLOWED_DOMAINS,
)


logger = logging.getLogger(__name__)


def _load_allowed_domains() -> Set[str]:
    """
    Load allowed domains from environment variable or use defaults.

    Environment: SSRF_ALLOWED_DOMAINS — comma-separated list of domains.
    """
    env_domains = os.getenv("SSRF_ALLOWED_DOMAINS")
    if env_domains:
        return {d.strip() for d in env_domains.split(",") if d.strip()}
    return DEFAULT_ALLOWED_DOMAINS


class HTTPXClient(IHTTPClient):
    """
    Async HTTP client using HTTPX library — with OWASP SSRF protection.

    This adapter implements the IHTTPClient interface, following
    the Dependency Inversion Principle (DIP) from SOLID.

    SSRF Protection (OWASP A01):
        - All outbound URLs are validated against an allowlist
        - Blocked requests raise URLValidationError
        - Allowlist can be configured via SSRF_ALLOWED_DOMAINS env var
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None,
        allowed_domains: Optional[Set[str]] = None,
        ssrf_enabled: bool = True,
    ):
        """
        Initialize HTTPX client with optional SSRF protection.

        Args:
            base_url: Base URL for all requests
            timeout: Request timeout in seconds
            headers: Default headers for all requests
            allowed_domains: Custom allowlist of trusted domains
                             (defaults from SSRF_ALLOWED_DOMAINS env or built-in list)
            ssrf_enabled: Enable/disable SSRF validation
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.default_headers = headers or {}
        self._client: Optional[httpx.AsyncClient] = None
        self._ssrf_enabled = ssrf_enabled
        self._allowed_domains = (
            allowed_domains if allowed_domains is not None else _load_allowed_domains()
        )

    def _resolve_url(self, url: str) -> str:
        """
        Resolve a potentially relative URL against the base URL.

        Args:
            url: URL path (may be relative or absolute)

        Returns:
            Fully qualified URL string
        """
        if url.startswith(("http://", "https://")):
            return url
        return f"{self.base_url}/{url.lstrip('/')}"

    def _validate_url(self, url: str) -> None:
        """
        Validate a URL against the SSRF allowlist.

        Args:
            url: The URL to validate (resolved to absolute first).

        Raises:
            URLValidationError: If the URL is not in the allowlist and SSRF is enabled.
        """
        if not self._ssrf_enabled:
            return

        full_url = self._resolve_url(url)
        validate_url(full_url, allowed_domains=self._allowed_domains)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTPX client (Singleton pattern for connection pooling)"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self.default_headers,
            )
        return self._client

    async def get(self, url: str, **kwargs: Any) -> Any:
        """
        Perform GET request with SSRF validation.

        Args:
            url: Endpoint URL (relative to base_url or absolute)
            **kwargs: Additional httpx arguments

        Returns:
            Response object with status_code, json() method

        Raises:
            URLValidationError: If the target URL is not in the allowlist (SSRF prevention).
        """
        self._validate_url(url)
        client = await self._get_client()
        response = await client.get(url, **kwargs)
        return response

    async def post(self, url: str, data: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
        """
        Perform POST request with SSRF validation.

        Args:
            url: Endpoint URL
            data: Request body data
            **kwargs: Additional httpx arguments

        Returns:
            Response object

        Raises:
            URLValidationError: If the target URL is not in the allowlist (SSRF prevention).
        """
        self._validate_url(url)
        client = await self._get_client()
        response = await client.post(url, json=data, **kwargs)
        return response

    async def put(self, url: str, data: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
        """
        Perform PUT request with SSRF validation.

        Args:
            url: Endpoint URL
            data: Request body data
            **kwargs: Additional httpx arguments

        Returns:
            Response object

        Raises:
            URLValidationError: If the target URL is not in the allowlist (SSRF prevention).
        """
        self._validate_url(url)
        client = await self._get_client()
        response = await client.put(url, json=data, **kwargs)
        return response

    async def delete(self, url: str, **kwargs: Any) -> Any:
        """
        Perform DELETE request with SSRF validation.

        Args:
            url: Endpoint URL
            **kwargs: Additional httpx arguments

        Returns:
            Response object

        Raises:
            URLValidationError: If the target URL is not in the allowlist (SSRF prevention).
        """
        self._validate_url(url)
        client = await self._get_client()
        response = await client.delete(url, **kwargs)
        return response

    async def close(self) -> None:
        """Close HTTPX client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "HTTPXClient":
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit"""
        await self.close()
