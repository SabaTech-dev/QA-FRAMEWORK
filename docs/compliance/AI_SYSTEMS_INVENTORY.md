# AI Systems Inventory — GPAI Models Used in QA-FRAMEWORK

> **EU AI Act Art. 53-55 (GPAI Obligations) Compliance Document**
> 
> **Last Updated:** 2026-07-09
> **Owner:** DevOps / Compliance
> **Classification:** Internal — Compliance Documentation

---

## 1. Purpose

This document inventories all General-Purpose AI (GPAI) models used within the QA-FRAMEWORK platform, as required by EU AI Act Articles 53-55 (obligations for GPAI providers and deployers). It serves as the authoritative reference for compliance audits, transparency reporting, and risk assessments.

---

## 2. Summary

| # | Model | Provider | Purpose | Layer | Status |
|---|-------|----------|---------|-------|--------|
| 1 | Llama 3.3 70B Versatile | Groq | Browser-use AI test automation | Dashboard Backend | ✅ Active |

**Total GPAI models in production:** 1  
**Models in mock/placeholder:** 0 (test generation module has mock adapter, no real LLM)

---

## 3. Detailed Model Inventory

### 3.1 Meta Llama 3.3 70B Versatile (via Groq)

| Field | Value |
|-------|-------|
| **Model name** | `llama-3.3-70b-versatile` |
| **Provider** | Groq Inc. |
| **Provider API** | Groq Cloud API (`api.groq.com`) |
| **Integration library** | `langchain-groq` (>=0.1.0), `browser-use` (>=0.1.45) |
| **Purpose in QA-FRAMEWORK** | Powers the Browser-Use AI test automation service — accepts natural language prompts to navigate web pages and execute test actions autonomously |
| **Layer** | Dashboard Backend (`dashboard/backend/services/ai/browser_use_service.py`) |
| **Date of integration** | 2026-05 (QA-FRAMEWORK dashboard backend) |
| **Version at last review** | `llama-3.3-70b-versatile` (Meta Llama 3.3, 70B parameters, instruction-tuned) |
| **Config keys** | `BROWSER_USE_LLM_PROVIDER=groq`, `BROWSER_USE_MODEL=llama-3.3-70b-versatile`, `GROQ_API_KEY` (secret) |
| **Data sent to model** | Natural language test instructions, URL context, DOM snapshots (via browser-use agent) |
| **Data returned** | Browser action decisions (clicks, typing, navigation) |
| **PII risk** | Low — processes test URLs and instructions, not user PII |

#### Provider Compliance: Groq

| Check | Status | Notes |
|-------|--------|-------|
| GDPR compliance | ✅ | Groq has DPA available; data processed in US/EU |
| EU AI Act Art. 53 (GPAI provider obligations) | ⚠️ Pending | Groq relies on Meta's model card and Code of Practice adherence |
| Transparency documentation | ✅ | [Meta Llama 3.3 Model Card](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct) |
| Groq Privacy Policy | ✅ | Available at https://groq.com/privacy-policy/ |
| DPA status | ⚠️ Pending | Need signed DPA with Groq for production use |

---

## 4. Non-GPAI AI Components (No External Model Calls)

The following modules have AI-related naming but do **not** make external LLM API calls:

| Component | File | Status |
|-----------|------|--------|
| Test Generation LLM Adapter | `src/infrastructure/test_generation/llm_adapter.py` | Mock implementation — no real LLM calls. Future integration planned. |
| Accuracy Rule-Based Evaluator | `src/infrastructure/accuracy_testing/rule_based_evaluator.py` | Rule-based scoring, no LLM. `ai_model` field tracked for transparency only. |
| Coverage Analyzer | `src/infrastructure/` | Rule-based analysis, no LLM |
| Root Cause Analyzer | `src/infrastructure/` | Rule-based analysis, no LLM |
| Test Optimizer | `src/infrastructure/` | Rule-based optimization, no LLM |

---

## 5. GPAI Provider Verification (Art. 53 Compliance)

### 5.1 Groq (deployer of Meta Llama 3.3)

**Article 53 requirements for GPAI providers:**

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Technical documentation available | ✅ | Meta Llama 3.3 Model Card published on HuggingFace |
| Training data summary disclosed | ✅ | Meta provides training methodology in model card |
| Copyright compliance policy | ✅ | Meta Llama Community License + acceptable use policy |
| Cooperation with downstream providers | ✅ | Groq provides API documentation and usage policies |

**Article 54 — Obligations of downstream providers (Groq):**
- Groq operates as a hosted inference provider for Meta's open-weight model
- Groq publishes their own terms of service and acceptable use policy
- ⚠️ **Action needed:** Verify Groq has signed the EU AI Act GPAI Code of Practice

**Article 55 — Transparency for deployers (SabaTech/QA-FRAMEWORK):**
- ✅ This document serves as the deployer transparency record
- ✅ Model purpose and usage documented above
- ✅ No fine-tuning or modification of the base model
- ⚠️ **Action needed:** Implement usage logging via Langfuse for audit trail

---

## 6. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Model outputs biased test results | Low | Medium | Human review of generated tests before execution |
| API unavailability | Medium | Low | Groq 99.9% SLA; fallback to manual test creation |
| Data leakage via prompts | Low | Medium | No PII sent in prompts; only test URLs and instructions |
| Regulatory change (new GPAI obligations) | Medium | Medium | Quarterly review of EU AI Act guidance updates |

---

## 7. Planned Additions

| Model | Provider | Purpose | Target Date | Status |
|-------|----------|---------|-------------|--------|
| GPT-4o / GPT-4o-mini | OpenAI | Test generation (replacing mock adapter) | Q3 2026 | Planned |
| Embedding model (TBD) | Local / OpenAI | Semantic test search | Q4 2026 | Planned |

> When new models are integrated, this document MUST be updated within 30 days.

---

## 8. Maintenance

- **Review frequency:** Quarterly (next review: 2026-10-09)
- **Trigger events:** New model integration, provider change, regulatory update
- **Owner:** DevOps team
- **Audit trail:** Git version control in `SabaTech-dev/QA-FRAMEWORK`

---

## References

- [EU AI Act Full Text](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
- [Meta Llama 3.3 Model Card](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct)
- [Groq Privacy Policy](https://groq.com/privacy-policy/)
- [EU AI Act GPAI Code of Practice](https://digital-strategy.ec.europa.eu/en/policies/ai-code-conduct)
- Source gap analysis: `reports/research/eu-ai-act-gap-analysis-2026-07-09.md` (§3.2 G3)
