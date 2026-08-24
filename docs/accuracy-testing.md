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

## Configuration

| Variable | Default | Description |
|---|---|---|
| `ACCURACY_TESTING_ENABLED` | unset | Opt-in mount of the accuracy router (dashboard backend) |
| `ACCURACY_SPLIT_SECRET` | — | Platform secret for per-tenant salt derivation (required when enabled) |

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
