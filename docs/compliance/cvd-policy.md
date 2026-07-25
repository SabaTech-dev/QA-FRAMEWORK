# Coordinated Vulnerability Disclosure (CVD) Policy

**Version:** 1.0
**Effective Date:** 2026-09-11
**Last Updated:** 2026-07-24
**Owner:** Jose Manuel Sabarís García (Tech Lead)
**Legal Basis:** Cyber Resilience Act (Regulation (EU) 2024/2847), Article 13(8) and Annex I, Part II, point (5)
**Applicable To:** QA-FRAMEWORK and all SabaTech products with digital elements

---

## 1. Purpose

This Coordinated Vulnerability Disclosure (CVD) Policy establishes the framework for receiving, evaluating, and remediating security vulnerabilities reported by internal teams, external researchers, and users. It fulfills the vulnerability handling requirements mandated by **Article 13(8)** of the Cyber Resilience Act (CRA) and **Annex I, Part II, point (5)**, which require manufacturers to have appropriate policies and procedures to process and remediate potential vulnerabilities reported from internal or external sources.

## 2. Scope

This policy applies to:

- **QA-FRAMEWORK** — SaaS platform (qa.sabatech.dev), backend API (FastAPI), frontend dashboard (Vite+React)
- **SabaTrace** — Traceability platform
- **Saba Agent OS** — Agentic infrastructure (OpenClaw-based)
- **SabaTech.dev** — Corporate website
- All software components, dependencies, and infrastructure operated by SabaTech

## 3. Reporting a Vulnerability

### 3.1 Contact Channel

| Channel | Use | Response Time |
|---------|-----|---------------|
| **security@sabatech.dev** | Primary — all vulnerability reports | ≤ 48 hours (acknowledgment) |
| **GitHub Security Advisories** | Project-specific reports on SabaTech-dev repos | ≤ 48 hours (acknowledgment) |
| **PGP-encrypted email** | Sensitive reports (request key first) | ≤ 48 hours (acknowledgment) |

**Single Point of Contact (per CRA Art. 13(17)):**

```
security@sabatech.dev
Jose Manuel Sabarís García
SabaTech
```

This contact is publicly listed in:
- `SECURITY.md` in all SabaTech-dev repositories
- `docs/compliance/cvd-policy.md` (this document)
- User documentation and onboarding materials
- Corporate website footer

### 3.2 What to Include in a Report

Vulnerability reports should include:

1. **Description** of the vulnerability and affected component
2. **Steps to reproduce** (PoC if available)
3. **Impact assessment** — what an attacker could achieve
4. **Suggested mitigation** (if known)
5. **Reporter contact details** (for follow-up and credit)

### 3.3 PGP Key

For sensitive reports, use our PGP key:

```
Request key from: security@sabatech.dev
Fingerprint: [TO BE GENERATED — see Implementation Checklist §7]
```

## 4. Response SLA

SabaTech commits to the following response times for vulnerability reports:

| Severity | CVSS v3.1 | Acknowledgment | Triage | Fix or Mitigation | Public Disclosure |
|----------|-----------|----------------|--------|-------------------|-------------------|
| **Critical** | 9.0–10.0 | 24 hours | 48 hours | 7 days (patch) or 24 hours (mitigation) | 90 days |
| **High** | 7.0–8.9 | 48 hours | 5 days | 30 days | 120 days |
| **Medium** | 4.0–6.9 | 72 hours | 14 days | 60 days | 180 days |
| **Low** | 0.1–3.9 | 7 days | 30 days | Next release | Best effort |

### 4.1 Severity Calibration

Severity is assessed using **CVSS v3.1** per the FIRST.org standard. SabaTech reserves the right to adjust severity based on:
- Actual exploitability in production environment
- Data sensitivity at risk
- Number of affected users
- Existence of mitigating controls

## 5. Coordinated Disclosure Process

### 5.1 Principles

1. **We do not pursue legal action** against good-faith security research
2. **We acknowledge** all legitimate reports promptly
3. **We collaborate** with researchers on timelines and disclosure
4. **We credit** researchers (opt-in) in release notes and security advisories
5. **We publish** advisories after fix is available (or per agreed timeline)

### 5.2 Timeline

```
Day 0:  Report received → Acknowledgment within 24-72h
Day 1-5: Triage and severity assessment
Day 5+: Fix development (timeline per severity)
Fix+14: Security advisory published (GHSA + CVE request)
Fix+30: Public disclosure (unless embargo agreed)
```

### 5.3 Safe Harbor

SabaTech provides **safe harbor** for vulnerability research conducted in good faith, provided:
- Researcher does not access, modify, or delete data belonging to others
- Researcher does not degrade service availability
- Researcher reports findings exclusively to security@sabatech.dev before public disclosure
- Researcher adheres to the disclosure timeline in §5.2

## 6. CRA-Compliant Vulnerability Handling

### 6.1 Internal Vulnerability Discovery (CRA Art. 13(6))

When SabaTech identifies a vulnerability in a component (including open-source dependencies):
1. Report the vulnerability to the upstream maintainer
2. Develop a patch or mitigation
3. Share the fix with the upstream project (per CRA Art. 13(6))
4. Document in the Risk Register (`docs/security/RISK_REGISTER.md`)

### 6.2 Actively Exploited Vulnerabilities (CRA Art. 14(1))

If a vulnerability in our product is being **actively exploited**, SabaTech must:
1. **Notify** the CSIRT designated as coordinator (INCIBE-CERT for Spain) and ENISA **without undue delay**
2. Submit via the **single reporting platform** (operated by ENISA, available from Sept 2026)
3. Notify impacted users with mitigation guidance (CRA Art. 14(8))

**CSIRT for Spain:** INCIBE-CERT (https://www.incibe.es/incibe-cert)
**Coordinating CSIRT:** Determined by main establishment (Spain)

### 6.3 Vulnerability Documentation (CRA Art. 13(7))

All discovered vulnerabilities are systematically documented in:
- **GitHub Security Advisories** (per-repo)
- **Risk Register** (`docs/security/RISK_REGISTER.md`)
- **Security Advisories** published on GitHub

### 6.4 Support Period (CRA Art. 13(8))

| Product | Support Period | End Date |
|---------|---------------|----------|
| QA-FRAMEWORK | 5 years from v1.0 release | TBD (v1.0 pending) |
| SabaTrace | 5 years from v1.0 release | TBD |

Security updates are guaranteed for the support period. End-of-support date is communicated to users at least 6 months in advance.

### 6.5 SBOM (CRA Annex I, Part II, point (1))

A Software Bill of Materials (SBOM) is maintained for each product and available upon request to market surveillance authorities. Generated via:
- `pip-audit` for Python dependencies
- `npm audit` for Node.js dependencies
- Trivy for Docker images

## 7. Implementation Checklist

- [ ] **PGP key pair** generated and published (security@sabatech.dev)
- [ ] **GitHub Security Advisories** enabled on all SabaTech-dev repos
- [ ] **SECURITY.md** created in all repos (referencing this policy)
- [ ] **INCIBE-CERT** contact verified (Spain's CSIRT coordinator)
- [ ] **ENISA single reporting platform** account created (when available)
- [ ] **security@sabatech.dev** mailbox verified (forwarding to jmsabaris@sabatech.dev)

## 8. Governance

| Role | Responsibility |
|------|---------------|
| **Tech Lead (Joker)** | Policy owner, final decisions on severity and disclosure |
| **Security Agent (Alfred)** | Triage, assessment, CVE requests, advisory drafting |
| **Coder Agent** | Fix implementation |
| **DevOps Agent** | Fix deployment and user notification |

## 9. References

- **Cyber Resilience Act:** Regulation (EU) 2024/2847, Articles 13, 14; Annex I Part II
- **NIS2 Directive:** Directive (EU) 2022/2555, Article 12 (CVD procedures)
- **ISO/IEC 29147:** Vulnerability disclosure standard
- **ISO/IEC 30111:** Vulnerability handling processes
- **FIRST.org CVSS v3.1:** Severity scoring
- **INCIBE-CERT:** Spanish CSIRT — https://www.incibe.es/incibe-cert
- **EU CSIRTs Network:** https://csirtsnetwork.eu/
- **Related docs:** `SECURITY_POLICY.md`, `INCIDENT_RESPONSE_PLAYBOOK.md`, `incident-reporting-procedure.md`

## 10. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-07-24 | Initial CVD policy (CRA compliance) |

---

**Contact:** security@sabatech.dev
**Public URL:** https://github.com/SabaTech-dev/QA-FRAMEWORK/blob/main/docs/compliance/cvd-policy.md
