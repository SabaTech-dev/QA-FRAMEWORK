# QA Visual Module

Vision-model screenshot analysis integrated into the QA framework. Validated
in Fase A (score 95/100, $0.000428/screenshot, 4.37s latency, 0 hallucinations)
and productized per the GO-NOGO Fase B decision.

## Overview

The module lives in `src/infrastructure/qa_visual/` and provides:

- **REST API** (`POST /api/v1/qa-visual/analyze`) — upload a screenshot, get a
  structured QA report (score, issues, accessibility, visual regression flags).
- **Report storage** — JSON reports under `reports/qa-visual/`.
- **Configurable threshold** — `score < threshold` marks the report as failed
  (default 80).
- **Playwright post-test hook** — capture + analyze + append to the test report.
- **Baseline visual regression** — first analysis of a target becomes its
  baseline; later runs flag regressions on score drops or regression flags.
- **Trends** — score history and degradation alerts for dashboards.

## Spike conditions (C1-C5)

Enforced in `config.py` and `gateway_client.py`:

| Condition | Enforcement |
|---|---|
| C1: `thinking: {type: "disabled"}` always | Default in every gateway payload |
| C2: `max_tokens >= 4000` when thinking ON | `ValueError` at config validation |
| C3: Browser User-Agent | Sent on every gateway request (Cloudflare 1010 mitigation) |
| C4: Model id via config, not hardcode | `QA_VISUAL_MODEL` env override (ready for exp -> GA) |
| C5: Pricing pin 2026-08-22 | $0.22/$0.66 per 1M tokens (off-peak), per-analysis cost tracking |

The API key is read **only** from the environment (`OPENCODE_GO_API_KEY`,
e.g. from `~/.openclaw/.env`). It is never committed to this repository.

## Configuration

All settings via environment variables (safe defaults when unset):

| Variable | Default | Description |
|---|---|---|
| `OPENCODE_GO_API_KEY` | — | Gateway API key (required for real analysis) |
| `QA_VISUAL_MODEL` | `deepseek-v4-flash-vision-exp` | Vision model id (C4) |
| `QA_VISUAL_THRESHOLD_SCORE` | `80` | Passing score threshold |
| `QA_VISUAL_GATEWAY_URL` | `https://opencode.ai/zen/go/v1/chat/completions` | Gateway endpoint |
| `QA_VISUAL_REPORTS_DIR` | `reports/qa-visual` | Report storage directory |

## REST API

Mount the router in any FastAPI app:

```python
from fastapi import FastAPI
from src.infrastructure.qa_visual import create_qa_visual_router

app = FastAPI()
app.include_router(create_qa_visual_router())  # config from env
```

The factory accepts injectable router-level `dependencies` so the mounter
controls authentication without coupling the module to any auth service
(security hardening S-1):

```python
from fastapi import Depends
app.include_router(
    create_qa_visual_router(dependencies=[Depends(get_current_user)])
)
```

It also accepts `get_current_principal` for owner scoping (S-1R): the
dependency must return a `QAVisualPrincipal` (`owner`, `is_admin`). Every
endpoint then scopes reports to that owner; `is_admin=True` bypasses the
scoping. Without it the router keeps its legacy unscoped behaviour for
standalone mounts:

```python
from src.infrastructure.qa_visual import QAVisualPrincipal

def get_principal():  # e.g. resolve from your auth service
    return QAVisualPrincipal(owner="alice", is_admin=False)

app.include_router(
    create_qa_visual_router(
        dependencies=[Depends(get_current_user)],
        get_current_principal=get_principal,
    )
)
```

Owner-scoping rules (S-1R):

- `POST /analyze` stamps the principal as the report `owner` and the
  baseline/regression comparison never crosses owners.
- `GET /reports` and `GET /trends` only return the caller's reports
  (admins see everything).
- `GET /reports/{id}` answers 403 for authenticated non-owners, 404 for
  unknown ids.
- `GET /baselines/{target}` is scoped to the caller's reports for that
  target.
- Reports persisted before owner-scoping (`owner` absent) are admin-only.

### Dashboard wiring (Fase C)

The dashboard backend (`dashboard/backend/main.py`) mounts the router with
`dependencies=[Depends(get_current_user)]` and
`get_current_principal=get_qa_visual_principal` (maps `owner` to the
authenticated username and `is_admin` to the existing `is_superuser`
role): **all five endpoints require a valid JWT and reports are
owner-scoped (S-1R resolved)**. The mount is still **gated behind
`QA_VISUAL_ENABLED=1` (default off)** — without the flag the router is
not mounted and every qa-visual endpoint returns 404; with the S-1R fix
in place the flag is safe to enable in staging. Because the Docker build
context only
ships `dashboard/backend`,
the module is vendored at `dashboard/backend/src/infrastructure/qa_visual/`
(same pattern as the cache module). A parity test
(`tests/unit/infrastructure/test_qa_visual_vendor_parity.py`) fails loudly if
the two copies drift — after changing `src/infrastructure/qa_visual/`, re-copy:

```bash
cp src/infrastructure/qa_visual/*.py dashboard/backend/src/infrastructure/qa_visual/
```

Upload hardening (S-2/S-5) applies to `POST /analyze`: `Content-Length`
pre-check + chunked read capped at 10 MB (413), `image/png` content-type and
PNG magic-byte validation (415), and `target` limited to 200 chars (422).
Upstream gateway errors return a generic 502 with full detail in server logs
only (S-3, CWE-209).

### Data handling (S-4)

Every `POST /analyze` call sends the **full screenshot** (base64, up to ~13 MB
payload for a 10 MB image) to the external vision gateway
(`https://opencode.ai/zen/go/v1/chat/completions`). Policy:

- **Synthetic/test data only** — QA Visual targets must not contain real PII,
  customer data or credentials. If screenshots may capture real user data,
  evaluate GDPR Art. 32 (processor transfer) and add pre-send redaction
  before enabling the module in that environment.
- Reports and screenshots stored under `reports/qa-visual/` are runtime
  artifacts; the directory is gitignored to prevent accidental commits.


### Analyze a screenshot

```http
POST /api/v1/qa-visual/analyze
Content-Type: multipart/form-data
```

| Field | Type | Description |
|---|---|---|
| `screenshot` | file | PNG screenshot (max 10 MB) |
| `target` | string | Target identifier (page/feature name) |

**Response (200):**

```json
{
  "report_id": "a1b2c3d4e5f6",
  "target": "amc",
  "owner": "alice",
  "passed": true,
  "score": 95,
  "threshold": 80,
  "cost_usd": 0.000428,
  "latency_s": 4.37,
  "model": "deepseek-v4-flash-vision-exp",
  "regression_detected": false,
  "analysis": {
    "page_title": "AMC",
    "visible_texts": ["Login", "Sign in"],
    "qa_issues": [
      {"severity": "medium", "category": "contrast", "description": "..."}
    ],
    "accessibility": {"contrast_issues": [], "missing_alt": false, "missing_labels": []},
    "visual_regression": {
      "unexpected_whitespace": false, "overlapping_elements": false,
      "cut_off_content": false, "misaligned": false
    },
    "overall_score": 95,
    "summary": "Clean page with one contrast issue."
  }
}
```

Errors: `422` (missing/empty fields), `413` (screenshot > 10 MB),
`502` (gateway or model-output failure, generic body — details in server
logs only).

### Reports and trends

All read endpoints are owner-scoped when the router is mounted with a
principal (S-1R); admins bypass the scoping.

- `GET /api/v1/qa-visual/reports?target=amc&limit=50` — stored reports, newest first.
- `GET /api/v1/qa-visual/reports/{report_id}` — one report (404 if unknown,
  403 if owned by another user).
- `GET /api/v1/qa-visual/trends?target=amc` — dashboard data source:
  `points` (score history) + `alerts` (degradation: score drop >= 10 points
  between consecutive runs, or `regression_detected` flags).
- `GET /api/v1/qa-visual/baselines/{target}` — baseline report of a target
  (404 if none for the caller).

## Playwright E2E integration

Add the hook to an E2E test lifecycle:

```python
import pytest
from src.infrastructure.qa_visual import QAVisualAnalyzer, QAVisualHook

@pytest.fixture
def qa_visual_hook():
    return QAVisualHook(analyzer=QAVisualAnalyzer())  # config from env

@pytest.mark.asyncio
async def test_login(page, qa_visual_hook, tmp_path):
    await page.goto("https://app.example.com/login")
    # ... assertions ...

    # Post-test hook: screenshot -> vision analysis -> append to test report
    await qa_visual_hook.on_test_end(
        page,
        test_name="test_login",
        report_path=tmp_path / "test_login_report.json",
    )
```

The hook is **fail-soft**: any failure (browser crash, gateway down, parse
error) is logged and swallowed, returning `None`. A QA hook must never break
the suite it observes.

The first analysis of a target is stored as its **baseline**. Subsequent runs
set `regression_detected: true` when the score drops by
`degradation_alert_points` (default 10) against the baseline or the model
reports visual regression flags.

## Programmatic usage

```python
from src.infrastructure.qa_visual import QAVisualAnalyzer

analyzer = QAVisualAnalyzer()  # reads env config
response = await analyzer.analyze(image_bytes, target="landing")
print(response.score, response.passed, response.cost_usd)
# owner-scoped runs (S-1R): stamp the caller and scope baselines to them
response = await analyzer.analyze(image_bytes, target="landing", owner="alice")
```

## Model lifecycle note (C4)

`deepseek-v4-flash-vision-exp` is an experimental model id. When it moves to
GA, set `QA_VISUAL_MODEL=deepseek-v4-flash-vision` (no code changes needed)
and re-evaluate quality per the Fase A protocol. The model actually used is
recorded in every report (`model` field, as reported by the gateway).

## Cost tracking

Each report includes `cost_usd` computed from gateway token usage with the
pinned 2026-08-22 pricing (C5). Typical analysis: ~$0.0004/screenshot. Set
an alert threshold if cost exceeds $0.01/screenshot consistently (GO-NOGO
risk mitigation).

## Tests

```bash
pytest tests/unit/infrastructure/test_qa_visual_*.py -v
pytest tests/unit/infrastructure/test_qa_visual_*.py \
    --cov=src.infrastructure.qa_visual --cov-report=term-missing
```

Module coverage: 96% (threshold: >= 80%). All tests run without network:
the gateway client is tested with `httpx.MockTransport`.
