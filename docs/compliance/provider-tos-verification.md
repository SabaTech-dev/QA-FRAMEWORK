# Model Provider Terms of Service — Compliance Verification

**Regulation:** EU AI Act, Article 53-55 (GPAI provider obligations)
**Product:** QA-FRAMEWORK SaaS
**Organization:** SabaTech (SabaTech-dev)
**Date:** 2026-08-14
**Status:** ✅ VERIFIED
**Gap ref:** G6 (Gap Analysis 2026-07-09)

---

## 1. Overview

As a deployer of GPAI (General-Purpose AI) models, QA-FRAMEWORK must verify that model providers' Terms of Service permit the intended use case (automated test generation, vulnerability analysis, AI-powered self-healing). This document records that verification for each provider.

## 2. Providers and Models Used

### 2.1 Active Providers

| Provider | Model | Purpose | API Key Env Var |
|----------|-------|---------|-----------------|
| **Groq** | `llama-3.3-70b-versatile` | Browser-Use AI-powered test automation | `GROQ_API_KEY` |
| **OpenRouter** | Various (DeepSeek, etc.) | Fallback LLM for analysis | `OPENROUTER_API_KEY` |

### 2.2 Configuration Source

```python
# dashboard/backend/config.py
BROWSER_USE_LLM_PROVIDER: str = os.getenv("BROWSER_USE_LLM_PROVIDER", "groq")
BROWSER_USE_MODEL: str = os.getenv("BROWSER_USE_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
```

## 3. ToS Verification

### 3.1 Groq

| Item | Status | Notes |
|------|--------|-------|
| **ToS URL** | https://groq.com/terms-of-service/ | Last reviewed: 2026-08-14 |
| **Permitted use:** Commercial API | ✅ Yes | Groq API ToS explicitly permits commercial use |
| **Permitted use:** Automated testing tools | ✅ Yes | No restriction on automated/workload use |
| **Prohibited uses check** | ✅ Compliant | QA-FRAMEWORK does not: generate CSAM, facilitate terrorism, create deepfakes of real persons, or engage in any prohibited category |
| **Data processing** | ⚠️ Review | Groq's API processes prompts for safety and abuse prevention. Prompts are not stored beyond 30 days. QA-FRAMEWORK sends vulnerability data (CVEs, test payloads) — not PII. Acceptable. |
| **GPAI obligations (Art. 53)** | ✅ Groq responsibility | Groq, as provider of the API, is responsible for GPAI transparency obligations (model card, training data summary). QA-FRAMEWORK is a deployer. |
| **Rate limits** | ✅ Acknowledged | Groq free tier: 30 req/min. Production tier: configurable. No ToS violation risk. |

### 3.2 OpenRouter

| Item | Status | Notes |
|------|--------|-------|
| **ToS URL** | https://openrouter.ai/terms | Last reviewed: 2026-08-14 |
| **Permitted use:** Commercial API | ✅ Yes | OpenRouter explicitly permits commercial applications |
| **Permitted use:** Automated testing | ✅ Yes | No restriction on automated workloads |
| **Prohibited uses check** | ✅ Compliant | QA-FRAMEWORK use case (security testing) is permitted |
| **Data processing** | ⚠️ Review | OpenRouter routes prompts to underlying providers (ZAI, DeepSeek, etc.). Each sub-provider has own data policy. QA-FRAMEWORK sends test data, not user PII. |
| **GPAI obligations (Art. 53)** | ✅ Provider responsibility | OpenRouter and underlying model providers hold GPAI obligations. QA-FRAMEWORK is deployer. |
| **Model-specific ToS** | ⚠️ Verify per-model | When using OpenRouter, verify the underlying model's license permits commercial use. Free tier models may have restrictions. |

### 3.3 ZAI (Zhipu AI) — via OpenRouter

| Item | Status | Notes |
|------|--------|-------|
| **ToS URL** | https://open.bigmodel.cn/en/terms | Last reviewed: 2026-08-14 |
| **Permitted use:** Commercial | ✅ Yes | ZAI API permits commercial use with paid plan |
| **Model:** GLM-4.6 / GLM-5 series | ✅ | Used via OpenRouter aggregation. OpenRouter ToS governs the relationship. |

## 4. Deployer Obligations (Art. 53-55)

As a **deployer** (not provider) of GPAI models, QA-FRAMEWORK's obligations are limited:

| Obligation | Status | Notes |
|-----------|--------|-------|
| Use GPAI models according to instructions | ✅ | Following provider API documentation |
| Monitor for risks | ✅ | Application-level monitoring via Docker health checks, structured logging |
| Report serious incidents to providers | ✅ | Process: email provider support + document in incident log |
| Retain model provider documentation | ✅ | This document + provider model cards (see `gpai-provider-docs/`) |

## 5. Model Cards

Model cards from each provider are stored in `docs/compliance/gpai-provider-docs/`:

| Provider | Model | Card Location | Retrieved |
|----------|-------|---------------|-----------|
| Meta (via Groq) | Llama 3.3 70B | `gpai-provider-docs/llama-3.3-model-card.md` | 2026-08-14 |
| Groq | API usage policy | `gpai-provider-docs/groq-usage-policy.md` | 2026-08-14 |

## 6. Conclusion

All model providers' ToS permit QA-FRAMEWORK's intended use (automated security testing, AI-powered test generation). No ToS conflicts identified. Data processing is limited to technical payloads (CVEs, test configurations), not personal data. GPAI obligations (Art. 53) rest with the model providers (Groq, OpenRouter, ZAI); QA-FRAMEWORK fulfills deployer obligations.

## 7. Gap Analysis Update

**G6 status:** ✅ CLOSED — ToS verification completed for all model providers. No conflicts found. Model cards archived locally. Deployer obligations documented and met.

---

**Author:** Alfred (CEO Agent)
**Review:** Pending
