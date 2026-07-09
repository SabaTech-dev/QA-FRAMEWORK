# Risk Register — QA-FRAMEWORK

**Version:** 1.0 | **Last Updated:** 2026-07-09 | **Owner:** Tech Lead

## Methodology

Risks scored on Likelihood (1-5) × Impact (1-5) = Score (1-25).
- 🔴 Critical: 15-25 (immediate action)
- 🟠 High: 10-14 (action within 30 days)
- 🟡 Medium: 5-9 (action within 90 days)
- 🟢 Low: 1-4 (monitor)

## Active Risks

| ID | Risk | Likelihood | Impact | Score | Status | Mitigation |
|----|------|-----------|--------|-------|--------|------------|
| R-001 | Prompt injection via user-submitted test cases | 3 | 4 | 12 🟠 | Open | Input sanitization + output schema validation. LLM does not have arbitrary code execution access. |
| R-002 | LLM API unavailability (llama.cpp downtime) | 2 | 4 | 8 🟡 | Open | Fallback model chain configured. Health check every 5min. Auto-restart on failure. |
| R-003 | Database data loss (PostgreSQL corruption) | 1 | 5 | 5 🟡 | Mitigated | Daily automated backups (30-day retention). WAL archiving enabled. |
| R-004 | Unauthorized API access (token leak) | 2 | 4 | 8 🟡 | Mitigated | JWT 24h expiry. API keys rotated every 90 days. Rate limiting (100 req/min). |
| R-005 | Supply chain attack (dependency compromise) | 2 | 5 | 10 🟠 | Open | Dependabot + Trivy on every build. SHA-pinned GitHub Actions. Lockfile enforced. |
| R-006 | Cloudflare tunnel outage (loss of public access) | 1 | 3 | 3 🟢 | Accepted | Cloudflare SLA 99.9%. No alternative ingress needed at current scale. |
| R-007 | GPU memory exhaustion (V100 32GB full) | 2 | 3 | 6 🟡 | Mitigated | Model unloading on idle configured. Single-model-at-a-time policy. |
| R-008 | EU AI Act non-compliance fines | 1 | 5 | 5 🟡 | In Progress | Gap analysis underway. Deadline 2-Aug-2026. Disclosure banner being implemented. |
| R-009 | Self-hosted runner compromise | 2 | 4 | 8 🟡 | Open | Runners share user `joker`. Containerization planned (M-3 from GitLost audit). |
| R-010 | CORS misconfiguration exposing API | 1 | 3 | 3 🟢 | Mitigated | CORS restricted to known origins (localhost, qa.sabatech.dev). |

## Retired Risks

| ID | Risk | Resolution | Date |
|----|------|-----------|------|
| R-R1 | PR-Agent PAT org-wide exfiltration | Replaced JOKERSERVER_PAT with GITHUB_TOKEN (repo-scoped) | 2026-07-09 |
| R-R2 | open-code-review pull_request_target secret exposure | Changed to pull_request trigger | 2026-07-09 |
| R-R3 | .secrets.toml world-readable (0644) | chmod 600 | 2026-07-09 |

## Review Cadence

- **Monthly:** Full risk register review
- **On Incident:** Add new risks, update existing
- **Quarterly:** Threat model refresh

---

*This document is versioned in git. Changes require PR review.*
