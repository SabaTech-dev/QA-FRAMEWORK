# PII Masking opt-in con @desert-ant-labs/redact

- **Objetivo**: hook único de PII masking opt-in (DEFAULT OFF) en el pipeline de ingest de QA-FW: scrub de logs/fixtures/transcripts ANTES de LLM externo o storage. Placeholder-map reversible para round-trips LLM + modo anonimización + regex determinista en paralelo para campos estructurados.
- **Rama**: `feat/pii-masking-redact` (worktree `/home/joker/repos/qa-fw-wt-pii`, base main f0418bf).
- **Delivery**: PR a main, NO merge (branch ruleset; Alfred mergea --admin post-review).
- **Test runner**: `python -m pytest tests/security/ -v --cov=src/security/pii_masking --cov-report=term-missing`

## Specs

- **S1**: Hook único en el pipeline de ingest + flag opt-in configurable, **DEFAULT OFF**. "flag opt-in (DEFAULT OFF) configurable". Verificación: test que prueba que sin configuración el hook es no-op y el flag resuelve a False.
- **S2**: Log de placeholders + placeholder-map reversible para round-trips LLM ("Log de placeholders + placeholder-map reversible para round-trips LLM"), con "modo anonimización que borra el mapa" (el texto redactado NO es reversible; el mapa no se emite ni se persiste).
- **S3**: "Regex determinista en paralelo para campos estructurados aislados (complementa el redact SDK para texto libre)". Reutiliza los 9 detectores con validación semántica (Luhn, mod-97, SSA) del commit previo d3c05a6.
- **S4**: SDK `@desert-ant-labs/redact` **v3.1.0 exacta** para texto libre, vía bridge Node (subproceso JSON-lines) — el repo es Python. p50 163ms CPU aceptado.
- **S5**: Tests TDD: hook, flag default-OFF, map handling, regex paralelo. **Cobertura >80% del módulo nuevo** (`src/security/pii_masking/`). Suite completa verde.
- **S6**: README del módulo documentando: MODO HIGIENE (**NO es DLP formal** — recall publicado 88.8%, ~11% fuga residual en texto libre) y límite de licencia (>10k dispositivos/mes) + plan B GLiNER-PII (OSS).

Supuestos (marcados como asunciones): (a) el repo no tiene un módulo `ingest` explícito; el "pipeline de ingest" se materializa en los sinks actuales — logging (`src/infrastructure/logger`) y generación LLM (`src/infrastructure/test_generation/llm_adapter.py`); el hook único se expone como `PiiMaskingHook` y se integra en esos sinks. (b) La fuente aprobada (spike 63574e2f) no está en Engram; se toman los parámetros verbatim de la card.

## Tasks

| ID | S# | Route | Estado | Commit |
|----|----|-------|--------|--------|
| T1 | S1 | inline | done | fcf94a0 |
| T2 | S3 | inline | done | e88f33f |
| T3 | S2 | inline | done | 0fb93b0 |
| T4 | S4, S1 | inline | done | c9a3da5, 494f0e4 |
| T5 | S1, S5 | inline | done | (ver Log L5) |
| T6 | S6 | inline | done | — |

Route declarada: todo inline (un solo módulo nuevo, sin unidades paralelas independientes; ningún trigger de writer aplica).

## Log

- L1 (2026-10-23): Card 6ebfc99b — "PICK DEL DUEÑO (poll 23-oct): GO — implementar YA (doble gate levantado por Joker: post-beta waived + GO explícito). Fuente aprobada: spike 63574e2f (Alfred 10-sep, GO condicionado). OBJETIVO: módulo PII masking opt-in en el pipeline de ingest de QA-FW (scrub de logs/fixtures/transcripts ANTES de LLM externo o storage), usando @desert-ant-labs/redact v3.1.0 (SDK Node 195MB, p50 163ms CPU). TAREA (rama feat/pii-masking-redact, TDD): 1. Hook único en el pipeline de ingest + flag opt-in (DEFAULT OFF) configurable. 2. Log de placeholders + placeholder-map reversible para round-trips LLM (con modo anonimización que borra el mapa). 3. Regex determinista en paralelo para campos estructurados aislados (complementa el redact SDK para texto libre). 4. Tests TDD: hook, flag default-OFF, map handling, regex paralelo. Cobertura >80% del módulo nuevo. 5. Docs: README del módulo documentando MODO HIGIENE (NO es DLP formal — recall publicado 88.8%, ~11% fuga residual en texto libre) y límites de licencia (>10k dispositivos/mes) + plan B GLiNER-PII (OSS). 6. PR a main. NO mergear (branch ruleset bloquea; Alfred mergea con --admin post-review). Verificación: suite completa verde + cobertura módulo >80% + flag default OFF verificado en test. PROTOCOLO ANTI-SELF-CERTIFY: Termina en review: handoff 5 campos. NO ejecutar workboard_complete. NO merge/close PRs. NO firmar proofs."
- L1b (2026-10-23): Verificado en npm registry que `@desert-ant-labs/redact@3.1.0` existe (latest 4.1.0; se pinea 3.1.0 según card). API: `Redact.load()` (native subpath `/native` en Node), `redact.redaction(text)` → `{redactedText, items}`, `r.restore(reply)`.
- L1c (2026-10-23): Encontrados detectores regex previos (9 categorías con Luhn/mod-97/SSA) en commit d3c05a6 (rama feat/pii-masking-verifier, no mergeada a main) — se reutilizan como capa determinista (S3).
- L2 (2026-10-23): Corrección de alcance documental: el eval (memoria #4784) corrige el gate — licencia DAL 1.0 gratuita hasta 100k MAU (la card decía ">10k dispositivos/mes", umbral conservador ×10). El README (S6) documenta ambos.
- L3 (2026-10-23): Fallo preexistente en base: hook bandit de pre-commit roto en main (args + filenames). Aplicado el mismo fix ya aceptado en chore/backend-lockfile (1b47ca9): commit aee82b6.
- L4 (2026-10-23): Aprendizaje TDD: `importlib.reload` en tests de config contamina la identidad del enum entre tests (fallo solo en suite paralela). Eliminado el reload; `from_env()` ya lee el entorno por llamada.
- L5 (2026-10-23): Verificación T5: cobertura módulo 92% (>80% S5) ✓; flag default OFF verificado en test ✓; suite completa: 44 failed/87 errors IDÉNTICOS a base f0418bf (diff de nombres vacío), +36 tests nuevos passing. Fallos de base: tests/security/test_owasp_top10_2025.py (7) y otros preexistentes — fuera de alcance, reportados al reviewer.
- L6 (2026-10-23): Diseño final del routing del hook: regex determinista SIEMPRE primero (estructura y texto libre, complementa al SDK), bridge SDK solo para texto libre; todas las detecciones (regex y SDK) se registran en el PlaceholderMap en modo MASK.
- L7 (2026-10-23): T6 done — README del módulo con MODO HIGIENE (recall 88.8%, ~11% residual), licencia DAL 1.0 (100k MAU, umbral card ×10) y plan B GLiNER-PII. Pendiente: PR a main (sin merge) + handoff anti-self-certify.
