"""Permission entity - Domain model for RBAC permissions"""

from dataclasses import dataclass
from typing import Set


@dataclass(frozen=True)
class Permission:
    """
    Entity representing a permission in the RBAC system.

    This is a value object following Clean Architecture principles.
    Permissions follow the pattern: resource:action (e.g., "tests:read")

    Attributes:
        resource: The resource type (tests, projects, users, settings)
        action: The action allowed (read, write, delete, run, *)
    """

    resource: str
    action: str

    @property
    def full_name(self) -> str:
        """
        Get full permission name in format "resource:action".

        Returns:
            Full permission string
        """
        return f"{self.resource}:{self.action}"

    def matches(self, required_permission: str) -> bool:
        """
        Check if this permission matches a required permission.

        Supports wildcard matching:
        - "admin:*" matches any permission
        - "tests:*" matches "tests:read", "tests:write", etc.

        Args:
            required_permission: Permission to check against

        Returns:
            True if permission matches
        """
        # Exact match
        if self.full_name == required_permission:
            return True

        # Wildcard action match (e.g., "tests:*" matches "tests:read")
        if self.action == "*":
            required_parts = required_permission.split(":")
            if len(required_parts) == 2 and required_parts[0] == self.resource:
                return True

        # Global wildcard match ("admin:*" matches everything)
        if self.resource == "admin" and self.action == "*":
            return True

        return False

    @classmethod
    def from_string(cls, permission_str: str) -> "Permission":
        """
        Create Permission from string format "resource:action".

        Args:
            permission_str: Permission string

        Returns:
            Permission instance

        Raises:
            ValueError: If string format is invalid
        """
        parts = permission_str.split(":")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid permission format: {permission_str}. Expected 'resource:action'"
            )

        return cls(resource=parts[0], action=parts[1])

    def __str__(self) -> str:
        """String representation"""
        return self.full_name

    def __repr__(self) -> str:
        """Developer representation"""
        return f"Permission(resource={self.resource!r}, action={self.action!r})"


# Predefined permissions
PERMISSIONS: Set[str] = {
    # Tests
    "tests:read",
    "tests:write",
    "tests:delete",
    "tests:run",
    # Projects
    "projects:read",
    "projects:write",
    "projects:delete",
    # Users
    "users:read",
    "users:write",
    "users:delete",
    # Settings
    "settings:read",
    "settings:write",
    # Admin (wildcard)
    "admin:*",
}


def validate_permission(permission_str: str) -> bool:
    """
    Validate if a permission string is valid.

    Args:
        permission_str: Permission string to validate

    Returns:
        True if permission is valid
    """
    try:
        # Check format
        parts = permission_str.split(":")
        if len(parts) != 2:
            return False

        resource, action = parts

        # Check for wildcard action
        if action == "*":
            return True

        # Check if permission exists in predefined set
        return permission_str in PERMISSIONS
    except Exception:
        return False
