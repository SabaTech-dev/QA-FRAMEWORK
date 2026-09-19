# GO/NO-GO — Estrategia "agent-pickable" (llms.txt + MCP + quickstart)

**Fecha:** 2026-09-14 · **Autor:** research (card `d9888701`) · **Estado: PROPUESTA — decisión gated 1-a-1 (producto)**
**Ventana:** pre-beta. Ser elegible por agentes cuesta poco ahora; refactorizarlo post-lanzamiento cuesta caro.

## Señal de mercado (cités con fecha)

- **llms.txt v2** ([llmstxt.org](https://llmstxt.org), consultado 2026-09-14): propuesta 2024, v2 tras 2 años de adopción — *miles de sitios* publican llms.txt, Mintlify lo genera automáticamente, **Chrome Lighthouse lo audita** (agentic browsing checks) y OpenAI/Anthropic/Gemini publican el suyo.
- **Vercel**: >30% de deployments iniciados por coding agents (+1000% en 6 meses) → **>50% a sep-2026** ([vercel.com/blog/agentic-infrastructure](https://vercel.com/blog/agentic-infrastructure); cobertura Vercel Ship 2026).
- **MCP**: adoptado por OpenAI (mar-2025) y ChatGPT apps (sep-2025) ([Wikipedia/MCP](https://en.wikipedia.org/wiki/Model_Context_Protocol)); registry oficial desde sep-2025; **~9.650 server records** (pull 24-may-2026, [MCP Adoption Statistics 2026](https://www.digitalapplied.com/blog/mcp-adoption-statistics-2026-model-context-protocol)).
- **Armature** (16.893 sesiones reales de instalación, 75 repos, 3 agentes): los agentes **eligen herramientas de forma determinista por facilidad real de instalación** (vía digest interno 14-sep, LTG Card 4).

## Coste/impacto por ítem

| Ítem | Coste | Impacto | Veredicto |
|---|---|---|---|
| **llms.txt** (raíz + docs/) | **XS** — 1 archivo estático + 1h de mantenimiento al añadir docs | **M** — discoverability base, gratis; Lighthouse lo checks | **GO** (fase 1, pre-beta) |
| **Docs parseables** (higiene) | **S** — nav de mkdocs cubre 5 páginas vs 40+ archivos sueltos en `docs/`; consolidar + garantizar .md servidos en el site | **M** — sin esto, llms.txt apunta a ruido | **GO** (fase 1) |
| **Quickstart agent-friendly** | **S-M** — el actual requiere 35 min de infra manual (Railway/Stripe); reescribir a ≤5 min para evaluar la API (`docker compose up` + API key + 3 curl) | **M-A** — Armature: la elección se decide por install real | **GO** (fase 2, con beta) |
| **MCP server** | **M** — envolver el `openapi.yaml` existente (FastMCP), tools read-only v1 (consultas de resultados/coverage), auth igual que la API | **M** — diferenciador pre-beta; el API surface ya está especificado | **GO** (fase 2, read-only v1) |

## Veredicto: GO por fases (condicionado)

- **Fase 1 (ahora, pre-beta)**: llms.txt + higiene de docs parseables. Coste total XS-S, riesgo ~0, todo docs-only.
- **Fase 2 (post-beta-privada)**: quickstart agent-friendly + MCP server read-only v1. Requiere estabilizar API surface primero.
- **Issues creados (sin implementar, gated su arranque):** #1 llms.txt · #2 quickstart ≤5min · #3 MCP server read-only — enlazados a este doc.
- **NO-GO triggers / re-eval:** si post-beta la adquisición es 100% humana directa sin señal de tráfico agente en 90 días → congelar fase 2 y re-evaluar; si el MCP spec ROMPE compat (ya ocurrió v1→v1.x) → re-evaluar coste.

## Fuentes

llmstxt.org (v2, 2026) · vercel.com/blog/agentic-infrastructure (sep-2026) · en.wikipedia.org/wiki/Model_Context_Protocol (2026) · digitalapplied.com MCP stats (pull 24-may-2026) · digest-diario-ia interno 2026-09-14 (Armature, LTG Card 4). Auditoría del repo: sin llms.txt, sin MCP propio, QUICK_START_GUIDE.md 35-min manual, mkdocs nav 5 vs 40+ docs sueltos (2026-09-14).
