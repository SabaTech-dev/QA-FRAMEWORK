"""Runtime contract tests for the browser-use 0.13 integration.

These tests FORCE the real import of browser_use (the import is never mocked)
and exercise the 0.13 Agent API exactly the way ``BrowserUseService`` uses it.

Rationale (card fbe1e86d, Dependabot PR #159): the service imports browser_use
lazily inside ``_execute_browser_agent``, so the rest of the suite stays green
even when the installed library no longer matches the code. These tests are the
canary: if the pinned ``browser-use==0.13.*`` surface drifts, they fail loudly
instead of breaking in production at task-execution time.

No network access and no real browser launch is required: the LLM key
verification is skipped via ``SKIP_LLM_API_KEY_VERIFICATION`` and agents are
only constructed, never run.
"""

import inspect
from importlib.metadata import PackageNotFoundError, version

import pytest
from pydantic import SecretStr

from config import settings
from services.ai.browser_use_service import BrowserUseService

FAKE_GROQ_KEY = (
    "gsk-test-fake-0123456789abcdef"  # gitleaks:allow - synthetic fixture, not a real secret
)


def _browser_use_version() -> str:
    try:
        return version("browser-use")
    except PackageNotFoundError:  # pragma: no cover - CI always installs the dep
        pytest.fail("browser-use is not installed in this environment")


def _service(monkeypatch) -> BrowserUseService:
    """Build the service against a deterministic groq configuration."""
    monkeypatch.setattr(settings, "BROWSER_USE_LLM_PROVIDER", "groq")
    monkeypatch.setattr(settings, "BROWSER_USE_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setattr(settings, "GROQ_API_KEY", SecretStr(FAKE_GROQ_KEY))
    return BrowserUseService()


class TestBrowserUse013RuntimeContract:
    """The pinned dependency and its public surface must stay on the 0.13 API."""

    def test_browser_use_013_is_installed(self):
        installed = _browser_use_version()
        assert installed.startswith("0.13."), (
            f"expected browser-use 0.13.x, got {installed}; the Agent construction path in "
            "browser_use_service.py must be re-validated before changing the pin"
        )

    def test_agent_constructor_has_no_browser_config_parameter(self):
        from browser_use import Agent  # real import, never mocked

        params = inspect.signature(Agent.__init__).parameters
        assert "browser_profile" in params
        assert (
            "browser_config" not in params
        ), "browser_config was removed in browser-use 0.13; pass browser_profile=BrowserProfile(...) instead"

    def test_agent_run_has_no_url_parameter(self):
        from browser_use import Agent  # real import, never mocked

        params = inspect.signature(Agent.run).parameters
        assert "max_steps" in params
        assert (
            "url" not in params
        ), "browser-use 0.13 takes the start URL from the task text, not run()"


class TestBrowserUseServiceLLM:
    """The LLM must be browser-use's native ChatGroq (BaseChatModel protocol)."""

    def test_get_llm_returns_browser_use_native_chat_groq(self, monkeypatch):
        svc = _service(monkeypatch)
        llm = svc._get_llm()

        from browser_use import ChatGroq  # real import, never mocked

        assert isinstance(llm, ChatGroq)
        assert llm.model == "llama-3.3-70b-versatile"

    def test_get_llm_unsupported_provider_raises(self, monkeypatch):
        monkeypatch.setattr(settings, "BROWSER_USE_LLM_PROVIDER", "openai")
        svc = BrowserUseService()
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            svc._get_llm()


class TestBrowserUseServiceBuildsAgent:
    """_build_agent must construct a real 0.13 Agent (profile + URL-in-task)."""

    @pytest.fixture(autouse=True)
    def _skip_llm_verification(self, monkeypatch):
        # Construction-time key verification would hit the network; skip it.
        monkeypatch.setenv("SKIP_LLM_API_KEY_VERIFICATION", "true")

    def test_compose_task_embeds_the_start_url(self, monkeypatch):
        svc = _service(monkeypatch)
        composed = svc._compose_task("Check the pricing page.", "https://example.com/pricing")
        assert "Check the pricing page." in composed
        assert "https://example.com/pricing" in composed

    def test_build_agent_real_construction_headless(self, monkeypatch):
        svc = _service(monkeypatch)
        agent = svc._build_agent(
            "Check the pricing page.", "https://example.com/pricing", {"headless": True}
        )

        from browser_use import Agent  # real class for the isinstance check

        assert isinstance(agent, Agent)
        assert agent.browser_profile.headless is True
        # 0.13 extracts the start URL from the task text (directly_open_url=True default)
        assert agent.initial_url == "https://example.com/pricing"

    def test_build_agent_headless_defaults_to_true_without_options(self, monkeypatch):
        svc = _service(monkeypatch)
        agent = svc._build_agent("Check the docs.", "https://example.com/docs", options=None)
        assert agent.browser_profile.headless is True

    def test_build_agent_can_run_headful(self, monkeypatch):
        svc = _service(monkeypatch)
        agent = svc._build_agent("Check the docs.", "https://example.com/docs", {"headless": False})
        assert agent.browser_profile.headless is False
