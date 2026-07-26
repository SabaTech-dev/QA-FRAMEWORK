# GPAI Model Inventory — QA-FRAMEWORK

> **EU AI Act Art. 53-55 — General-Purpose AI Model Transparency Documentation**
>
> **Regulation:** Regulation (EU) 2024/1689 (EU AI Act), Articles 53–55
> **System:** QA-FRAMEWORK SaaS Platform
> **Organization:** SabaTech (SabaTech-dev)
> **Last Updated:** 2026-07-26
> **Next Review:** 2026-10-26 (quarterly)
> **Owner:** DevOps / Compliance
> **Classification:** Internal — Compliance Documentation
> **Supersedes:** `AI_SYSTEMS_INVENTORY.md` (2026-07-09) — consolidated and expanded

---

## 1. Purpose

This document provides the authoritative inventory of all General-Purpose AI (GPAI) models used within the QA-FRAMEWORK platform, as required by EU AI Act Articles 53–55 (obligations for GPAI providers and deployers). It serves as:

- **Transparency record** for deployer obligations (Art. 53)
- **Audit reference** for internal and external compliance assessments
- **Risk assessment basis** for model-specific vulnerabilities
- **Onboarding documentation** for new team members and stakeholders

**GPAI Definition (Art. 3(63)):** An AI model that displays significant generality and is capable of competently performing a wide range of distinct tasks, regardless of how the model is placed on the market, and that can be integrated in a variety of downstream systems or applications.

---

## 2. Executive Summary

| Metric | Value |
|--------|-------|
| **GPAI models in production** | **1** |
| **GPAI models in mock/placeholder** | 0 (test generation module uses mock adapter, no real LLM calls) |
| **Risk classification** | Limited Risk (Art. 53 transparency obligations) |
| **High-risk models** | 0 |
| **Data exfiltration risk** | Low — no PII processed; test URLs and instructions only |
| **Art. 50(1) applicability** | ❌ Not applicable — no direct human-AI interaction (see `art-50-1-assessment.md`) |

---

## 3. Model Inventory

### 3.1 Production GPAI Model: Meta Llama 3.3 70B Versatile (via Groq)

| Field | Value |
|-------|-------|
| **Model name** | `llama-3.3-70b-versatile` |
| **Version** | Llama 3.3 (released December 6, 2024 by Meta) |
| **Provider (model)** | Meta Platforms, Inc. |
| **Provider (inference)** | Groq Inc. |
| **Provider API endpoint** | `https://api.groq.com/openai/v1` |
| **Integration library** | `langchain-groq` (>=0.1.0), `browser-use` (>=0.1.45) |
| **Architecture** | Dense transformer, 70B parameters, Grouped-Query Attention (GQA) |
| **Training method** | Supervised Fine-Tuning (SFT) + Reinforcement Learning with Human Feedback (RLHF) |
| **License** | Llama 3.3 Community License |
| **Context window** | 131,072 tokens (128K) |
| **Max output tokens** | 32,768 tokens |
| **Input modalities** | Text |
| **Output modalities** | Text |
| **Languages** | Multilingual (8 core languages: English, German, French, Italian, Portuguese, Hindi, Spanish, Thai) |
| **Quantization** | Groq TruePoint Numerics (lossless precision reduction) |
| **Throughput** | ~280 tokens/second (Groq LPU) |
| **Purpose in QA-FRAMEWORK** | Powers the Browser-Use AI test automation service — accepts natural language prompts to navigate web pages and execute test actions autonomously |
| **Integration layer** | Dashboard Backend (`dashboard/backend/services/ai/browser_use_service.py`) |
| **Date of deployment** | April 2026 |
| **Config keys** | `BROWSER_USE_LLM_PROVIDER=groq`, `BROWSER_USE_MODEL=llama-3.3-70b-versatile`, `GROQ_API_KEY` (secret) |
| **Data sent to model** | Natural language test instructions, URL context, DOM snapshots (via browser-use agent) |
| **Data returned** | Browser action decisions (clicks, typing, navigation commands) |
| **PII risk** | Low — processes test URLs and instructions only, no user PII |
| **Pricing** | $0.59 per 1M input tokens, $0.79 per 1M output tokens |

#### Capabilities

| Capability | Benchmark | Score |
|-----------|-----------|-------|
| General understanding | MMLU | 86.0% |
| Code generation | HumanEval (pass@1) | 88.4% |
| Mathematical reasoning | MATH (sympy intersection) | 77.0% |
| Multilingual math | MGSM (exact match) | 91.1% |
| Tool/function calling | Native support | ✅ |

*Source: [Groq Model Documentation](https://console.groq.com/docs/model/llama-3.3-70b-versatile), verified 2026-07-26*

#### Known Limitations

| Limitation | Impact on QA-FRAMEWORK | Mitigation |
|-----------|----------------------|------------|
| **Hallucination** — may generate plausible but incorrect outputs | Low — outputs are browser actions verified by test execution | Test actions validated against real DOM state before execution |
| **Knowledge cutoff** — training data has a fixed cutoff date | Minimal — QA testing patterns are stable; no dependency on recent events | N/A |
| **Prompt injection susceptibility** — malicious page content could manipulate agent actions | **Medium** — agent processes external web pages during testing | Browser-use agent sandboxed; test environments isolated; no production data exposed |
| **Context degradation** — quality may degrade with very long conversations | Low — browser-use sessions are short-lived (< 50 steps typically) | Session timeout and reset configured |
| **Multilingual variance** — performance varies across the 8 supported languages | Minimal — primary usage is English and Spanish | Test instructions provided in English by default |
| **No image/vision input** — text-only model | Medium — cannot visually verify page state | Browser-use extracts DOM structure for the model; visual verification via separate assertion layer |
| **Rate limits** — Groq API has request/time windows | Low — test automation is batch-oriented, not real-time | Retry logic with exponential backoff in `browser_use_service.py` |

#### Provider Compliance: Groq

| Check | Status | Evidence |
|-------|--------|----------|
| GDPR compliance | ✅ | [Groq Privacy Policy](https://groq.com/privacy-policy/) available; DPA available upon request |
| EU AI Act Art. 53 (GPAI provider obligations) | ⚠️ Pending verification | Groq relies on Meta's model card and Code of Practice adherence |
| Transparency documentation | ✅ | [Meta Llama 3.3 Model Card](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct) |
| Groq Privacy Policy | ✅ | Available at https://groq.com/privacy-policy/ |
| DPA (Data Processing Agreement) | ⚠️ Action needed | Signed DPA with Groq required before production launch |
| EU AI Act GPAI Code of Practice | ⚠️ Action needed | Verify Groq has signed the [GPAI Code of Practice](https://digital-strategy.ec.europa.eu/en/policies/ai-code-conduct) |
| Data processing location | USA | Data transferred outside EU — Standard Contractual Clauses (SCC) required |

---

### 3.2 Non-GPAI AI Components (No External Model Calls)

The following components have AI-related naming or structure but do **not** make external GPAI API calls. They are documented for completeness.

| Component | File | Status | Details |
|-----------|------|--------|---------|
| Test Generation LLM Adapter | `src/infrastructure/test_generation/llm_adapter.py` | **Mock** | Constructor accepts `provider="openai"`, `model="gpt-4"` but implementation returns hardcoded mock test code. No real LLM call. **Planned:** Q3 2026 integration. |
| Root Cause Analyzer | `dashboard/backend/services/ai/root_cause_analyzer.py` | **Rule-based** | Pattern analysis and error clustering. `llm_provider` parameter in constructor but never instantiated with a real provider. |
| Coverage Analyzer | `dashboard/backend/services/ai/coverage_analyzer.py` | **Rule-based** | No LLM integration. Static analysis of test coverage. |
| Test Optimizer | `dashboard/backend/services/ai/test_optimizer.py` | **Rule-based** | No LLM integration. Heuristic-based optimization. |
| Accuracy Rule-Based Evaluator | `src/infrastructure/accuracy_testing/rule_based_evaluator.py` | **Rule-based** | Rule-based scoring. `ai_model` field tracked for future transparency only. |

> **Note:** When the Test Generation module is upgraded from mock to a real LLM (planned Q3 2026), this inventory MUST be updated within 7 days of integration per Art. 53 obligations.

---

## 4. Article 53 Compliance Matrix

### 4.1 GPAI Provider Obligations (Meta / Groq)

| Art. 53 Requirement | Status | Evidence |
|---------------------|--------|----------|
| Technical documentation available (Annex XI) | ✅ | Meta Llama 3.3 Model Card published on HuggingFace |
| Training data summary disclosed | ✅ | Meta provides training methodology overview in model card |
| Copyright compliance policy | ✅ | Llama 3.3 Community License + Acceptable Use Policy |
| Cooperation with downstream providers | ✅ | Groq provides API documentation and usage policies |
| GPAI Code of Practice adherence | ⚠️ Pending | Verify Meta and Groq signatory status |

### 4.2 Deployer Obligations (SabaTech / QA-FRAMEWORK)

| Art. 53/55 Requirement | Status | Action |
|------------------------|--------|--------|
| Maintain GPAI model inventory | ✅ This document | — |
| Document model purpose and usage | ✅ Section 3.1 | — |
| No fine-tuning or modification of base model | ✅ Confirmed | Using base model via API, no modifications |
| Implement usage logging for audit trail | ⚠️ Partial | Langfuse tracing configured but not fully integrated for browser-use |
| Inform users of AI interaction | ❌ N/A | Art. 50(1) does not apply (see `art-50-1-assessment.md`) |
| Label AI-generated content | ⚠️ Recommended | Add "AI-assisted" badge in test generation UI (best practice) |
| Report serious incidents to AI Office | ✅ Procedure defined | See `incident-reporting-procedure.md` |

---

## 5. Data Flow Diagram

```
User (Dashboard/API)
    │
    ▼
QA-FRAMEWORK Backend
    │
    ├── browser_use_service.py
    │       │
    │       ├── Constructs prompt (test instructions + URL + DOM context)
    │       │
    │       ▼
    │   Groq API (api.groq.com)
    │       │
    │       ▼
    │   Llama 3.3 70B Inference
    │       │
    │       ▼
    │   Browser action decisions returned
    │       │
    │       ▼
    │   Browser-use agent executes actions in sandboxed browser
    │
    └── (No other GPAI calls in current production code)
```

**Data sent to Groq:** Test instructions (natural language), target URLs, serialized DOM snapshots
**Data received from Groq:** Browser action commands (click coordinates, text input, navigation URLs)
**No PII, credentials, or customer data is sent to the model.**

---

## 6. Risk Assessment

| Risk | Likelihood | Impact | Mitigation | Residual |
|------|-----------|--------|------------|----------|
| Model outputs biased test results | Low | Medium | Human review of generated tests before execution; test results validated against assertions | Low |
| Prompt injection via web page content | Medium | Medium | Browser-use agent sandboxed in isolated environment; no production data exposed; test targets are pre-validated | Low |
| API unavailability (Groq outage) | Low | Low | Retry logic with exponential backoff; fallback to manual test creation | Minimal |
| Data leakage via prompts | Low | Medium | No PII sent in prompts; only test URLs and instructions; Groq does not retain data per policy | Low |
| Model deprecation by provider | Low | Medium | Groq supports multiple models; migration path documented; quarterly provider review | Low |
| Regulatory change (new GPAI obligations) | Medium | Medium | Quarterly review of EU AI Act guidance; subscribe to AI Office updates | Medium |
| Vendor lock-in (Groq-specific features) | Low | Low | Using LangChain abstraction layer; provider swappable via config | Minimal |

---

## 7. Planned Model Additions

| Model | Provider | Purpose | Target | Status |
|-------|----------|---------|--------|--------|
| GPT-4o / GPT-4o-mini | OpenAI | Test generation (replacing mock adapter) | Q3 2026 | Planned |
| Embedding model (TBD) | Local / OpenAI | Semantic test search | Q4 2026 | Evaluated |

> **Obligation:** When new GPAI models are integrated into production, this document MUST be updated within 7 days. The model card directory (`docs/compliance/model-cards/`) must include a corresponding card.

---

## 8. Dashboard Integration

**Status:** ⚠️ Pending implementation

The QA-FRAMEWORK dashboard API provides OpenAPI documentation at `/api/v1/docs`. A compliance documentation endpoint is recommended:

```
GET /api/v1/compliance/gpai-inventory → links to this document
GET /api/v1/compliance/ai-act-status → summary of compliance posture
```

**Action item:** Add compliance docs link to dashboard sidebar (Frontend task, estimated effort: 2h).

---

## 9. Related Documents

| Document | Path | Description |
|----------|------|-------------|
| AI Systems Register (SabaTech-wide) | `docs/compliance/ai-systems-register.md` | All GPAI models across SabaTech (20 models) |
| Model Cards Directory | `docs/compliance/model-cards/` | Summary model cards per provider |
| Art. 50(1) Assessment | `docs/compliance/art-50-1-assessment.md` | Transparency obligation analysis (not applicable) |
| AI Literacy Policy | `docs/compliance/AI_LITERACY_POLICY.md` | Art. 4 AI literacy requirements |
| CVD Policy | `docs/compliance/cvd-policy.md` | Coordinated Vulnerability Disclosure |
| Incident Reporting | `docs/compliance/incident-reporting-procedure.md` | Art. 55 serious incident procedure |
| EU AI Act Gap Analysis | (research) `reports/research/eu-ai-act-gap-analysis-2026-07-09.md` | Original gap analysis (G3 reference) |
| Security Policy | `docs/security/SECURITY_POLICY.md` | Overall security framework |
| Risk Register | `docs/security/RISK_REGISTER.md` | Security risks including AI-related |

---

## 10. Maintenance & Review

- **Review frequency:** Quarterly (next review: 2026-10-26)
- **Trigger events:** New model integration, provider change, regulatory update, serious incident
- **Owner:** DevOps team
- **Audit trail:** Git version control in `SabaTech-dev/QA-FRAMEWORK`
- **Notification:** Changes to this document must be communicated to all stakeholders within 7 days

---

## 11. Verification

To verify the accuracy of this inventory:

```bash
# 1. Check production GPAI model configuration
grep -n "BROWSER_USE_LLM_PROVIDER\|BROWSER_USE_MODEL" \
  /home/joker/repos/QA-FRAMEWORK/dashboard/backend/.env.example

# 2. Verify no other LLM API keys are configured
grep -rE "OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY|GOOGLE_API_KEY" \
  /home/joker/repos/QA-FRAMEWORK/.env 2>/dev/null
# Expected: no results (no other API keys in production env)

# 3. Verify mock adapter has no real API calls
grep -n "api_key\|requests.post\|httpx\|aiohttp\|openai\|anthropic" \
  /home/joker/repos/QA-FRAMEWORK/src/infrastructure/test_generation/llm_adapter.py
# Expected: only type hints and docstring mentions

# 4. Verify browser-use service uses Groq only
grep -n "BROWSER_USE_LLM_PROVIDER\|ChatGroq\|langchain_groq" \
  /home/joker/repos/QA-FRAMEWORK/dashboard/backend/services/ai/browser_use_service.py

# 5. List all GPAI-related docs
ls -la /home/joker/repos/QA-FRAMEWORK/docs/compliance/
```

---

## References

- [EU AI Act Full Text (EUR-Lex)](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
- [Meta Llama 3.3 Model Card (HuggingFace)](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct)
- [Groq Model Documentation](https://console.groq.com/docs/model/llama-3.3-70b-versatile)
- [Groq Privacy Policy](https://groq.com/privacy-policy/)
- [EU AI Act GPAI Code of Practice](https://digital-strategy.ec.europa.eu/en/policies/ai-code-conduct)
- [Llama 3.3 Community License](https://llama.com/llama3_3/license)
- [Digital Omnibus timeline changes](https://digital-strategy.ec.europa.eu/en/policies/digital-omnibus)

---

**Document Owner:** SabaTech DevOps / Compliance
**Approved by:** Alfred (AI CEO Agent)
**Classification:** Internal — Compliance Document
**Git tracking:** `SabaTech-dev/QA-FRAMEWORK/docs/compliance/GPAI-Inventory.md`
