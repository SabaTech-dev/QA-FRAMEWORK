"""Wiring tests for the accuracy router in the dashboard (card c9825844).

Contracts verified on the REAL app and on a hand-built app:

- Feature flag: ACCURACY_TESTING_ENABLED off -> endpoints 404 (unmounted).
- Fail-closed L-1: enabling the flag without ACCURACY_SPLIT_SECRET must
  crash the mount (ValueError) instead of collapsing tenants into a shared
  holdout namespace.
- Auth: with the router mounted, unauthenticated requests are rejected 401.
- Happy path: a hand-built app with an injected principal proves the
  owner-scoped aggregate-only behaviour without any AI gateway call.
"""

import importlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.infrastructure.accuracy_testing.endpoint import create_accuracy_router
from src.infrastructure.accuracy_testing.security import AccuracyPrincipal

ACCURACY_PATHS = [
    "/accuracy/benchmarks",
    "/accuracy/sessions/some-id",
    "/accuracy/sessions/some-id/holdout",
]


def _synthetic_benchmarks(n: int = 10):
    from src.domain.accuracy_testing.entities import AccuracyBenchmark

    return [
        AccuracyBenchmark(
            id=f"synth-{i:02d}",
            name=f"synthetic-{i}",
            question=f"SYNTH-QUESTION-{i:02d} what is the answer?",
            ground_truth=f"SYNTH-TRUTH-{i:02d} the answer is {i}",
        )
        for i in range(n)
    ]


class _EchoProvider:
    def get_response(self, prompt: str, model: str = "") -> str:
        return "According to the ruling, liability depends on the defect."


@pytest.fixture()
def main_app_unmounted():
    mp = pytest.MonkeyPatch()
    mp.delenv("ACCURACY_TESTING_ENABLED", raising=False)
    mp.delenv("ACCURACY_SPLIT_SECRET", raising=False)
    import main as dashboard_main

    app = importlib.reload(dashboard_main).app
    yield app
    mp.undo()


@pytest.fixture()
def main_app_mounted():
    mp = pytest.MonkeyPatch()
    mp.setenv("ACCURACY_TESTING_ENABLED", "1")
    mp.setenv("ACCURACY_SPLIT_SECRET", "wiring-test-secret")
    import main as dashboard_main

    app = importlib.reload(dashboard_main).app
    yield app
    mp.undo()


def test_accuracy_unmounted_without_flag(main_app_unmounted):
    client = TestClient(main_app_unmounted)
    for path in ACCURACY_PATHS:
        assert client.get(path).status_code == 404, path


def test_accuracy_mounted_rejects_unauthenticated(main_app_mounted):
    client = TestClient(main_app_mounted)
    resp = client.get("/accuracy/benchmarks")
    assert resp.status_code == 401


def test_accuracy_mount_fails_closed_without_secret():
    mp = pytest.MonkeyPatch()
    mp.setenv("ACCURACY_TESTING_ENABLED", "1")
    mp.delenv("ACCURACY_SPLIT_SECRET", raising=False)
    import main as dashboard_main

    with pytest.raises(ValueError, match="split_secret"):
        importlib.reload(dashboard_main)
    mp.undo()


@pytest.fixture()
def main_app_mounted_with_provider():
    mp = pytest.MonkeyPatch()
    mp.setenv("ACCURACY_TESTING_ENABLED", "1")
    mp.setenv("ACCURACY_SPLIT_SECRET", "wiring-test-secret")
    mp.setenv("ACCURACY_PROVIDER_API_KEY", "wiring-test-key")
    import main as dashboard_main

    app = importlib.reload(dashboard_main).app
    yield app
    mp.undo()


def test_accuracy_mount_with_provider_env_assembles(main_app_mounted_with_provider):
    """Card 2f9afe89: with a provider API key in the env the dashboard
    mounts cleanly with the response provider wired (no import/mount error;
    auth still gates the endpoints)."""
    client = TestClient(main_app_mounted_with_provider)
    # Mounted (not 404) and still auth-gated.
    assert client.get("/accuracy/benchmarks").status_code == 401
    resp = client.post("/accuracy/sessions", json={"ai_model": "m"})
    assert resp.status_code == 401
    # Not the provider-less 503: the request never reached the handler
    # because auth rejects it first, proving the router (and provider
    # import) assembled without error.
    assert resp.status_code != 503


def test_vendored_factory_returns_none_without_key(monkeypatch):
    """The vendored copy exposes the env factory and honours fail-closed
    by omission: no key -> None (endpoint keeps its explicit 503)."""
    from src.infrastructure.accuracy_testing.llm_gateway_provider import (
        create_response_provider_from_env,
    )

    monkeypatch.delenv("ACCURACY_PROVIDER_API_KEY", raising=False)
    monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)
    assert create_response_provider_from_env() is None


def test_vendored_router_happy_path_owner_scoped():
    app = FastAPI()
    app.include_router(
        create_accuracy_router(
            principal_dependency=lambda: AccuracyPrincipal(owner="tenant-A"),
            benchmarks=_synthetic_benchmarks(),
            response_provider=_EchoProvider(),
            split_secret="wiring-test-secret",
        )
    )
    client = TestClient(app)

    created = client.post("/accuracy/sessions", json={"ai_model": "test"})
    assert created.status_code == 200, created.text
    body = created.json()

    # AC2: aggregates only — no holdout serialization anywhere.
    assert "holdout_benchmarks" not in _deep_keys(body)
    assert "ground_truth" not in _deep_keys(body)
    assert set(body["holdout_summary"].keys()) == {
        "holdout_count",
        "pass_rate",
        "average_score",
        "hallucination_count",
        "accuracy_level",
        "evaluated_at",
    }

    holdout = client.get(f"/accuracy/sessions/{body['id']}/holdout")
    assert holdout.status_code == 200
    assert "holdout_count" in holdout.json()


def _deep_keys(obj) -> set:
    keys = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(k)
            keys |= _deep_keys(v)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            keys |= _deep_keys(item)
    return keys
