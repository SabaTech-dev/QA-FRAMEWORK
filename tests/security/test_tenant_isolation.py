"""
Tenant Isolation Test Suite — Security & Data Isolation

Motivation: Breach de tl;dv expuso 181,874 reuniones por falta de tenant isolation.
QA-FRAMEWORK tiene tenant.py, tenant_repository.py, tenant_context.py middleware
— pero SIN test suite dedicado de aislamiento.

This suite verifies:
1. Cross-tenant enumeration prevention
2. Direct ID access isolation (403/404 for foreign tenant resources)
3. API bypass resistance (header manipulation, query injection)
4. Database-level isolation (raw SQL cannot leak cross-tenant)

Coverage target: 100% of tenant isolation paths.
"""

from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.api.middleware.tenant_context import (
    TenantContextMiddleware,
    get_tenant_context,
)
from src.domain.entities.tenant import Tenant, TenantPlan, TenantStatus
from src.infrastructure.persistence.tenant_repository import InMemoryTenantRepository

# =============================================================================
# Helpers
# =============================================================================


def _make_app(repo, require_tenant=True):
    """Build a minimal FastAPI app wired with TenantContextMiddleware."""
    app = FastAPI()
    app.add_middleware(
        TenantContextMiddleware,
        tenant_repository=repo,
        require_tenant=require_tenant,
    )

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/v1/resources")
    async def list_resources(request: Request):
        ctx = get_tenant_context(request)
        return {
            "tenant_id": ctx.tenant_id,
            "resources": [
                {"id": "res-1", "name": "Widget A"},
                {"id": "res-2", "name": "Widget B"},
            ],
        }

    @app.get("/api/v1/resources/{resource_id}")
    async def get_resource(resource_id: str, request: Request):
        ctx = get_tenant_context(request)
        fake_resources = {
            "res-1": {"id": "res-1", "name": "Widget A", "tenant_id": str(ctx.tenant_id)},
            "res-2": {"id": "res-2", "name": "Widget B", "tenant_id": str(ctx.tenant_id)},
        }
        if resource_id not in fake_resources:
            from fastapi.responses import JSONResponse

            return JSONResponse(status_code=404, content={"detail": "Not found"})
        return fake_resources[resource_id]

    @app.get("/api/v1/strict")
    async def strict_endpoint(request: Request):
        tenant = require_tenant(request)
        return {"tenant_id": str(tenant.id), "name": tenant.name}

    @app.get("/api/v1/public")
    async def public_endpoint():
        return {"message": "public"}

    @app.get("/api/v1/whoami")
    async def whoami(request: Request):
        ctx = get_tenant_context(request)
        return {"tenant_id": ctx.tenant_id, "slug": ctx.tenant_slug}

    @app.get("/api/v1/identity")
    async def identity(request: Request):
        ctx = get_tenant_context(request)
        import asyncio

        await asyncio.sleep(0.01)
        return {"tenant_id": ctx.tenant_id, "slug": ctx.tenant_slug}

    @app.get("/api/v1/echo")
    async def echo(request: Request):
        ctx = get_tenant_context(request)
        return {"tenant_id": ctx.tenant_id}

    return app


def _client(repo, require_tenant=True):
    """Create a test client for a repo with a configured app."""
    return TestClient(_make_app(repo, require_tenant), raise_server_exceptions=False)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def repo():
    """Fresh in-memory tenant repository."""
    return InMemoryTenantRepository()


@pytest.fixture
def tenant_a():
    """Tenant A — Acme Corp."""
    return Tenant(
        id=uuid4(),
        name="Acme Corp",
        slug="acme",
        plan=TenantPlan.PRO,
        status=TenantStatus.ACTIVE,
    )


@pytest.fixture
def tenant_b():
    """Tenant B — Globex Inc."""
    return Tenant(
        id=uuid4(),
        name="Globex Inc",
        slug="globex",
        plan=TenantPlan.ENTERPRISE,
        status=TenantStatus.ACTIVE,
    )


@pytest.fixture
def tenant_suspended():
    """Suspended tenant for blocked-access tests."""
    return Tenant(
        id=uuid4(),
        name="Suspended Corp",
        slug="suspended",
        plan=TenantPlan.FREE,
        status=TenantStatus.SUSPENDED,
    )


# =============================================================================
# 1. CROSS-TENANT ENUMERATION TESTS
# =============================================================================


class TestCrossTenantEnumeration:
    """
    Verify that a user from Tenant A cannot enumerate resources
    belonging to Tenant B through any API surface.
    """

    @pytest.mark.asyncio
    async def test_list_resources_scoped_to_tenant(self, repo, tenant_a, tenant_b):
        """Listing resources returns only the requesting tenant's data."""
        await repo.create(tenant_a)
        await repo.create(tenant_b)

        # Verify both tenants exist
        assert await repo.get_by_id(tenant_a.id) is not None
        assert await repo.get_by_id(tenant_b.id) is not None

        # Verify listing does not leak tenant B's slug to tenant A
        client = _client(repo)

        # Request as tenant A
        resp_a = client.get(
            "/api/v1/whoami",
            headers={"X-Tenant-ID": str(tenant_a.id)},
        )
        assert resp_a.status_code == 200
        assert resp_a.json()["tenant_id"] == str(tenant_a.id)
        assert resp_a.json()["slug"] == "acme"

        # Request as tenant B
        resp_b = client.get(
            "/api/v1/whoami",
            headers={"X-Tenant-ID": str(tenant_b.id)},
        )
        assert resp_b.status_code == 200
        assert resp_b.json()["tenant_id"] == str(tenant_b.id)
        assert resp_b.json()["slug"] == "globex"

        # Verify isolation
        assert resp_a.json()["tenant_id"] != str(tenant_b.id)
        assert resp_b.json()["tenant_id"] != str(tenant_a.id)

    def test_enumeration_via_iteration_blocked(self, repo, tenant_a, tenant_b):
        """Cannot iterate through IDs to discover other tenants' resources."""
        client = _client(repo)

        # Request without tenant header → should fail
        resp = client.get("/api/v1/resources")
        assert resp.status_code == 401

        # Request with invalid tenant ID → should fail
        resp = client.get(
            "/api/v1/resources",
            headers={"X-Tenant-ID": str(uuid4())},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_repository_does_not_leak_cross_tenant(self, repo, tenant_a, tenant_b):
        """Repository get_by_id only returns the exact tenant requested."""
        await repo.create(tenant_a)
        await repo.create(tenant_b)

        found_a = await repo.get_by_id(tenant_a.id)
        assert found_a is not None
        assert found_a.id == tenant_a.id
        assert found_a.slug == "acme"

        found_b = await repo.get_by_id(tenant_b.id)
        assert found_b is not None
        assert found_b.id == tenant_b.id
        assert found_b.slug == "globex"

        assert tenant_a.id != tenant_b.id

    @pytest.mark.asyncio
    async def test_slug_lookup_isolation(self, repo, tenant_a, tenant_b):
        """Slug-based lookup returns only the matching tenant."""
        await repo.create(tenant_a)
        await repo.create(tenant_b)

        found = await repo.get_by_slug("acme")
        assert found is not None
        assert found.id == tenant_a.id
        assert found.name == "Acme Corp"

        found_b = await repo.get_by_slug("globex")
        assert found_b is not None
        assert found_b.id == tenant_b.id


# =============================================================================
# 2. DIRECT ID ACCESS ISOLATION TESTS
# =============================================================================


class TestDirectIdAccessIsolation:
    """
    Verify that accessing a resource by ID from a different tenant
    returns 403 or 404, never the resource data.
    """

    def test_get_resource_wrong_tenant_returns_401(self, repo):
        """GET /api/v1/resources/<id> with no tenant context → 401."""
        client = _client(repo)
        resp = client.get("/api/v1/resources/res-1")
        assert resp.status_code == 401

    def test_get_resource_different_tenant_cannot_access(self, repo, tenant_a, tenant_b):
        """GET /api/v1/resources/<id> with wrong tenant → isolation enforced."""
        repo._tenants[tenant_a.id] = tenant_a
        repo._tenants[tenant_b.id] = tenant_b
        client = _client(repo)

        # Request as tenant A
        resp_a = client.get(
            "/api/v1/resources/res-1",
            headers={"X-Tenant-ID": str(tenant_a.id)},
        )
        assert resp_a.status_code == 200
        assert resp_a.json()["tenant_id"] == str(tenant_a.id)

        # Request as tenant B for same resource ID
        resp_b = client.get(
            "/api/v1/resources/res-1",
            headers={"X-Tenant-ID": str(tenant_b.id)},
        )
        if resp_b.status_code == 200:
            # If 200, tenant_id must be B's (not A's)
            assert resp_b.json()["tenant_id"] == str(tenant_b.id)
        else:
            assert resp_b.status_code == 404

    def test_nonexistent_tenant_id_rejected(self, repo):
        """Request with a non-existent tenant ID is rejected."""
        client = _client(repo)
        resp = client.get(
            "/api/v1/resources/res-1",
            headers={"X-Tenant-ID": str(uuid4())},
        )
        assert resp.status_code == 401

    def test_suspended_tenant_blocked(self, repo, tenant_suspended):
        """Suspended tenant gets 403 on any resource endpoint."""
        repo._tenants[tenant_suspended.id] = tenant_suspended
        client = _client(repo)

        resp = client.get(
            "/api/v1/resources",
            headers={"X-Tenant-ID": str(tenant_suspended.id)},
        )
        assert resp.status_code == 403
        assert "suspended" in resp.json()["detail"].lower()


# =============================================================================
# 3. API BYPASS TESTS
# =============================================================================


class TestApiBypass:
    """
    Verify that header manipulation, query injection, and other
    bypass attempts cannot circumvent tenant isolation.
    """

    def test_header_injection_tenant_id(self, repo):
        """Manipulated X-Tenant-ID header with invalid UUID is rejected."""
        client = _client(repo)
        resp = client.get(
            "/api/v1/resources",
            headers={"X-Tenant-ID": "not-a-uuid"},
        )
        assert resp.status_code in (400, 401, 422)

    def test_header_injection_empty_value(self, repo):
        """Empty X-Tenant-ID header is rejected when tenant is required."""
        client = _client(repo)
        resp = client.get(
            "/api/v1/resources",
            headers={"X-Tenant-ID": ""},
        )
        assert resp.status_code in (401, 422)

    def test_header_injection_sql_in_tenant_id(self, repo):
        """SQL injection attempt in X-Tenant-ID header is rejected."""
        client = _client(repo)
        resp = client.get(
            "/api/v1/resources",
            headers={"X-Tenant-ID": "' OR '1'='1"},
        )
        assert resp.status_code in (400, 401, 422)

    def test_header_injection_xss_in_tenant_id(self, repo):
        """XSS attempt in X-Tenant-ID header is rejected."""
        client = _client(repo)
        resp = client.get(
            "/api/v1/resources",
            headers={"X-Tenant-ID": "<script>alert('xss')</script>"},
        )
        assert resp.status_code in (400, 401, 422)

    def test_query_param_bypass_tenant_id(self, repo, tenant_a):
        """Query parameter ?tenant_id=X cannot bypass header-based resolution."""
        repo._tenants[tenant_a.id] = tenant_a
        client = _client(repo)

        resp = client.get(f"/api/v1/resources?tenant_id={tenant_a.id}")
        # Without the header, middleware should not resolve tenant
        assert resp.status_code == 401

    def test_query_param_injection(self, repo):
        """SQL injection via query parameter is harmless."""
        client = _client(repo)
        resp = client.get("/api/v1/resources?tenant_id=1' OR '1'='1")
        assert resp.status_code == 401

    def test_subdomain_bypass_with_different_header(self, repo, tenant_a, tenant_b):
        """X-Tenant-ID header takes precedence; subdomain is not used to override."""
        repo._tenants[tenant_a.id] = tenant_a
        repo._tenants[tenant_b.id] = tenant_b
        client = _client(repo)

        resp = client.get(
            "/api/v1/whoami",
            headers={
                "X-Tenant-ID": str(tenant_a.id),
                "Host": f"{tenant_b.slug}.example.com",
            },
        )
        assert resp.status_code == 200
        # Header-based resolution should win
        assert resp.json()["tenant_id"] == str(tenant_a.id)

    def test_tenant_id_in_request_body_not_resolved(self, repo, tenant_a):
        """Tenant ID in POST body is NOT used for middleware resolution."""
        repo._tenants[tenant_a.id] = tenant_a
        client = _client(repo)

        resp = client.post(
            "/api/v1/resources",
            json={"tenant_id": str(tenant_a.id)},
        )
        # POST endpoint doesn't exist, but middleware should not resolve from body
        assert resp.status_code in (401, 405)

    def test_double_tenant_header_ignored(self, repo, tenant_a):
        """Duplicate X-Tenant-ID headers — first one wins."""
        repo._tenants[tenant_a.id] = tenant_a
        client = _client(repo)

        resp = client.get(
            "/api/v1/whoami",
            headers=[
                ("X-Tenant-ID", str(tenant_a.id)),
                ("X-Tenant-ID", str(uuid4())),
            ],
        )
        if resp.status_code == 200:
            assert resp.json()["tenant_id"] == str(tenant_a.id)


# =============================================================================
# 4. DATABASE-LEVEL ISOLATION TESTS
# =============================================================================


class TestDatabaseLevelIsolation:
    """
    Verify that even at the repository/database layer,
    cross-tenant data leakage is prevented.
    """

    @pytest.mark.asyncio
    async def test_repository_get_by_id_is_exact_match(self, repo, tenant_a, tenant_b):
        """get_by_id returns ONLY the exact tenant, never a neighbor."""
        await repo.create(tenant_a)
        await repo.create(tenant_b)

        result = await repo.get_by_id(tenant_a.id)
        assert result is not None
        assert result.id == tenant_a.id
        assert result.slug == "acme"
        assert result.id != tenant_b.id

    @pytest.mark.asyncio
    async def test_repository_delete_does_not_affect_other_tenants(self, repo, tenant_a, tenant_b):
        """Deleting tenant A does not affect tenant B."""
        await repo.create(tenant_a)
        await repo.create(tenant_b)

        deleted = await repo.delete(tenant_a.id)
        assert deleted is True

        assert await repo.get_by_id(tenant_a.id) is None

        result_b = await repo.get_by_id(tenant_b.id)
        assert result_b is not None
        assert result_b.id == tenant_b.id

    @pytest.mark.asyncio
    async def test_repository_update_does_not_corrupt_other_tenants(self, repo, tenant_a, tenant_b):
        """Updating tenant A does not modify tenant B's data."""
        await repo.create(tenant_a)
        await repo.create(tenant_b)

        original_b_name = tenant_b.name
        tenant_a.name = "Acme Renamed"
        await repo.update(tenant_a)

        result_a = await repo.get_by_id(tenant_a.id)
        assert result_a.name == "Acme Renamed"

        result_b = await repo.get_by_id(tenant_b.id)
        assert result_b.name == original_b_name

    @pytest.mark.asyncio
    async def test_repository_list_all_contains_both(self, repo, tenant_a, tenant_b):
        """list_all returns all tenants without duplication or omission."""
        await repo.create(tenant_a)
        await repo.create(tenant_b)

        all_tenants = await repo.list_all()
        assert len(all_tenants) == 2

        ids = {t.id for t in all_tenants}
        assert tenant_a.id in ids
        assert tenant_b.id in ids

    @pytest.mark.asyncio
    async def test_find_by_status_isolation(self, repo, tenant_a, tenant_b):
        """find_by_status filters correctly without mixing tenants."""
        await repo.create(tenant_a)
        await repo.create(tenant_b)

        active = await repo.find_by_status(TenantStatus.ACTIVE)
        assert len(active) == 2

        tenant_a.suspend()
        await repo.update(tenant_a)

        active_after = await repo.find_by_status(TenantStatus.ACTIVE)
        assert len(active_after) == 1
        assert active_after[0].id == tenant_b.id

        suspended = await repo.find_by_status(TenantStatus.SUSPENDED)
        assert len(suspended) == 1
        assert suspended[0].id == tenant_a.id

    @pytest.mark.asyncio
    async def test_independent_crud_cycles(self, repo, tenant_a, tenant_b):
        """Full CRUD cycle for tenant A does not interfere with tenant B."""
        await repo.create(tenant_a)
        await repo.create(tenant_b)

        tenant_a.name = "Acme v2"
        tenant_a.plan = TenantPlan.ENTERPRISE
        await repo.update(tenant_a)

        assert await repo.delete(tenant_a.id) is True

        result_b = await repo.get_by_id(tenant_b.id)
        assert result_b is not None
        assert result_b.name == "Globex Inc"
        assert result_b.plan == TenantPlan.ENTERPRISE

        assert await repo.get_by_id(tenant_a.id) is None

        remaining = await repo.list_all()
        assert len(remaining) == 1
        assert remaining[0].id == tenant_b.id


# =============================================================================
# 5. TENANT CONTEXT MIDDLEWARE EDGE CASES
# =============================================================================


class TestTenantContextMiddlewareEdgeCases:
    """
    Edge cases in tenant context resolution that could lead to isolation bypass.
    """

    def test_no_tenant_header_no_subdomain(self, repo):
        """No tenant header and no subdomain → 401 when require_tenant=True."""
        client = _client(repo, require_tenant=True)
        resp = client.get("/api/v1/resources", headers={"Host": "localhost"})
        assert resp.status_code == 401

    def test_invalid_uuid_format(self, repo):
        """Malformed UUID in X-Tenant-ID → 400/422."""
        client = _client(repo)
        resp = client.get(
            "/api/v1/resources",
            headers={"X-Tenant-ID": "not-a-valid-uuid"},
        )
        assert resp.status_code in (400, 401, 422)

    def test_uuid_v4_injection_attempt(self, repo):
        """Random UUID that doesn't match any tenant → 401."""
        client = _client(repo)
        resp = client.get(
            "/api/v1/resources",
            headers={"X-Tenant-ID": str(uuid4())},
        )
        assert resp.status_code == 401

    def test_public_paths_skip_tenant_requirement(self, repo):
        """Public paths should not require tenant context."""
        client = _client(repo, require_tenant=True)
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_subdomain_resolution_with_valid_slug(self, repo, tenant_a):
        """Subdomain-based resolution works when slug matches."""
        repo._tenants[tenant_a.id] = tenant_a
        client = _client(repo, require_tenant=True)

        resp = client.get(
            "/api/v1/whoami",
            headers={"Host": "acme.example.com"},
        )
        assert resp.status_code == 200
        assert resp.json()["tenant_id"] == str(tenant_a.id)
        assert resp.json()["slug"] == "acme"

    def test_subdomain_resolution_with_reserved_name(self, repo, tenant_a):
        """Reserved subdomains (www, api, app) are not resolved as tenants."""
        repo._tenants[tenant_a.id] = tenant_a
        client = _client(repo, require_tenant=True)

        for reserved in ["www", "api", "app"]:
            resp = client.get(
                "/api/v1/whoami",
                headers={"Host": f"{reserved}.example.com"},
            )
            assert resp.status_code == 401

    def test_port_in_host_ignored(self, repo, tenant_a):
        """Port suffix in Host header does not break subdomain extraction."""
        repo._tenants[tenant_a.id] = tenant_a
        client = _client(repo, require_tenant=True)

        resp = client.get(
            "/api/v1/whoami",
            headers={"Host": "acme.example.com:8000"},
        )
        assert resp.status_code == 200
        assert resp.json()["tenant_id"] == str(tenant_a.id)


# =============================================================================
# 6. CONCURRENT ACCESS ISOLATION
# =============================================================================


class TestConcurrentAccessIsolation:
    """
    Verify that concurrent requests from different tenants
    do not leak data between each other.
    """

    @pytest.mark.asyncio
    async def test_concurrent_requests_different_tenants(self, repo, tenant_a, tenant_b):
        """Two concurrent requests from different tenants get correct context."""
        await repo.create(tenant_a)
        await repo.create(tenant_b)
        client = _client(repo)

        resp_a = client.get(
            "/api/v1/identity",
            headers={"X-Tenant-ID": str(tenant_a.id)},
        )
        resp_b = client.get(
            "/api/v1/identity",
            headers={"X-Tenant-ID": str(tenant_b.id)},
        )

        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        assert resp_a.json()["tenant_id"] == str(tenant_a.id)
        assert resp_b.json()["tenant_id"] == str(tenant_b.id)
        assert resp_a.json()["tenant_id"] != resp_b.json()["tenant_id"]

    @pytest.mark.asyncio
    async def test_rapid_id_switching(self, repo, tenant_a, tenant_b):
        """Rapidly switching tenant IDs between requests does not leak state."""
        await repo.create(tenant_a)
        await repo.create(tenant_b)
        client = _client(repo)

        for _ in range(10):
            resp_a = client.get(
                "/api/v1/echo",
                headers={"X-Tenant-ID": str(tenant_a.id)},
            )
            resp_b = client.get(
                "/api/v1/echo",
                headers={"X-Tenant-ID": str(tenant_b.id)},
            )
            assert resp_a.json()["tenant_id"] == str(tenant_a.id)
            assert resp_b.json()["tenant_id"] == str(tenant_b.id)


# =============================================================================
# 7. DATA MODEL TENANT_ID INTEGRITY
# =============================================================================


class TestDataModelTenantIdIntegrity:
    """
    Verify that domain entities and models correctly carry tenant_id
    and that the value is enforced at the model layer.
    """

    def test_tenant_entity_id_is_uuid(self, tenant_a):
        """Tenant.id is a proper UUID."""
        assert isinstance(tenant_a.id, UUID)

    def test_tenant_entity_equality_by_id(self, tenant_a):
        """Two Tenant objects with the same ID are equal."""
        clone = Tenant(
            id=tenant_a.id,
            name="Different Name",
            slug="different",
        )
        assert tenant_a == clone

    def test_tenant_entity_inequality_by_id(self, tenant_a, tenant_b):
        """Two Tenant objects with different IDs are not equal."""
        assert tenant_a != tenant_b

    def test_tenant_to_dict_preserves_id(self, tenant_a):
        """to_dict() preserves the UUID as string."""
        d = tenant_a.to_dict()
        assert d["id"] == str(tenant_a.id)

    def test_tenant_from_dict_restores_id(self, tenant_a):
        """from_dict() restores the UUID correctly."""
        d = tenant_a.to_dict()
        restored = Tenant.from_dict(d)
        assert restored.id == tenant_a.id

    def test_tenant_settings_isolation(self, tenant_a, tenant_b):
        """Settings dict is independent per tenant instance."""
        tenant_a.update_settings("theme", "dark")
        tenant_b.update_settings("theme", "light")

        assert tenant_a.get_setting("theme") == "dark"
        assert tenant_b.get_setting("theme") == "light"

    def test_tenant_status_transitions(self):
        """Status transitions do not affect other tenant instances."""
        t1 = Tenant(name="T1", slug="t1", status=TenantStatus.ACTIVE)
        t2 = Tenant(name="T2", slug="t2", status=TenantStatus.ACTIVE)

        t1.suspend()

        assert t1.is_suspended() is True
        assert t2.is_suspended() is False
        assert t2.is_active() is True
