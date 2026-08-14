# CI/CD Pipeline Documentation

## Overview

The QA Framework includes a comprehensive CI/CD pipeline with multiple stages for quality assurance, testing, and deployment.

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      TRIGGER                                │
│         Push │ PR │ Schedule │ Manual                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 1: Code Quality                                      │
│  ├── Black (formatting)                                     │
│  ├── Ruff (linting)                                         │
│  ├── isort (imports)                                        │
│  ├── MyPy (type checking)                                   │
│  ├── Bandit (security)                                      │
│  └── Safety (dependencies)                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 2: Unit Tests (Parallel)                            │
│  ├── Python 3.11                                             │
│  └── Python 3.12                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 3: Integration Tests                                │
│  ├── PostgreSQL                                             │
│  ├── Redis                                                  │
│  └── External Services                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 4: E2E Tests                                        │
│  └── Playwright (Chromium)                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 5: Security Tests                                   │
│  ├── Bandit (SAST)                                          │
│  ├── Semgrep (SAST)                                         │
│  └── Safety (Dependency Scan)                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 6: Performance Tests (Conditional)                  │
│  └── Locust + pytest-benchmark                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 7: Coverage Analysis                                │
│  ├── Combine reports                                        │
│  └── Upload to Codecov                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 8: Documentation                                     │
│  └── Build MkDocs                                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 9: Package Build                                     │
│  └── Build & Verify                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 10: Notifications                                    │
│  ├── Slack (Success/Failure)                                │
│  └── PR Comments                                            │
└─────────────────────────────────────────────────────────────┘
```

## Workflow Files

### 1. Main CI/CD Pipeline (`ci-cd.yml`)

Triggered on:
- Push to `main`, `develop`, or `feature/*` branches
- Pull requests to `main` or `develop`
- Daily schedule (2 AM UTC)

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop, feature/* ]
  pull_request:
    branches: [ main, develop ]
  schedule:
    - cron: '0 2 * * *'
```

### 2. PR Checks (`pr-checks.yml`)

Lightweight checks for fast feedback on PRs:
- Code quality checks only
- Tests for changed files only
- PR size warnings
- Automatic PR comments

### 3. Nightly Tests (`nightly.yml`)

Comprehensive test suite running daily:
- All Python versions
- All test types
- Benchmark collection
- Nightly reports
- Issue creation on failure

## Stage Details

### Stage 1: Code Quality

Validates code style, types, and security:

```yaml
code-quality:
  steps:
    - Run Black (formatting check)
    - Run Ruff (linting)
    - Run isort (import sorting)
    - Run MyPy (type checking)
    - Run Bandit (security linting)
    - Run Safety (vulnerability check)
```

**Key Points:**
- Black: Line length 100
- Ruff: Python 3.12 target
- MyPy: Strict mode
- Bandit: JSON output for reports
- Safety: Dependency vulnerability scanning

### Stage 2: Unit Tests

Runs unit tests in parallel across Python versions:

```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12"]
```

**Commands:**
```bash
pytest tests/unit -v \
  -m "not integration and not e2e and not performance and not security" \
  --cov=src \
  --cov-report=xml \
  --cov-report=html \
  -n auto
```

### Stage 3: Integration Tests

Tests with real services (PostgreSQL, Redis):

```yaml
services:
  postgres:
    image: postgres:15
  redis:
    image: redis:7-alpine
```

**Features:**
- Service health checks
- Environment variables for connections
- Coverage reporting

### Stage 4: E2E Tests

End-to-end tests using Playwright:

```yaml
steps:
  - Install Playwright dependencies
  - Install browsers (chromium)
  - Run E2E tests in headless mode
```

### Stage 5: Security Tests

Static Application Security Testing (SAST):

```yaml
security-tests:
  steps:
    - Run Bandit
    - Run Semgrep
    - Run Safety
```

### Stage 6: Performance Tests

Conditional execution (daily or `[perf]` in commit):

```yaml
if: github.event_name == 'schedule' || contains(github.event.head_commit.message, '[perf]')
```

### Stage 7: Coverage Analysis

Combines coverage from all test stages:

```yaml
coverage-analysis:
  needs: [unit-tests, integration-tests]
  steps:
    - Download coverage reports
    - Combine with coverage combine
    - Upload to Codecov
```

**Coverage Thresholds:**
- Fail if coverage < 80%
- HTML reports generated
- XML reports for Codecov

### Stage 8: Documentation

Builds documentation with MkDocs:

```yaml
documentation:
  steps:
    - Install mkdocs-material
    - Build docs
    - Upload artifacts
```

### Stage 9: Package Build

Builds and verifies the package:

```yaml
build-package:
  steps:
    - Build with python -m build
    - Verify with twine check
    - Upload dist/ artifacts
```

### Stage 10: Notifications

Slack notifications for pipeline status:

```yaml
notify:
  steps:
    - Summarize test results
    - Notify Slack on failure
    - Notify Slack on success
```

## Caching Strategy

The pipeline uses aggressive caching for faster builds:

```yaml
- name: Cache pip packages
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ env.CACHE_VERSION }}-${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
```

**Cached Items:**
- pip packages
- Playwright browsers
- pre-commit hooks

## Secrets Required

Configure these secrets in GitHub:

```bash
SLACK_WEBHOOK_URL          # For notifications
CODECOV_TOKEN             # For coverage uploads
TEST_DATABASE_URL         # Integration tests
TEST_REDIS_URL           # Integration tests
```

## Local Testing

Run the same checks locally:

```bash
# Code quality
black --check --diff --line-length 100 src tests
ruff check src tests
mypy src --strict

# Unit tests
pytest tests/unit -v -n auto

# Integration tests (requires services)
docker-compose up -d postgres redis
pytest tests/integration -v

# E2E tests
playwright install chromium
pytest tests/e2e -v

# Security tests
bandit -r src
safety check

# Coverage
pytest --cov=src --cov-report=html
```

## Performance Optimization

### Parallel Execution

Use pytest-xdist for parallel test execution:

```bash
pytest -n auto        # Auto-detect CPU count
pytest -n 4           # Use 4 workers
pytest -n logical     # Use logical CPUs
```

### Selective Testing

Run only relevant tests:

```bash
pytest -m unit        # Only unit tests
pytest -m integration # Only integration tests
pytest -k "test_user" # Tests matching pattern
```

### Artifact Retention

Configure artifact retention in workflow:

```yaml
uses: actions/upload-artifact@v4
with:
  name: test-results
  path: test-results/
  retention-days: 30
```

## Troubleshooting

### Common Issues

**Issue: Tests timeout**
```yaml
# Add timeout to pytest
pytest --timeout=300
```

**Issue: Service not ready**
```yaml
# Add wait step
- name: Wait for services
  run: sleep 10
```

**Issue: Cache not hitting**
```bash
# Clear cache by updating CACHE_VERSION
env:
  CACHE_VERSION: v2  # Increment when needed
```

## Best Practices

1. **Fail Fast**: Use `-x` flag to stop on first failure
2. **Conditional Jobs**: Skip expensive jobs on PRs
3. **Matrix Strategy**: Test multiple versions/configurations
4. **Artifact Uploads**: Always upload logs and reports
5. **Notifications**: Alert on failures only
6. **Secrets Management**: Never log secrets
7. **Timeouts**: Set reasonable job timeouts

## Monitoring

Monitor pipeline health:

```bash
# View recent runs
gh run list

# View specific run
gh run view <run-id>

# Download artifacts
gh run download <run-id>
```

## Future Enhancements

- [ ] Docker image builds
- [ ] Multi-platform testing (Windows, macOS)
- [ ] Chaos engineering tests
- [ ] Visual regression testing
- [ ] Accessibility testing
- [ ] Load testing in staging
- [ ] Blue-green deployments
