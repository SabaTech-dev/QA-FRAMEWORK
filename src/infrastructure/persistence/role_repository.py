"""Role Repository - Persistence layer for Role entity

This module provides:
1. Abstract repository interface (Clean Architecture)
2. SQLAlchemy implementation for async database operations
3. InMemory implementation for testing
4. CRUD operations for Role entities
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from src.domain.entities.role import Role


class RoleRepositoryInterface(ABC):
    """
    Abstract interface for Role repository.

    Following Clean Architecture principles, this interface defines
    the contract for data persistence without depending on implementation details.
    """

    @abstractmethod
    async def create(self, role: Role) -> Role:
        """
        Create a new role.

        Args:
            role: Role entity to create

        Returns:
            Created role with generated ID
        """
        pass

    @abstractmethod
    async def get_by_id(self, role_id: UUID) -> Optional[Role]:
        """
        Get role by ID.

        Args:
            role_id: Role UUID

        Returns:
            Role if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_tenant_and_name(self, tenant_id: UUID, name: str) -> Optional[Role]:
        """
        Get role by tenant ID and role name.

        Args:
            tenant_id: Tenant UUID
            name: Role name

        Returns:
            Role if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_default_role(self, tenant_id: UUID) -> Optional[Role]:
        """
        Get the default role for a tenant (used for new users).

        Args:
            tenant_id: Tenant UUID

        Returns:
            Default role if found, None otherwise
        """
        pass

    @abstractmethod
    async def list_by_tenant(self, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[Role]:
        """
        List all roles for a tenant with pagination.

        Args:
            tenant_id: Tenant UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of roles
        """
        pass

    @abstractmethod
    async def update(self, role: Role) -> Role:
        """
        Update existing role.

        Args:
            role: Role entity with updated data

        Returns:
            Updated role
        """
        pass

    @abstractmethod
    async def delete(self, role_id: UUID) -> bool:
        """
        Delete role by ID.

        Args:
            role_id: Role UUID

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def create_default_roles(self, tenant_id: UUID) -> List[Role]:
        """
        Create default roles (owner, admin, member, viewer) for a tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            List of created roles
        """
        pass


class SQLAlchemyRoleRepository(RoleRepositoryInterface):
    """
    SQLAlchemy implementation of RoleRepositoryInterface.

    This implementation uses async SQLAlchemy sessions for database operations.
    """

    def __init__(self, session):
        """
        Initialize repository with database session.

        Args:
            session: AsyncSession instance from SQLAlchemy
        """
        self.session = session

    async def create(self, role: Role) -> Role:
        """Create a new role in the database"""
        # Import here to avoid circular dependency
        from dashboard.backend.models import RoleModel

        db_role = RoleModel(
            id=str(role.id),
            tenant_id=str(role.tenant_id) if role.tenant_id else None,
            name=role.name,
            permissions=role.permissions,
            is_default=role.is_default,
            created_at=role.created_at,
        )

        self.session.add(db_role)
        await self.session.commit()
        await self.session.refresh(db_role)

        return self._map_to_entity(db_role)

    async def get_by_id(self, role_id: UUID) -> Optional[Role]:
        """Get role by ID from database"""
        from sqlalchemy import select

        from dashboard.backend.models import RoleModel

        query = select(RoleModel).where(RoleModel.id == str(role_id))
        result = await self.session.execute(query)
        db_role = result.scalar_one_or_none()

        if db_role is None:
            return None

        return self._map_to_entity(db_role)

    async def get_by_tenant_and_name(self, tenant_id: UUID, name: str) -> Optional[Role]:
        """Get role by tenant ID and name from database"""
        from sqlalchemy import select

        from dashboard.backend.models import RoleModel

        query = select(RoleModel).where(
            RoleModel.tenant_id == str(tenant_id), RoleModel.name == name
        )
        result = await self.session.execute(query)
        db_role = result.scalar_one_or_none()

        if db_role is None:
            return None

        return self._map_to_entity(db_role)

    async def get_default_role(self, tenant_id: UUID) -> Optional[Role]:
        """Get default role for tenant from database"""
        from sqlalchemy import select

        from dashboard.backend.models import RoleModel

        query = select(RoleModel).where(
            RoleModel.tenant_id == str(tenant_id), RoleModel.is_default.is_(True)
        )
        result = await self.session.execute(query)
        db_role = result.scalar_one_or_none()

        if db_role is None:
            return None

        return self._map_to_entity(db_role)

    async def list_by_tenant(self, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[Role]:
        """List all roles for a tenant with pagination"""
        from sqlalchemy import select

        from dashboard.backend.models import RoleModel

        query = (
            select(RoleModel).where(RoleModel.tenant_id == str(tenant_id)).offset(skip).limit(limit)
        )

        result = await self.session.execute(query)
        db_roles = result.scalars().all()

        return [self._map_to_entity(db_role) for db_role in db_roles]

    async def update(self, role: Role) -> Role:
        """Update existing role in database"""
        from sqlalchemy import select

        from dashboard.backend.models import RoleModel

        query = select(RoleModel).where(RoleModel.id == str(role.id))
        result = await self.session.execute(query)
        db_role = result.scalar_one_or_none()

        if db_role is None:
            raise ValueError(f"Role with id {role.id} not found")

        # Update fields
        db_role.name = role.name
        db_role.permissions = role.permissions
        db_role.is_default = role.is_default

        await self.session.commit()
        await self.session.refresh(db_role)

        return self._map_to_entity(db_role)

    async def delete(self, role_id: UUID) -> bool:
        """Delete role from database"""
        from sqlalchemy import select

        from dashboard.backend.models import RoleModel

        query = select(RoleModel).where(RoleModel.id == str(role_id))
        result = await self.session.execute(query)
        db_role = result.scalar_one_or_none()

        if db_role is None:
            return False

        await self.session.delete(db_role)
        await self.session.commit()

        return True

    async def create_default_roles(self, tenant_id: UUID) -> List[Role]:
        """Create default roles for tenant"""
        from src.domain.entities.role import ROLE_PERMISSIONS

        roles = []
        for role_name, permissions in ROLE_PERMISSIONS.items():
            role = Role.create_default_role(tenant_id, role_name, permissions)
            created_role = await self.create(role)
            roles.append(created_role)

        return roles

    def _map_to_entity(self, db_role) -> Role:
        """
        Map SQLAlchemy model to domain entity.

        Args:
            db_role: RoleModel instance

        Returns:
            Role domain entity
        """
        from uuid import UUID

        return Role(
            id=UUID(db_role.id),
            tenant_id=UUID(db_role.tenant_id) if db_role.tenant_id else None,
            name=db_role.name,
            permissions=db_role.permissions or [],
            is_default=db_role.is_default,
            created_at=db_role.created_at,
        )


class InMemoryRoleRepository(RoleRepositoryInterface):
    """
    In-memory implementation of RoleRepositoryInterface for testing.

    This implementation stores roles in memory and is useful for unit tests.
    """

    def __init__(self):
        """Initialize in-memory storage"""
        self._roles: dict = {}

    async def create(self, role: Role) -> Role:
        """Create role in memory"""
        self._roles[role.id] = role
        return role

    async def get_by_id(self, role_id: UUID) -> Optional[Role]:
        """Get role from memory by ID"""
        return self._roles.get(role_id)

    async def get_by_tenant_and_name(self, tenant_id: UUID, name: str) -> Optional[Role]:
        """Get role from memory by tenant ID and name"""
        for role in self._roles.values():
            if role.tenant_id == tenant_id and role.name == name:
                return role
        return None

    async def get_default_role(self, tenant_id: UUID) -> Optional[Role]:
        """Get default role for tenant from memory"""
        for role in self._roles.values():
            if role.tenant_id == tenant_id and role.is_default:
                return role
        return None

    async def list_by_tenant(self, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[Role]:
        """List all roles for tenant from memory with pagination"""
        roles = [r for r in self._roles.values() if r.tenant_id == tenant_id]
        return roles[skip : skip + limit]

    async def update(self, role: Role) -> Role:
        """Update role in memory"""
        if role.id not in self._roles:
            raise ValueError(f"Role with id {role.id} not found")
        self._roles[role.id] = role
        return role

    async def delete(self, role_id: UUID) -> bool:
        """Delete role from memory"""
        if role_id not in self._roles:
            return False
        del self._roles[role_id]
        return True

    async def create_default_roles(self, tenant_id: UUID) -> List[Role]:
        """Create default roles for tenant in memory"""
        from src.domain.entities.role import ROLE_PERMISSIONS

        roles = []
        for role_name, permissions in ROLE_PERMISSIONS.items():
            role = Role.create_default_role(tenant_id, role_name, permissions)
            self._roles[role.id] = role
            roles.append(role)

        return roles
