# 📋 Data Provenance Audit — SabaTech

**Auditor:** 🔒 Security Agent  
**Fecha:** 2026-06-29  
**Card:** 1f00aca4-72f0-4c97-ad02-24dcf76e2897  
**Scope:** 19 repositorios en `~/repos/`  
**Metodología:** OWASP Top 10:2025 + GDPR Art. 9 + AI Act readiness

---

## 1. Executive Summary

| Severidad | Count | Descripción |
|-----------|-------|-------------|
| 🔴 CRITICAL | 2 | DB con datos operativos committed a git; base model license sin documentar |
| 🟠 HIGH | 5 | Datasets sintéticos con PII markers committed; 7 repos sin LICENSE; training data sin provenance doc; voice recordings con PII informal |
| 🟡 MEDIUM | 4 | Datos de entrenamiento contienen internals operacionales; modelos externos sin pin; eventos de memoria committed |
| 🟢 LOW | 3 | Ficheros de configuración con metadata; datos demo sintéticos |

**Veredicto:** **MEDIO-ALTO riesgo legal**. Los datos son mayoritariamente sintéticos o auto-generados, pero la falta de documentación de procedencia y los archivos committed a git crean exposición legal innecesaria.

---

## 2. Repositorios Auditados

### 2.1 Repos con datos/training datasets

#### 🔴 saba-llm-auto-train — CRITICAL

| Campo | Valor |
|-------|-------|
| **License** | ❌ **NO LICENSE FILE** (README dice "MIT" pero no existe archivo) |
| **Datasets** | `data/train.jsonl` (787K), `data/val.jsonl` (81K), `data/raw/alpaca.jsonl` (341K), `data/raw/dataset-v3-raw.jsonl` (364K), `data/training/dataset-v3-combined.jsonl` (431K) |
| **Base Model** | `unsloth/gemma-4-e2b-it-unsloth-bnb-4bit` (Google Gemma 4) |
| **Origen datos** | Memoria del agente OpenClaw: daily notes (`memory/YYYY-MM-DD.md`), Engram recall, Hindsight retain, wiki concepts, workspace docs |
| **Formato** | Alpaca / Gemma instruct template |
| **Tamaño** | 542 samples (487 train + 55 val) |
| **Git tracking** | ✅ `.gitignore` excluye `data/*.jsonl`, `data/raw/`, `models/*` |
| **Committed** | Solo `benchmark/questions.jsonl` (30 preguntas sintéticas) |

**Findings:**

- **C-1 (CVSS 7.5 HIGH):** No existe archivo LICENSE. README declara "MIT — PoC interna" pero sin archivo LICENSE/MIT, la declaración no tiene validez legal. Default copyright aplica.
- **C-2 (CVSS 7.2 HIGH):** Base model `unsloth/gemma-4-e2b-it-unsloth-bnb-4bit` usa Google Gemma con [Gemma Terms of Use](https://ai.google.dev/gemma/terms). Los términos de Gemma prohíben ciertos usos (ilegal, dañino, competitivo). **No hay documentación de compliance con Gemma Terms** en el repo. Un fine-tuning comercial de Gemma requiere revisión de términos.
- **H-1 (CVSS 6.5 MEDIUM):** Training data extrae contenido de daily notes que incluyen: infraestructura del servidor, configuraciones de agentes, nombres de proyectos, métricas operacionales. Si el modelo fine-tuned se despliega o comparte, estos internals podrían filtrarse vía regeneración.
- **M-1 (CVSS 5.3 LOW):** `dataset-v3-meta.json` documenta fuentes parcialmente (wiki_concepts: 188, workspace_docs: 46, etc.) pero no incluye licencia de los datos fuente (la memoria del agente es propietaria, pero si incluye contenido de terceros — CVEs, referencias externas — la cadena de licencias se rompe).

**Mitigación:**
1. Crear `LICENSE` file (MIT) para formalizar la declaración del README
2. Añadir `GEMMA_TERMS_COMPLIANCE.md` documentando que el uso cumple Gemma Terms of Use
3. Añadir `DATA_PROVENANCE.md` con: origen de cada subset, licencia de datos fuente, proceso de curación
4. Implementar redacting de internals antes de training (filtrar IPs, hostnames, paths)

---

#### 🔴 AsistenteConversacional — HIGH

| Campo | Valor |
|-------|-------|
| **License** | ✅ PolyForm Noncommercial License 1.0.0 |
| **Datasets** | `data/sft_toy.json` (SFT training), `data/sft_toy_clean.json` (versión limpia), `data/pref_toy.json` (preferencias), `data/dataset_acoustic_toy/metadata.csv` (metadatos audio), `data/knowledge_base.json` (conocimiento empresa ficticia) |
| **Base Model** | `unsloth/gemma-4-12b-it-GGUF` (descargado vía `download_model.py`) |
| **Origen datos** | **Sintéticos** — diálogos de venta telefónica de energía (empresa ficticia "GigaEnergia") |
| **Git tracking** | ⚠️ **5 archivos de datos committed a git** (sft_toy.json, sft_toy_clean.json, pref_toy.json, metadata.csv, knowledge_base.json) |
| **Modelo** | `.gitignore` excluye `models/*`, `*.gguf` ✅ |

**Findings:**

- **H-2 (CVSS 6.8 HIGH):** `sft_toy.json` committed a git contiene PII markers: `DNI 12345678A`, `teléfono 600123456`, `CUPS ES0021000000001234AB`. Aunque son datos sintéticos/ficticios, están committed en git permanentemente. Cualquiera con acceso al repo puede verlos. `sft_toy_clean.json` tiene los mismos datos con placeholders `[DNI_NIE]`, `[TELEFONO]`, `[CUPS]` — pero **ambas versiones son idénticas en contenido**, la "clean" no limpia nada.
- **H-3 (CVSS 5.5 HIGH):** `metadata.csv` committed referencia archivos de audio (`audio\sample_00000_andaluz.wav`) que **no existen en el repo** (correctamente excluidos por `.gitignore`). Pero el CSV contiene transcripciones completas con PII markers.
- **M-2 (CVSS 4.3 MEDIUM):** Los datos son sintéticos pero **no están etiquetados como tales**. No hay ningún documento que declare "estos datos son ficticios, no representan personas reales". Esto es un gap de compliance si el modelo se usa en producción.
- **M-3 (CVSS 4.0 MEDIUM):** `download_model.py` descarga `gemma-4-12b-it-GGUF` desde HuggingFace sin pin de revisión. Cada descarga puede dar un archivo diferente si el upstream cambia.

**Mitigación:**
1. Mover archivos de datos fuera de git tracking (añadir a `.gitignore`, usar `git rm --cached`)
2. Crear `DATA_PROVENANCE.md` declarando: datos 100% sintéticos, empresa ficticia, no PII real
3. Eliminar `sft_toy.json` del historial git (BFG Repo-Cleaner o `git filter-branch`)
4. Pinear revisión de modelo en `download_model.py` (`revision="abc123"`)
5. Añadir disclaimer en README: "All data is synthetic. Any resemblance to real persons is coincidental."

---

#### 🟠 Alfred_Reports_Docs — HIGH

| Campo | Valor |
|-------|-------|
| **License** | ❌ **NO LICENSE FILE** |
| **Datos** | `memory/recordings/*.json` (6 Whisper transcriptions), `memory/.dreams/events.jsonl` (988K), `memory/cron-sla-history.jsonl`, `memory/disk-usage-history.jsonl`, `archive/mission-control-custom-2026-03/backend/data/mission-control.db` |
| **Origen** | Transcripciones de voz del usuario (Whisper), eventos de memoria OpenClaw, histórico de métricas |
| **Git tracking** | ⚠️ **3 archivos committed**: `events.jsonl`, `cron-sla-history.jsonl`, `disk-usage-history.jsonl` + `archive/mission-control.db` |

**Findings:**

- **H-4 (CVSS 7.0 HIGH):** `archive/mission-control-custom-2026-03/backend/data/mission-control.db` está **committed a git**. Es una SQLite DB con tablas: `users`, `agent_positions`, `office_config`, `office_zones`, `costs`, `office_events`, `security_audit_log`, `daily_summary`, `token_usage`. Contiene datos operacionales de una versión anterior de Mission Control. **Riesgo: exposición de estructura interna, costes, posiciones de agentes.**
- **H-5 (CVSS 6.5 HIGH):** `memory/recordings/*.json` son transcripciones Whisper de voz del usuario. Contienen lenguaje informal, referencias a demos, auditorías, nombres de personas. Aunque no son "datos de entrenamiento", son **biometría de voz procesada** (GDPR Art. 9 aplicable si se considera dato biométrico). Están en disco pero no committed.
- **M-4 (CVSS 5.0 MEDIUM):** `events.jsonl` committed contiene queries de memoria semántica: `"Joker prefiere open source"`, paths a archivos internos, scores de relevancia. Expone estructura de memoria del agente.

**Mitigación:**
1. Eliminar `archive/mission-control.db` del repo (mover a storage local o eliminar si es histórico)
2. Añadir `*.db` a `.gitignore` (ya está para `data/` pero no para `archive/`)
3. Crear política de retención para `memory/recordings/` (eliminar tras X días)
4. Crear LICENSE file

---

#### 🟡 Alfred-Mission-Control — MEDIUM

| Campo | Valor |
|-------|-------|
| **License** | ❌ **NO LICENSE FILE** |
| **Datos** | `data/kanban.db` (664K), `data/activities.db` (88K), `data/usage-tracking.db` (28K) |
| **Origen** | Operacional: tareas kanban, actividad de agentes, métricas de uso |
| **Git tracking** | ✅ `.gitignore` excluye `/data/*.db` |

**Findings:**

- **M-5 (CVSS 4.5 MEDIUM):** `kanban.db` contiene tareas, descripciones, asignados, dependencias. `activities.db` registra acciones de agentes con timestamps y metadatos. `usage-tracking.db` mide consumo de tokens. Sin LICENSE, sin política de retención.
- Sin datos externos. Todo es operacional interno. Riesgo principal: exposición si el repo se hace público.

**Mitigación:**
1. Crear LICENSE file
2. Añadir política de retención en README

---

#### 🟢 QA-FRAMEWORK — LOW

| Campo | Valor |
|-------|-------|
| **License** | ✅ MIT |
| **Datos** | Solo resultados de tests (JSON), coverage reports |
| **Origen** | Auto-generado por test runs |
| **Git tracking** | Reports committed, `.venv` excluido |

**Findings:** Sin datasets externos. Los datos son métricas de tests. Sin riesgo de compliance.

---

#### 🟢 saba-osint — LOW (datos operacionales)

| Campo | Valor |
|-------|-------|
| **License** | ✅ Propietaria (SabaTech.dev) |
| **Datos** | `data/osint_nexus.db` (68K), `data/osint.db` (12K), `data/waitlist.db` (0K) |
| **Origen** | Usuarios registrados, scans OSINT, API keys, grafos |
| **Git tracking** | ✅ `.gitignore` excluye `data/`, `*.db` |

**Findings:**

- **M-6 (CVSS 4.0 MEDIUM):** `osint_nexus.db` contiene: `users` (email, hashed_password, name, company, stripe_customer_id), `api_keys` (key_hash, key_prefix), `scans` (target, results JSON). **GDPR aplicable** — contiene PII de usuarios (email, nombre, empresa). El README documenta GDPR Art. 9 para facial recognition ✅ pero no menciona GDPR general para la tabla `users`.
- Los datos de scans OSINT son generados por los usuarios para sus propios targets. La plataforma actúa como processor, no controller.

**Mitigación:**
1. Añadir Privacy Policy / GDPR compliance doc (Art. 13, 14, 15, 17)
2. Documentar data retention policy para scans antiguos
3. Añadir DPIA reference en README

---

### 2.2 Repos sin datos/training datasets

| Repo | License | Datos | Notas |
|------|---------|-------|-------|
| alfred-autoresearch | ✅ MIT | Ninguno | Config + scripts |
| craft-agents-oss | ✅ Apache 2.0 | Ninguno | OSS reference |
| flowsint | ✅ Apache 2.0 | Ninguno | CLI tool |
| huawei-health-mcp | ✅ MIT | Ninguno | MCP server |
| jose-sabaris-portfolio | ❌ NO LICENSE | Ninguno | Web personal |
| open-code-review | ✅ Apache 2.0 | Ninguno | CLI tool |
| orquestacion-poc | ❌ NO LICENSE | Ninguno | PoC interna |
| Saba-AgenticFlow | ✅ MIT | Ninguno | Agent framework |
| Saba-Agent-Os | ✅ Propietaria | Ninguno | Commercial product |
| sabatech.dev | ❌ NO LICENSE | Ninguno | Website |
| sabatrace | ✅ Apache 2.0 | Ninguno | Tracing tool |
| Saba-xMemory | ✅ Apache 2.0 | Ninguno | Memory system |
| security-poc | ❌ NO LICENSE | Ninguno | Security demos |

---

## 3. License Compliance Matrix

| Repo | License File | Declared License | Valid? |
|------|-------------|-----------------|--------|
| alfred-autoresearch | ✅ | MIT | ✅ |
| Alfred-Mission-Control | ❌ | None | ⚠️ Default copyright |
| Alfred_Reports_Docs | ❌ | None | ⚠️ Default copyright |
| AsistenteConversacional | ✅ | PolyForm Noncommercial 1.0.0 | ✅ |
| craft-agents-oss | ✅ | Apache 2.0 | ✅ |
| flowsint | ✅ | Apache 2.0 | ✅ |
| huawei-health-mcp | ✅ | MIT | ✅ |
| jose-sabaris-portfolio | ❌ | None | ⚠️ Default copyright |
| open-code-review | ✅ | Apache 2.0 | ✅ |
| orquestacion-poc | ❌ | None | ⚠️ Default copyright |
| QA-FRAMEWORK | ✅ | MIT | ✅ |
| Saba-AgenticFlow | ✅ | MIT | ✅ |
| Saba-Agent-Os | ✅ | Propietaria | ✅ |
| saba-llm-auto-train | ❌ | "MIT" (solo en README) | ⚠️ Sin archivo |
| saba-osint | ✅ | Propietaria | ✅ |
| sabatech.dev | ❌ | None | ⚠️ Default copyright |
| sabatrace | ✅ | Apache 2.0 | ✅ |
| Saba-xMemory | ✅ | Apache 2.0 | ✅ |
| security-poc | ❌ | None | ⚠️ Default copyright |

**Gap:** 7/19 repos (37%) sin LICENSE file.

---

## 4. Findings Consolidados

### 🔴 CRITICAL

| ID | Finding | CVSS | Repo |
|----|---------|------|------|
| C-1 | LICENSE file missing (MIT declared but not formalizado) | 7.5 | saba-llm-auto-train |
| C-2 | Google Gemma Terms of Use sin documentar/verificar compliance | 7.2 | saba-llm-auto-train, AsistenteConversacional |

### 🟠 HIGH

| ID | Finding | CVSS | Repo |
|----|---------|------|------|
| H-1 | Training data contiene internals operacionales (infra, configs, paths) | 6.5 | saba-llm-auto-train |
| H-2 | Datos sintéticos con PII markers committed a git (DNI, teléfono, CUPS) | 6.8 | AsistenteConversacional |
| H-3 | metadata.csv committed con transcripciones + PII markers | 5.5 | AsistenteConversacional |
| H-4 | SQLite DB con datos operacionales committed a git | 7.0 | Alfred_Reports_Docs |
| H-5 | Voice transcriptions (biometría) sin política de retención | 6.5 | Alfred_Reports_Docs |

### 🟡 MEDIUM

| ID | Finding | CVSS | Repo |
|----|---------|------|------|
| M-1 | Dataset provenance parcialmente documentado (sin licencias fuente) | 5.3 | saba-llm-auto-train |
| M-2 | Datos sintéticos no etiquetados como tales | 4.3 | AsistenteConversacional |
| M-3 | Modelo externo descargado sin pin de revisión | 4.0 | AsistenteConversacional |
| M-4 | Events.jsonl committed expone estructura de memoria del agente | 5.0 | Alfred_Reports_Docs |
| M-5 | DBs operacionales sin política de retención ni LICENSE | 4.5 | Alfred-Mission-Control |
| M-6 | GDPR compliance documentado parcialmente (solo facial recognition) | 4.0 | saba-osint |

### 🟢 LOW

| ID | Finding | CVSS | Repo |
|----|---------|------|------|
| L-1 | 7 repos sin LICENSE file (default copyright) | 3.8 | Múltiples |
| L-2 | Saba-osint SNA demo data es sintético pero no etiquetado | 3.2 | saba-osint |
| L-3 | Alfred_Reports_Docs recordings en disco sin encryption | 3.5 | Alfred_Reports_Docs |

---

## 5. Plan de Mitigación

### P0 — Inmediato (esta semana)

1. **Crear LICENSE files** para 7 repos sin: `saba-llm-auto-train`, `Alfred-Mission-Control`, `Alfred_Reports_Docs`, `jose-sabaris-portfolio`, `orquestacion-poc`, `sabatech.dev`, `security-poc`
2. **Eliminar `archive/mission-control.db`** de git tracking en Alfred_Reports_Docs
3. **Eliminar PII markers de git history** en AsistenteConversacional (BFG Repo-Cleaner)
4. **Crear `DATA_PROVENANCE.md`** en saba-llm-auto-train y AsistenteConversacional

### P1 — Corto plazo (este mes)

5. **Documentar Gemma Terms compliance** en ambos repos que usan Gemma
6. **Añadir disclaimer "datos 100% sintéticos"** en AsistenteConversacional
7. **Pinear revisión de modelo** en `download_model.py`
8. **Crear Privacy Policy** para saba-osint (GDPR Art. 13, 14, 15, 17)
9. **Política de retención** para voice recordings en Alfred_Reports_Docs
10. **Redacting de internals** en pipeline de extracción de training data

### P2 — Medio plazo (trimestre)

11. **DPIA completo** para saba-osint (no solo facial recognition)
12. **Encryption at rest** para DBs con PII
13. **Automated PII scanning** en CI/CD (pre-commit hook)
14. **Data catalog** centralizado para todos los repos SabaTech

---

## 6. Referencias

- [Google Gemma Terms of Use](https://ai.google.dev/gemma/terms)
- [GDPR Art. 9 — Special Categories](https://gdpr-info.eu/art-9-gdpr/)
- [OWASP Top 10:2025](https://owasp.org/www-project-top-ten/)
- [HuggingFace Model Cards](https://huggingface.co/docs/hub/model-cards)
- [PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/)
- [EU AI Act — Data Governance](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai)

---

**Last Updated:** 2026-06-29  
**Next Review:** 2026-09-29 (trimestral)
