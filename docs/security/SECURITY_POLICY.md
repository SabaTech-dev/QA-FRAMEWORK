# Security Policy — QA-FRAMEWORK

**Version:** 1.0 | **Last Updated:** 2026-07-09 | **Owner:** Jose Manuel Sabarís (Tech Lead)

## Overview

QA-FRAMEWORK is an agentic QA automation SaaS that uses AI models for test generation, vulnerability analysis, and code review. This policy defines the security commitments and controls for all deployments.

## Scope

This policy applies to:
- QA-FRAMEWORK production deployment (qa.sabatech.dev)
- Backend API (FastAPI, port 8010)
- Frontend dashboard (Vite+React, port 3010)
- Supporting infrastructure (PostgreSQL, Redis, Prometheus, Grafana)

## Security Principles

1. **Secure by Default** — All endpoints require authentication. CORS restricted to known origins.
2. **Least Privilege** — Service accounts and API keys have minimum required permissions.
3. **Defense in Depth** — Multiple layers: network (Tailscale), application (auth), data (encryption).
4. **AI Transparency** — All AI-generated results include disclosure per EU AI Act Art. 50(1).
5. **Open Source First** — Security tools are open-source and auditable.

## Access Control

| Role | Access | Authentication |
|------|--------|---------------|
| Admin | Full system, Docker, configs | SSH key + Tailscale |
| User | Dashboard, API endpoints | JWT (HS256, 24h expiry) |
| Service | Internal API calls | API key (per-service) |

## Vulnerability Management

- **SAST:** Semgrep + Bandit on every PR (GitHub Actions)
- **DAST:** OWASP ZAP weekly scan
- **Dependencies:** Trivy + pip-audit on every build
- **Disclosure:** Security issues → security@sabatech.dev (PGP optional)
- **SLA:** Critical (24h), High (72h), Medium (7d), Low (30d)

## Data Protection

- **At Rest:** PostgreSQL with encrypted connections (TLS 1.3)
- **In Transit:** HTTPS only (Cloudflare tunnel + nginx TLS)
- **Backups:** Daily PostgreSQL dumps (30-day retention)
- **Retention:** User data deleted on account termination + 30-day grace

## AI-Specific Security

- **Prompt Injection:** User inputs are sanitized before LLM processing. LLM outputs are validated against JSON schemas.
- **Model Isolation:** LLM inference runs on dedicated llama.cpp instance (port 8001), not exposed externally.
- **Tool Calling:** Agent tools have explicit allowlists. No arbitrary code execution from LLM output.

## Incident Response

See `INCIDENT_RESPONSE_PLAYBOOK.md` for runbooks.

## Compliance

- **NIST CSF 2.0:** See `nist-csf-2.0-mapping.md` for coverage details
- **EU AI Act:** See `EU_AI_ACT_COMPLIANCE.md` for gap analysis
- **OWASP Top 10:2025:** Mapped and tracked

## Contact

- **Security Lead:** Jose Manuel Sabarís — jmsabaris@sabatech.dev
- **PGP:** Available on request
- **Response Time:** 48h maximum for security inquiries

---

*This document is versioned in git. Changes require PR review.*
