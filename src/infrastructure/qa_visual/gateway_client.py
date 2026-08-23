"""Async client for the vision model gateway (spike conditions C1-C5).

C1: thinking disabled by default (4.37s vs 10-23s with thinking ON).
C2: max_tokens >= 4000 enforced by config when thinking is ON.
C3: browser User-Agent on every request (Cloudflare 1010 mitigation).
C4: model id from config (exp -> GA transition without code changes).
C5: per-analysis cost tracking with pinned 2026-08-22 pricing.
"""

import base64
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from src.infrastructure.qa_visual.config import QAVisualConfig

logger = logging.getLogger(__name__)

QA_PROMPT = """Eres un QA visual automatizado para SabaTech. Analiza esta captura de pantalla y responde en formato JSON con esta estructura EXACTA:

{
  "page_title": "título exacto visible o null",
  "visible_texts": ["lista de TODOS los textos literales visibles (botones, labels, placeholders, headings, footer, etc.)"],
  "layout": {
    "description": "descripción del layout (elementos, orden, alineación)",
    "colors": {"background": "#hex", "primary_accent": "#hex", "text": "#hex"}
  },
  "qa_issues": [
    {
      "severity": "critical|high|medium|low|info",
      "category": "contrast|alignment|overflow|missing|text|spacing|other",
      "description": "descripción del problema",
      "element": "elemento afectado si identificable"
    }
  ],
  "accessibility": {
    "contrast_issues": ["lista de problemas de contraste WCAG"],
    "missing_alt": true/false,
    "missing_labels": ["inputs sin label"]
  },
  "visual_regression": {
    "unexpected_whitespace": true/false,
    "overlapping_elements": true/false,
    "cut_off_content": true/false,
    "misaligned": true/false
  },
  "overall_score": 0-100,
  "summary": "resumen en 1-2 oraciones"
}

Responde SOLO con el JSON, sin texto adicional."""


class VisionGatewayError(Exception):
    """Raised when the gateway call fails or returns an unusable response."""


@dataclass
class VisionResult:
    """Raw result of one gateway call."""

    content: str
    latency_s: float
    usage: Dict[str, Any]
    cost_usd: float
    model_reported: str
    finish_reason: Optional[str]


class VisionGatewayClient:
    """Talks to the vision gateway with spike conditions baked in."""

    def __init__(self, config: QAVisualConfig, http_client: Optional[httpx.AsyncClient] = None):
        self._config = config
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=config.request_timeout_s)

    async def analyze_image(self, image_bytes: bytes) -> VisionResult:
        """Send a PNG screenshot for QA analysis and return the raw result."""
        if not self._config.api_key:
            raise VisionGatewayError("API key missing: set OPENCODE_GO_API_KEY in the environment")

        payload = self._build_payload(image_bytes)
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
            # C3: browser UA required by the gateway.
            "User-Agent": self._config.user_agent,
        }

        started = time.monotonic()
        try:
            response = await self._client.post(
                self._config.gateway_url,
                content=json.dumps(payload),
                headers=headers,
            )
        except httpx.TimeoutException as exc:
            raise VisionGatewayError(f"Gateway timeout: {exc}") from exc
        except httpx.HTTPError as exc:
            raise VisionGatewayError(f"Gateway connection error: {exc}") from exc

        latency_s = time.monotonic() - started
        if response.status_code != 200:
            # S-3 (CWE-209): upstream body stays in server logs only, never
            # in the exception message that could reach an HTTP client.
            logger.error("Gateway HTTP %s: %s", response.status_code, response.text[:200])
            raise VisionGatewayError(f"Gateway HTTP {response.status_code}")

        try:
            body = response.json()
            choice = body["choices"][0]
            content = choice["message"].get("content", "")
            usage = body.get("usage", {}) or {}
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise VisionGatewayError(f"Malformed gateway response: {exc}") from exc

        cost_usd = self._config.calculate_cost_usd(
            prompt_tokens=usage.get("prompt_tokens", 0) or 0,
            completion_tokens=usage.get("completion_tokens", 0) or 0,
        )

        return VisionResult(
            content=content,
            latency_s=round(latency_s, 2),
            usage=usage,
            cost_usd=round(cost_usd, 6),
            model_reported=body.get("model", "unknown"),
            finish_reason=choice.get("finish_reason"),
        )

    def _build_payload(self, image_bytes: bytes) -> Dict[str, Any]:
        data_url = "data:image/png;base64," + base64.b64encode(image_bytes).decode()
        payload: Dict[str, Any] = {
            "model": self._config.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": QA_PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            "max_tokens": self._config.max_tokens,
            "temperature": self._config.temperature,
            # C1: thinking disabled for QA loops (fast + deterministic).
            "thinking": {"type": "disabled" if not self._config.thinking_enabled else "enabled"},
        }
        return payload

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "VisionGatewayClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
