# ADR-001: Endpoint Accuracy Index como criterio de selección de providers LLM

**Fecha:** 2026-08-21
**Estado:** Propuesta (accepted tras Alfred Review)
**Decisores:** Joker, Alfred
**Fuentes:** [Artificial Analysis — Launching the Endpoint Accuracy Index (4-ago-2026)](https://artificialanalysis.ai/articles/endpoint-accuracy-index) · [Methodology v1.0](https://artificialanalysis.ai/methodology/endpoint-accuracy-index)

---

## Contexto

Los modelos open-weight (GLM-5.2, gpt-oss-120b, DeepSeek V4 Pro, Kimi K3…) los sirven decenas de providers serverless bajo el **mismo nombre de modelo**, pero cada uno es libre de cuantizar pesos, limitar output tokens, truncar contexto o escribir kernels propios. Resultado medido por [Artificial Analysis Endpoint Accuracy Index](https://artificialanalysis.ai/articles/endpoint-accuracy-index) (lanzado 4-ago-2026):

- **GLM-5.2:** 51.9% (Blackbox AI) a 100.3% (Fireworks/Nebius) del reference — **mismos pesos oficiales** (datos launch 4-ago-2026; refresh ago-2026: mínimo actual DeepInfra FP4 73%, máximo Together AI 102%).
- **gpt-oss-120b:** 69.8% (Cloudflare) a 100.8% (Amazon Bedrock). Cloudflare es de los más caros ($0.39/1M) y el peor en accuracy.
- **DeepSeek V4 Pro:** 97.2% a 107% — cluster apretado, demuestra que la fidelidad es **decisión del provider, no física**.
- **El precio NO predice accuracy:** Blackbox $0.778/1M por 51.9% vs Fireworks $0.818/1M por 100.3% (5 céntimos más por el doble de accuracy).
- **El daño se concentra en tool calling y long-context recall** (las skills agénticas que QA-FRAMEWORK mide), no en razonamiento general: GPQA spread solo 8pp (70.7%–79%) vs 31pp composite. El reference de gpt-oss-120b saca 37% en BFCL-500; el peor endpoint, 22% (−40% relativo).

Métrica: cada endpoint se puntúa como % de un deployment self-hosted de los pesos oficiales (SGLang, precision recomendada por el lab, publicada y reproducible). Suite: BFCL v4-500 (tool calling) + HLE-250 (razonamiento duro) + AA-LCR-25 (long-context recall), 33% cada una, IC 95%. Resultados point-in-time, fechados.

**Relevancia para QA-FRAMEWORK:** el SaaS genera evidencia de testing sobre LLMs. Si el endpoint degradinga la accuracy del modelo que evaluamos o usamos, nuestras conclusions y nuestros propios pipelines (test generation, self-healing, AI assistant) heredan esa degradación silenciosamente. "Quién sirve el modelo" importa tanto como "qué modelo".

## Decisión

1. **Criterio obligatorio:** todo provider LLM (propio o recomendado a clientes) que sirva un modelo open-weight debe tener **Endpoint Accuracy Index ≥95% o paridad estadística con el reference** (IC 95% incluye 100%) para uso en producción/evals. Por debajo de 90% queda excluido para cualquier función que dependa de tool calling o long-context.
2. **El precio nunca es predictor:** prohibido seleccionar endpoint solo por precio/velocidad. El precio se evalúa SOLO entre endpoints que ya pasen el umbral de accuracy.
3. **Verificación point-in-time:** el índice es snapshot fechado. Antes de fijar un default y al menos trimestralmente (o al cambiar de versión de modelo), re-verificar la tabla del modelo en [artificialanalysis.ai/models/{model}/providers](https://artificialanalysis.ai/models/glm-5-2/providers). Los providers actualizan sus serving stacks sin aviso.
4. **Auditar la ruta real en agregadores:** al usar OpenRouter u otros routers, identificar el endpoint subyacente (routing/pin by provider) — el router no es el endpoint. OpenRouter publicó su propio análisis de performance por provider (p99 77–92s vs p50 6–8s en Claude Sonnet 4.5 según provider), mismo problema, métrica distinta.
5. **Documentar en el radar:** toda selección queda registrada en [Model & Provider Radar](model-provider-radar.md) con fecha de verificación y score EAI.

## Consecuencias

**Positivas:**
- Evita el failure mode silencioso: mismas respuestas "se ven" correctas pero el endpoint degrada ~50% la capability medida.
- Refuerza el valor del SaaS: QA-FRAMEWORK puede ofrecer "endpoint accuracy auditing" como parte de su evaluación de sistemas con LLM (alineado con EU AI Act Art. 15 — accuracy/robustness declarada vs real).
- Reduce coste: dentro de los aprobados hay opciones baratas (CoreWeave 97.6% a $0.044/1M en gpt-oss-120b vs Cloudflare 69.8% a $0.390).

**Negativas/costes:**
- Dependencia de una fuente externa (Artificial Analysis) para modelos cubiertos (hoy 3; Kimi K3 próximamente). Para modelos no cubiertos, el criterio no puede aplicarse directamente → flag "sin datos EAI" en el radar y evaluación propia puntual (golden-set propio).
- Los datos rotan: un provider puede mejorar/empeorar tras un refresh → obligación de re-verificación trimestral.

## Alternativas consideradas

| Alternativa | Descartada porque |
|---|---|
| Seleccionar solo por precio/speed (status quo implícito) | Precio no correlaciona con accuracy (caso Blackbox vs Fireworks); degradación invisible en tool calling |
| Benchmarks propios desde cero | Coste alto; AA publica suite reproducible (BFCL/HLE/AA-LCR) con reference deployment documentado; usarlo y complementar con golden-set propio solo donde no hay cobertura |
| Usar solo first-party endpoints (z.ai, DeepSeek) | Válido como default conservador, pero first-party no siempre es el más rápido/barato; y el primer party también debe verificarse (DeepSeek 107% > reference; Zai sin score EAI publicado aún — ver radar) |

## Aplicación inmediata SabaTech (stack propio)

- **OpenClaw/QA-FW usan GLM-5.2 vía ZAI first-party + OpenRouter.** ZAI no tenía score EAI publicado al 21-ago-2026 (`n/a` en tabla). Acción: (a) mantener ZAI como default (first-party = serving recipe del lab), (b) en OpenRouter, fijar routing a endpoints verificados ≥95% (Fireworks 100%, FriendliAI 100%, SiliconFlow 99%, Novita 98%, Wafer 98%, Parasail 98%, Baseten 98%, CoreWeave 97%), evitar DeepInfra FP4 (73%) y Scaleway (75%).
- Re-evaluar cuando GLM-5.3 weights se sirvan ampliamente (la cobertura EAI rota: entra con ecosistema amplio, sale al ser supersedida).

---

*ADRs siguientes → `docs/explanation/adr-*.md`. Radar vivo de providers → [model-provider-radar.md](model-provider-radar.md).*
