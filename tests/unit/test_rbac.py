"""
Unit tests for RBAC system (Role, Permission, RBACContext)

Tests cover:
1. Permission entity
2. Role entity with permission checking
3. RBACContext permission utilities
4. InMemoryRoleRepository operations
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from src.api.middleware.rbac_middleware import RBACContext
from src.domain.entities.permission import Permission, validate_permission
from src.domain.entities.role import Role
from src.infrastructure.persistence.role_repository import InMemoryRoleRepository


class TestPermissionEntity:
    """Unit tests for Permission entity"""

    def test_permission_creation(self):
        """Test creating a permission"""
        perm = Permission(resource="tests", action="read")

        assert perm.resource == "tests"
        assert perm.action == "read"
        assert perm.full_name == "tests:read"

    def test_permission_from_string(self):
        """Test creating permission from string"""
        perm = Permission.from_string("tests:write")

        assert perm.resource == "tests"
        assert perm.action == "write"

    def test_permission_from_string_invalid(self):
        """Test invalid permission string format"""
        with pytest.raises(ValueError, match="Invalid permission format"):
            Permission.from_string("invalid")

    def test_permission_matches_exact(self):
        """Test exact permission matching"""
        perm = Permission(resource="tests", action="read")

        assert perm.matches("tests:read") is True
        assert perm.matches("tests:write") is False

    def test_permission_matches_wildcard_action(self):
        """Test wildcard action matching"""
        perm = Permission(resource="tests", action="*")

        assert perm.matches("tests:read") is True
        assert perm.matches("tests:write") is True
        assert perm.matches("tests:delete") is True
        assert perm.matches("projects:read") is False

    def test_permission_matches_admin_wildcard(self):
        """Test admin wildcard matching"""
        perm = Permission(resource="admin", action="*")

        assert perm.matches("tests:read") is True
        assert perm.matches("projects:write") is True
        assert perm.matches("users:delete") is True

    def test_permission_str(self):
        """Test string representation"""
        perm = Permission(resource="tests", action="read")

        assert str(perm) == "tests:read"

    def test_validate_permission_valid(self):
        """Test valid permission validation"""
        assert validate_permission("tests:read") is True
        assert validate_permission("projects:write") is True
        assert validate_permission("admin:*") is True

    def test_validate_permission_invalid(self):
        """Test invalid permission validation"""
        assert validate_permission("invalid") is False
        assert validate_permission("tests:invalid") is False


class TestRoleEntity:
    """Unit tests for Role entity"""

    def test_role_creation(self):
        """Test creating a role"""
        tenant_id = uuid4()
        role = Role(tenant_id=tenant_id, name="member", permissions=["tests:read", "tests:write"])

        assert role.name == "member"
        assert role.tenant_id == tenant_id
        assert "tests:read" in role.permissions
        assert isinstance(role.id, UUID)
        assert isinstance(role.created_at, datetime)

    def test_role_has_permission_exact(self):
        """Test exact permission checking"""
        role = Role(name="member", permissions=["tests:read", "tests:write"])

        assert role.has_permission("tests:read") is True
        assert role.has_permission("tests:write") is True
        assert role.has_permission("tests:delete") is False

    def test_role_has_permission_wildcard_resource(self):
        """Test resource wildcard permission checking"""
        role = Role(name="admin", permissions=["tests:*"])

        assert role.has_permission("tests:read") is True
        assert role.has_permission("tests:write") is True
        assert role.has_permission("tests:delete") is True
        assert role.has_permission("projects:read") is False

    def test_role_has_permission_admin_wildcard(self):
        """Test admin wildcard permission checking"""
        role = Role(name="owner", permissions=["admin:*"])

        assert role.has_permission("tests:read") is True
        assert role.has_permission("projects:write") is True
        assert role.has_permission("users:delete") is True
        assert role.has_permission("anything:anything") is True

    def test_role_has_any_permission(self):
        """Test has_any_permission method"""
        role = Role(name="member", permissions=["tests:read", "projects:read"])

        assert role.has_any_permission(["tests:write", "tests:read"]) is True
        assert role.has_any_permission(["tests:write", "projects:write"]) is False

    def test_role_has_all_permissions(self):
        """Test has_all_permissions method"""
        role = Role(name="member", permissions=["tests:read", "tests:write", "projects:read"])

        assert role.has_all_permissions(["tests:read", "projects:read"]) is True
        assert role.has_all_permissions(["tests:read", "tests:delete"]) is False

    def test_role_add_permission(self):
        """Test adding a permission"""
        role = Role(name="member", permissions=["tests:read"])

        role.add_permission("tests:write")

        assert "tests:write" in role.permissions

    def test_role_add_permission_invalid(self):
        """Test adding invalid permission"""
        role = Role(name="member", permissions=[])

        with pytest.raises(ValueError, match="Invalid permission"):
            role.add_permission("invalid_permission")

    def test_role_remove_permission(self):
        """Test removing a permission"""
        role = Role(name="member", permissions=["tests:read", "tests:write"])

        result = role.remove_permission("tests:read")

        assert result is True
        assert "tests:read" not in role.permissions

    def test_role_remove_permission_not_found(self):
        """Test removing non-existent permission"""
        role = Role(name="member", permissions=["tests:read"])

        result = role.remove_permission("tests:delete")

        assert result is False

    def test_role_is_owner(self):
        """Test is_owner method"""
        owner_role = Role(name="owner")
        admin_role = Role(name="admin")

        assert owner_role.is_owner() is True
        assert admin_role.is_owner() is False

    def test_role_is_admin(self):
        """Test is_admin method"""
        owner_role = Role(name="owner")
        admin_role = Role(name="admin")
        member_role = Role(name="member")

        assert owner_role.is_admin() is True
        assert admin_role.is_admin() is True
        assert member_role.is_admin() is False

    def test_role_to_dict(self):
        """Test converting role to dictionary"""
        role_id = uuid4()
        tenant_id = uuid4()
        role = Role(
            id=role_id,
            tenant_id=tenant_id,
            name="admin",
            permissions=["tests:*", "projects:*"],
            is_default=False,
        )

        role_dict = role.to_dict()

        assert role_dict["id"] == str(role_id)
        assert role_dict["tenant_id"] == str(tenant_id)
        assert role_dict["name"] == "admin"
        assert role_dict["permissions"] == ["tests:*", "projects:*"]
        assert role_dict["is_default"] is False

    def test_role_from_dict(self):
        """Test creating role from dictionary"""
        role_id = uuid4()
        tenant_id = uuid4()

        data = {
            "id": str(role_id),
            "tenant_id": str(tenant_id),
            "name": "viewer",
            "permissions": ["tests:read", "projects:read"],
            "is_default": False,
        }

        role = Role.from_dict(data)

        assert role.id == role_id
        assert role.tenant_id == tenant_id
        assert role.name == "viewer"
        assert role.permissions == ["tests:read", "projects:read"]

    def test_role_create_default_role(self):
        """Test creating default roles"""
        tenant_id = uuid4()

        # Owner role
        owner = Role.create_default_role(tenant_id, "owner")
        assert owner.name == "owner"
        assert owner.permissions == ["admin:*"]

        # Member role (default)
        member = Role.create_default_role(tenant_id, "member")
        assert member.name == "member"
        assert member.is_default is True

    def test_role_equality(self):
        """Test role equality based on ID"""
        role_id = uuid4()

        role1 = Role(id=role_id, name="Role 1")
        role2 = Role(id=role_id, name="Role 2")
        role3 = Role(name="Role 3")

        assert role1 == role2
        assert role1 != role3


class TestRBACContext:
    """Unit tests for RBACContext"""

    def test_rbac_context_has_permission(self):
        """Test RBACContext permission checking"""
        role1 = Role(name="member", permissions=["tests:read"])
        role2 = Role(name="admin", permissions=["projects:*"])

        rbac = RBACContext(roles=[role1, role2])

        assert rbac.has_permission("tests:read") is True
        assert rbac.has_permission("projects:write") is True
        assert rbac.has_permission("users:read") is False

    def test_rbac_context_has_any_permission(self):
        """Test has_any_permission"""
        roles = [
            Role(name="member", permissions=["tests:read"]),
            Role(name="admin", permissions=["projects:read"]),
        ]
        rbac = RBACContext(roles=roles)

        assert rbac.has_any_permission(["tests:write", "tests:read"]) is True
        assert rbac.has_any_permission(["users:read", "users:write"]) is False

    def test_rbac_context_has_all_permissions(self):
        """Test has_all_permissions"""
        roles = [Role(name="member", permissions=["tests:read", "projects:read"])]
        rbac = RBACContext(roles=roles)

        assert rbac.has_all_permissions(["tests:read", "projects:read"]) is True
        assert rbac.has_all_permissions(["tests:read", "tests:write"]) is False


class TestInMemoryRoleRepository:
    """Unit tests for InMemoryRoleRepository"""

    @pytest.fixture
    def repository(self):
        """Create fresh repository"""
        return InMemoryRoleRepository()

    @pytest.fixture
    def sample_role(self):
        """Create sample role"""
        return Role(
            tenant_id=uuid4(),
            name="member",
            permissions=["tests:read", "tests:write"],
            is_default=True,
        )

    @pytest.mark.asyncio
    async def test_create_role(self, repository, sample_role):
        """Test creating a role"""
        created = await repository.create(sample_role)

        assert created == sample_role

    @pytest.mark.asyncio
    async def test_get_by_id(self, repository, sample_role):
        """Test getting role by ID"""
        await repository.create(sample_role)

        found = await repository.get_by_id(sample_role.id)

        assert found == sample_role

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository):
        """Test getting non-existent role"""
        found = await repository.get_by_id(uuid4())

        assert found is None

    @pytest.mark.asyncio
    async def test_get_by_name(self, repository, sample_role):
        """Test getting role by name"""
        await repository.create(sample_role)

        found = await repository.get_by_tenant_and_name(sample_role.tenant_id, "member")

        assert found == sample_role

    @pytest.mark.asyncio
    async def test_get_default_role(self, repository, sample_role):
        """Test getting default role"""
        await repository.create(sample_role)

        found = await repository.get_default_role(sample_role.tenant_id)

        assert found == sample_role

    @pytest.mark.asyncio
    async def test_list_by_tenant(self, repository):
        """Test listing roles by tenant"""
        tenant_id = uuid4()

        role1 = Role(tenant_id=tenant_id, name="owner")
        role2 = Role(tenant_id=tenant_id, name="member")
        role3 = Role(tenant_id=uuid4(), name="admin")

        await repository.create(role1)
        await repository.create(role2)
        await repository.create(role3)

        roles = await repository.list_by_tenant(tenant_id)

        assert len(roles) == 2
        assert all(r.tenant_id == tenant_id for r in roles)

    @pytest.mark.asyncio
    async def test_update_role(self, repository, sample_role):
        """Test updating role"""
        await repository.create(sample_role)

        sample_role.permissions = ["tests:*"]
        updated = await repository.update(sample_role)

        assert updated.permissions == ["tests:*"]

    @pytest.mark.asyncio
    async def test_delete_role(self, repository, sample_role):
        """Test deleting role"""
        await repository.create(sample_role)

        deleted = await repository.delete(sample_role.id)

        assert deleted is True
        assert await repository.get_by_id(sample_role.id) is None
