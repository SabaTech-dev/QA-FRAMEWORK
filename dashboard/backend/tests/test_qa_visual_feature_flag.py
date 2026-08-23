"""Feature-flag tests for the QA Visual router mount (Fase C — S-1R).

The dashboard is multi-tenant without roles and the QA Visual report store
is global, so mounting the router exposes a cross-tenant BOLA surface
(CVSS 5.4). Until reports are scoped by owner (or roles exist), the router
must stay UNMOUNTED in deploys unless ``QA_VISUAL_ENABLED=1`` is set
explicitly:

- flag unset  -> every qa-visual endpoint returns 404 (router not mounted)
- flag = "1"  -> router mounted behind JWT auth: 401 without credentials

``main`` builds the app at import time, so each case reloads the module
under a controlled environment. The wiring tests reload it back with the
flag on; ordering between both files is therefore irrelevant.
"""

import importlib

from fastapi.testclient import TestClient

REPORTS_PATH = "/api/v1/qa-visual/reports"


def _client_with_fresh_main() -> TestClient:
    import main as dashboard_main

    return TestClient(importlib.reload(dashboard_main).app)


class TestQAVisualRouterFeatureFlag:
    def test_router_not_mounted_without_flag(self, monkeypatch):
        monkeypatch.delenv("QA_VISUAL_ENABLED", raising=False)
        client = _client_with_fresh_main()
        assert client.get(REPORTS_PATH).status_code == 404

    def test_router_mounted_with_flag_returns_401_without_credentials(self, monkeypatch):
        monkeypatch.setenv("QA_VISUAL_ENABLED", "1")
        client = _client_with_fresh_main()
        assert client.get(REPORTS_PATH).status_code == 401
