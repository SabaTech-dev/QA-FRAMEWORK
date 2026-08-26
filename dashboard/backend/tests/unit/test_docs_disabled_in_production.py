"""API docs must be disabled in production (card 2972521c, finding F3).

main.py mounted /api/v1/docs, /api/v1/openapi.json and /api/v1/redoc
unconditionally — verified live as 200 on the public staging. Contract:

- development: docs mounted (200) so local DX is unchanged;
- production: docs/openapi/redoc absent (404), app still serves traffic;
- production boot without an explicit SECRET_KEY crashes (fail closed).
"""

import importlib

import pytest
from fastapi.testclient import TestClient

DOCS_PATHS = ("/api/v1/docs", "/api/v1/openapi.json", "/api/v1/redoc")

PROD_ENV = {
    "ENVIRONMENT": "production",
    "SECRET_KEY": "docs-test-signing-key-0123456789abcdef",
    "DATABASE_URL": "postgresql://u:p@h:5432/d",
}


@pytest.fixture()
def dev_app(monkeypatch):
    for var in ("ENVIRONMENT", "QA_VISUAL_ENABLED", "ACCURACY_TESTING_ENABLED"):
        monkeypatch.delenv(var, raising=False)
    import config as dashboard_config
    import main as dashboard_main

    importlib.reload(dashboard_config)
    app = importlib.reload(dashboard_main).app
    yield app
    importlib.reload(dashboard_config)
    importlib.reload(dashboard_main)


@pytest.fixture()
def production_app(monkeypatch):
    for var, value in PROD_ENV.items():
        monkeypatch.setenv(var, value)
    import config as dashboard_config
    import main as dashboard_main

    importlib.reload(dashboard_config)
    app = importlib.reload(dashboard_main).app
    yield app
    monkeypatch.undo()
    importlib.reload(dashboard_config)
    importlib.reload(dashboard_main)


@pytest.fixture()
def dev_client(dev_app):
    return TestClient(dev_app)


@pytest.fixture()
def prod_client(production_app):
    return TestClient(production_app)


class TestDocsInDevelopment:
    @pytest.mark.parametrize("path", DOCS_PATHS)
    def test_docs_mounted_in_dev(self, dev_client, path):
        assert dev_client.get(path).status_code == 200


class TestDocsInProduction:
    @pytest.mark.parametrize("path", DOCS_PATHS)
    def test_docs_absent_in_production(self, prod_client, path):
        assert prod_client.get(path).status_code == 404

    def test_api_still_serves_traffic_in_production(self, prod_client):
        assert prod_client.get("/health").status_code == 200


class TestProductionBootCrashesWithoutSecret:
    def test_config_reload_without_secret_raises(self, monkeypatch):
        for var, value in PROD_ENV.items():
            monkeypatch.setenv(var, value)
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        import config as dashboard_config

        with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
            importlib.reload(dashboard_config)
        monkeypatch.undo()
        importlib.reload(dashboard_config)
