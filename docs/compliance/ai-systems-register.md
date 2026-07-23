# AI Systems Register — EU AI Act Compliance

> **Document Type:** SabaTech Group-Wide GPAI Model Inventory (Article 53 — Transparency obligations)
> **Regulation:** Regulation (EU) 2024/1689 (EU AI Act)
> **Organization:** SabaTech (SabaTech-dev)
> **Last Updated:** 2026-07-24
> **Next Review:** 2026-10-24 (quarterly)
> **Supersedes:** `AI_SYSTEMS_INVENTORY.md` (2026-07-09, QA-FRAMEWORK scope only)

---

## 1. Overview

This register documents all General-Purpose AI Models (GPAI) used within SabaTech's systems, as required by Article 53 of the EU AI Act. It covers models used in production, development, agent infrastructure, and internal tooling.

**GPAI Definition (Art. 3(63)):** An AI model — including where trained with large amounts of data through self-supervision — that displays significant generality and is capable of competently performing a wide range of distinct tasks, regardless of how the model is placed on the market, and that can be integrated in a variety of downstream systems or applications.

---

## 2. Summary Table

| # | Model | Provider | Category | Purpose | Risk Tier | Since | Status |
|---|-------|----------|----------|---------|-----------|-------|--------|
| 1 | GLM-5.2 | ZAI (Zhipu AI) | GPAI (LLM, text) | Primary agent LLM (DevOps, main) | Limited | 2026-07 | Active |
| 2 | GLM-5.1 | ZAI (Zhipu AI) | GPAI (LLM, text) | Agent LLM (research, qa-tester, coder, security) | Limited | 2026-06 | Active |
| 3 | GLM-5 | ZAI (Zhipu AI) | GPAI (LLM, text) | Agent LLM (backup/fallback) | Limited | 2026-05 | Active |
| 4 | GLM-5-Turbo | ZAI (Zhipu AI) | GPAI (LLM, text) | Low-latency agent tasks (cron jobs) | Limited | 2026-06 | Active |
| 5 | GLM-4.7 | ZAI (Zhipu AI) | GPAI (LLM, text) | Standard agent tasks | Limited | 2026-04 | Active |
| 6 | GLM-4.6 | ZAI (Zhipu AI) | GPAI (LLM, text) | Default model (gateway config) | Limited | 2026-03 | Active |
| 7 | GLM-4.6v | ZAI (Zhipu AI) | GPAI (LLM, text+vision) | Vision tasks (image analysis) | Limited | 2026-04 | Active |
| 8 | Nemotron-3 Ultra (550B) | NVIDIA (via OpenRouter) | GPAI (LLM, text) | Free-tier reasoning tasks | Limited | 2026-07 | Active |
| 9 | Nemotron-3 Nano Omni (30B) | NVIDIA (via OpenRouter) | GPAI (LLM, text+image) | Free-tier multimodal reasoning | Limited | 2026-07 | Active |
| 10 | Laguna S 2.1 | Poolside (via OpenRouter) | GPAI (LLM, text, code) | Free-tier code generation | Limited | 2026-07 | Active |
| 11 | Ornith 1.0 35B-A3B (Q4_K_M) | Self-hosted (llama.cpp) | GPAI (LLM, local) | PR-Agent code review, local inference | Limited | 2026-05 | Active |
| 12 | Llama-3.3-70B-Versatile | Groq | GPAI (LLM, text) | QA-FRAMEWORK browser-use AI agent | Limited | 2026-04 | Active |
| 13 | GPT-4 (family) | OpenAI | GPAI (LLM, text, vision) | Image generation, PDF analysis, fallback | High | 2026-03 | Active |
| 14 | Gemini (family) | Google DeepMind | GPAI (LLM, text, vision) | PDF analysis, multimodal fallback | High | 2026-03 | Active |
| 15 | Nomic Embed Text v2 | Nomic AI (via Ollama/llama.cpp) | Embedding model | Semantic search, memory indexing | Minimal | 2026-03 | Active |
| 16 | Gemma 4 (2B variants) | Google (via Ollama, local) | GPAI (LLM, small, local) | Experimental local inference | Limited | 2026-06 | Active |
| 17 | Whisper (base) | OpenAI (self-hosted, local) | GPAI (speech-to-text) | Audio transcription (voice messages) | Minimal | 2026-03 | Active |
| 18 | Eleven Multilingual v2 | ElevenLabs | GPAI (TTS) | Text-to-speech (voice output) | Minimal | 2026-06 | Active |
| 19 | Edge TTS (Neural) | Microsoft | GPAI (TTS) | Default TTS provider (es-ES) | Minimal | 2026-06 | Active |
| 20 | MiMo-V2.5 | OpenCode (via opencode-go) | GPAI (LLM, code) | OpenCode agent coding tasks | Limited | 2026-07 | Active |

---

## 3. Detailed Model Records

### 3.1 — GLM-5.2 (ZAI/Zhipu AI)

| Field | Value |
|-------|-------|
| **Model ID** | `zai/glm-5.2` |
| **Provider** | ZAI (Zhipu AI), Beijing, China |
| **API Endpoint** | `https://api.z.ai/api/coding/paas/v4` |
| **Version** | GLM-5.2 (Next-Gen) |
| **Modality** | Text input, text output |
| **Context Window** | 1,000,000 tokens |
| **Max Output** | 131,072 tokens |
| **Purpose** | Primary LLM for agent: DevOps workspace, gateway main agent |
| **Integration Date** | July 2026 |
| **Deployment Mode** | API (SaaS) |
| **Data Processing** | Off-premise (ZAI cloud). No training data sent intentionally. |
| **EU AI Act Risk** | Limited — deployer transparency obligations apply |
| **Model Card** | [ZAI GLM Model Family](https://z.ai/model-specifications) — see `model-cards/glm-5.2.md` |
| **Cost** | $1/M input, $3.2/M output, $0.2/M cache read |

**Mitigation Measures:**
- API key stored in `~/.openclaw/.env` (not in repos)
- All agent prompts sanitized before sending
- No PII or customer data sent to model
- Langfuse tracing enabled for audit

---

### 3.2 — GLM-5.1 (ZAI/Zhipu AI)

| Field | Value |
|-------|-------|
| **Model ID** | `zai/glm-5.1` |
| **Provider** | ZAI (Zhipu AI), Beijing, China |
| **Version** | GLM-5.1 (Next-Gen) |
| **Modality** | Text input, text output |
| **Context Window** | 204,800 tokens |
| **Max Output** | 131,072 tokens |
| **Purpose** | Agent LLM for: research, qa-tester, coder, security workspaces |
| **Integration Date** | June 2026 |
| **Deployment Mode** | API (SaaS) |
| **EU AI Act Risk** | Limited |
| **Model Card** | See `model-cards/glm-5.1.md` |

---

### 3.3 — GLM-5 (ZAI/Zhipu AI)

| Field | Value |
|-------|-------|
| **Model ID** | `zai/glm-5` |
| **Provider** | ZAI (Zhipu AI) |
| **Version** | GLM-5 (Flagship) |
| **Purpose** | Backup/fallback LLM for agent infrastructure |
| **Integration Date** | May 2026 |
| **EU AI Act Risk** | Limited |

---

### 3.4 — GLM-5-Turbo (ZAI/Zhipu AI)

| Field | Value |
|-------|-------|
| **Model ID** | `zai/glm-5-turbo` |
| **Provider** | ZAI (Zhipu AI) |
| **Purpose** | Low-latency tasks, cron jobs, Dreaming consolidation |
| **Integration Date** | June 2026 |
| **EU AI Act Risk** | Limited |

---

### 3.5 — GLM-4.7 (ZAI/Zhipu AI)

| Field | Value |
|-------|-------|
| **Model ID** | `zai/glm-4.7` |
| **Provider** | ZAI (Zhipu AI) |
| **Purpose** | Standard agent tasks |
| **Integration Date** | April 2026 |
| **EU AI Act Risk** | Limited |

---

### 3.6 — GLM-4.6 (ZAI/Zhipu AI)

| Field | Value |
|-------|-------|
| **Model ID** | `zai/glm-4.6` |
| **Provider** | ZAI (Zhipu AI) |
| **Purpose** | Default gateway model (configured in `openclaw.json`) |
| **Integration Date** | March 2026 |
| **EU AI Act Risk** | Limited |

---

### 3.7 — GLM-4.6v (ZAI/Zhipu AI)

| Field | Value |
|-------|-------|
| **Model ID** | `zai/glm-4.6v` |
| **Provider** | ZAI (Zhipu AI) |
| **Modality** | Text + Image input, text output |
| **Purpose** | Vision tasks — image analysis, screenshot review |
| **Integration Date** | April 2026 |
| **EU AI Act Risk** | Limited |

---

### 3.8 — Nemotron-3 Ultra (NVIDIA, via OpenRouter)

| Field | Value |
|-------|-------|
| **Model ID** | `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free` |
| **Provider** | NVIDIA Corporation (via OpenRouter aggregator) |
| **API Endpoint** | `https://openrouter.ai/api/v1` |
| **Version** | Nemotron-3 Ultra 550B (A55B) |
| **Modality** | Text input, text output |
| **Context Window** | 1,000,000 tokens |
| **Purpose** | Free-tier reasoning tasks (budget conservation) |
| **Integration Date** | July 2026 |
| **Deployment Mode** | API (SaaS, free tier) |
| **EU AI Act Risk** | Limited |
| **Cost** | Free (OpenRouter free tier) |

---

### 3.9 — Nemotron-3 Nano Omni (NVIDIA, via OpenRouter)

| Field | Value |
|-------|-------|
| **Model ID** | `openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` |
| **Provider** | NVIDIA Corporation (via OpenRouter) |
| **Modality** | Text + Image input, text output |
| **Purpose** | Free-tier multimodal reasoning |
| **Integration Date** | July 2026 |
| **EU AI Act Risk** | Limited |

---

### 3.10 — Laguna S 2.1 (Poolside, via OpenRouter)

| Field | Value |
|-------|-------|
| **Model ID** | `openrouter/poolside/laguna-s-2.1:free` |
| **Provider** | Poolside (via OpenRouter) |
| **Purpose** | Free-tier code generation |
| **Integration Date** | July 2026 |
| **EU AI Act Risk** | Limited |

---

### 3.11 — Ornith 1.0 35B-A3B (Self-hosted)

| Field | Value |
|-------|-------|
| **Model ID** | `mi-ornith-aeon-35b-mtp-q4km` |
| **Provider** | Self-hosted (llama.cpp on jokerserver, Tesla V100) |
| **API Endpoint** | `http://192.168.1.39:8001/v1` (LAN only, Tailscale) |
| **Quantization** | Q4_K_M (4-bit) |
| **Purpose** | PR-Agent automated code review, local inference |
| **Integration Date** | May 2026 |
| **Deployment Mode** | On-premise (self-hosted) |
| **EU AI Act Risk** | Limited — self-hosted, no data leaves premises |
| **Hardware** | NVIDIA Tesla V100-SXM2-32GB |

**Key advantage:** No data exfiltration risk. All inference runs locally.

---

### 3.12 — Llama-3.3-70B-Versatile (Groq)

| Field | Value |
|-------|-------|
| **Model ID** | `llama-3.3-70b-versatile` |
| **Provider** | Groq Inc. (via LangChain `ChatGroq`) |
| **API Endpoint** | `https://api.groq.com/openai/v1` |
| **Purpose** | QA-FRAMEWORK browser-use AI agent (automated test generation) |
| **Integration Date** | April 2026 |
| **Deployment Mode** | API (SaaS) |
| **EU AI Act Risk** | Limited |
| **Config Location** | `dashboard/backend/services/ai/browser_use_service.py`, `dashboard/backend/config.py` |

---

### 3.13 — GPT-4 family (OpenAI)

| Field | Value |
|-------|-------|
| **Model ID** | `gpt-4`, `gpt-4o`, `gpt-image-1` |
| **Provider** | OpenAI, San Francisco, USA |
| **Purpose** | Image generation, PDF analysis, multimodal fallback |
| **Integration Date** | March 2026 |
| **Deployment Mode** | API (SaaS) |
| **EU AI Act Risk** | High — deployer obligations (fundamental rights impact assessment, Art. 27) |
| **Model Card** | [OpenAI Model Cards](https://platform.openai.com/docs/models) |

**High-Risk Justification:** GPT-4 image generation may be used in contexts that could affect individuals. Mitigation: all generated content is for internal use only, clearly labeled as AI-generated.

---

### 3.14 — Gemini family (Google)

| Field | Value |
|-------|-------|
| **Model ID** | `gemini-2.5-pro`, `gemini-2.5-flash` |
| **Provider** | Google DeepMind |
| **Purpose** | PDF analysis, multimodal tasks, fallback reasoning |
| **Integration Date** | March 2026 |
| **Deployment Mode** | API (SaaS) |
| **EU AI Act Risk** | High — same rationale as GPT-4 |
| **Model Card** | [Google Gemini Model Card](https://deepmind.google/technologies/gemini/) |

---

### 3.15 — Nomic Embed Text v2

| Field | Value |
|-------|-------|
| **Model ID** | `nomic-embed-text` |
| **Provider** | Nomic AI (self-hosted via Ollama and llama.cpp) |
| **Purpose** | Semantic embeddings for memory search, wiki indexing, QMD documental search |
| **Integration Date** | March 2026 |
| **Deployment Mode** | On-premise (self-hosted, CPU + GPU) |
| **EU AI Act Risk** | Minimal — embedding model, not generative |
| **Endpoints** | `http://localhost:8002/v1` (llama.cpp), `http://localhost:11434` (Ollama) |

---

### 3.16 — Gemma 4 (Google, self-hosted via Ollama)

| Field | Value |
|-------|-------|
| **Model IDs** | `gemma4:latest`, `gemma4:e2b`, `saba-gemma4-2b-v3-q8` |
| **Provider** | Google (self-hosted via Ollama) |
| **Purpose** | Experimental local inference, fine-tuning experiments |
| **Integration Date** | June 2026 |
| **Deployment Mode** | On-premise (self-hosted) |
| **EU AI Act Risk** | Limited |

---

### 3.17 — Whisper (OpenAI, self-hosted)

| Field | Value |
|-------|-------|
| **Model ID** | `whisper-base` |
| **Provider** | OpenAI (self-hosted via `openai-whisper`) |
| **Purpose** | Audio transcription — voice message to text |
| **Integration Date** | March 2026 |
| **Deployment Mode** | On-premise (self-hosted, local binary) |
| **EU AI Act Risk** | Minimal — transcription only, no decision-making |

---

### 3.18 — Eleven Multilingual v2 (ElevenLabs)

| Field | Value |
|-------|-------|
| **Model ID** | `eleven_multilingual_v2` |
| **Provider** | ElevenLabs |
| **Purpose** | Text-to-speech — voice output for agent responses |
| **Integration Date** | June 2026 |
| **Deployment Mode** | API (SaaS) |
| **EU AI Act Risk** | Minimal — TTS only |
| **Voice ID** | `HMCmDsbKeaSZp5LMOYKR` |

---

### 3.19 — Edge TTS Neural (Microsoft)

| Field | Value |
|-------|-------|
| **Model ID** | `es-ES-AlvaroNeural` |
| **Provider** | Microsoft (Edge TTS) |
| **Purpose** | Default TTS provider (Spanish) |
| **Integration Date** | June 2026 |
| **EU AI Act Risk** | Minimal |

---

### 3.20 — MiMo-V2.5 (OpenCode)

| Field | Value |
|-------|-------|
| **Model ID** | `opencode-go/MiMo-V2.5` |
| **Provider** | OpenCode (via opencode-go provider) |
| **Purpose** | OpenCode agent coding tasks |
| **Integration Date** | July 2026 |
| **EU AI Act Risk** | Limited |

---

## 4. Risk Classification Summary

### High Risk (Art. 27 — Fundamental Rights Impact Assessment required)

| Model | Justification | Mitigation |
|-------|---------------|------------|
| GPT-4 family (OpenAI) | Potential use in contexts affecting individuals (image generation, analysis) | Internal use only; AI-generated content labeled; no automated decisions affecting rights |
| Gemini family (Google) | Same as above | Same mitigations |

**Action required by 2 Aug 2026:** Complete Fundamental Rights Impact Assessment (FRIA) for high-risk deployments.

### Limited Risk (Art. 53 — Transparency obligations)

All LLM models used for agent infrastructure (GLM family, Nemotron, Laguna, Ornith, Llama, MiMo).

**Obligations:**
- Maintain this register ✅
- Inform users they are interacting with AI (where applicable)
- Document model capabilities and limitations
- Report serious incidents to AI Office

### Minimal Risk

Embedding models (Nomic), TTS (ElevenLabs, Microsoft), transcription (Whisper).

**Obligations:** None beyond voluntary best practices.

---

## 5. Data Processing Locations

| Provider | Data Location | Transfer Mechanism |
|----------|---------------|-------------------|
| ZAI (Zhipu AI) | China | Standard Contractual Clauses (SCC) — **REVIEW NEEDED** |
| OpenRouter | USA (routes to various) | Provider-dependent |
| OpenAI | USA | SCC + EU-US Data Privacy Framework |
| Google | USA / EU | SCC + EU-US Data Privacy Framework |
| Groq | USA | SCC |
| ElevenLabs | USA / UK | SCC |
| Microsoft | EU (Edge TTS — EU deployment) | EU data residency |
| Self-hosted (Ornith, Whisper, Nomic, Gemma) | EU (jokerserver, Madrid) | No transfer |

⚠️ **Flag:** ZAI (Zhipu AI) is a Chinese provider. Data sent to ZAI is subject to Chinese law. Review adequacy decision and assess whether SCCs provide sufficient protection. Consider whether sensitive data is being processed.

---

## 6. Incident Response

In case of a serious incident related to a GPAI model (Art. 55):

1. **Immediately:** Stop using the affected model
2. **Within 48h:** Report to AI Office via [EU AI Act incident reporting portal](https://artificialintelligenceact.eu/incident-reporting/)
3. **Within 15 days:** Detailed report including:
   - Model identity and provider
   - Description of incident
   - Number of affected persons
   - Mitigation measures taken
4. **Notify:** Joker (Jose Manuel Sabarís) as DPO

---

## 7. Review Schedule

- **Quarterly review:** Verify model list is current, update versions/purposes
- **On new model adoption:** Add to register within 7 days
- **On model deprecation:** Mark as deprecated, migrate within 30 days
- **Annual review:** Full FRIA refresh for high-risk models

---

## 8. References

- [EU AI Act Full Text](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
- [Article 53 — GPAI Transparency](https://artificialintelligenceact.eu/annex/4/)
- [AI Office Guidance](https://digital-strategy.ec.europa.eu/en/policies/ai-office)
- [Harmonized Standards](https://www.cencenelec.eu/areas-of-work/cen-sectors/information-and-communication-technologies/artificial-intelligence/)

---

**Document Owner:** SabaTech DevOps
**Approved by:** Alfred (AI CEO Agent)
**Classification:** Internal — Compliance Document
