# Model Cards — GPAI Models Used by SabaTech

> **Purpose:** EU AI Act Art. 53 transparency — summary model cards for all GPAI models in use.
> **Source:** Official provider documentation, OpenRouter listings, and self-hosted model metadata.
> **Last Updated:** 2026-07-24

---

## GLM-5.2 (ZAI / Zhipu AI)

- **Architecture:** Transformer-based autoregressive LLM (Mixture-of-Experts)
- **Parameters:** Not publicly disclosed (estimated >100B)
- **Training Data:** Public internet text, code, academic papers, books (not fully disclosed)
- **Modalities:** Text in → Text out
- **Capabilities:** Code generation, reasoning, analysis, writing, math
- **Limitations:** May produce hallucinations; limited knowledge of events after training cutoff; Chinese regulatory compliance may affect responses on sensitive topics
- **Provider:** Zhipu AI (Beijing, China)
- **API:** `https://api.z.ai/api/coding/paas/v4`
- **EU AI Act Note:** Provider is Chinese — data transferred outside EU. SCC review required.
- **Model spec:** https://z.ai (official site)

## GLM-5.1 / GLM-5 / GLM-5-Turbo (ZAI)

Same family as GLM-5.2, earlier versions and variants:
- **GLM-5.1:** Previous generation, similar architecture
- **GLM-5:** Flagship baseline
- **GLM-5-Turbo:** Distilled for lower latency

## GLM-4.7 / GLM-4.6 / GLM-4.6v (ZAI)

- **Architecture:** Transformer-based autoregressive LLM
- **GLM-4.6v:** Multimodal variant (text + image input)
- **Parameters:** Not publicly disclosed
- **Same provider notes as GLM-5.x family**

## Nemotron-3 Ultra 550B (NVIDIA)

- **Architecture:** Mixture-of-Experts, 550B total parameters, 55B active per token
- **Provider:** NVIDIA Corporation
- **Accessed via:** OpenRouter (free tier)
- **Capabilities:** Text reasoning, code generation, analysis
- **Model spec:** https://build.nvidia.com/nvidia/nemotron-3-ultra
- **License:** NVIDIA Open Model License (per provider)

## Nemotron-3 Nano Omni 30B (NVIDIA)

- **Architecture:** Mixture-of-Experts, 30B total, 3B active
- **Modality:** Multimodal (text + image input)
- **Capabilities:** Reasoning, multimodal understanding
- **License:** NVIDIA Open Model License

## Laguna S 2.1 (Poolside)

- **Architecture:** Code-specialized LLM
- **Provider:** Poolside (via OpenRouter free tier)
- **Capabilities:** Code generation, completion, refactoring
- **Limitations:** Specialized for code; general reasoning may be weaker

## Ornith 1.0 35B-A3B (Self-hosted)

- **Architecture:** Mixture-of-Experts, 35B total, 3B active
- **Quantization:** Q4_K_M (4-bit, GGUF format)
- **Provider:** Self-hosted on llama.cpp (jokerserver, Tesla V100)
- **Capabilities:** Code review, general reasoning
- **License:** Heretic variant — verify license terms
- **EU AI Act Note:** Fully on-premise, no data transfer

## Llama-3.3-70B-Versatile (Groq)

- **Architecture:** Dense transformer, 70B parameters
- **Provider:** Meta (original) / Groq (inference hosting)
- **Capabilities:** General purpose text generation, reasoning
- **License:** Llama Community License
- **Model card:** https://llama.meta.com/llama3/
- **Accessed via:** Groq API (`https://api.groq.com`)

## GPT-4 family (OpenAI)

- **Architecture:** Transformer-based (details not fully public)
- **Provider:** OpenAI
- **Modalities:** Text + Image input → Text/Image output
- **Capabilities:** General reasoning, code generation, image generation, multimodal analysis
- **Model card:** https://platform.openai.com/docs/models
- **License:** OpenAI Terms of Use
- **EU AI Act Note:** Classified as High Risk for image generation capabilities

## Gemini family (Google)

- **Architecture:** Multimodal transformer (details not fully public)
- **Provider:** Google DeepMind
- **Modalities:** Text + Image + Video input → Text output
- **Model card:** https://deepmind.google/technologies/gemini/
- **License:** Google Terms of Service
- **EU AI Act Note:** High Risk classification

## Nomic Embed Text v2

- **Architecture:** Encoder-only transformer (embedding model)
- **Parameters:** ~137M
- **Provider:** Nomic AI (self-hosted via Ollama/llama.cpp)
- **Capabilities:** Text embeddings (768 dimensions)
- **License:** Apache 2.0
- **Model card:** https://nomic.ai/atlas/models/embed-text

## Gemma 4 (Google, self-hosted)

- **Architecture:** Decoder-only transformer (small model)
- **Provider:** Google (self-hosted via Ollama)
- **Variants:** 2B base, 2B e2B, custom fine-tune (saba-gemma4-2b-v3)
- **License:** Gemma Terms of Use
- **Model card:** https://ai.google.dev/gemma

## Whisper Base (OpenAI, self-hosted)

- **Architecture:** Encoder-decoder transformer for ASR
- **Parameters:** 74M (base model)
- **Provider:** OpenAI (self-hosted via openai-whisper)
- **Capabilities:** Multilingual speech-to-text (77 languages)
- **License:** MIT
- **Model card:** https://github.com/openai/whisper

## Eleven Multilingual v2 (ElevenLabs)

- **Type:** Neural text-to-speech
- **Provider:** ElevenLabs
- **Capabilities:** Multilingual voice synthesis (29 languages)
- **Model card:** https://elevenlabs.io/docs/api-reference/models
- **License:** ElevenLabs Terms of Service

## Edge TTS Neural (Microsoft)

- **Type:** Neural text-to-speech
- **Provider:** Microsoft
- **Model:** `es-ES-AlvaroNeural` (Spanish, male voice)
- **Accessed via:** Microsoft Edge TTS API (no API key needed)
- **License:** Microsoft Terms

## MiMo-V2.5 (OpenCode)

- **Architecture:** Code-specialized LLM
- **Provider:** OpenCode (via opencode-go provider)
- **Capabilities:** Code generation and editing
- **License:** Verify with provider

---

**Disclaimer:** Model specifications are based on publicly available information at time of writing. Some details (parameter counts, training data) may not be fully disclosed by providers. This document should be updated as providers release more information.
