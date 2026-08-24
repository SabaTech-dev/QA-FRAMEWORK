"""API wiring contracts for the accuracy_testing module (card c9825844).

Covers the three security contracts:

- L-1 (salt per-tenant): the API derives the split salt server-side from the
  authenticated tenant. A client cannot choose, send, or observe the salt.
- L-2 (to_dict_full admin-only + owner-scoping): ground_truth/tenant_id are
  only served to admins; resources are scoped to the requesting owner.
- AC2 (canary anti-leak): API endpoints serialise benchmarks via to_dict()
  and holdout results via HoldoutSummary ONLY — never split.holdout_benchmarks
  nor to_dict_full().
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.domain.accuracy_testing.entities import AccuracyBenchmark
from src.domain.accuracy_testing.splitting import SplitPolicy, split_benchmarks
from src.infrastructure.accuracy_testing.security import AccuracyPrincipal, derive_tenant_salt

# ------------------------------------------------------------------------
# Fixtures: synthetic catalog with canary strings
# ------------------------------------------------------------------------

SPLIT_SECRET = "unit-test-secret"


def _synthetic_benchmarks(n: int = 10) -> list:
    return [
        AccuracyBenchmark(
            id=f"synth-{i:02d}",
            name=f"synthetic-{i}",
            question=f"SYNTH-QUESTION-{i:02d} what is the answer?",
            ground_truth=f"SYNTH-TRUTH-{i:02d} the answer is {i}",
            key_points=[f"point-{i}"],
            tenant_id=None,
        )
        for i in range(n)
    ]


class FakeResponseProvider:
    """Deterministic IResponseProvider: same response for every question."""

    def get_response(self, prompt: str, model: str = "") -> str:
        return "According to the ruling, liability depends on the defect."

    __call__ = get_response


def _make_client(
    principal: AccuracyPrincipal,
    benchmarks=None,
    provider=None,
    secret: str = SPLIT_SECRET,
) -> TestClient:
    from src.infrastructure.accuracy_testing.endpoint import create_accuracy_router

    app = FastAPI()
    app.include_router(
        create_accuracy_router(
            principal_dependency=lambda: principal,
            benchmarks=benchmarks if benchmarks is not None else _synthetic_benchmarks(),
            response_provider=provider,
            split_secret=secret,
        )
    )
    return TestClient(app)


def _tenant_eval_ids(benchmarks, tenant_id: str, secret: str = SPLIT_SECRET) -> set:
    """Expected eval-set ids for a tenant, computed independently of the API."""
    salt = derive_tenant_salt(secret, tenant_id)
    split = split_benchmarks(benchmarks, SplitPolicy(holdout_ratio=0.2, salt=salt))
    return {b.id for b in split.eval_benchmarks}


TENANT_A = AccuracyPrincipal(owner="tenant-A", is_admin=False)
TENANT_B = AccuracyPrincipal(owner="tenant-B", is_admin=False)
ADMIN = AccuracyPrincipal(owner="admin-0", is_admin=True)


# ------------------------------------------------------------------------
# L-1: salt per-tenant
# ------------------------------------------------------------------------


class TestL1SaltPerTenant:
    def test_client_supplied_salt_in_body_rejected(self):
        """Request bodies must not accept a salt field (extra=forbid)."""
        client = _make_client(TENANT_A, provider=FakeResponseProvider())
        resp = client.post("/accuracy/sessions", json={"salt": "evil", "ai_model": "m"})
        assert resp.status_code == 422

    def test_two_tenants_get_different_eval_sets(self):
        """Same catalog, different tenants -> different visible (eval) sets."""
        benchmarks = _synthetic_benchmarks()
        client_a = _make_client(TENANT_A, benchmarks=benchmarks)
        client_b = _make_client(TENANT_B, benchmarks=benchmarks)

        ids_a = {b["id"] for b in client_a.get("/accuracy/benchmarks").json()}
        ids_b = {b["id"] for b in client_b.get("/accuracy/benchmarks").json()}

        assert ids_a == _tenant_eval_ids(benchmarks, "tenant-A")
        assert ids_b == _tenant_eval_ids(benchmarks, "tenant-B")
        assert ids_a != ids_b, "tenants must not share holdout membership"

    def test_salt_derivation_is_deterministic_and_scoped(self):
        assert derive_tenant_salt(SPLIT_SECRET, "tenant-A") == derive_tenant_salt(
            SPLIT_SECRET, "tenant-A"
        )
        assert derive_tenant_salt(SPLIT_SECRET, "tenant-A") != derive_tenant_salt(
            SPLIT_SECRET, "tenant-B"
        )
        assert derive_tenant_salt(SPLIT_SECRET, "tenant-A") != derive_tenant_salt(
            "other-secret", "tenant-A"
        )


# ------------------------------------------------------------------------
# L-2: to_dict_full admin-only + owner-scoping
# ------------------------------------------------------------------------


class TestL2AuthAndScoping:
    def test_benchmark_detail_non_admin_has_no_sensitive_keys(self):
        client = _make_client(TENANT_A)
        listing = client.get("/accuracy/benchmarks").json()
        assert listing, "tenant must see its eval set"
        bench_id = listing[0]["id"]

        detail = client.get(f"/accuracy/benchmarks/{bench_id}")
        assert detail.status_code == 200
        assert "ground_truth" not in detail.json()
        assert "tenant_id" not in detail.json()

    def test_benchmark_detail_admin_gets_full_view(self):
        client = _make_client(ADMIN)
        detail = client.get("/accuracy/benchmarks/synth-00")
        assert detail.status_code == 200
        assert "ground_truth" in detail.json()
        assert "tenant_id" in detail.json()

    def test_holdout_benchmark_hidden_from_tenant(self):
        """A benchmark in the tenant's holdout set must 404 for that tenant."""
        benchmarks = _synthetic_benchmarks()
        client = _make_client(TENANT_A, benchmarks=benchmarks)
        all_ids = {b.id for b in benchmarks}
        eval_ids = _tenant_eval_ids(benchmarks, "tenant-A")
        holdout_ids = all_ids - eval_ids

        for hid in holdout_ids:
            assert client.get(f"/accuracy/benchmarks/{hid}").status_code == 404

    def test_session_isolated_between_tenants(self):
        client_a = _make_client(TENANT_A, provider=FakeResponseProvider())
        client_b = _make_client(TENANT_B, provider=FakeResponseProvider())

        created = client_a.post("/accuracy/sessions", json={"ai_model": "test-model"})
        assert created.status_code == 200, created.text
        session_id = created.json()["id"]

        assert client_b.get(f"/accuracy/sessions/{session_id}").status_code == 404
        assert client_b.get(f"/accuracy/sessions/{session_id}/holdout").status_code == 404
        assert client_a.get(f"/accuracy/sessions/{session_id}").status_code == 200

    def test_unauthenticated_rejected(self):
        from fastapi import HTTPException, status

        from src.infrastructure.accuracy_testing.endpoint import create_accuracy_router

        def _raise_401():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no token")

        app = FastAPI()
        app.include_router(
            create_accuracy_router(
                principal_dependency=_raise_401,
                split_secret=SPLIT_SECRET,
            )
        )
        resp = TestClient(app).get("/accuracy/benchmarks")
        assert resp.status_code == 401


# ------------------------------------------------------------------------
# AC2: canary anti-leak at the API layer
# ------------------------------------------------------------------------


class TestAC2CanaryAntiLeak:
    @pytest.fixture()
    def session_setup(self):
        benchmarks = _synthetic_benchmarks()
        client = _make_client(TENANT_A, benchmarks=benchmarks, provider=FakeResponseProvider())
        created = client.post("/accuracy/sessions", json={"ai_model": "test-model"})
        assert created.status_code == 200, created.text
        all_ids = {b.id for b in benchmarks}
        eval_ids = _tenant_eval_ids(benchmarks, "tenant-A")
        holdout = [b for b in benchmarks if b.id in (all_ids - eval_ids)]
        return client, created.json(), holdout, eval_ids

    def test_session_response_has_no_holdout_serialization_keys(self, session_setup):
        _, session_json, _, _ = session_setup
        # The forbidden key: split.holdout_benchmarks must never be serialized
        assert "holdout_benchmarks" not in _deep_keys(session_json)

    def test_holdout_content_absent_from_all_endpoints(self, session_setup):
        client, session_json, holdout, _ = session_setup
        session_id = session_json["id"]
        canaries = [b.question for b in holdout] + [b.ground_truth for b in holdout]
        assert canaries, "test needs a non-empty holdout"

        payloads = [
            client.post("/accuracy/sessions", json={"ai_model": "test-model"}).text,
            client.get(f"/accuracy/sessions/{session_id}").text,
            client.get(f"/accuracy/sessions/{session_id}/holdout").text,
            client.get("/accuracy/benchmarks").text,
        ]
        for payload in payloads:
            for canary in canaries:
                assert canary not in payload, f"holdout content leaked: {canary}"

    def test_evaluations_cover_eval_set_only(self, session_setup):
        _, session_json, holdout, eval_ids = session_setup
        eval_benchmark_ids = {e["benchmark_id"] for e in session_json["evaluations"]}
        assert eval_benchmark_ids
        assert eval_benchmark_ids == eval_ids
        assert not (eval_benchmark_ids & {b.id for b in holdout})

    def test_session_includes_aggregate_holdout_summary(self, session_setup):
        _, session_json, _, _ = session_setup
        summary = session_json["holdout_summary"]
        assert set(summary.keys()) == {
            "holdout_count",
            "pass_rate",
            "average_score",
            "hallucination_count",
            "accuracy_level",
            "evaluated_at",
        }

    def test_holdout_endpoint_returns_aggregates_only(self, session_setup):
        client, session_json, _, _ = session_setup
        resp = client.get(f"/accuracy/sessions/{session_json['id']}/holdout")
        assert resp.status_code == 200
        assert set(resp.json().keys()) == {
            "holdout_count",
            "pass_rate",
            "average_score",
            "hallucination_count",
            "accuracy_level",
            "evaluated_at",
        }


# ------------------------------------------------------------------------
# Response provider wiring (card 2f9afe89)
# ------------------------------------------------------------------------


class _FailingProvider:
    """IResponseProvider whose gateway call fails (raises provider error)."""

    def get_response(self, prompt: str, model: str = "") -> str:
        from src.infrastructure.accuracy_testing.llm_gateway_provider import (
            LLMGatewayProviderError,
        )

        raise LLMGatewayProviderError("Gateway HTTP 500")


class TestProviderFailureMapping:
    def test_provider_failure_maps_to_502(self):
        client = _make_client(TENANT_A, provider=_FailingProvider())
        resp = client.post("/accuracy/sessions", json={"ai_model": "test-model"})
        assert resp.status_code == 502, resp.text

    def test_provider_failure_detail_is_generic(self):
        """CWE-209: the 502 detail must not echo upstream provider internals."""
        client = _make_client(TENANT_A, provider=_FailingProvider())
        resp = client.post("/accuracy/sessions", json={"ai_model": "test-model"})
        assert resp.status_code == 502
        assert "Gateway HTTP 500" not in resp.text


class TestProviderEndpointIntegration:
    """AC1 proof: POST /sessions returns 200 with a REAL provider wired
    through DI (the provider's HTTP client is a MockTransport — no network)."""

    def test_session_200_with_gateway_provider(self):
        import httpx

        from src.infrastructure.accuracy_testing.llm_gateway_provider import (
            LLMGatewayResponseProvider,
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": "MOCK-LLM-ANSWER liability depends on the defect."
                            },
                            "finish_reason": "stop",
                        }
                    ]
                },
            )

        provider = LLMGatewayResponseProvider(
            api_key="integration-key",
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        client = _make_client(TENANT_A, provider=provider)

        created = client.post("/accuracy/sessions", json={"ai_model": ""})
        assert created.status_code == 200, created.text
        body = created.json()

        evaluations = body["evaluations"]
        assert evaluations, "eval-set items must carry detailed evaluations"
        for evaluation in evaluations:
            assert "MOCK-LLM-ANSWER" in evaluation["ai_response"]

        provider.close()


def _deep_keys(obj) -> set:
    """Collect every dict key at any depth (canary: holdout_benchmarks)."""
    keys = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(k)
            keys |= _deep_keys(v)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            keys |= _deep_keys(item)
    return keys
