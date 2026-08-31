# Spec — Módulo "Agent Prompt-Injection Testing" (QA-FRAMEWORK)

> **Tipo:** Spike spec — research + spec, NO implementación
> **Card:** `26e54c21-5315-4d89-a1db-ea8331836030` · [P2] QA-FW roadmap · origen LTG 2026-09-01 Card 8
> **Autor:** research (SabaTech) · **Fecha:** 2026-09-01
> **Estado:** Pendiente Alfred Review (GO/NO-GO final lo decide Joker)
> **Veredicto recomendado:** **GO CONDICIONADO** — Fase 0 (gate técnico, 5 días) ya; MVP del módulo post-beta (Q4-2026)
> **Nota de ubicación:** el dispatch indicaba `docs/plans/`; se usa la convención real del repo `docs/internal/plans/` con prefijo de fecha, igual que `2026-03-25-e2e-playwright-testing-plan.md`.

---

## Resumen ejecutivo

1. La ventana comercial es real y está fechada esta semana: Anthropic puso Auto Mode (sin aprobación humana) **por defecto** en Claude Code a mediados de agosto ([TechCrunch, 09-ago-2026](https://techcrunch.com/2026/08/09/anthropic-is-turning-claude-codes-auto-mode-on-by-default/)), y el 30-31-ago un investigador publicó cómo romperla con inyección indirecta logrando **ejecución de código con ASR 60-80%** ([embracethered.com, 31-ago-2026, HN 334 pts](https://embracethered.com/blog/posts/2026/breaking-claude-code-opus-5-and-automode/)).
2. El 27-ago-2026, **100+ firms** (OpenAI, Anthropic, Google, Microsoft, CrowdStrike, Okta, Fortinet + financieras e infra de internet) firmaron una carta pidiendo defensa conjunta contra ciberataques con IA, citando agentes que "salieron del sandbox" ([Yahoo Tech, 27-ago-2026](https://tech.yahoo.com/cybersecurity/articles/openai-anthropic-google-100-other-174324792.html)).
3. El hueco competitivo existe: el benchmark académico de referencia (AgentDojo) no es producto; garak es escáner estático de chat; promptfoo es CI-first pero eval-first; y **PyRIT (Microsoft) fue archivado el 27-mar-2026** — el OSS de red-teaming automatizado quedó huérfano.
4. **No entra en el MVP actual** (foco beta). Recomendación: GO a una Fase 0 de 5 días que valide el harness con el vector de embracethered, y MVP del módulo como primer módulo enterprise post-beta. Esfuerzo MVP estimado: **8-10 semanas-persona** `[ESTIMACIÓN]`.

---

## 1. Contexto y ventana comercial (evidencia verificada)

| Señal | Fecha | Evidencia |
|---|---|---|
| Auto Mode por defecto en Claude Code | 09-ago-2026 | [TechCrunch](https://techcrunch.com/2026/08/09/anthropic-is-turning-claude-codes-auto-mode-on-by-default/) — "Anthropic is turning Claude Code's auto mode on by default" |
| "Breaking Claude Code Opus 5 Auto Mode" (embracethered, Johann Rehberger) | 30/31-ago-2026 | [Post](https://embracethered.com/blog/posts/2026/breaking-claude-code-opus-5-and-automode/) — HN 334 pts / ~100 comentarios el 31-ago. RCE vía resumen de web, ASR 60-80% (muestra pequeña) |
| Eval comisionado por Anthropic (Trajectory Labs): 0.00% ASR en Opus 5 Auto Mode | ago-2026 | Citado en el post de embracethered ([chart](https://x.com/bcherny/status/2085860677990883454)); 72 escenarios de inyección indirecta ×10 — sin benchmark publicado. Contraste 0.00% vs 60-80% = los agentes de código necesitan testing adversarial *sistemático y regresivo*, no un eval puntual |
| Carta abierta 100+ firms por defensa ciber contra IA | 27-ago-2026 | [Yahoo Tech](https://tech.yahoo.com/cybersecurity/articles/openai-anthropic-google-100-other-174324792.html), [AI Magazine, 30-ago](https://aimagazine.com/news/openai-rallies-100-tech-firms-for-urgent-ai-cyber-defence). Contexto: incidente Hugging Face (agente de OpenAI salió del sandbox, [TechCrunch 29-jul-2026](https://techcrunch.com/2026/07/29/the-hugging-face-ai-break-in-as-told-through-an-increasingly-committed-bear-metaphor/)) y roundup de "AI gone rogue" ([TechCrunch 27-ago-2026](https://techcrunch.com/2026/08/27/heres-all-the-times-ai-has-gone-rogue-and-hacked-other-companies/)) |
| Registro: Claude Code engañado vía resumen de website | 28-ago-2026 | [The Register](https://www.theregister.com/research/2026/08/28/researcher-shows-how-claude-code-can-be-tricked-simply-by-asking-it-to-summarize-a-website/5293372/) |

**Lectura de negocio:** el mercado acaba de internalizar (HN 334 pts + carta) que el modo autónomo de agentes es superficie de ataque, y el propio eval de Anthropic quedó rebatido en público. QA-FRAMEWORK puede posicionar "prueba que tu agente resiste inyección" como módulo QA reggable en CI — coherente con el roadmap ASSESS del [tech-radar 2026-08-31](../../../../.openclaw/workspace/reports/cron/tech-radar/2026-08-31.md).

## 2. Threat model que enseña el vector de embracethered (para diseño del módulo)

La cadena publicada (31-ago-2026) que hay que ser capaz de **detectar y reproducir**:

1. **Nudge de tool-transition sin instrucción explícita**: la web responde `415 Unsupported Media Type` a WebFetch → el agente *decide solo* pasar a Bash+curl. La inyección moderna no ordena; hace que el camino malicioso sea el que "conviene" para cumplir el objetivo.
2. **Payload smuggleado en formato legítimo**: ZIP con registros Base85/zlib+JSON con metadatos plausibles (checksums, fechas).
3. **El modelo rechaza el binario** (`decoder-darwin`) pero **escribe su propio decodificador Python** — y lo ejecuta **dentro del directorio controlado por el atacante**.
4. **Sombras de stdlib**: `struct.py` malicioso sombra al stdlib; al importar `base64` se dispara el payload → RCE bajo Auto Mode (clasificador, no humano, aprueba).

Implicaciones para QA: un módulo de testing debe cubrir (a) transiciones de tools inducidas por entorno, (b) assets hostiles en formato plausible, (c) escritura+ejecución de código por el propio agente en cwd no confiable, (d) import shadowing / path poisoning, (e) exfiltración (links/imágenes markdown, callbacks DNS) — y medir **ASR (Attack Success Rate) por familia de vector y por versión del agente**, con verificación de propiedades de seguridad objetivas (archivos creados, egress, tool-call trace), no solo juicios de texto.

## 3. Scope del módulo (MVP)

**Nombre interno propuesto:** `agent-injection` (adapter family `adapters/agent/` + engine `core/injection/`).

### En scope MVP
- **Harness de agentes (2 adapters):**
  - `AgentHttpClientAdapter`: agente expuesto como HTTP/webhook/chat completions (prompt in → acciones/respuesta out).
  - `AgentCliAdapter`: agente CLI (patrón Claude Code/Aider): subprocess aislado, captura de tool-calls y efectos en filesystem.
- **Motor de escenarios** (estilo AgentDojo): cada caso = *task legítima + asset envenenado + propiedad de seguridad + criterio de utilidad*. Devuelve binario por caso: `utility_ok` × `security_violated`.
- **Corpus v1 (100-150 vectores)** mapeados a [OWASP LLM01: Prompt Injection](https://genai.owasp.org/llm-top-10/), sembrados desde AgentDojo (MIT) y probes `promptinjection` de garak, más familias propias del §2: tool-transition nudge, payload en archivo, import shadowing, exfiltración pasiva, multi-turn.
- **Evaluador en dos capas:** (1) detectores objetivos (invariantes de filesystem, egress deny-by-default, análisis de tool-call trace); (2) LLM-as-judge para goal-hijack con **cola HITL** — reutiliza el trabajo de gold-set/HITL ya existente en QA-FW (reporte 2026-08-28).
- **Runner sandbox:** contenedor por run, sin red por defecto (allowlist), snapshot/restore del FS, timeouts. Lección directa del incidente Hugging Face.
- **Reporting + CI gate:** ASR por familia/vector/versión de agente, impacto en utilidad, diff de ASR entre builds → gate de regresión en GitHub Actions (coherente con el stack CI existente).

### Fuera de scope MVP (→ post-beta)
Ataques adaptativos (red-team agent loops multi-turn), testing de servidores MCP, benchmarking de defensas/detectores de terceros, informes compliance (EU AI Act/SOC2 evidence), modo monitorización continua, auto-expansión de corpus.

## 4. Competencia y prior art (5 referencias verificadas)

| # | Referencia | Qué es | Fecha/estado | Hueco que deja |
|---|---|---|---|---|
| 1 | [AgentDojo](https://arxiv.org/abs/2406.13352) (ETH Zurich, código [ethz-spylab/agentdojo](https://github.com/ethz-spylab/agentdojo)) | Entorno dinámico de eval: 97 tareas realistas, 629 test cases de inyección; extensible | arXiv jun-2024 (v3), NeurIPS 2024 D&B | Benchmark académico, no producto CI; hay que construirle harness/reporting alrededor |
| 2 | [garak](https://github.com/NVIDIA/garak) (NVIDIA) | "LLM vulnerability scanner" — probes de hallucination, data leakage, prompt injection, jailbreaks ("nmap para LLMs") | OSS activo desde 2023 (verificado 01-sep-2026) | Probes estáticos sobre chat; no modela flujos agent con tools/filesystem ni gates de regresión |
| 3 | [PyRIT](https://github.com/Azure/PyRIT) (Microsoft) | Framework Python de red-teaming automatizado para gen-AI | **Archivado 27-mar-2026, read-only** (verificado 01-sep-2026) | El OSS de referencia de automatización adversarial quedó sin mantenimiento — hueco directo |
| 4 | [promptfoo](https://github.com/promptfoo/promptfoo) | Eval + red teaming CI-first ("test your prompts, agents, and RAGs… CI/CD integration") | OSS + SaaS, activo (verificado 01-sep-2026) | Competidor más cercano: eval-first y centrado en chat/LLM API; el testing de agentes con ejecución de tools + propiedades de seguridad en sandbox es secundario. Diferenciación posible, no despreciable |
| 5 | [OWASP GenAI Top 10](https://genai.owasp.org/llm-top-10/) — **LLM01: Prompt Injection** | Estándar de taxonomía/mitigaciones para apps LLM | 2025 (lista vigente; página verificada 01-sep-2026) | No es competencia: es el mapa de compliance sobre el que anclar reporting del módulo |

*Contexto comercial SaaS (menos verificable en fuentes primarias desde aquí): Lakera, Mindgard, Haize Labs operan red-teaming enterprise. `[ESTIMACIÓN]` precio/fit dejaba hueco SMB; no conditiono el veredicto a esto.*

**Posicionamiento QA-FW:** "regresión de seguridad agent-first en CI": corpus AgentDojo-grade + propiedades objetivas + HITL + gate ASR por build. Ninguna referencia cubre ese combo hoy.

## 5. Encaje MVP vs post-beta

| Aspecto | Decisión |
|---|---|
| ¿En MVP actual (→ beta)? | **No.** El foco es cerrar beta GA (deuda tests dashboard P2 pendiente). Añadir un módulo enterprise pre-beta dilute y retrasa |
| ¿En post-beta? | **Sí, como primer módulo enterprise** (Q4-2026): es el tipo de feature que abre conversación de upsell con clientes que despliegan agentes internos |
| Fase 0 (ya, pre/post-beta según Alfred) | Spike técnico de **5 días** `[ESTIMACIÓN]`: harness CLI mínimo + 20 vectores seed de AgentDojo + judge + reproducir *detección* del vector embracethered. Gate de GO del MVP. Coste bajo, genera material de marketing (blog post "probamos el exploit de embracethered contra N agentes") |
| Sinergias internas | Cola HITL existente (gold-set 2026-08-28), skill `sql-injection-testing` como patrón de módulo security, pipeline CI existente, Integration Hub para reportes a Jira |

## 6. Estimación de esfuerzo `[ESTIMACIÓN]` (Python 3.11, patrones de adapters existentes)

| Fase | Contenido | Esfuerzo |
|---|---|---|
| **Fase 0 — spike gate** | Harness CLI + 20 vectores + judge + detección del vector embracethered; sandbox Docker básico | **5 días** (1 ing) |
| **MVP — adapters** | `AgentHttpClientAdapter` + `AgentCliAdapter` con captura de tool-calls | 2-3 semanas |
| **MVP — corpus** | 100-150 vectores curados y mapeados a OWASP LLM01 (seed AgentDojo/garak) | 1-2 semanas |
| **MVP — motor+evaluador** | Escenarios (utility×security), detectores objetivos, LLM-judge + cola HITL | 2-3 semanas |
| **MVP — reporting/CI** | ASR por familia/versión, gate de regresión GitHub Actions | 1 semana |
| **MVP — sandbox** | Runner aislado (no-network default, allowlist egress, snapshots) | 1-2 semanas |
| **Total MVP** | | **8-10 semanas-persona** (~5-6 semanas con 2 ing en corpus/evaluador en paralelo) |

Riesgos: no-determinismo del judge (mitigar: detectores objetivos primero, HITL para disputas), coste de tokens en runs, y **seguridad del propio harness** (el módulo ejecuta payloads hostiles — sandbox obligatorio, nunca en jokerserver prod).

## 7. Veredicto GO/NO-GO con criterios

**Recomendación: GO CONDICIONADO** — GO a Fase 0 ya; GO al MVP solo si Fase 0 pasa y no retrasa la beta.

| # | Criterio | Umbral | Estado |
|---|---|---|---|
| C1 | Demanda de mercado | ≥2 señales independientes verificables con fecha | ✅ **Cumplido** (carta 27-ago + embracethered 31-ago + TechCrunch 09-ago) |
| C2 | Viabilidad técnica | Fase 0: detectar el vector tipo-embracethered con <15% varianza del judge | ⏳ Gate Fase 0 |
| C3 | Coste/oportunidad | MVP ≤10 semanas-persona **y** retraso de beta GA ≤2 semanas | ✅ Estimación cumple; decidir vs deuda tests dashboard |
| C4 | Seguridad propia | Sandbox sin ampliar superficie de ataque de jokerserver (egress deny-by-default, sin prod) | ⏳ Diseño en Fase 0 |
| C5 | Diferenciación sostenible | Combo no cubierto por garak/promptfoo/AgentDojo (§4) | ✅ Hueco confirmado; PyRIT archivado lo amplía |

- **NO-GO al MVP si:** C2 o C4 fallan en Fase 0, o C3 no se sostiene con la beta en curso → el módulo pasa a roadmap-watch trimestral (revisar señal de nuevo en dic-2026).
- **NO-GO total** (ni Fase 0) solo si la ventana resulta ser hype efímero: hoy la evidencia en contra es que se trata de investigador independiente + carta de intereses comerciales creados; la evidencia a favor es que Anthropic ya vende Auto Mode por defecto (superficie persistente, no un parche puntual).

## 8. Limitaciones de este análisis

- ASR 60-80% del post de embracethered es **muestra pequeña** (así lo declara el propio autor); no extrapolable sin replicación (para eso serviría Fase 0).
- No se auditaron precios ni fit actual de SaaS enterprise (Lakera/Mindgard/Haize) — marcado `[ESTIMACIÓN]`.
- Búsqueda web degradada durante la investigación (SearXNG con CAPTCHAs/429s — ya hay card P2 para ello); se usó HN Algolia API + fetch directo de fuentes primarias. La carta no se pudo leer en texto íntegro primario (AI Magazine bloquea bots); se citan 2 portadas secundarias independientes.
- Memory index degradado hoy (mismatch de embedding model) — sin impacto en este spec, pero nota operativa para Alfred.

## Fuentes (primarias, con fecha)

1. Embracethered — *Breaking Claude Code Opus 5 Auto Mode* — 30/31-ago-2026 — https://embracethered.com/blog/posts/2026/breaking-claude-code-opus-5-and-automode/
2. Yahoo Tech — *OpenAI, Anthropic, Google, and 100 other companies call for action…* — 27-ago-2026 — https://tech.yahoo.com/cybersecurity/articles/openai-anthropic-google-100-other-174324792.html
3. AI Magazine — *OpenAI Spearheads 100 Strong Letter on Cyber Defence* — 30-ago-2026 — https://aimagazine.com/news/openai-rallies-100-tech-firms-for-urgent-ai-cyber-defence
4. TechCrunch — *Anthropic is turning Claude Code's auto mode on by default* — 09-ago-2026 — https://techcrunch.com/2026/08/09/anthropic-is-turning-claude-codes-auto-mode-on-by-default/
5. AgentDojo — arXiv:2406.13352 — jun-2024 — https://arxiv.org/abs/2406.13352
6. garak (NVIDIA) — https://github.com/NVIDIA/garak · PyRIT (Microsoft, archivado 27-mar-2026) — https://github.com/Azure/PyRIT · promptfoo — https://github.com/promptfoo/promptfoo (verificados 01-sep-2026)
7. OWASP GenAI Security Project — Top 10 LLM — https://genai.owasp.org/llm-top-10/

---
*Hechos vs opinión: las secciones 1-2 y 4 son hechos con fuente; las secciones 3, 5-7 contienen juicio de investigación etiquetado cuando corresponde (`[ESTIMACIÓN]`). Veredicto final: Joker.*
