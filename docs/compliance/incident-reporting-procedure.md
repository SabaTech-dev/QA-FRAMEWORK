# Cyber Resilience Act — Incident Reporting Procedure

**Version:** 1.0
**Effective Date:** 2026-09-11
**Last Updated:** 2026-07-24
**Owner:** Jose Manuel Sabarís García (Tech Lead)
**Legal Basis:** Cyber Resilience Act (Regulation (EU) 2024/2847), Article 14
**Applicable To:** QA-FRAMEWORK and all SabaTech products with digital elements
**Reporting Obligations Apply From:** 11 September 2026

---

## 1. Purpose

This procedure defines the **mandatory incident reporting process** required by **Article 14 of the Cyber Resilience Act (CRA)**. It establishes timelines, roles, templates, and escalation paths for reporting severe security incidents and actively exploited vulnerabilities to the competent authorities.

## 2. Legal Requirements Summary

### 2.1 What Must Be Reported

| Trigger | Reporting Obligation | Timeline |
|---------|---------------------|----------|
| **Actively exploited vulnerability** in our product (CRA Art. 14(1)) | Notify CSIRT coordinator + ENISA via single reporting platform | Without undue delay |
| **Severe incident** impacting product security (CRA Art. 14(3)) | Three-stage reporting (see §3 below) | 24h → 72h → 1 month |

### 2.2 What Constitutes a "Severe Incident" (CRA Art. 14(5))

An incident is **severe** if it meets ANY of:

- **(a)** It negatively affects (or could affect) the product's ability to protect the **availability, authenticity, integrity, or confidentiality** of sensitive or important data or functions
- **(b)** It has led (or could lead) to the **introduction or execution of malicious code** in the product or in users' systems

### 2.3 Examples of Severe Incidents

- Confirmed data breach exposing user PII or test data
- Supply chain compromise (malicious dependency injection)
- Prompt injection leading to unauthorized actions via AI agent
- Remote Code Execution (RCE) vulnerability being exploited in the wild
- Authentication bypass actively used to access user accounts
- Malware discovered in distributed Docker images or NPM packages

## 3. Three-Stage Reporting Timeline (CRA Art. 14(3)-(4))

```
┌──────────────────────────────────────────────────────────────────────┐
│                     CRA INCIDENT REPORTING TIMELINE                   │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  T+0h: Incident detected                                             │
│    │                                                                 │
│    ▼                                                                 │
│  T+24h: ┌─────────────────────────────────────────────┐             │
│         │ STAGE 1: EARLY WARNING (Art. 14(4)(a))       │             │
│         │ • Is it suspected malicious/unlawful?         │             │
│         │ • Which Member States affected?               │             │
│         │ • Via single reporting platform               │             │
│         └──────────────────────┬──────────────────────┘             │
│                                │                                     │
│    ▼                           ▼                                     │
│  T+72h: ┌─────────────────────────────────────────────┐             │
│         │ STAGE 2: INCIDENT NOTIFICATION (Art. 14(4)(b)│             │
│         │ • Nature of the incident                      │             │
│         │ • Initial assessment                          │             │
│         │ • Corrective/mitigating measures taken        │             │
│         │ • Measures users can take                     │             │
│         │ • Sensitivity level of information            │             │
│         └──────────────────────┬──────────────────────┘             │
│                                │                                     │
│    ▼                           ▼                                     │
│  T+1mo: ┌─────────────────────────────────────────────┐             │
│         │ STAGE 3: FINAL REPORT (Art. 14(4)(c))        │             │
│         │ • Detailed description (severity + impact)    │             │
│         │ • Type of threat / root cause                 │             │
│         │ • Applied and ongoing mitigation measures     │             │
│         └──────────────────────────────────────────────┘             │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## 4. Roles and Responsibilities

### 4.1 Incident Response Team

| Role | Person | Responsibility |
|------|--------|---------------|
| **Incident Commander** | Jose Manuel Sabarís (Joker) | Final authority, external comms, regulatory reporting |
| **Security Lead** | Alfred (AI Agent) | Triage, assessment, technical investigation |
| **DevOps** | Alfred / DevOps Agent | Containment, forensics, recovery |
| **Legal/Compliance** | Jose Manuel Sabarís | CRA compliance, CSIRT liaison |
| **Communications** | Jose Manuel Sabarís | User notifications, public advisories |

### 4.2 Escalation Matrix

```
SEV-1 (Critical):
  Detector (any) → Incident Commander (Joker) → 15 min response
  Joker decides: Is this a CRA "severe incident"? → If YES, start §3 timeline

SEV-2 (High):
  Detector → Security Lead (Alfred) → 1 hour response
  Alfred decides: CRA applicability → escalate to Joker if severe

SEV-3/4: Standard incident response (no CRA reporting unless reclassified)
```

## 5. Step-by-Step Reporting Procedure

### 5.1 Immediate Actions (T+0 to T+24h)

1. **Detect & Confirm** — Verify the incident is real, not a false positive
2. **Classify** — Is this a "severe incident" per §2.2?
3. **Contain** — Follow `INCIDENT_RESPONSE_PLAYBOOK.md` playbooks
4. **Escalate** — Notify Incident Commander (Joker) immediately for SEV-1
5. **Prepare Early Warning** (if severe) — Fill template §6.1
6. **Submit Early Warning** via ENISA single reporting platform (≤24h)
   - **CSIRT Coordinator:** INCIBE-CERT (Spain)
   - **Platform:** [ENISA single reporting platform URL — available Sept 2026]

### 5.2 Investigation (T+24h to T+72h)

1. **Investigate** — Root cause analysis, scope determination
2. **Assess Impact** — Affected users, data, systems
3. **Mitigate** — Apply corrective measures
4. **Prepare Incident Notification** — Fill template §6.2
5. **Submit Notification** via single reporting platform (≤72h)

### 5.3 Resolution (T+72h to T+1 month)

1. **Resolve** — Complete fix deployed and verified
2. **Document** — Full timeline, root cause, lessons learned
3. **Prepare Final Report** — Fill template §6.3
4. **Submit Final Report** via single reporting platform (≤1 month)
5. **User Notification** (CRA Art. 14(8)) — Notify impacted users with mitigation guidance

### 5.4 Post-Incident

1. **Post-mortem** within 48h (per `INCIDENT_RESPONSE_PLAYBOOK.md`)
2. **Update** Risk Register, security controls, this procedure if needed
3. **CVE Request** (if applicable) via MITRE or GitHub Security Advisory
4. **Public Advisory** after fix is available (per CVD Policy)

## 6. Report Templates

### 6.1 Early Warning (≤24h) — Template

```markdown
## CRA Early Warning Notification

**Date:** [YYYY-MM-DD HH:MM UTC]
**Reporter:** SabaTech (Jose Manuel Sabarís)
**Product:** [QA-FRAMEWORK / SabaTrace / etc.]
**Version:** [affected version(s)]

### Incident Summary
- **Nature:** [brief description]
- **Suspected cause:** [malicious/unlawful act? yes/no/unknown]
- **Affected Member States:** [list EU MS where product is available]

### Point of Contact
- security@sabatech.dev
- Jose Manuel Sabarís García
```

### 6.2 Incident Notification (≤72h) — Template

```markdown
## CRA Incident Notification

**Date:** [YYYY-MM-DD HH:MM UTC]
**Reference:** [Early Warning ID from stage 1]

### Incident Details
- **Nature of incident:** [data breach / RCE / auth bypass / supply chain / etc.]
- **Initial assessment:** [what happened, how, scope]
- **Severity:** [Critical / High / Medium] with CVSS if available

### Measures Taken
- **Corrective measures applied:** [list]
- **Mitigating measures for users:** [list actionable items]

### Data Classification
- **Sensitivity of notified information:** [High / Medium / Low]
```

### 6.3 Final Report (≤1 month) — Template

```markdown
## CRA Final Report

**Date:** [YYYY-MM-DD]
**Reference:** [Early Warning ID]

### 1. Detailed Description
- **Severity and impact:** [full assessment]
- **Timeline of events:** [chronological]

### 2. Root Cause
- **Type of threat:** [supply chain / prompt injection / auth bypass / etc.]
- **Root cause:** [technical explanation]
- **CVE(s):** [if assigned]

### 3. Mitigation Measures
- **Applied measures:** [permanent fixes]
- **Ongoing measures:** [monitoring, additional controls]
- **User-facing actions:** [what users should do]
```

## 7. Competent Authorities

### 7.1 Spain (Main Establishment)

| Authority | Role | Contact |
|-----------|------|---------|
| **INCIBE-CERT** | CSIRT coordinator for Spain | https://www.incibe.es/incibe-cert |
| **MSP (Market Surveillance)** | INCIBE (designated market surveillance authority) | https://www.incibe.es |
| **ENISA** | EU-level reporting platform operator | https://enisa.europa.eu |

### 7.2 Reporting Platform

Per CRA Art. 16, ENISA operates a **single reporting platform** with national electronic notification endpoints. This platform is expected to be operational by **11 September 2026**.

- **URL:** [To be published by ENISA — check https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act-implementation]
- **Access:** Manufacturers submit via the endpoint of their coordinating CSIRT
- **Confidentiality:** Platform ensures confidentiality of notifications, especially for unpatched vulnerabilities

### 7.3 Voluntary Reporting (CRA Art. 15)

SabaTech may also voluntarily report:
- Vulnerabilities not yet actively exploited
- Near-miss incidents
- Cyber threats that could affect product risk profile

These are submitted to INCIBE-CERT or ENISA via the same platform.

## 8. User Notification (CRA Art. 14(8))

After becoming aware of an actively exploited vulnerability or severe incident, SabaTech must inform impacted users (and, where appropriate, all users) of:

1. The vulnerability or incident
2. Risk mitigation and corrective measures users can deploy
3. Format: structured, machine-readable where appropriate

**Channels for user notification:**
- Email to registered users
- In-app banner / notification
- Security advisory on https://github.com/SabaTech-dev/QA-FRAMEWORK/security/advisories
- Status page (if implemented)

## 9. Interaction with Other Regulations

| Regulation | Relationship | Action |
|-----------|-------------|--------|
| **GDPR (Art. 33-34)** | Personal data breach → also report to AEPD (Spain) within 72h | Dual reporting if incident involves PII |
| **NIS2 Directive** | If classified as essential/important entity | Report to INCIBE-CERT |
| **EU AI Act** | If AI system incident (Art. 73) | Report per AI Act incident reporting |
| **Spanish LOPDGDD** | National GDPR implementation | Report to AEPD |

## 10. Records and Audit Trail

All CRA incident reports are archived for **10 years** (CRA Art. 13(13)) in:

- **GitHub Security Advisories** (public after fix)
- **Incident reports** (`docs/security/incidents/`) — internal, restricted access
- **Risk Register** (`docs/security/RISK_REGISTER.md`) — summary entries
- **ENISA platform** — regulatory record

## 11. Training and Testing

- **Annual tabletop exercise** — simulate CRA-reportable incident
- **Team briefing** — all incident response team members trained on this procedure
- **Template testing** — verify report templates work with ENISA platform (when available)

## 12. Implementation Checklist

- [ ] **INCIBE-CERT** registration as manufacturer (when platform opens)
- [ ] **ENISA single reporting platform** account created
- [ ] **security@sabatech.dev** verified and monitored
- [ ] **SEV-1 alerting** configured (Telegram → Joker with 15-min SLA)
- [ ] **Tabletop exercise** scheduled (pre-Sept 11)
- [ ] **User notification templates** prepared (email + in-app)

## 13. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-07-24 | Initial incident reporting procedure (CRA compliance) |

---

**Legal review:** Pending (consult with EU compliance advisor before Sept 11)
**Next review:** 2026-09-30 (post-implementation)
**Contact:** security@sabatech.dev

## References

1. **Cyber Resilience Act:** Regulation (EU) 2024/2847 — full text: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R2847
2. **CRA Implementation:** https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act-implementation
3. **INCIBE-CERT:** https://www.incibe.es/incibe-cert
4. **NIS2 Directive:** Directive (EU) 2022/2555
5. **GDPR Art. 33-34:** Personal data breach notification
6. **Related docs:** `cvd-policy.md`, `SECURITY_POLICY.md`, `INCIDENT_RESPONSE_PLAYBOOK.md`
