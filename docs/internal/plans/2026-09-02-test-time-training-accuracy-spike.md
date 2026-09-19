# Spike doc — Test-Time Training (TTT): aplicabilidad al módulo accuracy de QA-FRAMEWORK

> **Tipo:** Spike doc — research, DOC-ONLY (respeta freeze MVP→BETA; no toca código)
> **Card:** `64fd626f-5c89-4978-a40d-98781c3e9f6d` · [P3] · origen LTG 2026-09-02 card 2 (digest-diario-ia #2)
> **Autor:** research (SabaTech) · **Fecha:** 2026-09-02
> **Estado:** Pendiente Alfred Review · **Insumo para:** decisión post-beta del módulo accuracy (módulo previo: `72f97f1b`, done)
> **Ubicación:** `docs/internal/plans/` (convención del repo, misma desviación justificada que `2026-09-01-agent-prompt-injection-testing-spec.md`)
> **Veredicto recomendado:** **NO-GO para el módulo actual · GO CONDICIONADO post-beta como spike experimental** (criterios §6)

---

## Resumen ejecutivo

1. Test-Time Training (TTT) = **actualizar temporalmente los parámetros del modelo durante la inferencia**, con una loss derivada de los propios datos de entrada (p. ej. los ejemplos in-context del task), antes de responder. El paper canónico (MIT, [arXiv:2411.07279](https://arxiv.org/abs/2411.07279), nov-2024) muestra **hasta 6× accuracy vs baselines fine-tuned en ARC** y **+7.3 pp sobre few-shot 10-shot en BIG-Bench Hard** (50.5%→57.8%).
2. El disparador de esta card ([blog de Mithil Vakde, mar-2026](https://mvakde.github.io/blog/44-on-arc-1/)) lleva la idea al extremo de **sample efficiency**: transformer pequeño (8 capas) entrenado **from scratch en test time** logra **44% en ARC-AGI-1 por $0.67 de cómputo** (1.5 h en una RTX 5090), empatando modelos recursivos dedicados (TRM/HRM) y superando a muchos LLMs — open source ([mdlARC](https://github.com/mvakde/mdlARC/)).
3. **Para QA-FW el encaje no es sustituir el evaluador actual**: el módulo accuracy (PR #88) es **rule-based determinista** por diseño — responde a la sentencia alemana **BGH VI ZR 67/24** de responsabilidad AI, donde determinismo y auditabilidad son requisitos, no preferencias. TTT introduce varianza por-run y modelos ad-hoc por tarea: incompatible con ese núcleo, **potencial como capa experimental de adaptación de un LLM-judge por dominio** post-beta.
4. Coste en jokerserver (V100 32GB): la clase de modelo de Vakde (≤75M) **sí es viable** (~5-6 h por corrida completa `[ESTIMACIÓN]`, ~3-4× slower que la 5090 del blog, coste marginal ~€0.5 en electricidad, en ventana idle nocturna); la clase 8B del paper MIT (full-TTT por tarea) **no es viable** en V100 — solo LoRA-TTT como spike.
5. **Veredicto: NO-GO ahora** (freeze MVP→BETA + tensión determinismo/auditabilidad con el origen liability del módulo) · **GO CONDICIONADO post-beta**: spike de 1 semana con criterios explícitos §6 si aparece demanda real (clientes con gold-sets dominio-específicos ≥30 ejemplos y gaps de accuracy >5 pp).

---

## 1. Mecánica TTT + coste de cómputo

### 1.1 Qué es

TTT convierte la inferencia en un mini-ciclo de entrenamiento por tarea:

1. **Contexto → gradientes.** Se construye una loss *auto-supervisada o supervisada* a partir de los datos disponibles del propio task (los k ejemplos demostrativos, las entradas del puzzle, pares pregunta-verdict de referencia) y se actualizan los pesos del modelo (completa o parcialmente) **antes/durante** de responder. Tras resolver el task, el modelo se descarta o se restaura — el "entrenamiento" vive solo durante esa inferencia ([MIT 2411.07279](https://arxiv.org/abs/2411.07279): "temporarily updating model parameters during inference using a loss derived from input data").
2. **Dos escuelas:**
   - **TTT como adaptación de LLM existente** (MIT): LoRA/full-FT breve por task sobre los in-context examples → el LLM se especializa en la regla del task concreto. En ARC: 53.0% validación pública con un 8B, **61.9% ensembled con program synthesis** (~humano medio).
   - **TTT como entrenamiento from-scratch por tarea** (Vakde): un transformer pequeño (8 capas, SwiGLU, RMSNorm, 3D-RoPE + per-task embeddings) se **entrena desde cero en segundos-minutos** con los pares del puzzle + augmentaciones (color/dihedral), y se infiere con voto mayoritario sobre augmentaciones (AAIVR). Sin pre-entrenamiento: 44% ARC-AGI-1 por $0.67.
   - (Existe una tercera acepción — **TTT-layers**, capas que sustituyen atención con estado-aprendido, [arXiv:2407.04620](https://arxiv.org/abs/2407.04620), jul-2024, Stanford — relevante como arquitectura de long-context, **no** es la que aplica a QA-FW; se cita para desambiguar el término.)
3. **Por qué funciona:** sample efficiency — extrae señal de MUY pocos ejemplos ajustando explícitamente el modelo al task, en vez de confiar en que el prompt lo condicione. Vakde: "sample efficiency es el problema más importante de la IA hoy"; sus ablations muestran que las representaciones (3D RoPE + per-task embedding) son el factor dominante (quitarlas: 44%→~24%).

### 1.2 Coste de cómputo (hechos del blog, mar-2026)

| Métrica | Valor (declarado) |
|---|---|
| Score ARC-AGI-1 (public eval) | **44%** (7% en ARC-AGI-2) |
| Coste cómputo por corrida completa | **$0.67** (renta GPU cloud) |
| Tiempo por corrida | **1.5 h en RTX 5090** |
| Modelo | Transformer pequeño, 8 capas (params no declarados en el blog; cobertura secundaria habla de ~75M `[ESTIMACIÓN]`) |
| Data | ARC-1 train + tareas no solapadas de ARC-2 (filtrado anti-leak cuidadoso; solo ARC-1+ConceptARC ≈ 40%, el extra ahorra cómputo a la mitad) |
| Comparables | Empata TRM/HRM (redes recursivas tiny); paper MIT alcanza 61.9% con 8B + ensemble |

**Lectura de coste:** el dato "$0.67" es por *run completo del benchmark* (100 puzzles públicos) → **~$0.007/puzzle** `[ESTIMACIÓN aritmética]`. La barrera real no es el dólar: es la **latencia por tarea** (minutos) y la **infraestructura de entrenamiento** (loop de augmentación + optimizer + checkpointing por task), que no existe en el stack actual de QA-FW.

## 2. Referencias (5, verificadas 02-sep-2026)

| # | Referencia | Qué aporta | Fecha/estado |
|---|---|---|---|
| 1 | [M. Vakde — *44% on ARC-AGI-1 in 67 cents*](https://mvakde.github.io/blog/44-on-arc-1/) + código [mdlARC](https://github.com/mvakde/mdlARC/) | El disparador: TTT from-scratch, $0.67, 1.5h/5090, open source. Serie de 3 blogs (prev: *new-pareto-frontier-arc-agi*, *why-all-ARC-solvers-fail-today*) | Blog ~mar-2026 (story HN del autor `evilmathkid`, 05-mar-2026) |
| 2 | [Akyürek et al. (MIT) — *The Surprising Effectiveness of Test-Time Training for Few-Shot Learning*](https://arxiv.org/abs/2411.07279) | Paper canónico TTT-sobre-LLM: 6× vs fine-tuned en ARC, 61.9% ensembled (~humano medio), +7.3 pp sobre few-shot 10-shot en BBH | arXiv nov-2024 (v2) |
| 3 | [Sun et al. (Stanford) — *Learning to (Learn at Test Time): RNNs with Expressive Hidden States*](https://arxiv.org/abs/2407.04620) | TTT-layers (TTT-Linear/TTT-MLP): la otra acepción del término; long-context, no per-task adaptation | arXiv jul-2024 |
| 4 | [Jolicoeur-Martineau (Samsung SAIT) — *Less is More: Recursive Reasoning with Tiny Networks* (TRM)](https://arxiv.org/abs/2510.04871) | El "pool de comparación" de Vakde: redes tiny recursivas que igualan LLMs en ARC-AGI; contexto de que 44% tiny-networks es estado del arte de eficiencia, no outlier | arXiv oct-2025 |
| 5 | Card interna [`72f97f1b`](https://github.com/SabaTech-dev/QA-FRAMEWORK/pull/88) — módulo accuracy QA-FW (benchmarks **BGH VI ZR 67/24**, rule-based evaluator determinista, 5 criterios + safety, PR #88) | El receptor del encaje: qué existe hoy y sus restricciones de diseño (determinismo por origen liability) | done 11-jun-2026 |

## 3. Encaje con el módulo accuracy de QA-FW

### 3.1 Lo que existe hoy (y por qué es como es)

El módulo (`src/domain/accuracy_testing/` + `src/infrastructure/accuracy_testing/`) es un **evaluador rule-based determinista** (5 criterios + safety, sin LLM) sobre 4 benchmarks derivados de la sentencia **BGH VI ZR 67/24** (responsabilidad de producto AI, carga de la prueba, diligencia del usuario, EU AI Act). El determinismo no es una limitación accidental: es el diseño correcto para un módulo cuyo caso de uso original es **defender posiciones ante responsabilidad civil** — reproducibilidad y auditabilidad ante todo.

### 3.2 Escenarios donde TTT > few-shot/eval (potencial post-beta)

| # | Escenario | Por qué TTT gana a few-shot/eval | Evidencia |
|---|---|---|---|
| E1 | **Adaptación de un LLM-judge por cliente/dominio** (glosario legal/médico del cliente, formatos de respuesta propios) con gold-set pequeño (30-200 ejemplos anotados) | Few-shot degrada con rubrics complejas; TTT internaliza la rubrica en pesos → más accuracy con los mismos ejemplos | MIT: +7.3 pp vs 10-shot en BBH; 6× vs FT baseline en ARC |
| E2 | **Rubrics nuevas con pocas anotaciones** (p. ej. extender benchmarks tipo BGH a nueva jurisdicción/sector) | El coste de anotación domina; TTT maximiza lo extraído por ejemplo | MIT paper, tesis sample-efficiency de Vakde |
| E3 | **Regresión de accuracy por versiones de modelo cliente** cuando el dominio es niche y el modelo nuevo pierde en él | TTT por dominio (batch, nocturno) re-ancla el judge sin re-annotar | Misma mecánica que E1, aplicada como suite |
| E4 | (Exploratorio) **Meta-evaluación de evaluadores**: entrenar tiny-models specialized en detectar clases de error sistemáticas | La clase mdlARC demuestra que tiny+TTT alcanza scores notables a coste despreciable | Vakde mar-2026 |

### 3.3 Escenarios donde TTT NO gana (y hoy son la mayoría)

- **Scoring en tiempo real**: TTT añade minutos por tarea — incompatible con evaluación interactiva.
- **El evaluador determinista actual**: sustituirlo por TTT destruye exactamente la propiedad (determinismo) que el origen BGH del módulo exige; además su dominio (reglas legales codificadas) no es sample-hungry.
- **Gold-sets <~30 ejemplos**: no hay señal suficiente para que el gradiente batan a un buen prompt + modelo fuerte.
- **Certificación/auditoría congelada**: modelo que cambia por-run complica la historia de auditoría (mitigable con seeds + snapshots de pesos, pero es coste extra no trivial).

**Conclusión de encaje:** TTT es una **capa de adaptación de judges LLM para batch/post-beta**, no una evolución del núcleo rule-based. El orden natural sería: (1) QA-FW añade LLM-judge asistido (post-beta, decisión independiente), (2) si hay clientes con gold-sets dominio-específicos, (3) ahí TTT entra como optimización de ese judge.

## 4. Estimación de coste en jokerserver (V100 32GB)

Base: la V100 32GB de jokerserver está **ya ocupada** por llama.cpp :8001 (inferencia productiva) — cualquier TTT es contendido y en ventana idle nocturna.

| Clase de TTT | Viabilidad V100 32GB | Tiempo `[ESTIMACIÓN]` | Coste marginal |
|---|---|---|---|
| **From-scratch tiny (clase mdlARC, ≤100M, 8 capas)** | ✅ Plena (VRAM trivial; ojo: sin flash-attn v2 nativo en sm70 → usar SDPA/memory-efficient, penalización incluida en la estimación) | ~5-6 h por corrida completa (3-4× la 5090 del blog) | ~€0.3-0.5 electricidad por corrida |
| **TTT por tarea sobre tiny pre-entrenado** | ✅ Plena | min/tarea | despreciable |
| **LoRA-TTT sobre 8B (clase paper MIT)** | ⚠️ Solo spike: pesos fp16 16GB + activations + adapters → apretado; sin bf16 nativo (fp16 V100 OK) | ~30-60+ min/tarea → solo batch de decenas de tareas en noche | electricidad |
| **Full-TTT 8B por tarea** | ❌ No viable (optimizer state no cabe ni latency tiene sentido) | — | — |

**Notas:** (1) sm70 carece de bf16 y de soporte flash-attn moderno — el stack de Vakde usa flash attention varlen + flex kernels; portarlo a V100 requiere fallbacks (o correr en la 5090 de otro host si existiera — hoy no). (2) Contención con llama.cpp :8001: cualquier corrida TTT debe pasar por el gating de ventanas que ya usa devops para jobs GPU. (3) Toda cifra de esta sección es `[ESTIMACIÓN]` — no hay medida real aún; el spike de §6 la convierte en dato.

## 5. Riesgos específicos

- **Varianza y reproducibilidad**: runs TTT difieren por seeds/augmentación — para un producto QA hay que congelar seeds + versionar pesos por-run (coste de ingeniería real).
- **Leakage en gold-sets**: adaptar el judge a los mismos ejemplos con los que se mide infla accuracy; el propio Vakde documenta lo delicado del filtrado anti-leak (ARC-2: filtrar 773 puzzles repetidos o score falso 100%). QA-FW necesitaría holdouts estrictos por cliente.
- **Complejidad operativa**: loop entrenamiento por task = nueva infra (optimizers, checkpoints, limpieza) que QA-FW no tiene hoy; choca con freeze MVP→BETA.
- **Falso atractivo del coste**: "$0.67" es de un run benchmark académico; el coste real por cliente incluye port de kernels (V100), holdouts, yoperación — el TCO del spike no es extrapolable linealmente a producto.

## 6. Veredicto GO/NO-GO post-beta con criterios

**Recomendación: NO-GO para el módulo accuracy actual · GO CONDICIONADO a spike experimental post-beta** (1 semana, doc+PoC en V100 idle, sin tocar el evaluador rule-based).

| # | Criterio | Umbral | Estado |
|---|---|---|---|
| G1 | **Demanda real**: ≥1 cliente/piloto con gold-set dominio-específico ≥30 ejemplos anotados y gap de accuracy del judge genérico >5 pp vs necesidad | Sí/No | ⏳ Post-beta (encuesta en onboarding) |
| G2 | **Uplift medido**: spike TTT (LoRA sobre judge open-weights ≤8B, o tiny from-scratch) ≥ +3 pp sobre few-shot baseline en holdout que NO participó del TTT | ≥3 pp | ⏳ Es el output del spike |
| G3 | **Infra**: ventana idle nocturna V100 ≥6 h sin degradar :8001 + seeds/weights versionados para reproducibilidad | Sí/No | ✅ Viable según §4 (por confirmar con devops) |
| G4 | **Auditabilidad**: diseño de audit trail por run (seed, data, pesos, holdout) aceptable para el contexto liability del módulo | Sí/No | ⏳ Diseño en spike |
| G5 | **Roadmap**: no consume recursos del MVP→BETA; solo ventanas nocturnas post-beta | Sí/No | ✅ Este doc es DOC-ONLY; spike sería igual |

- **GO post-beta** = G1 ∧ G2 ∧ G3 ∧ G4. Si G1 falla (nadie pide adaptación por dominio), el watch pasa a revision trimestral sin spike — la señal actual (benchmark académico viral, cero demanda enterprise documentada) no justifica más.
- **NO-GO permanente** si G4 no tiene solución barata: un módulo nacido de una sentencia de responsabilidad no puede permitirse evaluadores no-reproducibles; en ese mundo TTT queda como paper-watch, no como feature.

## 7. Limitaciones de este análisis

- Cifras de score/coste citadas **tal cual las declara cada fuente** (blog self-published, paper peer-reviewed en progreso); sin replicación independiente del 44%/$0.67 (Willison-style) en el momento de escribir.
- La estimación V100 (§4) es teórica: no hay medida real en jokerserver; sm70 kernel-fallbacks pueden empeorar el 3-4× asumido.
- No evalué alternativas intermedias (p. ej. ICL con retrieval de gold-set, o distilación del judge) que podrían capturar parte del beneficio de E1 sin loop de entrenamiento — candidatas naturales si G1 se cumple y G2 falla.
- "Módulo accuracy" de QA-FW aquí = el implementado en PR #88 (`72f97f1b`); si la roadmap post-beta redefine el módulo (LLM-judge nativo), este análisis debe releerse contra esa versión.

## Fuentes

1. Vakde, M. — *44% on ARC-AGI-1 in 67 cents* — ~mar-2026 — https://mvakde.github.io/blog/44-on-arc-1/ (código: https://github.com/mvakde/mdlARC/)
2. Akyürek et al. — *The Surprising Effectiveness of Test-Time Training for Few-Shot Learning* — arXiv:2411.07279 — nov-2024 — https://arxiv.org/abs/2411.07279
3. Sun et al. — *Learning to (Learn at Test Time): RNNs with Expressive Hidden States* — arXiv:2407.04620 — jul-2024 — https://arxiv.org/abs/2407.04620
4. Jolicoeur-Martineau, A. — *Less is More: Recursive Reasoning with Tiny Networks* — arXiv:2510.04871 — oct-2025 — https://arxiv.org/abs/2510.04871
5. QA-FRAMEWORK PR #88 + card `72f97f1b` (módulo accuracy BGH VI ZR 67/24) — done 11-jun-2026

---
*Card-id: `64fd626f-5c89-4978-a40d-98781c3e9f6d` · Hechos con fuente: §1-2, §3.1, datos de blog/paper; juicios: §3.2-3.3, §5-6 (esfuerzo/coste etiquetados `[ESTIMACIÓN]`). Veredicto final: Joker.*
