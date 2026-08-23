"""Unit tests for the vision gateway client (spike conditions C1-C5)."""

import json

import httpx
import pytest

from src.infrastructure.qa_visual.config import QAVisualConfig
from src.infrastructure.qa_visual.gateway_client import (
    VisionGatewayClient,
    VisionGatewayError,
    VisionResult,
)


def make_config(**overrides) -> QAVisualConfig:
    defaults = {"api_key": "test-key"}
    defaults.update(overrides)
    return QAVisualConfig(**defaults)


def ok_response_body(model="deepseek-v4-flash-vision-exp") -> dict:
    return {
        "model": model,
        "choices": [
            {
                "message": {"content": '{"overall_score": 95, "summary": "ok"}'},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 1000, "completion_tokens": 800},
    }


def make_client(handler, config=None) -> VisionGatewayClient:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    return VisionGatewayClient(config or make_config(), http_client=client)


class TestRequestPayload:
    @pytest.mark.asyncio
    async def test_thinking_disabled_by_default(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["payload"] = json.loads(request.content)
            return httpx.Response(200, json=ok_response_body())

        async with make_client(handler) as client:
            await client.analyze_image(b"fake-png-bytes")

        # C1: thinking always disabled in QA loops
        assert captured["payload"]["thinking"] == {"type": "disabled"}

    @pytest.mark.asyncio
    async def test_thinking_enabled_when_configured(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["payload"] = json.loads(request.content)
            return httpx.Response(200, json=ok_response_body())

        config = make_config(thinking_enabled=True, max_tokens=4000)
        async with make_client(handler, config) as client:
            await client.analyze_image(b"fake-png-bytes")

        assert captured["payload"]["thinking"] == {"type": "enabled"}
        # C2: enough tokens for complete JSON when thinking is ON
        assert captured["payload"]["max_tokens"] >= 4000

    @pytest.mark.asyncio
    async def test_model_from_config(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["payload"] = json.loads(request.content)
            return httpx.Response(200, json=ok_response_body(model="deepseek-v4-flash-vision"))

        config = make_config(model="deepseek-v4-flash-vision")
        async with make_client(handler, config) as client:
            result = await client.analyze_image(b"png")

        # C4: model id comes from config, ready for exp->GA transition
        assert captured["payload"]["model"] == "deepseek-v4-flash-vision"
        assert result.model_reported == "deepseek-v4-flash-vision"

    @pytest.mark.asyncio
    async def test_image_sent_as_base64_data_url(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["payload"] = json.loads(request.content)
            return httpx.Response(200, json=ok_response_body())

        async with make_client(handler) as client:
            await client.analyze_image(b"fake-png-bytes")

        content = captured["payload"]["messages"][0]["content"]
        image_part = next(p for p in content if p["type"] == "image_url")
        assert image_part["image_url"]["url"].startswith("data:image/png;base64,")

    @pytest.mark.asyncio
    async def test_prompt_includes_json_contract(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["payload"] = json.loads(request.content)
            return httpx.Response(200, json=ok_response_body())

        async with make_client(handler) as client:
            await client.analyze_image(b"png")

        text_part = next(
            p for p in captured["payload"]["messages"][0]["content"] if p["type"] == "text"
        )
        assert "overall_score" in text_part["text"]
        assert "JSON" in text_part["text"]


class TestRequestHeaders:
    @pytest.mark.asyncio
    async def test_browser_user_agent_sent(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["headers"] = request.headers
            return httpx.Response(200, json=ok_response_body())

        async with make_client(handler) as client:
            await client.analyze_image(b"png")

        # C3: browser UA to avoid Cloudflare 1010
        assert "Mozilla/5.0" in captured["headers"]["user-agent"]

    @pytest.mark.asyncio
    async def test_authorization_bearer_key(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["headers"] = request.headers
            return httpx.Response(200, json=ok_response_body())

        async with make_client(handler) as client:
            await client.analyze_image(b"png")

        assert captured["headers"]["authorization"] == "Bearer test-key"

    @pytest.mark.asyncio
    async def test_missing_api_key_raises(self):
        config = QAVisualConfig(api_key=None)
        client = VisionGatewayClient(config)
        with pytest.raises(VisionGatewayError, match="API key"):
            await client.analyze_image(b"png")
        await client.close()


class TestResponseHandling:
    @pytest.mark.asyncio
    async def test_result_fields(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=ok_response_body())

        async with make_client(handler) as client:
            result = await client.analyze_image(b"png")

        assert isinstance(result, VisionResult)
        assert result.content == '{"overall_score": 95, "summary": "ok"}'
        assert result.finish_reason == "stop"
        assert result.usage["prompt_tokens"] == 1000

    @pytest.mark.asyncio
    async def test_cost_tracking(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=ok_response_body())

        async with make_client(handler) as client:
            result = await client.analyze_image(b"png")

        # C5: 1000 in * $0.22/1M + 800 out * $0.66/1M
        expected = (1000 * 0.22 + 800 * 0.66) / 1_000_000
        assert result.cost_usd == pytest.approx(expected)

    @pytest.mark.asyncio
    async def test_latency_measured(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=ok_response_body())

        async with make_client(handler) as client:
            result = await client.analyze_image(b"png")

        assert result.latency_s >= 0.0

    @pytest.mark.asyncio
    async def test_http_error_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, text="Cloudflare block")

        async with make_client(handler) as client:
            with pytest.raises(VisionGatewayError, match="403"):
                await client.analyze_image(b"png")

    @pytest.mark.asyncio
    async def test_http_error_detail_not_in_exception_but_logged(self, caplog):
        """S-3: upstream body goes to logs, never into the exception message."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="internal stack trace detail")

        async with make_client(handler) as client:
            with caplog.at_level("ERROR", logger="src.infrastructure.qa_visual.gateway_client"):
                with pytest.raises(VisionGatewayError) as exc_info:
                    await client.analyze_image(b"png")

        assert "internal stack trace detail" not in str(exc_info.value)
        assert any("internal stack trace detail" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_timeout_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("timed out")

        async with make_client(handler) as client:
            with pytest.raises(VisionGatewayError, match="[Tt]imeout"):
                await client.analyze_image(b"png")

    @pytest.mark.asyncio
    async def test_malformed_response_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"unexpected": "shape"})

        async with make_client(handler) as client:
            with pytest.raises(VisionGatewayError):
                await client.analyze_image(b"png")
