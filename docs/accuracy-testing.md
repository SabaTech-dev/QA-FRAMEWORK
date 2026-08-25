# Accuracy Testing Module

AI accuracy evaluation with German AI liability benchmarks (BGH 2025 ruling)
and anti-overfitting holdout sealing (F-ACC-006). Domain module from cards
72f97f1b/ca3090d5; API wiring and security contracts from card c9825844.

## Overview

- **Domain** (`src/domain/accuracy_testing/`) — benchmarks, evaluations,
  sessions, deterministic eval/holdout splitting, aggregate-only holdout.
- **Infrastructure** (`src/infrastructure/accuracy_testing/`) — rule-based
  evaluator, built-in German benchmarks, API router with owner scoping.
- **Vendored copy** under `dashboard/backend/src/` — the dashboard backend
  deploys with its own Docker context, so the module is vendored there too
  (same pattern as `qa_visual`).

## Anti-gaming design (F-ACC-006)

Observable benchmarks can be gamed by iterating against them until
memorization. The holdout set is therefore sealed:

- Deterministic split: `SHA-256(f"{salt}:{benchmark.id}")` bucketing — a pure
  function of (ids, policy), stable across processes.
- `HoldoutEvaluationService` discards per-item results; only a
  `HoldoutSummary` (counts + rates) leaves the service.
- `BenchmarkSplit.to_dict()`/`__repr__` expose counts only.
- The eval set is the legitimate development surface: its evaluations carry
  prompt/response detail; the holdout never does.

## Security contracts (card c9825844)

### L-1 — per-tenant split salt

`SplitPolicy.salt` is **required and non-empty** (a shared default would
reveal holdout membership platform-wide). The API derives it server-side:

```
salt = HMAC-SHA256(ACCURACY_SPLIT_SECRET, tenant_id)
```

- Clients cannot send or choose a salt (`SessionCreateRequest` is
  `extra="forbid"`; any attempt returns 422).
- Mount fails closed: enabling the router without `ACCURACY_SPLIT_SECRET`
  raises at startup instead of degrading to a shared namespace.
- Rotating the secret changes holdout membership for every tenant — rotate
  deliberately.

### L-2 — admin-only full views + owner scoping

- `AccuracyBenchmark.to_dict_full()` (exposes `ground_truth` + `tenant_id`)
  is served **to admins only**; owners get `to_dict()`.
- Resources are owner-scoped: sessions from another tenant 404. Holdout
  members 404 for non-admins (membership is not confirmable via probing).
- `AccuracyPrincipal(owner, is_admin)` reuses the QAVisualPrincipal pattern
  from PR #118 (pattern, not code).

### AC2 — API serialization contract

Endpoints serialize benchmarks via `to_dict()` and holdout results via
`HoldoutSummary` only. Never `split.holdout_benchmarks`, never
`to_dict_full()` for non-admins. A canary test
(`tests/unit/api/test_accuracy_endpoint_contracts.py`) fails if any holdout
question/ground-truth string or forbidden key appears in any response.

## Threshold threading

`AccuracyBenchmark.passing_threshold` flows into the pass decision:
`compute_overall(passing_threshold=...)` (legacy default 0.6 kept for
backwards compatibility; the rule-based evaluator always threads the
benchmark's own threshold).

## Response provider (card 2f9afe89)

`POST /accuracy/sessions` needs actual AI responses. The real provider —
`LLMGatewayResponseProvider` — calls an OpenAI-compatible chat
completions gateway (same gateway family as `qa_visual`, pattern not
shared code):

- **Sync by design**: `IResponseProvider.get_response` is a sync
  protocol and the endpoints are sync handlers (FastAPI threadpool).
- **Injectable HTTP client**: unit tests pass an `httpx.Client` with a
  `MockTransport`; no test touches the network.
- **No leakage**: the provider only ever receives `benchmark.question`
  (never ground truth), forwarded as-is with a neutral legal-assistant
  system prompt.
- **Fail-closed by omission**: `create_response_provider_from_env()`
  returns `None` when no API key is configured, so POST /sessions keeps
  its explicit 503 "no provider configured" signal.
- **Error semantics**: gateway failures raise `LLMGatewayProviderError`
  with a sanitized message (status/category only — upstream bodies go
  to server logs, CWE-209); the endpoint maps it to **502 Bad Gateway**
  with a generic detail. An empty completion (`""`) is returned verbatim
  as a measurable bad answer.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `ACCURACY_TESTING_ENABLED` | unset | Opt-in mount of the accuracy router (dashboard backend) |
| `ACCURACY_SPLIT_SECRET` | — | Platform secret for per-tenant salt derivation (required when enabled) |
| `ACCURACY_PROVIDER_API_KEY` | fallback `OPENCODE_GO_API_KEY` | LLM gateway key; absent key → provider stays off → 503 |
| `ACCURACY_PROVIDER_BASE_URL` | `https://opencode.ai/zen/go/v1/chat/completions` | OpenAI-compatible chat completions endpoint |
| `ACCURACY_PROVIDER_MODEL` | `deepseek-v4-flash-vision-exp` | Model id under test (overridable per session via `ai_model`) |
| `ACCURACY_PROVIDER_TIMEOUT_S` | `60` | Per-request timeout in seconds (invalid values fall back) |
| `ACCURACY_PROVIDER_MAX_TOKENS` | `1024` | Completion cap |

## Trying it out

Deploy env (dashboard backend):

```bash
export ACCURACY_TESTING_ENABLED=1
export ACCURACY_SPLIT_SECRET="<platform-secret>"
export ACCURACY_PROVIDER_API_KEY="<gateway-key>"   # or OPENCODE_GO_API_KEY
# optional overrides:
# ACCURACY_PROVIDER_MODEL, ACCURACY_PROVIDER_BASE_URL,
# ACCURACY_PROVIDER_TIMEOUT_S, ACCURACY_PROVIDER_MAX_TOKENS
```

Run a session (auth is the dashboard JWT):

```bash
curl -X POST http://localhost:8000/accuracy/sessions \
  -H "Authorization: Bearer $DASHBOARD_JWT" \
  -H "Content-Type: application/json" \
  -d '{"ai_model": ""}'
# 200 -> {"id": "...", "evaluations": [...], "holdout_summary": {...}, "split": {...}}
# 502 -> gateway failed (see server logs) | 503 -> no provider configured
```

## REST API

```python
from fastapi import FastAPI

from src.infrastructure.accuracy_testing import create_accuracy_router
from src.infrastructure.accuracy_testing.security import AccuracyPrincipal

app = FastAPI()
app.include_router(
    create_accuracy_router(
        principal_dependency=lambda: AccuracyPrincipal(owner="tenant-1"),
        split_secret=os.environ["ACCURACY_SPLIT_SECRET"],
    )
)
```

| Endpoint | Description |
|---|---|
| `GET /accuracy/benchmarks` | Catalog; tenant-filtered to the tenant's eval set |
| `GET /accuracy/benchmarks/{id}` | Detail — `to_dict_full()` for admins only |
| `POST /accuracy/sessions` | Run evaluation session (split + eval + sealed holdout) |
| `GET /accuracy/sessions/{id}` | Session view: eval detail + holdout aggregates |
| `GET /accuracy/sessions/{id}/holdout` | `HoldoutSummary` aggregates only |

The dashboard backend mounts the router behind JWT auth
(`Depends(get_current_user)`), deriving `owner` from `User.tenant_id` (or
`user-{id}`) and `is_admin` from `User.is_superuser`.
