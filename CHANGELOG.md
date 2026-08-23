# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
