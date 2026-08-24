# CI Test Coverage Inventory

**Generated:** 2026-08-24  
**Context:** Card 5ec904d4 — CI gap: middleware tests not running in CI  
**Status:** Dashboard backend middleware tests ADDED to CI (ci-cd.yml + pr-checks.yml)

---

## ✅ Test Suites Currently Running in CI

| Test Suite | Workflow | Job | Trigger |
|------------|----------|-----|---------|
| `tests/unit` | ci-cd.yml | `unit-tests` | push, PR, schedule |
| `tests/integration` | ci-cd.yml | `integration-tests` | push, PR, schedule |
| `tests/performance` | ci-cd.yml | `performance-tests` | schedule, `[perf]` commit |
| `tests/security` | ci-cd.yml | `security-tests` | push, PR, schedule |
| `dashboard/tests/e2e` (Playwright) | ci-cd.yml | `e2e-tests` | push, PR, schedule |
| `dashboard/tests/performance` (Locust) | ci-cd.yml | `e2e-tests` | push, PR, schedule |
| **`dashboard/backend/tests/middleware`** | **ci-cd.yml + pr-checks.yml** | **`dashboard-middleware-tests`** | **push, PR, schedule** |

---

## ❌ Test Suites NOT Running in CI (Gap Inventory)

| Test Directory | Estimated Tests | Type | Notes |
|----------------|-----------------|------|-------|
| `dashboard/tests/regression` | ~5-10 | Regression | Small, could add to e2e-tests |
| `dashboard/backend/tests/unit` | ~20-30 | Unit (backend-specific) | Separate from root `tests/unit` |
| `dashboard/backend/tests/core` | ~15-20 | Core functionality | Query optimizer, feature flags, smart cache, metrics |
| `dashboard/backend/tests/services` | ~50-80 | Service layer | 15+ service test files |
| `dashboard/backend/tests/infrastructure` | ~5-10 | Infrastructure | Cache, backup tests |
| `dashboard/backend/tests/integration` | ~5-10 | Integration | Cron routes |
| `dashboard/backend/tests/integration_clients` | ~5-10 | Integration | Jira, Azure DevOps, ALM clients |

**Total untested in CI: ~105-170 tests** (backend-heavy)

---

## Recommendations

### Priority 1: Dashboard Backend Unit Tests (`dashboard/backend/tests/unit`, `core`, `services`)
- **Why:** These are the core business logic tests for the dashboard backend
- **Effort:** Add a new job `dashboard-backend-unit-tests` similar to `dashboard-middleware-tests`
- **Dependencies:** Requires `dashboard/backend/requirements.txt` + test database (postgres) for some tests

### Priority 2: Dashboard Backend Integration Tests (`dashboard/backend/tests/integration`, `integration_clients`)
- **Why:** Test external integrations (Jira, Azure DevOps, ALM)
- **Effort:** Requires mock servers or test credentials; could run in nightly only

### Priority 3: Regression Tests (`dashboard/tests/regression`)
- **Why:** Small suite, easy win
- **Effort:** Add to existing `e2e-tests` job

---

## Implementation Notes

### Middleware Tests (NOW DONE)
Added to:
- **ci-cd.yml**: New job `dashboard-middleware-tests` (runs after `code-quality`, before `unit-tests`)
- **pr-checks.yml**: Conditional step in `dashboard-middleware-tests` job (runs only when `dashboard/backend/**` files changed)

**Command used:**
```bash
cd dashboard/backend && python -m pytest tests/middleware -v --junitxml=junit-middleware.xml
```

**Dependencies:** `dashboard/backend/requirements.txt` (pip, not poetry)

---

## Follow-up Cards to Create

1. **P3** — Add `dashboard/backend/tests/unit` + `core` + `services` to CI
2. **P3** — Add `dashboard/backend/tests/integration` + `integration_clients` to CI (nightly only)
3. **P3** — Add `dashboard/tests/regression` to CI (extend e2e-tests)