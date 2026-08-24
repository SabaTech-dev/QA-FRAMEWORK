"""Role entity - Domain model for RBAC roles"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from src.domain.entities.permission import Permission, validate_permission

# Predefined role permissions mapping
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "owner": ["admin:*"],
    "admin": ["tests:*", "projects:*", "users:read", "settings:*"],
    "member": ["tests:*", "projects:read", "projects:write"],
    "viewer": ["tests:read", "projects:read"],
}


@dataclass
class Role:
    """
    Entity representing a role in the RBAC system.

    This is a domain entity following Clean Architecture principles.
    Roles are tenant-scoped and contain a list of permissions.

    Attributes:
        id: Unique identifier (UUID)
        tenant_id: FK to Tenant (roles are tenant-scoped)
        name: Role name (owner, admin, member, viewer)
        permissions: List of permission strings (e.g., ["tests:read", "tests:write"])
        is_default: Whether this is the default role for new users
        created_at: When the role was created
    """

    id: UUID = field(default_factory=uuid4)
    tenant_id: UUID | None = None
    name: str = ""
    permissions: list[str] = field(default_factory=list)
    is_default: bool = False
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        """Initialize default values"""
        if self.created_at is None:
            self.created_at = datetime.now(UTC)
        if self.permissions is None:
            self.permissions = []

    def has_permission(self, required_permission: str) -> bool:
        """
        Check if role has a specific permission.

        Supports wildcard matching:
        - Role has "admin:*" -> has any permission
        - Role has "tests:*" -> has any tests:* permission

        Args:
            required_permission: Permission to check (e.g., "tests:read")

        Returns:
            True if role has the permission
        """
        for perm_str in self.permissions:
            # Check for admin wildcard
            if perm_str == "admin:*":
                return True

            # Check for resource wildcard
            if ":*" in perm_str:
                resource = perm_str.split(":")[0]
                required_resource = required_permission.split(":")[0]
                if resource == required_resource:
                    return True

            # Exact match
            if perm_str == required_permission:
                return True

        return False

    def has_any_permission(self, required_permissions: list[str]) -> bool:
        """
        Check if role has any of the specified permissions.

        Args:
            required_permissions: List of permissions to check

        Returns:
            True if role has at least one permission
        """
        return any(self.has_permission(perm) for perm in required_permissions)

    def has_all_permissions(self, required_permissions: list[str]) -> bool:
        """
        Check if role has all specified permissions.

        Args:
            required_permissions: List of permissions to check

        Returns:
            True if role has all permissions
        """
        return all(self.has_permission(perm) for perm in required_permissions)

    def add_permission(self, permission: str) -> None:
        """
        Add a permission to the role.

        Args:
            permission: Permission string to add

        Raises:
            ValueError: If permission format is invalid
        """
        if not validate_permission(permission):
            raise ValueError(f"Invalid permission: {permission}")

        if permission not in self.permissions:
            self.permissions.append(permission)

    def remove_permission(self, permission: str) -> bool:
        """
        Remove a permission from the role.

        Args:
            permission: Permission string to remove

        Returns:
            True if permission was removed, False if not found
        """
        if permission in self.permissions:
            self.permissions.remove(permission)
            return True
        return False

    def get_permissions(self) -> set[Permission]:
        """
        Get all permissions as Permission objects.

        Returns:
            Set of Permission objects
        """
        permissions = set()
        for perm_str in self.permissions:
            try:
                permissions.add(Permission.from_string(perm_str))
            except ValueError:
                # Skip invalid permissions
                pass
        return permissions

    def is_owner(self) -> bool:
        """Check if this is an owner role"""
        return self.name == "owner"

    def is_admin(self) -> bool:
        """Check if this is an admin role or higher"""
        return self.name in ["owner", "admin"]

    def to_dict(self) -> dict[str, Any]:
        """Convert role entity to dictionary"""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "name": self.name,
            "permissions": self.permissions,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Role":
        """
        Create a Role instance from a dictionary.

        Args:
            data: Dictionary with role data

        Returns:
            Role instance
        """
        tenant_id = data.get("tenant_id")
        if tenant_id and isinstance(tenant_id, str):
            tenant_id = UUID(tenant_id)

        role_id = data.get("id")
        if role_id and isinstance(role_id, str):
            role_id = UUID(role_id)

        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            id=role_id or uuid4(),
            tenant_id=tenant_id,
            name=data.get("name", ""),
            permissions=data.get("permissions", []),
            is_default=data.get("is_default", False),
            created_at=created_at,
        )

    @classmethod
    def create_default_role(
        cls, tenant_id: UUID, name: str, permissions: list[str] | None = None
    ) -> "Role":
        """
        Create a role with predefined permissions.

        Args:
            tenant_id: Tenant UUID
            name: Role name (owner, admin, member, viewer)
            permissions: Optional custom permissions (uses predefined if not provided)

        Returns:
            Role instance
        """
        if permissions is None:
            permissions = ROLE_PERMISSIONS.get(name, [])

        return cls(
            tenant_id=tenant_id,
            name=name,
            permissions=permissions,
            is_default=(name == "member"),  # member is default role for new users
        )

    def __repr__(self) -> str:
        """String representation of Role"""
        return f"Role(id={self.id}, name={self.name}, tenant_id={self.tenant_id}, permissions={len(self.permissions)})"

    def __eq__(self, other: object) -> bool:
        """Check equality based on ID"""
        if not isinstance(other, Role):
            return False
        return self.id == other.id
