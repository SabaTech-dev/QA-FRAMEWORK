"""Real IResponseProvider backed by an OpenAI-compatible LLM gateway.

Card 2f9afe89: POST /accuracy/sessions needs actual AI responses to
measure accuracy. This provider talks to the same gateway family as
``qa_visual`` (OpenAI-compatible chat completions, Bearer auth, browser
User-Agent against Cloudflare 1010) — pattern, not shared code.

Design notes:

- SYNC on purpose: ``IResponseProvider.get_response`` is a sync protocol
  and the accuracy endpoints are sync handlers (FastAPI runs them in a
  threadpool). Making the protocol async would ripple through the domain
  layer for no benefit at this catalog size.
- Injectable HTTP client: unit tests pass an ``httpx.Client`` with a
  ``MockTransport`` so no test ever touches the network.
- Fail-closed by omission: ``create_response_provider_from_env`` returns
  ``None`` when no API key is configured, so the endpoint keeps its
  explicit 503 "not configured" signal instead of half-working.
- CWE-209 / S-3: upstream bodies are logged server-side only; the raised
  error message carries the status/category, never the body.
"""

from __future__ import annotations

import logging
import os

import httpx

from src.domain.accuracy_testing.interfaces import IResponseProvider

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://opencode.ai/zen/go/v1/chat/completions"
DEFAULT_MODEL = "deepseek-v4-flash-vision-exp"
DEFAULT_TIMEOUT_S = 60.0
DEFAULT_MAX_TOKENS = 1024

# Browser UA required to avoid Cloudflare 1010 rejections (qa_visual C3).
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Neutral persona: the model under test answers the benchmark question as
# itself. The provider never receives ground truth (the session store only
# forwards ``benchmark.question``), so no evaluation leakage is possible.
SYSTEM_PROMPT = (
    "You are a legal information assistant. Answer the user's question concisely and accurately."
)


class LLMGatewayProviderError(RuntimeError):
    """Raised when the LLM gateway call fails or returns an unusable body.

    The message is sanitized (status/category only) so it can safely cross
    the API boundary; upstream bodies stay in server logs.
    """


class LLMGatewayResponseProvider(IResponseProvider):
    """``IResponseProvider`` implementation calling an LLM gateway.

    Args:
        api_key: gateway credentials (env-only in production, never committed).
        base_url: OpenAI-compatible chat completions endpoint.
        model: default model id under test.
        timeout_s: per-request timeout in seconds.
        max_tokens: completion cap.
        http_client: injectable ``httpx.Client`` (tests use ``MockTransport``);
            when omitted, a client is created with ``timeout_s``.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout_s = timeout_s
        self.max_tokens = max_tokens
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=timeout_s)

    def get_response(self, prompt: str, model: str = "") -> str:
        """Fetch an AI response for ``prompt`` (``model`` overrides the
        configured default for this call)."""
        if not self.api_key:
            raise LLMGatewayProviderError(
                "API key missing: set ACCURACY_PROVIDER_API_KEY in the environment"
            )

        payload = {
            "model": model or self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0.1,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": BROWSER_USER_AGENT,
        }

        try:
            response = self._client.post(self.base_url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise LLMGatewayProviderError(f"Gateway timeout: {type(exc).__name__}") from exc
        except httpx.HTTPError as exc:
            raise LLMGatewayProviderError("Gateway connection error") from exc

        if response.status_code != 200:
            # CWE-209 (S-3): upstream body stays in server logs only.
            logger.error(
                "Accuracy LLM gateway HTTP %s: %s",
                response.status_code,
                response.text[:200],
            )
            raise LLMGatewayProviderError(f"Gateway HTTP {response.status_code}")

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMGatewayProviderError(
                f"Malformed gateway response: {type(exc).__name__}"
            ) from exc
        if not isinstance(content, str):
            # null/non-string content breaks the -> str contract; "" is the
            # only acceptable empty answer (measurable by the evaluator).
            raise LLMGatewayProviderError("Malformed gateway response: non-string content")

        # An empty completion is a measurable bad answer, not a transport
        # error: return it verbatim and let the evaluator score it.
        return content

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "")
    try:
        return float(raw) if raw else default
    except ValueError:
        logger.warning("Invalid %s=%r; falling back to %s", name, raw, default)
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    try:
        return int(raw) if raw else default
    except ValueError:
        logger.warning("Invalid %s=%r; falling back to %s", name, raw, default)
        return default


def create_response_provider_from_env() -> LLMGatewayResponseProvider | None:
    """Build the provider from deploy env vars.

    Returns ``None`` when no API key is configured (checked in order:
    ``ACCURACY_PROVIDER_API_KEY``, then the repo-wide ``OPENCODE_GO_API_KEY``),
    keeping POST /accuracy/sessions at its explicit 503 "not configured".
    """
    api_key = (
        os.environ.get("ACCURACY_PROVIDER_API_KEY") or os.environ.get("OPENCODE_GO_API_KEY") or ""
    ).strip()
    if not api_key:
        return None

    return LLMGatewayResponseProvider(
        api_key=api_key,
        base_url=os.environ.get("ACCURACY_PROVIDER_BASE_URL", DEFAULT_BASE_URL),
        model=os.environ.get("ACCURACY_PROVIDER_MODEL", DEFAULT_MODEL),
        timeout_s=_env_float("ACCURACY_PROVIDER_TIMEOUT_S", DEFAULT_TIMEOUT_S),
        max_tokens=_env_int("ACCURACY_PROVIDER_MAX_TOKENS", DEFAULT_MAX_TOKENS),
    )
