# 📊 Radar de Modelos & Providers para QA-FRAMEWORK

**Última actualización:** 2026-08-21
**Fuente principal:** [Artificial Analysis Endpoint Accuracy Index](https://artificialanalysis.ai/articles/endpoint-accuracy-index) (launch 4-ago-2026, methodology reproducible)
**Policy:** Se aplica [ADR-001: Endpoint Accuracy Index como criterio de selección](adr-endpoint-accuracy-provider-selection.md)

Este radar documenta qué modelos y qué endpoints SabaTech usa o recomienda en QA-FRAMEWORK, con scores EAI (% de reference self-hosted), precios y fechas de verificación. Los datos son snapshots point-in-time (no monitoreo continuo) — re-evaluar trimestralmente o al cambiar de versión.

---

## 🟢 APROBADOS (para uso producción/evals)

Requisitos: EAI ≥95% o paridad estadística (IC 95% incluye 100%), verificado recientemente.

| Modelo | Provider (endpoint) | EAI % | Precio $/1M (blended) | Fecha verificación | Notas |
|---|---|---|---|---|---|
| GLM-5.2 | Fireworks | 100.3% | $0.48 / $0.82 | 2026-08-21 (launch) / 2026-08-21 (refresh) | Paridad completa; serving fiable |
| GLM-5.2 | FriendliAI | 100.2% | $0.42 | 2026-08-21 | Paridad |
| GLM-5.2 | Nebius (FP4) | 100.3% | $1.06 / $1.70 | 2026-08-21 | Paridad; más caro |
| GLM-5.2 | SiliconFlow (FP8) | 99.0% | $0.62 | 2026-08-21 | Ligeramente bajo paridad; OK |
| GLM-5.2 | Novita (FP8) | 97.7% / 98% | $0.42 | 2026-08-21 | OK |
| GLM-5.2 | Wafer | 98.1% | $0.36 | 2026-08-21 | OK |
| GLM-5.2 | Parasail (NVFP4) | 98.3% | — (no precio listado en launch) | 2026-08-21 | OK; precio desconocido |
| GLM-5.2 | Baseten | 98% | $0.46 | 2026-08-21 | OK |
| GLM-5.2 | CoreWeave | 90.5% / 97% | $0.38 / $0.49 | 2026-08-21 | Launch 90.5%; refresh 97% — mejora marcada |
| GLM-5.2 | Makora (NVFP4) | 95.2% | $0.34 | 2026-08-21 | Umbral justo; OK |
| GLM-5.2 | Together AI | — / 102% | $0.67 | 2026-08-21 | Por encima de reference (102%); OK |
| GLM-5.2 | ZAI first-party | n/a | $0.44 | 2026-08-21 | Sin score EAI publicado aún — mantenido por ser first-party (serving recipe del lab), pero requiere verificación propia puntual |

| Modelo | Provider (endpoint) | EAI % | Precio $/1M | Fecha verificación | Notas |
|---|---|---|---|---|---|
| gpt-oss-120b | Amazon Bedrock | 100.8% | $0.07 | 2026-08-21 | Mejor score; precio competido |
| gpt-oss-120b | SambaNova | 98.2% | $0.10 | 2026-08-21 | Paridad |
| gpt-oss-120b | CoreWeave | 97.6% | $0.02 | 2026-08-21 | Excepcional ratio accuracy/precio (97.6% por $0.02) |
| gpt-oss-120b | Parasail | 98% | — | 2026-08-21 | Paridad |
| gpt-oss-120b | Nebius | 97% | $0.07 | 2026-08-21 | OK |
| gpt-oss-120b | Scaleway | 97% | $0.08 | 2026-08-21 | OK |
| gpt-oss-120b | DeepInfra | 97% | $0.02 | 2026-08-21 | OK |
| gpt-oss-120b | Microsoft Azure | 93% | $0.07 | 2026-08-21 | Justo debajo de 95% pero cerca de paridad — usar con cuidado |
| gpt-oss-120b | SGLang (ref-matched) | 100% | — | 2026-08-21 | Reference implementation; no applicable comercialmente |

| Modelo | Provider (endpoint) | EAI % | Precio $/1M | Fecha verificación | Notas |
|---|---|---|---|---|---|
| DeepSeek V4 Pro | DeepSeek first-party | 107.0% | $0.25 | 2026-08-21 | Mejor score; ligeramente arriba de reference |
| DeepSeek V4 Pro | Makora | 104.3% | — | 2026-08-21 | Paridad+ |
| DeepSeek V4 Pro | SiliconFlow (FP8) | 103.5% | $0.51 | 2026-08-21 | Paridad+ |
| DeepSeek V4 Pro | GMI | 103.1% | $0.56 | 2026-08-21 | Paridad+ |
| DeepSeek V4 Pro | Novita | 101.5% | $0.55 | 2026-08-21 | Paridad |
| DeepSeek V4 Pro | Nebius | 101.2% | — | 2026-08-21 | Paridad |
| DeepSeek V4 Pro | Azure | 99.2% | — | 2026-08-21 | Paridad |
| DeepSeek V4 Pro | Fireworks | 98.1% | $0.65 | 2026-08-21 | Paridad |
| DeepSeek V4 Pro | DeepInfra (FP4) | 97.2% | $0.46 | 2026-08-21 | Paridad |

**Nota DeepSeek:** todos los endpoints están en paridad estadística (97–107%). Este modelo family demuestra que la fidelidad es alcanzable — algunos providers simplemente no la priorizan.

---

## 🟡 EN OBSERVACIÓN (no aún verificados o datos parciales)

| Modelo | Provider | EAI % | Precio $/1M | Notas |
|---|---|---|---|---|
| GLM-5.2 | Databricks | n/a | — | Fastest speed provider pero sin score EAI; verificar antes de uso crítico |
| GLM-5.2 | Scaleway | 74.8% / 75% | $1.57 / — | Por debajo de 90% → no aprobar para uso que dependa de tool calling / long-context |
| GLM-5.2 | DeepInfra (FP4) | 73% | $0.25 | Por debajo de 90%; pero es el más barato — evaluar si aceptable para use-cases no críticos |
| GLM-5.2 | Bitdeer AI | n/a | $0.17 | Más barato pero sin score EAI |

| Modelo | Provider | EAI % | Precio $/1M | Notas |
|---|---|---|---|---|
| gpt-oss-120b | DeepInfra (Turbo) | 84.4% | $0.195 | Por debajo de 90%; variante turbo puede ser más rápida pero menos precisa |
| gpt-oss-120b | Groq | 86.4% | $0.143 | Por debajo de 90%; muy rápido pero accuracy comprometida |
| gpt-oss-120b | Fireworks | 86.2% | $0.195 | Por debajo de 90%; sorprendentemente bajo para Fireworks (en otros modelos está al 100%) |
| gpt-oss-120b | Cerebras | 87.3% | $0.390 | Por debajo de 90%; más caro y menos preciso que alternativas |
| gpt-oss-120b | Cloudflare | 69.8% / 70% | $0.39 | El peor score (≈30pp bajo mejor endpoint); más caro que Amazon Bedrock; native FP4 en Workers AI |
| gpt-oss-120b | Google Vertex | 72.2% | $0.117 | Por debajo de 90%; barato pero underperforms |
| gpt-oss-120b | Baseten | n/a | $0.05 | Sin score EAI listado; muy barato |

| Modelo | Provider | EAI % | Precio $/1M | Notas |
|---|---|---|---|---|
| DeepSeek V4 Pro | Baseten | — | $1.09 | Sin score EAI listado en extract; alto precio |

---

## 🔴 EXCLUIDOS (o solo para benchmarks)

| Modelo | Provider | Motivo de exclusión |
|---|---|---|
| GLM-5.2 | Blackbox AI | EAI 51.9% (launch) — demasiada degradación; ≈50% accuracy vs reference; precio medio ($0.778), no es el barato. No listado en refresh ago-2021 — posiblemente eliminado o mejorado, pero requiere re-verificación. |
| gpt-oss-120b | Cloudflare | EAI 69.8% — degradación severa (−30pp vs mejor). Más caro que alternativas. Documentación propia confirma native FP4 (compromiso accuracy/speed) no divulgado en pricing. |
| gpt-oss-120b | Google Vertex | EAI 72.2% — degradación severa. Barato pero no compensa pérdida. |
| gpt-oss-120b | Baseten (no score) | Sin verificación EAI; no usar en pipelines críticos sin datos. |

---

## 📈 Spread de Accuracy vs Precio (GLM-5.2)

```
Accuracy: 73% (DeepInfra FP4) — 102% (Together AI)
Spread: 29pp ≈ 1.4x ratio

Precio: $0.17 (Bitdeer) — $1.57 (Scaleway launch) / $1.06 (Nebius refresh)
Spread: 6.8x–9.2x (según dataset: launch vs current)
```

**Clave:** precio NO predice accuracy. Blackbox ($0.778) tiene 51.9% mientras Fireworks ($0.818, +5 centavos) tiene 100.3%. Para selección primero filtrar por accuracy ≥95%, después por precio.

---

## 🔍 OpenRouter & Agregadores

Al usar OpenRouter u otros routers que exponen "GLM-5.2" sin especificar el endpoint subyacente, no se puede aplicar el criterio EAI directamente.

**Recomendación SabaTech:**
- En OpenClaw: fijar routing a endpoints verificados (provider pin) — e.g., `provider:fireworks` o `provider:friendliai` en routing config.
- En QA-FRAMEWORK: documentar en perfil de cliente qué endpoint subyacente se usa; si es routing opaco sin pin, marcar como "sin datos EAI" y sugerir migración a endpoint directo o pin especificado.

OpenRouter publicó análisis propio de performance por provider (p99 77–92s vs p50 6–8s en Claude Sonnet 4.5 según provider) — mismo problema, métrica distinta.

---

## 🔄 Proceso de Actualización

1. **Frecuencia:** trimestral (cada 3 meses) o al cambiar de versión de modelo (e.g., GLM-5.3 cuando weights se sirvan ampliamente).
2. **Fuente:** [artificialanalysis.ai/models/{model}/providers](https://artificialanalysis.ai/models/glm-5-2/providers) — buscar tablero "Endpoint Accuracy".
3. **Action:** (a) actualizar tablas arriba con nuevas scores y fechas; (b) re-evaluar umbrales; (c) mover providers entre secciones si cruza ≥95%.
4. **Registro:** cada cambio queda en git commit con referencia a la fecha de snapshot de Artificial Analysis.

---

## 📚 Referencias

- [Artificial Analysis — Launching the Endpoint Accuracy Index (4-ago-2026)](https://artificialanalysis.ai/articles/endpoint-accuracy-index)
- [Methodology v1.0 — Endpoint Accuracy Benchmarking](https://artificialanalysis.ai/methodology/endpoint-accuracy-index)
- [GLM-5.2 Providers Page](https://artificialanalysis.ai/models/glm-5-2/providers)
- [gpt-oss-120b Providers Page](https://artificialanalysis.ai/models/gpt-oss-120b/providers)
- [DeepSeek V4 Pro Providers Page](https://artificialanalysis.ai/models/deepseek-v4-pro/providers)
- [getmegabrain.com — One Provider Sells GLM-5.2 at 51.9% Accuracy (6-ago-2026)](https://getmegabrain.com/blog/endpoint-accuracy-index-same-model-2026)
- [OpenRouter — Claude Sonnet 4.5 Performance by Provider (fechado ~jul-2026)](https://openrouter.ai/models/anthropic/claude-sonnet-4.5)

---

**Integración con ADR-001:** este radar es la fuente viva de datos que alimenta la decisión de seleccionar providers. Para cualquier duda o cambio, revisar primero [ADR-001](adr-endpoint-accuracy-provider-selection.md).