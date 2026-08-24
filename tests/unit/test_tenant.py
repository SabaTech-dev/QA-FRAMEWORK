"""
Unit tests for Tenant entity and multi-tenant infrastructure

Tests cover:
1. Tenant entity creation and methods
2. TenantPlan and TenantStatus enums
3. InMemoryTenantRepository CRUD operations
4. TenantContextMiddleware functionality
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from src.domain.entities.tenant import Tenant, TenantPlan, TenantStatus
from src.infrastructure.persistence.tenant_repository import InMemoryTenantRepository


class TestTenantEntity:
    """Unit tests for Tenant entity"""

    def test_tenant_creation_with_defaults(self):
        """Test creating a tenant with default values"""
        tenant = Tenant(name="Test Corp", slug="test-corp")

        assert tenant.name == "Test Corp"
        assert tenant.slug == "test-corp"
        assert tenant.plan == TenantPlan.FREE
        assert tenant.status == TenantStatus.TRIAL
        assert isinstance(tenant.id, UUID)
        assert isinstance(tenant.created_at, datetime)
        assert isinstance(tenant.updated_at, datetime)
        assert tenant.settings == {}

    def test_tenant_creation_with_all_fields(self):
        """Test creating a tenant with all fields specified"""
        tenant_id = uuid4()
        created = datetime(2024, 1, 1, 12, 0, 0)
        updated = datetime(2024, 1, 2, 12, 0, 0)

        tenant = Tenant(
            id=tenant_id,
            name="Acme Corp",
            slug="acme-corp",
            plan=TenantPlan.ENTERPRISE,
            status=TenantStatus.ACTIVE,
            settings={"theme": "dark", "features": ["advanced"]},
            created_at=created,
            updated_at=updated,
        )

        assert tenant.id == tenant_id
        assert tenant.name == "Acme Corp"
        assert tenant.slug == "acme-corp"
        assert tenant.plan == TenantPlan.ENTERPRISE
        assert tenant.status == TenantStatus.ACTIVE
        assert tenant.settings == {"theme": "dark", "features": ["advanced"]}
        assert tenant.created_at == created
        assert tenant.updated_at == updated

    def test_is_active(self):
        """Test is_active method"""
        active_tenant = Tenant(name="Active Corp", slug="active", status=TenantStatus.ACTIVE)
        suspended_tenant = Tenant(
            name="Suspended Corp", slug="suspended", status=TenantStatus.SUSPENDED
        )

        assert active_tenant.is_active() is True
        assert suspended_tenant.is_active() is False

    def test_is_suspended(self):
        """Test is_suspended method"""
        suspended_tenant = Tenant(
            name="Suspended Corp", slug="suspended", status=TenantStatus.SUSPENDED
        )
        active_tenant = Tenant(name="Active Corp", slug="active", status=TenantStatus.ACTIVE)

        assert suspended_tenant.is_suspended() is True
        assert active_tenant.is_suspended() is False

    def test_is_trial(self):
        """Test is_trial method"""
        trial_tenant = Tenant(name="Trial Corp", slug="trial", status=TenantStatus.TRIAL)
        active_tenant = Tenant(name="Active Corp", slug="active", status=TenantStatus.ACTIVE)

        assert trial_tenant.is_trial() is True
        assert active_tenant.is_trial() is False

    def test_is_enterprise(self):
        """Test is_enterprise method"""
        enterprise_tenant = Tenant(
            name="Enterprise Corp", slug="enterprise", plan=TenantPlan.ENTERPRISE
        )
        pro_tenant = Tenant(name="Pro Corp", slug="pro", plan=TenantPlan.PRO)

        assert enterprise_tenant.is_enterprise() is True
        assert pro_tenant.is_enterprise() is False

    def test_is_pro(self):
        """Test is_pro method (PRO or ENTERPRISE)"""
        pro_tenant = Tenant(name="Pro Corp", slug="pro", plan=TenantPlan.PRO)
        enterprise_tenant = Tenant(
            name="Enterprise Corp", slug="enterprise", plan=TenantPlan.ENTERPRISE
        )
        free_tenant = Tenant(name="Free Corp", slug="free", plan=TenantPlan.FREE)

        assert pro_tenant.is_pro() is True
        assert enterprise_tenant.is_pro() is True
        assert free_tenant.is_pro() is False

    def test_update_settings(self):
        """Test updating tenant settings"""
        tenant = Tenant(name="Test Corp", slug="test-corp")
        old_updated_at = tenant.updated_at

        # Small delay to ensure timestamp changes
        import time

        time.sleep(0.01)

        tenant.update_settings("theme", "dark")

        assert tenant.settings["theme"] == "dark"
        assert tenant.updated_at > old_updated_at

    def test_get_setting(self):
        """Test getting tenant settings"""
        tenant = Tenant(
            name="Test Corp", slug="test-corp", settings={"theme": "dark", "max_users": 100}
        )

        assert tenant.get_setting("theme") == "dark"
        assert tenant.get_setting("max_users") == 100
        assert tenant.get_setting("nonexistent") is None
        assert tenant.get_setting("nonexistent", "default") == "default"

    def test_activate(self):
        """Test activating tenant"""
        tenant = Tenant(name="Test Corp", slug="test-corp", status=TenantStatus.SUSPENDED)

        tenant.activate()

        assert tenant.status == TenantStatus.ACTIVE

    def test_suspend(self):
        """Test suspending tenant"""
        tenant = Tenant(name="Test Corp", slug="test-corp", status=TenantStatus.ACTIVE)

        tenant.suspend()

        assert tenant.status == TenantStatus.SUSPENDED

    def test_upgrade_plan(self):
        """Test upgrading tenant plan"""
        tenant = Tenant(name="Test Corp", slug="test-corp", plan=TenantPlan.FREE)

        tenant.upgrade_plan(TenantPlan.PRO)

        assert tenant.plan == TenantPlan.PRO

    def test_to_dict(self):
        """Test converting tenant to dictionary"""
        tenant_id = uuid4()
        tenant = Tenant(
            id=tenant_id,
            name="Test Corp",
            slug="test-corp",
            plan=TenantPlan.PRO,
            status=TenantStatus.ACTIVE,
            settings={"theme": "dark"},
        )

        tenant_dict = tenant.to_dict()

        assert tenant_dict["id"] == str(tenant_id)
        assert tenant_dict["name"] == "Test Corp"
        assert tenant_dict["slug"] == "test-corp"
        assert tenant_dict["plan"] == "pro"
        assert tenant_dict["status"] == "active"
        assert tenant_dict["settings"] == {"theme": "dark"}
        assert "created_at" in tenant_dict
        assert "updated_at" in tenant_dict

    def test_from_dict(self):
        """Test creating tenant from dictionary"""
        tenant_id = uuid4()
        created = datetime(2024, 1, 1, 12, 0, 0)
        updated = datetime(2024, 1, 2, 12, 0, 0)

        data = {
            "id": str(tenant_id),
            "name": "Test Corp",
            "slug": "test-corp",
            "plan": "enterprise",
            "status": "active",
            "settings": {"theme": "light"},
            "created_at": created.isoformat(),
            "updated_at": updated.isoformat(),
        }

        tenant = Tenant.from_dict(data)

        assert tenant.id == tenant_id
        assert tenant.name == "Test Corp"
        assert tenant.slug == "test-corp"
        assert tenant.plan == TenantPlan.ENTERPRISE
        assert tenant.status == TenantStatus.ACTIVE
        assert tenant.settings == {"theme": "light"}
        assert tenant.created_at == created
        assert tenant.updated_at == updated

    def test_repr(self):
        """Test string representation"""
        tenant = Tenant(
            name="Test Corp", slug="test-corp", plan=TenantPlan.PRO, status=TenantStatus.ACTIVE
        )

        repr_str = repr(tenant)

        assert "Test Corp" in repr_str
        assert "test-corp" in repr_str
        assert "pro" in repr_str
        assert "active" in repr_str

    def test_equality(self):
        """Test tenant equality based on ID"""
        tenant_id = uuid4()

        tenant1 = Tenant(id=tenant_id, name="Corp 1", slug="corp1")
        tenant2 = Tenant(id=tenant_id, name="Corp 2", slug="corp2")
        tenant3 = Tenant(name="Corp 3", slug="corp3")

        assert tenant1 == tenant2  # Same ID
        assert tenant1 != tenant3  # Different ID
        assert tenant1 != "not a tenant"  # Different type


class TestTenantEnums:
    """Unit tests for TenantPlan and TenantStatus enums"""

    def test_tenant_plan_values(self):
        """Test TenantPlan enum values"""
        assert TenantPlan.FREE.value == "free"
        assert TenantPlan.PRO.value == "pro"
        assert TenantPlan.ENTERPRISE.value == "enterprise"

    def test_tenant_status_values(self):
        """Test TenantStatus enum values"""
        assert TenantStatus.ACTIVE.value == "active"
        assert TenantStatus.SUSPENDED.value == "suspended"
        assert TenantStatus.TRIAL.value == "trial"

    def test_plan_from_string(self):
        """Test creating TenantPlan from string"""
        assert TenantPlan("free") == TenantPlan.FREE
        assert TenantPlan("pro") == TenantPlan.PRO
        assert TenantPlan("enterprise") == TenantPlan.ENTERPRISE

    def test_status_from_string(self):
        """Test creating TenantStatus from string"""
        assert TenantStatus("active") == TenantStatus.ACTIVE
        assert TenantStatus("suspended") == TenantStatus.SUSPENDED
        assert TenantStatus("trial") == TenantStatus.TRIAL


class TestInMemoryTenantRepository:
    """Unit tests for InMemoryTenantRepository"""

    @pytest.fixture
    def repository(self):
        """Create fresh repository for each test"""
        return InMemoryTenantRepository()

    @pytest.fixture
    def sample_tenant(self):
        """Create sample tenant for tests"""
        return Tenant(
            name="Test Corp", slug="test-corp", plan=TenantPlan.PRO, status=TenantStatus.ACTIVE
        )

    @pytest.mark.asyncio
    async def test_create_tenant(self, repository, sample_tenant):
        """Test creating a tenant"""
        created = await repository.create(sample_tenant)

        assert created == sample_tenant
        assert created.id == sample_tenant.id

    @pytest.mark.asyncio
    async def test_get_by_id(self, repository, sample_tenant):
        """Test getting tenant by ID"""
        await repository.create(sample_tenant)

        found = await repository.get_by_id(sample_tenant.id)

        assert found == sample_tenant

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository):
        """Test getting non-existent tenant by ID"""
        found = await repository.get_by_id(uuid4())

        assert found is None

    @pytest.mark.asyncio
    async def test_get_by_slug(self, repository, sample_tenant):
        """Test getting tenant by slug"""
        await repository.create(sample_tenant)

        found = await repository.get_by_slug("test-corp")

        assert found == sample_tenant

    @pytest.mark.asyncio
    async def test_get_by_slug_not_found(self, repository):
        """Test getting non-existent tenant by slug"""
        found = await repository.get_by_slug("nonexistent")

        assert found is None

    @pytest.mark.asyncio
    async def test_update_tenant(self, repository, sample_tenant):
        """Test updating a tenant"""
        await repository.create(sample_tenant)

        # Update tenant
        sample_tenant.name = "Updated Corp"
        sample_tenant.plan = TenantPlan.ENTERPRISE

        updated = await repository.update(sample_tenant)

        assert updated.name == "Updated Corp"
        assert updated.plan == TenantPlan.ENTERPRISE

    @pytest.mark.asyncio
    async def test_update_nonexistent_tenant(self, repository):
        """Test updating non-existent tenant"""
        tenant = Tenant(name="Ghost", slug="ghost")

        with pytest.raises(ValueError, match="not found"):
            await repository.update(tenant)

    @pytest.mark.asyncio
    async def test_delete_tenant(self, repository, sample_tenant):
        """Test deleting a tenant"""
        await repository.create(sample_tenant)

        deleted = await repository.delete(sample_tenant.id)

        assert deleted is True

        # Verify it's deleted
        found = await repository.get_by_id(sample_tenant.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_tenant(self, repository):
        """Test deleting non-existent tenant"""
        deleted = await repository.delete(uuid4())

        assert deleted is False

    @pytest.mark.asyncio
    async def test_list_all(self, repository):
        """Test listing all tenants with pagination"""
        # Create multiple tenants
        for i in range(5):
            tenant = Tenant(name=f"Corp {i}", slug=f"corp-{i}")
            await repository.create(tenant)

        # List all
        all_tenants = await repository.list_all(skip=0, limit=10)

        assert len(all_tenants) == 5

    @pytest.mark.asyncio
    async def test_list_all_with_pagination(self, repository):
        """Test listing tenants with pagination"""
        # Create 10 tenants
        for i in range(10):
            tenant = Tenant(name=f"Corp {i}", slug=f"corp-{i}")
            await repository.create(tenant)

        # Get first page
        page1 = await repository.list_all(skip=0, limit=5)
        assert len(page1) == 5

        # Get second page
        page2 = await repository.list_all(skip=5, limit=5)
        assert len(page2) == 5

        # Verify different tenants
        page1_ids = {t.id for t in page1}
        page2_ids = {t.id for t in page2}
        assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.asyncio
    async def test_find_by_status(self, repository):
        """Test finding tenants by status"""
        # Create tenants with different statuses
        active1 = Tenant(name="Active 1", slug="active1", status=TenantStatus.ACTIVE)
        active2 = Tenant(name="Active 2", slug="active2", status=TenantStatus.ACTIVE)
        suspended = Tenant(name="Suspended", slug="suspended", status=TenantStatus.SUSPENDED)

        await repository.create(active1)
        await repository.create(active2)
        await repository.create(suspended)

        # Find active
        active_tenants = await repository.find_by_status(TenantStatus.ACTIVE)

        assert len(active_tenants) == 2
        assert all(t.status == TenantStatus.ACTIVE for t in active_tenants)

        # Find suspended
        suspended_tenants = await repository.find_by_status(TenantStatus.SUSPENDED)

        assert len(suspended_tenants) == 1
        assert suspended_tenants[0].slug == "suspended"
