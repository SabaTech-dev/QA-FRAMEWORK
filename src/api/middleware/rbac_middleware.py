"""RBAC Middleware - Role-Based Access Control for permissions checking

This module provides:
1. Dependency to require specific permissions for endpoints
2. Decorator for protecting routes with permission checks
3. Helper functions for permission validation
4. Integration with tenant context and role system
"""

import logging
from functools import wraps
from typing import Callable, List, Optional
from uuid import UUID

from fastapi import HTTPException, Request, status

from src.api.middleware.tenant_context import get_tenant_context
from src.domain.entities.role import Role
from src.infrastructure.persistence.role_repository import RoleRepositoryInterface

logger = logging.getLogger(__name__)


class RBACContext:
    """
    Context object holding RBAC information for the current request.

    This would typically contain:
    - User roles (in a full implementation with User entity)
    - Effective permissions
    - Tenant context integration

    For now, we'll implement permission checking based on roles
    """

    def __init__(self, roles: List[Role]):
        """
        Initialize RBAC context.

        Args:
            roles: List of roles for the current user
        """
        self.roles = roles

    def has_permission(self, permission: str) -> bool:
        """
        Check if any role has the specified permission.

        Args:
            permission: Permission to check (e.g., "tests:read")

        Returns:
            True if any role has the permission
        """
        return any(role.has_permission(permission) for role in self.roles)

    def has_any_permission(self, permissions: List[str]) -> bool:
        """
        Check if any role has any of the specified permissions.

        Args:
            permissions: List of permissions to check

        Returns:
            True if any role has at least one permission
        """
        return any(self.has_permission(perm) for perm in permissions)

    def has_all_permissions(self, permissions: List[str]) -> bool:
        """
        Check if any role has all specified permissions.

        Args:
            permissions: List of permissions to check

        Returns:
            True if any role has all permissions
        """
        return all(self.has_permission(perm) for perm in permissions)

    @property
    def role_names(self) -> List[str]:
        """Get list of role names"""
        return [role.name for role in self.roles]

    @property
    def is_admin(self) -> bool:
        """Check if user has admin or higher privileges"""
        return any(role.is_admin() for role in self.roles)


def require_permission(
    permission: str, role_repository: RoleRepositoryInterface, tenant_id: Optional[UUID] = None
):
    """
    FastAPI dependency to require a specific permission for access.

    This function returns a dependency that can be used in FastAPI route handlers.
    It will check if the current user (via roles) has the required permission.

    Args:
        permission: Required permission (e.g., "tests:read")
        role_repository: Repository to fetch roles
        tenant_id: Optional tenant ID to filter roles by

    Returns:
        Dependency function

    Raises:
        HTTPException: If permission check fails

    Example:
        ```python
        @app.get("/tests")
        async def list_tests(
            user: User = Depends(get_current_user),
            _: None = Depends(require_permission("tests:read", role_repo))
        ):
            return await test_service.list_tests()
        ```
    """

    async def check_permission(request: Request):
        """
        Check if current request has required permission.

        Args:
            request: FastAPI request object

        Returns:
            None if permission check passes

        Raises:
            HTTPException: If permission check fails
        """
        # Get tenant context
        _tenant_context = get_tenant_context(request)

        # Get user from request state (assuming user is set by auth middleware)
        # For now, we'll need user roles from request state
        if not hasattr(request.state, "user_roles"):
            logger.warning("No user roles found in request state")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
            )

        user_roles = request.state.user_roles
        rbac_context = RBACContext(user_roles)

        # Check permission
        if not rbac_context.has_permission(permission):
            logger.warning(f"Permission denied: {permission} for roles: {rbac_context.role_names}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission} required",
            )

        logger.debug(f"Permission granted: {permission} for roles: {rbac_context.role_names}")
        return None

    return check_permission


def permission_required(permission: str):
    """
    Decorator to protect route handlers with permission checking.

    This decorator wraps route handlers and checks if the current user
    has the required permission before executing the handler.

    Args:
        permission: Required permission (e.g., "tests:write")

    Returns:
        Decorator function

    Example:
        ```python
        @router.post("/tests")
        @permission_required("tests:write")
        async def create_test(request: Request, test_data: TestCreate):
            return await test_service.create_test(test_data)
        ```
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs (FastAPI passes request explicitly or as part of args)
            request = kwargs.get("request")
            if request is None and args:
                # Try to find request in args (usually first arg after self for class-based views)
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                logger.error("No request object found for permission check")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Permission check failed: no request context",
                )

            # Check user roles
            if not hasattr(request.state, "user_roles"):
                logger.warning("No user roles found in request state")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
                )

            user_roles = request.state.user_roles
            rbac_context = RBACContext(user_roles)

            # Check permission
            if not rbac_context.has_permission(permission):
                logger.warning(
                    f"Permission denied: {permission} for roles: {rbac_context.role_names}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission} required",
                )

            logger.debug(f"Permission granted: {permission} for roles: {rbac_context.role_names}")

            # Execute the original function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(permissions: List[str]):
    """
    FastAPI dependency to require any of the specified permissions.

    Args:
        permissions: List of permissions, at least one is required

    Returns:
        Dependency function
    """

    async def check_permissions(request: Request):
        """Check if current request has any of the required permissions"""
        if not hasattr(request.state, "user_roles"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
            )

        user_roles = request.state.user_roles
        rbac_context = RBACContext(user_roles)

        if not rbac_context.has_any_permission(permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: one of {permissions} required",
            )

        return None

    return check_permissions


def require_all_permissions(permissions: List[str]):
    """
    FastAPI dependency to require all of the specified permissions.

    Args:
        permissions: List of permissions, all are required

    Returns:
        Dependency function
    """

    async def check_permissions(request: Request):
        """Check if current request has all required permissions"""
        if not hasattr(request.state, "user_roles"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
            )

        user_roles = request.state.user_roles
        rbac_context = RBACContext(user_roles)

        if not rbac_context.has_all_permissions(permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: all of {permissions} required",
            )

        return None

    return check_permissions


def is_admin_only():
    """
    FastAPI dependency to require admin privileges.

    Returns:
        Dependency function that checks for admin role
    """

    async def check_admin(request: Request):
        """Check if current request has admin privileges"""
        if not hasattr(request.state, "user_roles"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
            )

        user_roles = request.state.user_roles
        rbac_context = RBACContext(user_roles)

        if not rbac_context.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
            )

        return None

    return check_admin
