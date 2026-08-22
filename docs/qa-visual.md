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
`502` (gateway or model-output failure, includes a raw output excerpt).

### Reports and trends

- `GET /api/v1/qa-visual/reports?target=amc&limit=50` — stored reports, newest first.
- `GET /api/v1/qa-visual/reports/{report_id}` — one report (404 if unknown).
- `GET /api/v1/qa-visual/trends?target=amc` — dashboard data source:
  `points` (score history) + `alerts` (degradation: score drop >= 10 points
  between consecutive runs, or `regression_detected` flags).
- `GET /api/v1/qa-visual/baselines/{target}` — baseline report of a target (404 if none).

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
