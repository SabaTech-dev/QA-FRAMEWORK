"""Contract tests for the playwright port of BrowserUseService (card c478c23a).

Replaces the browser-use 0.13 runtime canary. The canary contract is kept:
these tests FORCE the real import of the service module (never mocked) and
verify the port surface: no browser-use imports anywhere, same public
interface, LiteLLM routing, and JSON action parsing.
"""

import json

import pytest

import importlib

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]  # dashboard/backend

from services.ai.browser_use_service import (  # noqa: E402
    BrowserAutomationError,
    BrowserUseService,
)


def test_no_browser_use_dependency_in_service_source():
    """The ported service must not reference browser-use or ChatGroq anymore."""
    source = (BACKEND_ROOT / "services" / "ai" / "browser_use_service.py").read_text()
    # the browser-use LIBRARY must be gone (the BrowserUseTask DB model name stays)
    assert "import browser_use" not in source
    assert "from browser_use" not in source
    assert "ChatGroq" not in source


def test_requirements_have_no_browser_use():
    """browser-use must be gone from requirements (AC 2 of card c478c23a)."""
    reqs = (BACKEND_ROOT / "requirements.txt").read_text().splitlines()
    assert not any(line.strip().startswith("browser-use") for line in reqs)
    # playwright must remain the engine
    assert any(line.strip().startswith("playwright") for line in reqs)


def test_requirements_have_no_pillow_pin():
    """No conflicting pillow pin may remain (AC 3 of card c478c23a)."""
    reqs = (BACKEND_ROOT / "requirements.txt").read_text().splitlines()
    assert not any(line.strip().startswith("pillow") for line in reqs)


def test_public_interface_preserved():
    """Same public surface as the browser-use era (routes keep working)."""
    svc = BrowserUseService()
    assert hasattr(svc, "execute_task")
    assert hasattr(svc, "get_status")
    assert hasattr(svc, "active_tasks")
    # _compose_task keeps embedding the URL (compat with old callers)
    assert "https://example.com" in BrowserUseService._compose_task("t", "https://example.com")


@pytest.mark.asyncio
async def test_llm_routes_through_litellm(monkeypatch):
    """_ask_llm must hit the LiteLLM gateway, not Groq directly."""
    svc = BrowserUseService()
    captured = {}

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "{\"action\": \"done\", \"text\": \"ok\"}"}}]}

    class FakeClient:
        def __init__(self, **kw):
            captured.update(kw)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **kw):
            captured["url"] = url
            captured["payload"] = kw.get("json")
            return FakeResp()

    import services.ai.browser_use_service as mod
    monkeypatch.setattr(mod.httpx, "AsyncClient", FakeClient)
    out = await svc._ask_llm([{"role": "user", "content": "hi"}])
    assert out.startswith("{")
    assert captured["url"].endswith("/chat/completions")
    assert "127.0.0.1:4000" in captured["url"]
    assert captured["payload"]["model"]


@pytest.mark.asyncio
async def test_plan_step_parses_json_action():
    svc = BrowserUseService()

    async def fake_ask(messages):
        return 'blah {"action": "click", "selector": "#buy", "text": ""} trailing'

    svc._ask_llm = fake_ask
    action = await svc._plan_step("buy item", "URL: x\nTitle: y", [])
    assert action["action"] == "click"
    assert action["selector"] == "#buy"


@pytest.mark.asyncio
async def test_plan_step_rejects_non_json():
    svc = BrowserUseService()

    async def fake_ask(messages):
        return "I cannot comply"

    svc._ask_llm = fake_ask
    with pytest.raises(BrowserAutomationError):
        await svc._plan_step("t", "s", [])
