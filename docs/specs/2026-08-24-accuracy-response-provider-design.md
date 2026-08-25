# Accuracy Response Provider — Design (card 2f9afe89)

Date: 2026-08-24
Branch: `feat/accuracy-response-provider` (base `origin/main` bfb388a)

## Problem

`POST /accuracy/sessions` returns **503** because the dashboard mount
(`dashboard/backend/main.py`) never passes a `response_provider` to
`create_accuracy_router`. The evaluation pipeline (split → eval → sealed
holdout) is complete and tested, but there is no real implementation of
`IResponseProvider` that fetches actual AI responses.

## Approaches considered

### A. Sync LLM gateway provider (OpenAI-compatible) + env factory — SELECTED

A new `LLMGatewayResponseProvider` implements the existing **sync**
`IResponseProvider` protocol with a sync `httpx.Client`, following the
proven gateway pattern of `qa_visual/gateway_client.py` (same
OpenAI-compatible chat-completions endpoint, Bearer auth, browser UA,
sanitized errors per CWE-209/S-3) **without touching qa_visual**.

- Pros: real AI responses (the point of accuracy testing); DI intact —
  the constructor accepts an injectable HTTP client for network-free
  unit tests; zero domain changes (protocol stays sync); vendor sync is
  a file copy; deploy via env vars like every other module flag.
- Cons: introduces a network call in the POST request path — inherent
  to a real provider; mitigated with timeout + explicit 502 mapping.

### B. Deterministic rule-based provider — REJECTED

Canned/stub answers would make the "accuracy" measurement meaningless:
it would evaluate a constant string, not an AI system. The card asks
for a real provider.

### C. Async refactor of `IResponseProvider` — REJECTED (deferred)

Changing the protocol to async ripples through `session_store`,
`holdout_service`, the vendored copy and every existing test. The
benchmark catalog is small (tens of items) and FastAPI already runs
sync endpoints in a threadpool, so sync is adequate here.

## Selected design

### New file: `src/infrastructure/accuracy_testing/llm_gateway_provider.py`

1. `LLMGatewayProviderError(RuntimeError)` — message is always
   sanitized (status/category only). Upstream bodies are logged
   server-side, never raised into HTTP responses (CWE-209).
2. `LLMGatewayResponseProvider` — implements `IResponseProvider`:
   - `__init__(api_key, base_url=..., model=..., timeout_s=..., max_tokens=..., http_client=None)`.
     The optional `http_client` keeps unit tests network-free (same DI
     pattern as `VisionGatewayClient`).
   - `get_response(prompt, model="") -> str` — POST
     `{"model": model or configured, "messages": [system, user], "temperature": 0.1, "max_tokens": ...}`.
     The system prompt is a neutral legal-assistant persona; the
     benchmark question is forwarded as-is. The provider NEVER sees
     ground truth (the session store only passes `benchmark.question`),
     so no evaluation leakage is possible.
   - Browser `User-Agent` (Cloudflare 1010 mitigation, same as qa_visual C3).
   - `close()` for resource hygiene.
3. `create_response_provider_from_env() -> LLMGatewayResponseProvider | None` —
   returns `None` when no API key is configured, so the existing 503
   stays as the explicit "not configured" signal (fail-closed by
   omission, mirrors `QA_VISUAL_ENABLED` opt-in style).

### Endpoint mapping (`endpoint.py`)

`LLMGatewayProviderError` raised during `run_accuracy_session` maps to
**502 Bad Gateway** with a generic detail. All other semantics
untouched.

### Wiring (`dashboard/backend/main.py`)

```python
response_provider=create_response_provider_from_env(),
```

added to the existing `create_accuracy_router(...)` mount behind
`ACCURACY_TESTING_ENABLED=1`.

### Vendored copy

Copy `src/infrastructure/accuracy_testing/*.py` to
`dashboard/backend/src/infrastructure/accuracy_testing/` — enforced by
`tests/unit/infrastructure/test_accuracy_vendor_parity.py`.

## Configuration (deploy)

| Variable | Default | Description |
|---|---|---|
| `ACCURACY_PROVIDER_API_KEY` | fallback `OPENCODE_GO_API_KEY` | Gateway key; absent key → provider stays `None` → 503 |
| `ACCURACY_PROVIDER_BASE_URL` | `https://opencode.ai/zen/go/v1/chat/completions` | OpenAI-compatible endpoint (same gateway family as qa_visual) |
| `ACCURACY_PROVIDER_MODEL` | `deepseek-v4-flash-vision-exp` | Model id under test |
| `ACCURACY_PROVIDER_TIMEOUT_S` | `60` | Per-request timeout (robust parse, falls back on invalid) |
| `ACCURACY_PROVIDER_MAX_TOKENS` | `1024` | Completion cap |

## Testing strategy (TDD)

- Unit (`tests/unit/infrastructure/test_llm_gateway_provider.py`):
  request contract (payload/headers/URL), happy path, per-call model
  override, sanitized error mapping (HTTP error, timeout, connection
  error, malformed JSON, empty choices), factory env matrix — all via
  `httpx.MockTransport`, zero network.
- Endpoint contract (`tests/unit/api/test_accuracy_endpoint_contracts.py`):
  provider failure → 502, upstream body never reaches the client.
- Provider+endpoint integration via DI: router + real provider +
  MockTransport → `POST /accuracy/sessions` **200** (AC1 proof,
  network-free).
- Dashboard wiring: module reload with provider env set assembles the
  app cleanly (mount still fail-closed without the split secret).
- Coverage ≥ 80% on the new module file.

## Out of scope

- Async provider protocol (approach C).
- LLM-based evaluator (rule-based evaluator stays).
- `qa_visual` module and dashboard middleware/rate_limit (forbidden by
  the card).
