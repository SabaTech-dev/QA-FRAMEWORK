"""Tenant Repository - Persistence layer for Tenant entity

This module provides:
1. Abstract repository interface (Clean Architecture)
2. SQLAlchemy implementation for async database operations
3. CRUD operations for Tenant entities
"""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.tenant import Tenant, TenantPlan, TenantStatus


class TenantRepositoryInterface(ABC):
    """
    Abstract interface for Tenant repository.

    Following Clean Architecture principles, this interface defines
    the contract for data persistence without depending on implementation details.
    """

    @abstractmethod
    async def create(self, tenant: Tenant) -> Tenant:
        """
        Create a new tenant.

        Args:
            tenant: Tenant entity to create

        Returns:
            Created tenant with generated ID
        """

    @abstractmethod
    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        """
        Get tenant by ID.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Tenant if found, None otherwise
        """

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Tenant | None:
        """
        Get tenant by slug (URL-friendly identifier).

        Args:
            slug: Tenant slug

        Returns:
            Tenant if found, None otherwise
        """

    @abstractmethod
    async def update(self, tenant: Tenant) -> Tenant:
        """
        Update existing tenant.

        Args:
            tenant: Tenant entity with updated data

        Returns:
            Updated tenant
        """

    @abstractmethod
    async def delete(self, tenant_id: UUID) -> bool:
        """
        Delete tenant by ID.

        Args:
            tenant_id: Tenant UUID

        Returns:
            True if deleted, False if not found
        """

    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Tenant]:
        """
        List all tenants with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of tenants
        """

    @abstractmethod
    async def find_by_status(self, status: TenantStatus) -> list[Tenant]:
        """
        Find tenants by status.

        Args:
            status: Tenant status to filter by

        Returns:
            List of tenants with matching status
        """


class SQLAlchemyTenantRepository(TenantRepositoryInterface):
    """
    SQLAlchemy implementation of TenantRepositoryInterface.

    This implementation uses async SQLAlchemy sessions for database operations.
    """

    def __init__(self, session):
        """
        Initialize repository with database session.

        Args:
            session: AsyncSession instance from SQLAlchemy
        """
        self.session = session

    async def create(self, tenant: Tenant) -> Tenant:
        """Create a new tenant in the database"""
        # Import here to avoid circular dependency
        from dashboard.backend.models import TenantModel

        db_tenant = TenantModel(
            id=str(tenant.id),
            name=tenant.name,
            slug=tenant.slug,
            plan=tenant.plan.value,
            status=tenant.status.value,
            settings=tenant.settings,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )

        self.session.add(db_tenant)
        await self.session.commit()
        await self.session.refresh(db_tenant)

        return self._map_to_entity(db_tenant)

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        """Get tenant by ID from database"""
        from sqlalchemy import select

        from dashboard.backend.models import TenantModel

        query = select(TenantModel).where(TenantModel.id == str(tenant_id))
        result = await self.session.execute(query)
        db_tenant = result.scalar_one_or_none()

        if db_tenant is None:
            return None

        return self._map_to_entity(db_tenant)

    async def get_by_slug(self, slug: str) -> Tenant | None:
        """Get tenant by slug from database"""
        from sqlalchemy import select

        from dashboard.backend.models import TenantModel

        query = select(TenantModel).where(TenantModel.slug == slug)
        result = await self.session.execute(query)
        db_tenant = result.scalar_one_or_none()

        if db_tenant is None:
            return None

        return self._map_to_entity(db_tenant)

    async def update(self, tenant: Tenant) -> Tenant:
        """Update existing tenant in database"""
        from sqlalchemy import select

        from dashboard.backend.models import TenantModel

        query = select(TenantModel).where(TenantModel.id == str(tenant.id))
        result = await self.session.execute(query)
        db_tenant = result.scalar_one_or_none()

        if db_tenant is None:
            raise ValueError(f"Tenant with id {tenant.id} not found")

        # Update fields
        db_tenant.name = tenant.name
        db_tenant.slug = tenant.slug
        db_tenant.plan = tenant.plan.value
        db_tenant.status = tenant.status.value
        db_tenant.settings = tenant.settings
        db_tenant.updated_at = tenant.updated_at

        await self.session.commit()
        await self.session.refresh(db_tenant)

        return self._map_to_entity(db_tenant)

    async def delete(self, tenant_id: UUID) -> bool:
        """Delete tenant from database"""
        from sqlalchemy import select

        from dashboard.backend.models import TenantModel

        query = select(TenantModel).where(TenantModel.id == str(tenant_id))
        result = await self.session.execute(query)
        db_tenant = result.scalar_one_or_none()

        if db_tenant is None:
            return False

        await self.session.delete(db_tenant)
        await self.session.commit()

        return True

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Tenant]:
        """List all tenants with pagination"""
        from sqlalchemy import select

        from dashboard.backend.models import TenantModel

        query = select(TenantModel).offset(skip).limit(limit)
        result = await self.session.execute(query)
        db_tenants = result.scalars().all()

        return [self._map_to_entity(db_tenant) for db_tenant in db_tenants]

    async def find_by_status(self, status: TenantStatus) -> list[Tenant]:
        """Find tenants by status"""
        from sqlalchemy import select

        from dashboard.backend.models import TenantModel

        query = select(TenantModel).where(TenantModel.status == status.value)
        result = await self.session.execute(query)
        db_tenants = result.scalars().all()

        return [self._map_to_entity(db_tenant) for db_tenant in db_tenants]

    def _map_to_entity(self, db_tenant) -> Tenant:
        """
        Map SQLAlchemy model to domain entity.

        Args:
            db_tenant: TenantModel instance

        Returns:
            Tenant domain entity
        """

        return Tenant(
            id=UUID(db_tenant.id),
            name=db_tenant.name,
            slug=db_tenant.slug,
            plan=TenantPlan(db_tenant.plan),
            status=TenantStatus(db_tenant.status),
            settings=db_tenant.settings or {},
            created_at=db_tenant.created_at,
            updated_at=db_tenant.updated_at,
        )


class InMemoryTenantRepository(TenantRepositoryInterface):
    """
    In-memory implementation of TenantRepositoryInterface for testing.

    This implementation stores tenants in memory and is useful for unit tests.
    """

    def __init__(self):
        """Initialize in-memory storage"""
        self._tenants: dict = {}

    async def create(self, tenant: Tenant) -> Tenant:
        """Create tenant in memory"""
        self._tenants[tenant.id] = tenant
        return tenant

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        """Get tenant from memory by ID"""
        return self._tenants.get(tenant_id)

    async def get_by_slug(self, slug: str) -> Tenant | None:
        """Get tenant from memory by slug"""
        for tenant in self._tenants.values():
            if tenant.slug == slug:
                return tenant
        return None

    async def update(self, tenant: Tenant) -> Tenant:
        """Update tenant in memory"""
        if tenant.id not in self._tenants:
            raise ValueError(f"Tenant with id {tenant.id} not found")
        self._tenants[tenant.id] = tenant
        return tenant

    async def delete(self, tenant_id: UUID) -> bool:
        """Delete tenant from memory"""
        if tenant_id not in self._tenants:
            return False
        del self._tenants[tenant_id]
        return True

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Tenant]:
        """List all tenants from memory with pagination"""
        tenants = list(self._tenants.values())
        return tenants[skip : skip + limit]

    async def find_by_status(self, status: TenantStatus) -> list[Tenant]:
        """Find tenants by status in memory"""
        return [t for t in self._tenants.values() if t.status == status]
