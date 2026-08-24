"""Tenant Context Middleware - Resolve and inject tenant context in requests

This middleware:
1. Resolves tenant from subdomain (e.g., acme.app.com)
2. Resolves tenant from X-Tenant-ID header (for API clients)
3. Injects tenant context into request state
4. Validates tenant is active before allowing access
"""

import logging
from collections.abc import Callable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.domain.entities.tenant import Tenant
from src.infrastructure.persistence.tenant_repository import TenantRepositoryInterface

logger = logging.getLogger(__name__)


class TenantContext:
    """
    Context object holding tenant information for the current request.

    This is attached to request.state.tenant_context
    """

    def __init__(self, tenant: Tenant | None, resolved_from: str):
        """
        Initialize tenant context.

        Args:
            tenant: Tenant entity (None if not resolved)
            resolved_from: How the tenant was resolved ('subdomain', 'header', 'none')
        """
        self.tenant = tenant
        self.resolved_from = resolved_from

    @property
    def is_authenticated(self) -> bool:
        """Check if a valid tenant was resolved"""
        return self.tenant is not None

    @property
    def tenant_id(self) -> str | None:
        """Get tenant ID if authenticated"""
        return str(self.tenant.id) if self.tenant else None

    @property
    def tenant_slug(self) -> str | None:
        """Get tenant slug if authenticated"""
        return self.tenant.slug if self.tenant else None


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    FastAPI/Starlette middleware for multi-tenant context resolution.

    Resolution order:
    1. X-Tenant-ID header (for API clients)
    2. Subdomain from host header (e.g., acme.app.com)

    If tenant is resolved, it's attached to request.state.tenant_context
    """

    def __init__(
        self,
        app,
        tenant_repository: TenantRepositoryInterface,
        require_tenant: bool = False,
        public_paths: list | None = None,
    ):
        """
        Initialize middleware.

        Args:
            app: FastAPI/Starlette application
            tenant_repository: Repository to fetch tenant data
            require_tenant: If True, reject requests without valid tenant
            public_paths: List of paths that don't require tenant context
        """
        super().__init__(app)
        self.tenant_repository = tenant_repository
        self.require_tenant = require_tenant
        self.public_paths = public_paths or [
            "/",
            "/health",
            "/api/v1/health",
            "/api/v1/docs",
            "/api/v1/openapi.json",
            "/docs",
            "/openapi.json",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and resolve tenant context.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler

        Returns:
            HTTP response
        """
        # Skip tenant resolution for public paths
        if request.url.path in self.public_paths:
            request.state.tenant_context = TenantContext(None, "none")
            return await call_next(request)

        # Try to resolve tenant
        tenant = None
        resolved_from = "none"

        # Method 1: Try X-Tenant-ID header
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            try:
                from uuid import UUID

                tenant = await self.tenant_repository.get_by_id(UUID(tenant_id))
                if tenant:
                    resolved_from = "header"
                    logger.debug(f"Resolved tenant {tenant.slug} from header")
            except Exception as e:
                logger.warning(f"Invalid tenant ID in header: {tenant_id}, error: {e}")

        # Method 2: Try subdomain from host
        if not tenant:
            host = request.headers.get("host", "")
            subdomain = self._extract_subdomain(host)

            if subdomain and subdomain not in ["www", "api", "app"]:
                tenant = await self.tenant_repository.get_by_slug(subdomain)
                if tenant:
                    resolved_from = "subdomain"
                    logger.debug(f"Resolved tenant {tenant.slug} from subdomain")

        # Create tenant context
        tenant_context = TenantContext(tenant, resolved_from)
        request.state.tenant_context = tenant_context

        # Check if tenant is required but not resolved
        if self.require_tenant and not tenant_context.is_authenticated:
            logger.warning(f"Tenant required but not resolved for path: {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant context required"
            )

        # Check if tenant is suspended
        if tenant and tenant.is_suspended():
            logger.warning(f"Tenant {tenant.slug} is suspended")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Tenant account is suspended"
            )

        # Continue processing request
        return await call_next(request)

    def _extract_subdomain(self, host: str) -> str | None:
        """
        Extract subdomain from host header.

        Args:
            host: Host header value (e.g., "acme.app.com:8000")

        Returns:
            Subdomain or None
        """
        # Remove port if present
        if ":" in host:
            host = host.split(":")[0]

        # Split by dots
        parts = host.split(".")

        # If we have at least 3 parts, the first is the subdomain
        # e.g., acme.app.com -> acme
        if len(parts) >= 3:
            return parts[0]

        # For localhost or IP addresses, no subdomain
        return None


def get_tenant_context(request: Request) -> TenantContext:
    """
    Dependency to get tenant context from request.

    Args:
        request: FastAPI request object

    Returns:
        TenantContext from request state

    Raises:
        HTTPException: If tenant context not found
    """
    if not hasattr(request.state, "tenant_context"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tenant context middleware not configured",
        )

    return request.state.tenant_context


def require_tenant(request: Request) -> Tenant:
    """
    Dependency that requires an authenticated tenant.

    Args:
        request: FastAPI request object

    Returns:
        Tenant entity

    Raises:
        HTTPException: If no tenant context or not authenticated
    """
    context = get_tenant_context(request)

    if not context.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant authentication required"
        )

    return context.tenant
