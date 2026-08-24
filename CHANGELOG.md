# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Accuracy response provider (card 2f9afe89)**: real
  `IResponseProvider` implementation (`LLMGatewayResponseProvider`)
  backed by an OpenAI-compatible LLM gateway, so `POST
  /accuracy/sessions` returns 200 with a provider configured instead of
  503. Deploy config via `ACCURACY_PROVIDER_API_KEY` (fallback
  `OPENCODE_GO_API_KEY`) plus optional `ACCURACY_PROVIDER_BASE_URL`,
  `ACCURACY_PROVIDER_MODEL`, `ACCURACY_PROVIDER_TIMEOUT_S`,
  `ACCURACY_PROVIDER_MAX_TOKENS`; no key → provider stays off and the
  explicit 503 remains (fail-closed by omission). Injectable HTTP client
  keeps unit tests network-free; provider failures map to 502 with a
  sanitized detail (CWE-209). Vendored copy synced (vendor-parity test)
  and wired in `dashboard/backend/main.py`. Docs in
  `docs/accuracy-testing.md`.
- **Accuracy testing API wiring (card c9825844)**: the accuracy_testing
  module (merged from cards 72f97f1b/ca3090d5) is mounted in the dashboard
  backend behind JWT auth, opt-in via `ACCURACY_TESTING_ENABLED=1` with
  `ACCURACY_SPLIT_SECRET` required (fail-closed mount). Owner-scoped
  endpoints (`GET /accuracy/benchmarks[/{id}]`,
  `POST /accuracy/sessions`, `GET /accuracy/sessions/{id}[/holdout]`) with
  an aggregate-only holdout contract (AC2 canary tests). Vendored copy
  under `dashboard/backend/src/` guarded by a vendor-parity test. Docs in
  `docs/accuracy-testing.md`.
- **QA Visual owner scoping + roles (S-1R)**: the router factory accepts a
  `get_current_principal` dependency returning a `QAVisualPrincipal`
  (`owner`, `is_admin`). The dashboard mounts the qa-visual router with
  `get_qa_visual_principal`, mapping `owner` to the authenticated username
  and `is_admin` to the existing `is_superuser` role. Reports are stamped
  with their owner at analyze time; `GET /reports`, `GET /reports/{id}`,
  `GET /trends` and `GET /baselines/{target}` are scoped to the caller,
  superusers see everything, and an authenticated non-owner reading
  someone else's report gets 403. Baseline/regression comparison never
  crosses owners. Reports persisted before owner-scoping (`owner` absent)
  are admin-only. Backward compatible: without `get_current_principal`
  the router keeps its legacy unscoped behaviour for standalone mounts.
- **QA Visual dashboard wiring (Fase C)**: the dashboard backend mounts the
  qa-visual router behind JWT auth (`Depends(get_current_user)`) — all five
  endpoints require authentication — gated behind `QA_VISUAL_ENABLED=1`
  (default off). With S-1R resolved the flag is now safe to enable in
  staging. The module is vendored at
  `dashboard/backend/src/infrastructure/qa_visual/` (Docker build context only
  ships `dashboard/backend`), guarded by a vendor-parity test that fails on
  drift between the two copies.
- **Dashboard test-suite collection fix**: empty `__init__.py` markers in
  `dashboard/backend/tests/`, `tests/services/` and `tests/unit/` fix the
  `import file mismatch` abort caused by nine duplicate test basenames;
  the full local suite (`python -m pytest tests/`) collects again.

### Fixed

- **Threshold threading (card c9825844)**: `compute_overall()` no longer
  hardcodes 0.6 — `AccuracyBenchmark.passing_threshold` flows into the pass
  decision via the evaluator (legacy 0.6 kept as backwards-compatible
  default when no threshold is threaded).

### Security

- **L-1 (card c9825844)**: `SplitPolicy.salt` is now required and non-empty
  (breaking); the API derives a per-tenant salt server-side
  (`HMAC-SHA256(ACCURACY_SPLIT_SECRET, tenant_id)`) — clients cannot send or
  choose a salt (422), and holdout membership is tenant-scoped.
- **L-2 (card c9825844)**: `AccuracyBenchmark.to_dict_full()` (exposes
  `ground_truth` + `tenant_id`) is served to admins only; sessions and
  benchmarks are owner-scoped (cross-tenant 404, holdout members 404 for
  non-admins).
- **AC2 (card c9825844)**: API responses serialize benchmarks via
  `to_dict()` and holdout results via `HoldoutSummary` only — canary tests
  fail on any `holdout_benchmarks` serialization or holdout-content leak.
- **S-1R (HIGH, CVSS 5.4)**: cross-tenant BOLA closed — the QA Visual
  report store was global, so any authenticated user could read, list,
  trend-analyse and baseline-compare other users' reports. Reports are now
  owner-scoped (see Added above); authorization is proven with real-JWT
  tests (403 non-owner / 200 owner / 200 admin) against the real mounted
  app.
- **S-1 (HIGH)**: router factory now accepts injectable `dependencies`;
  mounted in the dashboard with auth. Backward compatible (no dependencies
  by default).
- **S-2 (MEDIUM)**: upload hardening in `POST /analyze` — `Content-Length`
  pre-check before reading, chunked read capped at 10 MB (never loads an
  oversized file fully into memory), `image/png` content-type plus PNG
  magic-byte validation (415, no paid API calls on junk uploads).
- **S-3 (LOW)**: 502 responses no longer leak upstream gateway bodies or raw
  model output excerpts to HTTP clients (CWE-209); full detail is logged
  server-side only.
- **S-5 (LOW)**: `target` form field capped at 200 chars (422; 200 + the
  29-byte filename suffix stays under the 255-byte filesystem NAME_MAX,
  avoiding the uncontrolled OSError 500 that 227–255-char targets triggered).
- **S-7 (INFO)**: `reports/qa-visual/` runtime artifacts gitignored.
- **S-4 (LOW)**: data-handling policy documented in `docs/qa-visual.md`
  (screenshots egress to the external vision gateway; synthetic/test data
  only; GDPR Art. 32 note).

## [1.1.0] - 2026-08-22

### Added

- **QA Visual module** (`src/infrastructure/qa_visual/`): vision-model
  screenshot analysis productized from the Fase A spike (GO-NOGO approved).
  - `POST /api/v1/qa-visual/analyze` endpoint (FastAPI router factory) with
    multipart screenshot upload, threshold policy and structured QA reports.
  - JSON report storage under `reports/qa-visual/` with baseline support.
  - Playwright E2E post-test hook (`QAVisualHook`): screenshot -> vision
    analysis -> append to the test report; fail-soft by design.
  - Baseline visual regression detection (score drop >= 10 points or model
    regression flags).
  - Trends API (`GET /api/v1/qa-visual/trends`): score history plus
    degradation alerts as a dashboard data source.
  - Spike conditions C1-C5 enforced in code: thinking disabled by default,
    max_tokens >= 4000 guard when thinking on, browser User-Agent, model id
    via `QA_VISUAL_MODEL` env (exp -> GA ready), pricing pinned 2026-08-22
    ($0.22/$0.66 per 1M tokens) with per-analysis cost tracking.
  - Documentation: `docs/qa-visual.md` (setup, API, hook usage, cost model).
  - Unit tests: 114 tests for the module, 96% coverage, no network required
    (`httpx.MockTransport` for the gateway).

## [1.0.0] - 2026-08-22 (baseline)

Previous history prior to the QA Visual module. See git log for details.
