# 🚀 QA-FRAMEWORK — Beta Onboarding

Welcome to the **QA-FRAMEWORK Beta**! This guide will get you set up and running in minutes.

## 📋 Quick Links

| Recurso | URL |
|---|---|
| Dashboard | https://qa-framework.sabatech.dev |
| API Docs | https://qa-framework.sabatech.dev/api/v1/docs |
| API Status | https://qa-framework.sabatech.dev/api/v1/health |
| GitHub | https://github.com/SabaTech-dev/QA-FRAMEWORK |

## 🎯 What Is QA-FRAMEWORK?

A comprehensive testing and quality assurance platform that provides:
- **Multi-framework test execution** — pytest, Playwright, Selenium, and custom runners
- **Parallel execution** — Run tests in parallel with full isolation and resource management
- **AI-powered analysis** — Smart flaky detection, root cause analysis, test optimization
- **Integrations** — Jira, Azure DevOps, TestLink, Zephyr, ALM
- **Granular reporting** — Allure, HTML, JSON, SBOM
- **Security scanning** — OWASP Top 10:2025, Trivy, Bandit, Semgrep, Gitleaks
- **CI/CD integrated** — GitHub Actions pipelines with security gates

## 📝 Getting Started

### 1. Sign Up
1. Go to https://qa-framework.sabatech.dev/signup
2. Complete the registration form
3. Verify your email
4. You'll receive a confirmation with your API key

### 2. Install the CLI (optional)
```bash
pip install git+https://github.com/SabaTech-dev/QA-FRAMEWORK.git
```

### 3. Configure Your First Project
```bash
qa-framework init --project "My Project" --api-key <your-api-key>
```

### 4. Run Your First Test
```python
# test_example.py
import pytest

class TestMyFeature:
    def test_hello(self):
        assert True  # Your test goes here
```

## 🔑 API Keys

| Plan | Rate Limit (hourly) | Burst | Features |
|---|---|---|---|
| **Beta Free** | 1,000 req/h | 50/min | Core features, community support |
| **Beta Pro** | 10,000 req/h | 200/min | All integrations, AI analysis |
| **Enterprise** | Custom | Custom | On-premise, dedicated support |

## 🛡️ Security

- All endpoints are HTTPS-only (TLS 1.3)
- API keys must be sent via `Authorization: Bearer <key>` header
- Rate limiting is enforced per plan
- Data at rest encrypted with AES-256
- SBOM generated daily for dependency tracking

## 🆘 Support

| Channel | Method |
|---|---|
| Issues | https://github.com/SabaTech-dev/QA-FRAMEWORK/issues |
| Discord | https://discord.gg/sabatech (invite pending) |

## 📊 Dashboard Features

| Feature | Status |
|---|---|
| Project Management | ✅ Available |
| Execution Dashboard | ✅ Available |
| Test Case Management | ✅ Available |
| Analytics & Reports | ✅ Available |
| Integration Management | ✅ Available |
| User Management | ✅ Available |
| Waitlist | ✅ Active |

## 🔄 CI/CD Integration

```yaml
# .github/workflows/qa-framework.yml
name: QA-Framework Scan
on: [push]
jobs:
  qa-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run QA-Framework
        uses: SabaTech-dev/QA-FRAMEWORK@v1
        with:
          api-key: ${{ secrets.QA_API_KEY }}
```

## 🚨 Known Beta Limitations

1. **Concurrent users**: Max 25 concurrent in beta
2. **Execution timeout**: 10 min per test suite
3. **Storage**: 500MB per project
4. **Historical data**: Retained for 30 days
5. **Email delivery**: May experience delays during onboarding surge

## 📈 Beta Program Timeline

| Milestone | Date |
|---|---|
| Beta Start | 2026-06-11 |
| Feedback Window | 2026-06-11 → 2026-07-11 |
| Feature Freeze | 2026-07-15 |
| Public Launch | 2026-07-30 |

## ✅ Checklist for Beta Testers

- [ ] Register at https://qa-framework.sabatech.dev/signup
- [ ] Verify your email
- [ ] Generate your first API key
- [ ] Connect a project
- [ ] Run your first test suite
- [ ] Explore integrations (Jira, TestLink, etc.)
- [ ] Provide feedback via GitHub Issues

---

*Thank you for participating in the QA-FRAMEWORK Beta!*

**SabaTech Team** — https://github.com/SabaTech-dev
