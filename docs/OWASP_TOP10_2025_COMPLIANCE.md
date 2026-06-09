# OWASP Top 10:2025 Compliance Matrix — QA-FRAMEWORK

**Generated:** 2026-06-05 | **Version:** 1.0 | **Author:** Security Agent

## Overview

This document maps QA-FRAMEWORK's security controls against the OWASP Top 10:2025 categories.

### Key 2025 Changes
- **A03:** Supply Chain Attacks (NEW category)
- **A10:** Mishandling of Exceptional Conditions (NEW, replaces SSRF)
- **SSRF** absorbed into Broken Access Control (A01)
- **Security Misconfiguration** moved to #2

---

## Compliance Matrix

| OWASP Category | Risk | Control | Tool/Implementation | Status | Evidence |
|---|---|---|---|---|---|
| **A01: Broken Access Control** | HIGH | RBAC middleware | `src/api/middleware/rbac_middleware.py` | ✅ PASS | RBAC + tenant isolation enforced |
| | | Tenant isolation | `src/api/middleware/tenant_context.py` | ✅ PASS | Multi-tenant context middleware |
| | | SSRF protection | URL allowlist validation in HTTP clients | ✅ PASS | `url_validator.py` + `httpx_client.py` + `base_oauth.py` |
| | | Hardcoded credentials | Gitleaks + Semgrep + test suite | ✅ PASS | Automated scanning |
| **A02: Cryptographic Failures** | MEDIUM | TLS enforcement | HTTPS in production configs | ✅ PASS | No HTTP URLs in src (excl. localhost) |
| | | Strong hashing | No MD5/SHA1 for security purposes | ✅ PASS | Semgrep rule active |
| **A03: Injection (+ Supply Chain)** | HIGH | SQL injection | SQLAlchemy ORM + parameterized queries | ✅ PASS | SQL injection tester exists |
| | | Code injection | No eval/exec usage | ✅ PASS | Semgrep + test suite |
| | | Dependency pinning | `poetry.lock` | ✅ PASS | Lockfile present |
| | | Supply chain scanning | Trivy + pip-audit + SBOM | ✅ PASS | CI/CD integrated |
| **A04: Insecure Design** | MEDIUM | Input validation | Pydantic models | ✅ PASS | Domain entities use Pydantic |
| | | Rate limiting | — | ⚠️ WARN | No explicit rate limiting detected |
| **A05: Security Misconfiguration** | HIGH | DEBUG off in prod | Test + Semgrep rule | ✅ PASS | DEBUG=True not found in src |
| | | No default secrets | Test suite check | ✅ PASS | Gitleaks + test |
| | | CORS configuration | — | ⚠️ REVIEW | Check CORS origins not wildcard |
| | | Security headers | — | ⚠️ WARN | No security headers middleware found |
| **A06: Vulnerable Components** | HIGH | Trivy scanning | `.github/workflows/trivy-security.yml` | ✅ PASS | FS + image + IaC scanning |
| | | Bandit (SAST) | `ci-cd.yml` | ✅ PASS | JSON report generated |
| | | pip-audit | `ci-cd.yml` | ✅ PASS | Dependency vulnerability check |
| | | SBOM generation | Trivy + Syft (CycloneDX + SPDX) | ✅ PASS | Dual format SBOM |
| **A07: Auth Failures** | HIGH | Auth domain | `src/domain/auth/` | ✅ PASS | Entities + value objects |
| | | Password hashing | Review needed | ⚠️ REVIEW | Verify bcrypt/argon2 usage |
| **A08: Data Integrity** | MEDIUM | SBOM integrity | Trivy + Syft | ✅ PASS | SPDX + CycloneDX |
| | | CI action pinning | SHA pinning in all workflow files | ✅ PASS | All 9 workflows pinned to SHAs; `trivy-action@master`→SHA, `pr-agent@main`→SHA |
| **A09: Logging Failures** | MEDIUM | Logging infra | `src/infrastructure/logger/` | ✅ PASS | Logger module exists |
| | | Auth audit logs | Auth domain | ✅ PASS | Logging in auth events |
| **A10: Exceptional Conditions** (NEW) | HIGH | Global error handler | FastAPI integration | ✅ PASS | Exception handling present |
| | | No bare except | Test suite + Semgrep | ✅ PASS | Automated check |
| | | No stack traces in prod | Test suite | ✅ PASS | Verified |

---

## Security Tools Matrix

| Tool | Purpose | Workflow | Frequency |
|---|---|---|---|
| **Trivy** | Vuln + secret + misconfig scanning | `trivy-security.yml` | Every push + daily |
| **Bandit** | Python SAST | `ci-cd.yml` | Every push |
| **pip-audit** | Dependency vulnerabilities | `ci-cd.yml` | Every push |
| **Semgrep** | OWASP-aware SAST | `owasp-security.yml` | Every push + weekly |
| **Gitleaks** | Secret scanning | `owasp-security.yml` | Every push |
| **Syft** | SBOM generation | `owasp-security.yml` | Every push |
| **OWASP Tests** | Category compliance | `owasp-security.yml` | Every push + weekly |

---

## Recommendations

1. **Add rate limiting middleware** (A04) — Use `slowapi` or FastAPI built-in middleware
2. **Add security headers middleware** (A05) — `X-Content-Type-Options`, `X-Frame-Options`, `CSP`, `HSTS`
3. **Pin GitHub Actions to SHA** (A08) — Use commit hashes instead of tags
4. **Verify password hashing algorithm** (A07) — Ensure bcrypt or argon2 is used
5. **Review CORS configuration** (A05) — Ensure origins are explicit, not wildcard
6. **✅ Add SSRF allowlist** (A01) — Implemented in `src/core/security/url_validator.py`, integrated in `httpx_client.py` and `base_oauth.py`
7. **✅ Pin GitHub Actions to SHA** (A08) — All 9 workflow files pinned to commit SHAs

---

## Test Execution

```bash
# Run OWASP compliance tests
pytest tests/security/test_owasp_top10_2025.py -v

# Run Semgrep locally
semgrep --config .semgrep.yml src/

# Run Gitleaks locally
gitleaks detect --source . --config .gitleaks.toml

# Generate SBOM locally
syft . -o cyclonedx-json > sbom.json
```
