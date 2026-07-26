# AI Literacy Plan — QA-FRAMEWORK

> **EU AI Act Art. 4 — Operational Plan for AI Literacy**
>
> **Regulation:** Regulation (EU) 2024/1689 (EU AI Act), Article 4
> **System:** QA-FRAMEWORK SaaS Platform
> **Organization:** SabaTech (SabaTech-dev)
> **Last Updated:** 2026-07-26
> **Next Review:** 2027-01-26 (6 months)
> **Owner:** Compliance / DevOps
> **Classification:** Internal — Compliance Documentation
> **Companion document:** `AI_LITERACY_POLICY.md` (policy framework)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Regulatory Basis](#2-regulatory-basis)
3. [Target Audience](#3-target-audience)
4. [Training Levels by Role](#4-training-levels-by-role)
5. [Training Resources](#5-training-resources)
6. [Workshop Program](#6-workshop-program)
7. [Onboarding Process](#7-onboarding-process)
8. [Annual Refresher](#8-annual-refresher)
9. [Compliance Tracking](#9-compliance-tracking)
10. [Effectiveness Review](#10-effectiveness-review)
11. [Related Documents](#11-related-documents)
12. [References](#12-references)

---

## 1. Executive Summary

This plan operationalises SabaTech's obligations under **EU AI Act Article 4**, which requires providers and deployers of AI systems to ensure a sufficient level of AI literacy among their staff and persons dealing with AI systems on their behalf.

**Key facts:**

| Metric | Value |
|--------|-------|
| **AI system in scope** | 1 production GPAI model (Meta Llama 3.3 70B via Groq) |
| **Use case** | Browser-Use AI test automation agent |
| **Risk classification** | Limited Risk (no Art. 50(1) applicability) |
| **Staff requiring training** | All SabaTech personnel + contractors interacting with AI systems |
| **Training format** | Workshops + self-paced guides + documentation review |
| **Frequency** | Onboarding (within 7 days) + annual refresher |
| **Art. 4 enforcement date** | 2 February 2025 (in force) |

**SabaTech role:** Deployer of GPAI models (uses Llama 3. 70B via Groq API). Not a GPAI provider — does not train or fine-tune foundation models.

---

## 2. Regulatory Basis

### 2.1 Article 4 Text

> *"Providers and deployers of AI systems shall take measures to ensure, to their best extent, a sufficient level of AI literacy of their staff and other persons dealing with the operation and use of AI systems on their behalf, taking into account their technical knowledge, experience, education and training and the context the AI systems are to be used in, and considering the persons or groups of persons on whom the AI systems are to be used."*
>
> — Regulation (EU) 2024/1689, Article 4

### 2.2 Key Requirements (per EC AI Office guidance)

Per the [EC AI Office Q&A on AI Literacy](https://digital-strategy.ec.europa.eu/en/faqs/ai-literacy-questions-answers), the minimum content for an Article 4 compliance programme:

| Requirement | How this plan addresses it |
|-------------|---------------------------|
| **(a) General AI understanding** — What is AI? How does it work? What AI is used in our organisation? | §4 Level 1 (Foundation) — required for all roles |
| **(b) Organisational role assessment** — Provider vs deployer? | §4 Level 1 + §3.2 Role mapping |
| **(c) Risk awareness** — What are the risks? How to mitigate? | §4 Level 2+ — role-specific risk modules |
| **(d) Concrete actions** calibrated to existing knowledge | §4 Tiered training + §7 Onboarding calibration |
| **Legal & ethical aspects** included | §4 All levels include EU AI Act obligations |

### 2.3 Digital Omnibus Adjustment

The **Digital Omnibus 2026** softened Article 4 from "ensure" to "support" the development of AI competencies for SMEs. This plan meets the softened standard proportionate to SabaTech's size while maintaining documentation rigor for audit readiness.

### 2.4 Applicability to QA-FRAMEWORK

QA-FRAMEWORK is classified as **Limited Risk** under the AI Act. It is not a high-risk system (no Annex III use cases) and does not involve direct human-AI interaction requiring Art. 50 transparency disclosures (see `art-50-1-assessment.md`). Article 4 applies regardless of risk classification — it is the only provision that applies universally to all deployers.

---

## 3. Target Audience

### 3.1 Internal Staff

| Group | Roles | AI Interaction | Risk Exposure |
|-------|-------|----------------|---------------|
| **Developers** | Backend devs, frontend devs, AI integration engineers | Build and maintain AI-powered features (Browser-Use service, LLM adapters) | **High** — direct model interaction, prompt engineering, API integration |
| **QA Engineers** | Test engineers, automation specialists | Operate AI-powered test generation and browser-use agents | **High** — execute AI actions, validate outputs, detect hallucinations |
| **DevOps / Infrastructure** | Platform engineers, SRE | Deploy and monitor AI services, manage API keys, configure model parameters | **Medium** — indirect model interaction via infrastructure |
| **Management** | CEO (Joker), product leads | Strategic decisions on AI adoption, compliance oversight, vendor selection | **Medium** — governance and decision-making |
| **Research** | Research agent | Evaluates AI models, monitors regulatory changes, produces compliance documentation | **Medium** — analytical and documentation role |

### 3.2 External Persons

| Group | AI Interaction | Training Requirement |
|-------|----------------|---------------------|
| **Contractors** | May operate AI systems on SabaTech's behalf | Same level as equivalent internal role |
| **Clients (QA-FRAMEWORK users)** | Indirect — use a platform that internally uses AI for test generation | Awareness-level: informed that AI assists in test generation (see §5.3) |

### 3.3 Calibration Principle

Per Article 4, training is **calibrated** to each person's:
- **Technical knowledge** — prior AI/ML experience
- **Experience** — hands-on time with the specific AI system
- **Education** — formal background
- **Training** — completed courses or certifications

A pre-training baseline assessment (§7.2) determines the starting point for each individual.

---

## 4. Training Levels by Role

### 4.1 Three-Tier Competency Model

```
┌──────────────────────────────────────────────────────────┐
│  Level 3: ADVANCED (Developers, AI Integration)          │
│  ├── Prompt injection & adversarial testing              │
│  ├── API rate limiting, fallback patterns                │
│  ├── Model evaluation methodology                        │
│  └── EU AI Act Art. 9-15 technical requirements          │
├──────────────────────────────────────────────────────────┤
│  Level 2: INTERMEDIATE (QA Engineers, DevOps)            │
│  ├── Hallucination detection & output verification       │
│  ├── Browser-Use agent operation & limitations           │
│  ├── Incident response for AI failures                   │
│  └── Data privacy in AI interactions (GDPR interplay)    │
├──────────────────────────────────────────────────────────┤
│  Level 1: FOUNDATION (All staff + contractors)           │
│  ├── What is AI / LLM / GPAI? Basic concepts              │
│  ├── What AI systems does SabaTech use?                   │
│  ├── Opportunities, risks, and limitations                │
│  ├── SabaTech role: Deployer (not provider)               │
│  └── EU AI Act basics & ethical AI use                    │
└──────────────────────────────────────────────────────────┘
```

### 4.2 Role-to-Level Matrix

| Role | Level 1 (Foundation) | Level 2 (Intermediate) | Level 3 (Advanced) | Estimated Hours |
|------|:--------------------:|:----------------------:|:------------------:|:---------------:|
| **Developers** | ✅ Required | ✅ Required | ✅ Required | 8h initial + 2h annual |
| **QA Engineers** | ✅ Required | ✅ Required | ⬜ Optional | 5h initial + 2h annual |
| **DevOps** | ✅ Required | ✅ Required | ⬜ Optional | 5h initial + 2h annual |
| **Management** | ✅ Required | ⬜ Overview only | ❌ Not required | 2h initial + 1h annual |
| **Research** | ✅ Required | ✅ Required | ✅ Required | 8h initial + 2h annual |
| **Contractors** | ✅ Required | Per role equivalent | Per role equivalent | Per role |
| **Clients** | ⬜ Awareness memo | ❌ | ❌ | N/A |

### 4.3 Level 1: Foundation Curriculum (All Staff)

**Objective:** Ensure every person interacting with AI systems at SabaTech understands what AI is, what systems we use, and what risks exist.

| Module | Topics | Duration | Format |
|--------|--------|----------|--------|
| **1.1 AI Fundamentals** | What is AI vs ML vs LLM? How do LLMs generate text? Tokenization basics. Capabilities & limitations. | 30 min | Workshop + slides |
| **1.2 SabaTech AI Systems** | Which AI systems we use (Llama 3.3 70B via Groq). What Browser-Use does. What OpenClaw agents are. Purpose of each. | 20 min | Walkthrough + live demo |
| **1.3 Opportunities & Risks** | Hallucination, bias, prompt injection, data leakage, model drift. Benefits: automation, test coverage, speed. | 30 min | Case studies + discussion |
| **1.4 Legal & Ethical Basics** | EU AI Act overview. SabaTech as deployer. Limited Risk classification. GDPR interplay. Ethical AI use principles. | 20 min | Presentation + Q&A |
| **1.5 Incident Reporting** | How to report AI-related issues. Incident response procedure. Escalation paths. | 10 min | Walkthrough |
| **Total** | | **~2h** | |

### 4.4 Level 2: Intermediate Curriculum (QA, DevOps)

**Prerequisite:** Level 1 completed.

| Module | Topics | Duration | Format |
|--------|--------|----------|--------|
| **2.1 Hallucination Detection** | How to recognise AI-generated errors. Output verification protocols. Confidence indicators. | 45 min | Hands-on exercises |
| **2.2 Browser-Use Agent Operation** | How the AI agent navigates pages. DOM snapshot interpretation. Step-by-step action review. Session timeout & reset. | 45 min | Live demo + practice |
| **2.3 Data Privacy in AI** | What data goes to Groq API. What must NEVER go (PII, credentials). GDPR Art. 32 (security of processing). | 30 min | Scenarios + checklist |
| **2.4 Incident Response** | AI failure modes. Groq API outage response. Incorrect action recovery. Escalation to DevOps. | 30 min | Tabletop exercise |
| **Total** | | **~2.5h** | |

### 4.5 Level 3: Advanced Curriculum (Developers, Research)

**Prerequisite:** Level 2 completed.

| Module | Topics | Duration | Format |
|--------|--------|----------|--------|
| **3.1 Prompt Injection & Adversarial Testing** | OWASP LLM Top 10. Promptfoo, Garak basics. How test URLs can be adversarial. Sandboxing boundaries. | 60 min | Technical workshop |
| **3.2 API Engineering** | Rate limiting, retry logic, exponential backoff. Token economics. Model swap patterns. LangChain abstraction. | 45 min | Code walkthrough |
| **3.3 Model Evaluation Methodology** | Benchmarks (SWE-bench, HumanEval, MMLU). Vendor-reported vs verified metrics. How to evaluate new models. | 45 min | Case study |
| **3.4 EU AI Act Technical Requirements** | Art. 9-15 requirements (for high-risk, future-proofing). Art. 53 GPAI obligations. Documentation requirements (Annex IV). | 30 min | Compliance briefing |
| **Total** | | **~3h** | |

---

## 5. Training Resources

### 5.1 Internal Documentation

| Resource | Location | Target Audience | Format |
|----------|----------|-----------------|--------|
| **AI Literacy Policy** | `docs/compliance/AI_LITERACY_POLICY.md` | All staff | Policy document |
| **GPAI Model Inventory** | `docs/compliance/GPAI-Inventory.md` | All staff (L1) + Developers (L3) | Technical reference |
| **AI Systems Register** | `docs/compliance/ai-systems-register.md` | All staff | Register |
| **Art. 50(1) Assessment** | `docs/compliance/art-50-1-assessment.md` | Management, Compliance | Assessment |
| **Incident Reporting Procedure** | `docs/compliance/incident-reporting-procedure.md` | All staff | Procedure |
| **Red-Teaming Toolkit Report** | `reports/research/red-teaming-toolkit-2026-06-11.md` | Developers, QA | Technical report |
| **EU AI Act Gap Analysis** | `reports/research/eu-ai-act-gap-analysis-2026-07-09.md` | Management, Compliance | Analysis |
| **EU AI Act Compliance Report** | `reports/research/eu-ai-act-compliance-2026.md` | Compliance | Full report |

### 5.2 External Resources

| Resource | URL | Type |
|----------|-----|------|
| **EC AI Office — AI Literacy Q&A** | https://digital-strategy.ec.europa.eu/en/faqs/ai-literacy-questions-answers | Official guidance |
| **EC Living Repository of AI Literacy Practices** | https://digital-strategy.ec.europa.eu/en/library/living-repository-foster-learning-and-exchange-ai-literacy | Best practices database |
| **AI Literacy Programs Database (FoLI)** | https://artificialintelligenceact.eu/ai-literacy-programs/ | Training programs |
| **EU AI Act Full Text (EUR-Lex)** | https://eur-lex.europa.eu/eli/reg/2024/1689/oj | Legal text |
| **Groq Model Documentation** | https://console.groq.com/docs/model/llama-3.3-70b-versatile | Model reference |
| **Meta Llama 3.3 Model Card** | https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct | Model documentation |
| **OWASP LLM Top 10** | https://owasp.org/www-project-top-10-for-large-language-model-applications/ | Security reference |

### 5.3 Client Awareness (Informational)

QA-FRAMEWORK clients are indirect users of AI — they use a platform that internally leverages AI for test generation. The following measures ensure client awareness without requiring formal training:

| Measure | Implementation | Status |
|---------|----------------|--------|
| **Service documentation** | README and API docs note that AI assists in test generation | ⚠️ To add |
| **AI disclosure badge** | Dashboard displays "AI-assisted testing" indicator | ⚠️ To add (recommended, not legally required per `art-50-1-assessment.md`) |
| **Model transparency** | GPAI Inventory publicly referenceable upon request | ✅ Available |
| **Client onboarding pack** | New client welcome email includes AI usage summary | ⚠️ To create |

> **Legal note:** Art. 50(1) transparency disclosure is NOT applicable to QA-FRAMEWORK (no direct human-AI interaction). Client awareness is best practice, not legal obligation. See `art-50-1-assessment.md`.

---

## 6. Workshop Program

### 6.1 Workshop 1: "AI Fundamentals for SabaTech" (Level 1)

**Audience:** All staff and contractors
**Duration:** 2 hours
**Format:** Interactive workshop with live demo
**Frequency:** On-demand for new hires + scheduled quarterly

#### Agenda

| Time | Segment | Description |
|------|---------|-------------|
| 0:00–0:10 | **Welcome & objectives** | Why we're here. EU AI Act Art. 4 requirement. What you'll learn. |
| 0:10–0:30 | **Module 1.1: AI Fundamentals** | What is AI? ML vs LLM vs GPAI. How LLMs generate text (tokenization, next-token prediction, temperature). Capabilities and hard limitations. |
| 0:30–0:40 | **Break** | 10 minutes |
| 0:40–1:00 | **Module 1.2: SabaTech AI Systems** | Live walkthrough: QA-FRAMEWORK Browser-Use agent. How Llama 3.3 70B powers test automation. OpenClaw multi-agent system overview. What each agent does. |
| 1:00–1:30 | **Module 1.3: Risks & Opportunities** | Case studies: (1) AI hallucination in test generation — how we catch it. (2) Prompt injection via test URLs — sandbox isolation. (3) Data leakage prevention — what never goes to the API. Benefits: 10x test coverage, automated browser testing, CI/CD integration. |
| 1:30–1:50 | **Module 1.4: Legal & Ethical** | EU AI Act in 5 minutes. SabaTech = deployer, not provider. Limited Risk = minimal obligations. Art. 4 (literacy, this workshop), Art. 53 (GPAI inventory). GDPR interplay: no PII to AI, Groq DPA. Ethics: we test AI, we don't blindly trust it. |
| 1:50–2:00 | **Module 1.5: Incident Reporting** | How to report AI issues. Link to `incident-reporting-procedure.md`. Escalation: QA → DevOps → Management. Serious incidents → AI Office (Art. 55). |

#### Materials

- Slide deck: `docs/compliance/workshops/ws1-ai-fundamentals-slides.md` (to be created)
- Live demo script: Browser-Use agent running a simple test
- Handout: One-page AI literacy quick reference card
- Feedback form: Post-workshop survey (3 questions)

#### Success Criteria

- [ ] Attendee can name the AI model used (Llama 3.3 70B)
- [ ] Attendee can name one risk and one mitigation
- [ ] Attendee knows how to report an AI-related incident
- [ ] Attendee understands SabaTech is a deployer, not provider

---

### 6.2 Workshop 2: "Operating AI Systems Safely" (Level 2)

**Audience:** QA Engineers, DevOps, Developers
**Prerequisite:** Workshop 1 completed
**Duration:** 3 hours (2.5h content + 0.5h hands-on)
**Format:** Hands-on workshop with practical exercises
**Frequency:** On-demand for new technical hires + scheduled semi-annually

#### Agenda

| Time | Segment | Description |
|------|---------|-------------|
| 0:00–0:15 | **Recap & objectives** | Quick review of Workshop 1. What we'll build on today. |
| 0:15–0:45 | **Module 2.1: Hallucination Detection** | Exercise: Review 5 AI-generated test outputs. Identify which are correct, which have subtle errors. Learn verification protocol: (1) Check action against DOM state, (2) Validate selectors exist, (3) Confirm assertion logic. |
| 0:45–1:30 | **Module 2.2: Browser-Use Agent Deep Dive** | Live demo: Start a Browser-Use session. Watch step-by-step: prompt → model → action → DOM snapshot → next prompt. Practice: Each attendee runs a simple browser-use test and reviews the action log. Learn: Session timeout (50 steps), reset behavior, error recovery. |
| 1:30–1:40 | **Break** | 10 minutes |
| 1:40–2:10 | **Module 2.3: Data Privacy in Practice** | Scenarios: (1) "Should I send this customer's email to the AI?" → No. (2) "This test URL contains a session token — is that OK?" → Strip it first. (3) "Can the model access our database?" → No, only what's in the prompt. Checklist: What data is safe vs unsafe. |
| 2:10–2:40 | **Module 2.4: Incident Response Tabletop** | Scenario: Groq API returns 500 errors mid-test-run. Walk through: detection → retry → fallback (manual test) → incident log → escalation. Scenario: AI agent clicks wrong button on a form. Walk through: rollback → report → root cause analysis. |
| 2:40–3:00 | **Q&A and feedback** | Open discussion. What questions remain? What scenarios worry you? |

#### Materials

- Exercise workbook: `docs/compliance/workshops/ws2-safe-operations-exercises.md` (to be created)
- Browser-Use demo environment (sandboxed test page)
- Incident response quick reference card
- Feedback form: Post-workshop survey (3 questions)

#### Success Criteria

- [ ] Attendee can identify a hallucinated test output
- [ ] Attendee can operate a Browser-Use session and review the action log
- [ ] Attendee can classify data as safe/unsafe for AI processing
- [ ] Attendee knows the incident response procedure for AI failures

---

### 6.3 Future Workshops (Planned)

| Workshop | Level | Target | Quarter |
|----------|-------|--------|---------|
| **WS3: Prompt Injection & Adversarial Testing** | Level 3 | Developers | Q4 2026 |
| **WS4: AI Model Evaluation Methodology** | Level 3 | Research, Devs | Q1 2027 |
| **WS5: EU AI Act Compliance for Developers** | Level 3 | Developers, Management | Q1 2027 |

---

## 7. Onboarding Process

### 7.1 New Hire AI Literacy Onboarding

```
Day 1: Welcome + AI Systems Overview (30 min)
  └── Manager provides: GPAI Inventory link + AI Literacy Policy link

Day 2-7: Workshop 1 (2h, scheduled within first week)
  └── "AI Fundamentals for SabaTech"
  └── Covers: Modules 1.1–1.5

Day 7-14: Role-specific training (per §4.2 matrix)
  ├── QA/DevOps: Workshop 2 (3h)
  ├── Developers: Workshop 2 (3h) + self-study Level 3 materials
  └── Management: Level 1 suffices

Day 14: Completion recorded in tracking matrix (§9)
```

### 7.2 Baseline Assessment

Before training, each new hire completes a **5-question self-assessment** to calibrate existing knowledge:

| Question | Purpose |
|----------|---------|
| 1. "Have you used AI tools (ChatGPT, Copilot, etc.) in a professional context?" | Baseline AI familiarity |
| 2. "Can you explain what a Large Language Model does in 2 sentences?" | Conceptual understanding |
| 3. "Have you encountered AI 'hallucination' (confident wrong answers)? How did you handle it?" | Risk awareness |
| 4. "Are you familiar with the EU AI Act?" | Regulatory knowledge |
| 5. "What concerns do you have about working with AI systems?" | Identify knowledge gaps |

**Scoring:** Not used for gatekeeping — only for calibrating training emphasis. Per EC guidance, Article 4 does not require formal knowledge testing.

### 7.3 Contractor Onboarding

Contractors who operate AI systems on SabaTech's behalf receive:
1. **Workshop 1** (or equivalent recorded version) within 7 days of engagement
2. **Role-specific training** matching their equivalent internal role
3. **Acknowledgement form** confirming completion (stored in §9 tracking matrix)

---

## 8. Annual Refresher

### 8.1 Frequency

| Element | Frequency | Duration |
|---------|-----------|----------|
| **Level 1 refresher** | Annual | 1h |
| **Level 2 refresher** | Annual | 1h |
| **Level 3 refresher** | Annual | 2h |
| **Policy review** | Every 6 months | 30 min (self-review) |
| **Regulatory update** | As needed (triggered by EC guidance changes) | Variable |

### 8.2 Refresher Content

The annual refresher covers:
1. **What changed since last year** — new models, new regulations, new risks
2. **Incident review** — any AI-related incidents in the past year, lessons learned
3. **New regulatory developments** — Digital Omnibus updates, new EC guidance
4. **Skills check** — can attendees still identify hallucinations, operate the system, report incidents?
5. **Feedback** — what training is needed next year?

### 8.3 Trigger Events (Ad-hoc Training)

Training is also triggered by:
- **New AI system adoption** — full Workshop 1 update + role-specific module
- **Model change** (e.g., Llama 3.3 → Llama 4) — Workshop 2 update for technical staff
- **Regulatory change** — policy update + targeted briefing
- **Serious incident** — root cause analysis workshop for relevant staff

---

## 9. Compliance Tracking

### 9.1 Tracking Matrix

All AI literacy training is recorded in the following tracking matrix. The matrix is maintained by the Compliance/DevOps owner and stored alongside this document.

| Name | Role | Hire/Start Date | Baseline Assessment | WS1 Date | WS1 Status | WS2 Date | WS2 Status | Level 3 Date | L3 Status | Last Refresher | Next Refresher Due | Notes |
|------|------|-----------------|--------------------| --------- | ---------- | -------- | ---------- | ------------ | --------- | -------------- | -------------------|-------|
| Jose Manuel Sabarís | CEO / Management | — | ✅ | 2026-07-26 | ✅ Complete | — | ⬜ N/A | — | ⬜ N/A | 2026-07-26 | 2027-07-26 | Self-paced review |
| *[New employee]* | *[Role]* | *[Date]* | ⬜ | ⬜ | ⬜ Pending | ⬜ | ⬜ Pending | ⬜ | ⬜ Pending | ⬜ | ⬜ | |
| *[Contractor]* | *[Role]* | *[Date]* | ⬜ | ⬜ | ⬜ Pending | ⬜ | ⬜ Pending | ⬜ | ⬜ Pending | ⬜ | ⬜ | |

> **Status values:** ✅ Complete | ⬜ Pending | 🔄 In Progress | ❌ Overdue

### 9.2 Tracking Procedure

| Step | Action | Owner | Frequency |
|------|--------|-------|-----------|
| 1 | Record baseline assessment results | Hiring manager | On new hire |
| 2 | Schedule Workshop 1 within 7 days | Hiring manager | On new hire |
| 3 | Record workshop completion dates | Compliance owner | After each session |
| 4 | Send annual refresher reminder | Compliance owner | 60 days before due |
| 5 | Record refresher completion | Compliance owner | After completion |
| 6 | Review tracking matrix for gaps | Compliance owner | Quarterly |
| 7 | Report compliance status to management | Compliance owner | Quarterly |

### 9.3 Compliance Metrics

| Metric | Target | Current |
|--------|--------|---------|
| **% staff with Level 1 complete** | 100% | TBD |
| **% technical staff with Level 2 complete** | 100% | TBD |
| **% developers with Level 3 complete** | 100% | TBD |
| **% staff with current annual refresher** | 100% | TBD |
| **Average days from hire to Level 1 completion** | ≤7 days | TBD |

### 9.4 Audit Evidence

For EU AI Act audit purposes, the following evidence trail is maintained:

| Evidence | Location | Retention |
|----------|----------|-----------|
| **This plan** | `docs/compliance/AI-Literacy-Plan.md` (Git versioned) | Permanent |
| **Training materials** | `docs/compliance/workshops/` (Git versioned) | Permanent |
| **Tracking matrix** | §9.1 of this document (Git versioned) | Permanent |
| **Attendance records** | §9.1 dates + Git commit history | Permanent |
| **Feedback forms** | Aggregated results in workshop materials | 3 years |
| **Policy document** | `docs/compliance/AI_LITERACY_POLICY.md` (Git versioned) | Permanent |
| **GPAI Inventory** | `docs/compliance/GPAI-Inventory.md` (Git versioned) | Permanent |

---

## 10. Effectiveness Review

### 10.1 Review Schedule

| Review Type | Frequency | Owner |
|-------------|-----------|-------|
| **Operational review** (are workshops running?) | Quarterly | Compliance owner |
| **Content review** (is material current?) | Every 6 months | Research agent |
| **Effectiveness review** (is training working?) | Annual | Management |
| **Regulatory alignment review** | On EC guidance change | Research agent |

### 10.2 Effectiveness Indicators

| Indicator | Measurement | Target |
|-----------|-------------|--------|
| **Workshop attendance** | % of required staff who attended | 100% |
| **Post-workshop confidence** | Self-reported (1-5 scale) | ≥4.0 avg |
| **AI incident rate** | Number of AI-related incidents per quarter | Trending down |
| **Time-to-detection** | How fast staff report AI issues | <24h |
| **Audit readiness** | Can we demonstrate compliance on demand? | ✅ Yes |

### 10.3 Continuous Improvement

Feedback from workshop attendees is incorporated into future iterations. The post-workshop survey asks:

1. *"How confident do you feel about working with AI systems at SabaTech after this workshop?"* (1-5 scale)
2. *"What topic would you like more depth on?"* (free text)
3. *"Was any topic confusing or unnecessary?"* (free text)

Results are reviewed quarterly and used to update workshop content.

---

## 11. Related Documents

| Document | Path | Relationship |
|----------|------|-------------|
| **AI Literacy Policy** | `docs/compliance/AI_LITERACY_POLICY.md` | Policy framework (the "what/why"). This plan is the operational implementation (the "how/when/who"). |
| **GPAI Model Inventory** | `docs/compliance/GPAI-Inventory.md` | Source of truth for AI models used. Workshop 1 references this. |
| **AI Systems Register** | `docs/compliance/ai-systems-register.md` | SabaTech-wide AI register. |
| **Art. 50(1) Assessment** | `docs/compliance/art-50-1-assessment.md` | Confirms transparency disclosure not required. |
| **Incident Reporting** | `docs/compliance/incident-reporting-procedure.md` | Referenced in Workshop 1, Module 1.5. |
| **CVD Policy** | `docs/compliance/cvd-policy.md` | Coordinated Vulnerability Disclosure procedure. |
| **CRA Compliance** | `docs/compliance/CRA-compliance.md` | Cyber Resilience Act assessment. |
| **EU AI Act Gap Analysis** | `reports/research/eu-ai-act-gap-analysis-2026-07-09.md` | Original gap analysis identifying G4. |
| **EU AI Act Compliance Report** | `reports/research/eu-ai-act-compliance-2026.md` | Full compliance investigation. |

---

## 12. References

| Reference | URL | Type |
|-----------|-----|------|
| EU AI Act Article 4 (AI literacy) | https://artificialintelligenceact.eu/article/4/ | Legal text |
| EU AI Act Full Text (EUR-Lex) | https://eur-lex.europa.eu/eli/reg/2024/1689/oj | Legal text |
| EC AI Office — AI Literacy Q&A | https://digital-strategy.ec.europa.eu/en/faqs/ai-literacy-questions-answers | Official guidance |
| EC Living Repository of AI Literacy Practices | https://digital-strategy.ec.europa.eu/en/library/living-repository-foster-learning-and-exchange-ai-literacy | Best practices |
| AI Literacy Programs Database (FoLI) | https://artificialintelligenceact.eu/ai-literacy-programs/ | Training programs |
| Digital Omnibus timeline changes | https://digital-strategy.ec.europa.eu/en/policies/digital-omnibus | Regulatory update |
| Article 4 Deployer Obligations Analysis | https://agentliability.eu/articles/eu-ai-act-article-4-ai-literacy-deployer-obligations-2026 | Legal analysis |
| OWASP LLM Top 10 | https://owasp.org/www-project-top-10-for-large-language-model-applications/ | Security reference |
| Groq Model Documentation | https://console.groq.com/docs/model/llama-3.3-70b-versatile | Technical docs |
| Meta Llama 3.3 Model Card | https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct | Model docs |

---

## 13. Document Control

| Field | Value |
|-------|-------|
| **Document owner** | SabaTech Compliance / DevOps |
| **Approved by** | Pending Joker approval |
| **Classification** | Internal — Compliance Documentation |
| **Git tracking** | `SabaTech-dev/QA-FRAMEWORK/docs/compliance/AI-Literacy-Plan.md` |
| **Review cycle** | 6 months (next: 2027-01-26) |
| **Trigger for ad-hoc review** | New AI system, model change, regulatory update, serious incident |

### Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-07-26 | Initial creation — Art. 4 operational plan | Research Agent |

---

*This plan is proportional to SabaTech's size as an SME per EU AI Act §69(2) and the Digital Omnibus softening of Article 4. It operationalises the AI Literacy Policy (`AI_LITERACY_POLICY.md`) with concrete workshops, timelines, and tracking mechanisms.*
