"""Unit tests for the LLM gateway response provider (card 2f9afe89).

All network interaction is simulated with ``httpx.MockTransport`` — the
provider's HTTP client is injectable, so these tests never touch the
network (same DI pattern as the qa_visual gateway client tests).
"""

import json

import httpx
import pytest

from src.infrastructure.accuracy_testing.llm_gateway_provider import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    LLMGatewayProviderError,
    LLMGatewayResponseProvider,
    create_response_provider_from_env,
)

GATEWAY_ANSWER = "According to the ruling, liability depends on the defect and producer fault."


def ok_response_body(content: str = GATEWAY_ANSWER, model: str = DEFAULT_MODEL) -> dict:
    return {
        "model": model,
        "choices": [
            {"message": {"content": content}, "finish_reason": "stop"},
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 40},
    }


def make_provider(handler, **overrides) -> LLMGatewayResponseProvider:
    defaults = {"api_key": "test-key"}
    defaults.update(overrides)
    transport = httpx.MockTransport(handler)
    return LLMGatewayResponseProvider(http_client=httpx.Client(transport=transport), **defaults)


class TestRequestContract:
    def test_openai_chat_payload_shape(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["payload"] = json.loads(request.content)
            return httpx.Response(200, json=ok_response_body())

        provider = make_provider(handler)
        provider.get_response("Who is liable for an AI defect?")

        payload = captured["payload"]
        assert payload["model"] == DEFAULT_MODEL
        assert payload["max_tokens"] == 1024
        assert payload["temperature"] == pytest.approx(0.1)
        messages = payload["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Who is liable for an AI defect?"

    def test_targets_configured_url(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            return httpx.Response(200, json=ok_response_body())

        provider = make_provider(handler)
        provider.get_response("q")

        assert captured["url"] == DEFAULT_BASE_URL

    def test_custom_base_url_used(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            return httpx.Response(200, json=ok_response_body())

        provider = make_provider(handler, base_url="https://llm.internal/v1/chat/completions")
        provider.get_response("q")

        assert captured["url"] == "https://llm.internal/v1/chat/completions"

    def test_bearer_auth_and_browser_user_agent(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["headers"] = request.headers
            return httpx.Response(200, json=ok_response_body())

        provider = make_provider(handler)
        provider.get_response("q")

        assert captured["headers"]["authorization"] == "Bearer test-key"
        # Browser UA required by the gateway (same Cloudflare 1010 mitigation as qa_visual).
        assert "Mozilla/5.0" in captured["headers"]["user-agent"]

    def test_no_ground_truth_leakage_in_payload(self):
        """The provider forwards the question only — it must never carry
        benchmark ground truth (the caller controls what is sent, and the
        session store only passes benchmark.question)."""
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["payload"] = json.loads(request.content)
            return httpx.Response(200, json=ok_response_body())

        provider = make_provider(handler)
        provider.get_response("SYNTH-QUESTION-00 what is the answer?")

        serialized = json.dumps(captured["payload"])
        assert "SYNTH-TRUTH" not in serialized


class TestGetResponse:
    def test_returns_content_string(self):
        provider = make_provider(
            lambda request: httpx.Response(200, json=ok_response_body("plain answer"))
        )
        assert provider.get_response("q") == "plain answer"

    def test_per_call_model_override(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["payload"] = json.loads(request.content)
            return httpx.Response(200, json=ok_response_body())

        provider = make_provider(handler)
        provider.get_response("q", model="model-under-test-x")

        assert captured["payload"]["model"] == "model-under-test-x"

    def test_empty_content_is_returned_verbatim(self):
        """An empty completion is a measurable bad answer, not a transport
        error: return it and let the evaluator score it."""

        provider = make_provider(lambda request: httpx.Response(200, json=ok_response_body("")))
        assert provider.get_response("q") == ""


class TestErrors:
    def test_missing_api_key_raises(self):
        provider = LLMGatewayResponseProvider(api_key="")
        with pytest.raises(LLMGatewayProviderError, match="API key"):
            provider.get_response("q")
        provider.close()

    def test_http_error_raises_sanitized(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, text="upstream secret detail")

        provider = make_provider(handler)
        with pytest.raises(LLMGatewayProviderError, match="403") as exc_info:
            provider.get_response("q")
        assert "upstream secret detail" not in str(exc_info.value)

    def test_http_error_body_logged_not_raised(self, caplog):
        """CWE-209: upstream body goes to server logs only."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="internal stack trace detail")

        provider = make_provider(handler)
        with caplog.at_level("ERROR"):
            with pytest.raises(LLMGatewayProviderError):
                provider.get_response("q")

        assert any("internal stack trace detail" in r.message for r in caplog.records)

    def test_timeout_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("timed out")

        provider = make_provider(handler)
        with pytest.raises(LLMGatewayProviderError, match="[Tt]imeout"):
            provider.get_response("q")

    def test_connect_error_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        provider = make_provider(handler)
        with pytest.raises(LLMGatewayProviderError, match="connection"):
            provider.get_response("q")

    def test_malformed_json_raises(self):
        provider = make_provider(lambda request: httpx.Response(200, text="not-json{"))
        with pytest.raises(LLMGatewayProviderError, match="[Mm]alformed"):
            provider.get_response("q")

    def test_unexpected_shape_raises(self):
        provider = make_provider(lambda request: httpx.Response(200, json={"unexpected": "shape"}))
        with pytest.raises(LLMGatewayProviderError, match="[Mm]alformed"):
            provider.get_response("q")

    def test_empty_choices_raises(self):
        provider = make_provider(lambda request: httpx.Response(200, json={"choices": []}))
        with pytest.raises(LLMGatewayProviderError, match="[Mm]alformed"):
            provider.get_response("q")

    def test_null_content_raises(self):
        """A null content breaks the -> str contract: malformed, not a
        measurable empty answer."""
        provider = make_provider(
            lambda request: httpx.Response(200, json={"choices": [{"message": {"content": None}}]})
        )
        with pytest.raises(LLMGatewayProviderError, match="[Mm]alformed"):
            provider.get_response("q")


class TestFactory:
    def test_no_key_returns_none(self, monkeypatch):
        monkeypatch.delenv("ACCURACY_PROVIDER_API_KEY", raising=False)
        monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)
        assert create_response_provider_from_env() is None

    def test_blank_key_returns_none(self, monkeypatch):
        monkeypatch.setenv("ACCURACY_PROVIDER_API_KEY", "   ")
        monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)
        assert create_response_provider_from_env() is None

    def test_provider_key_builds_provider(self, monkeypatch):
        monkeypatch.setenv("ACCURACY_PROVIDER_API_KEY", "key-1")
        monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)
        provider = create_response_provider_from_env()
        assert isinstance(provider, LLMGatewayResponseProvider)
        assert provider.api_key == "key-1"
        provider.close()

    def test_fallback_to_opencode_go_key(self, monkeypatch):
        monkeypatch.delenv("ACCURACY_PROVIDER_API_KEY", raising=False)
        monkeypatch.setenv("OPENCODE_GO_API_KEY", "shared-key")
        provider = create_response_provider_from_env()
        assert provider is not None
        assert provider.api_key == "shared-key"
        provider.close()

    def test_provider_key_takes_precedence_over_fallback(self, monkeypatch):
        monkeypatch.setenv("ACCURACY_PROVIDER_API_KEY", "explicit")
        monkeypatch.setenv("OPENCODE_GO_API_KEY", "fallback")
        provider = create_response_provider_from_env()
        assert provider.api_key == "explicit"
        provider.close()

    def test_env_overrides_applied(self, monkeypatch):
        monkeypatch.setenv("ACCURACY_PROVIDER_API_KEY", "key-1")
        monkeypatch.setenv("ACCURACY_PROVIDER_BASE_URL", "https://custom.example/v1/chat")
        monkeypatch.setenv("ACCURACY_PROVIDER_MODEL", "custom-model")
        monkeypatch.setenv("ACCURACY_PROVIDER_TIMEOUT_S", "12.5")
        monkeypatch.setenv("ACCURACY_PROVIDER_MAX_TOKENS", "512")
        provider = create_response_provider_from_env()
        assert provider.base_url == "https://custom.example/v1/chat"
        assert provider.model == "custom-model"
        assert provider.timeout_s == 12.5
        assert provider.max_tokens == 512
        provider.close()

    def test_invalid_timeout_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("ACCURACY_PROVIDER_API_KEY", "key-1")
        monkeypatch.setenv("ACCURACY_PROVIDER_TIMEOUT_S", "not-a-number")
        provider = create_response_provider_from_env()
        assert provider.timeout_s == 60.0
        provider.close()

    def test_invalid_max_tokens_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("ACCURACY_PROVIDER_API_KEY", "key-1")
        monkeypatch.setenv("ACCURACY_PROVIDER_MAX_TOKENS", "oops")
        provider = create_response_provider_from_env()
        assert provider.max_tokens == 1024
        provider.close()
