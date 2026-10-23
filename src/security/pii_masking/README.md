# PII Masking (opt-in) — QA-FW ingest hygiene

Módulo `src/security/pii_masking` — hook único de higiene PII para el
pipeline de ingest: scrub de logs, fixtures y transcripts ANTES de que
cualquier payload llegue a un LLM externo o a storage.

> ## ⚠️ MODO HIGIENE — NO es DLP formal
> Este módulo **reduce** la exposición de PII; **no la elimina**.
> Recall publicado del motor neuronal (@desert-ant-labs/redact): **88.8%**
> → queda ~**11% de fuga residual en texto libre**. No lo uses como
> control DLP/DPD único ni como cumplimiento normativo. Es una capa de
> higiene best-effort para round-trips LLM y storage interno.

## Motor

- **Texto libre**: SDK [`@desert-ant-labs/redact`](https://www.npmjs.com/package/@desert-ant-labs/redact) **v3.1.0** (pineada),
  vía sidecar Node (`pii-redact-bridge/bridge.mjs`, protocolo NDJSON por
  stdio). El modelo se descarga de Hugging Face en el primer arranque
  (revisión pineada, verificación SHA-256) y se cachea en disco.
  Rendimiento esperado: p50 ≈ 163 ms CPU por texto.
- **Campos estructurados aislados** (y complemento determinista del SDK):
  motor regex propio (`regex_engine.py`) con validación semántica —
  Luhn (tarjetas), mod-97 (IBAN), reglas SSA (SSN) — para email, teléfono,
  SSN, IBAN, tarjeta, API key, JWT. Ejecución paralela (`scrub_many`) con
  resultados idénticos al secuencial.

## Flag opt-in (DEFAULT OFF)

| Variable | Valores | Default |
|---|---|---|
| `QAFW_PII_MASKING` | `1/true/yes/on` activa | **OFF** (vacío o ausente) |
| `QAFW_PII_MASKING_MODE` | `mask` (reversible) / `anonymize` (irreversible) | `mask` |
| `QAFW_PII_BRIDGE_COMMAND` | comando del sidecar (space-split) | `node pii-redact-bridge/bridge.mjs` |

Sin el flag, el hook es un no-op verificado por test
(`tests/security/test_pii_masking_config.py`).

## Placeholder map y round-trips LLM

- `MASK` (default): cada detección se sustituye por `[TIPO_N]`
  (p. ej. `[EMAIL_1]`, `[CREDIT_CARD_1]`). El `PlaceholderMap` conserva
  placeholder → original en memoria para restaurar la respuesta del LLM
  (`map.restore(reply)`). El log de placeholders registra solo tipo y
  placeholder, **nunca el valor original**.
- `ANONYMIZE`: el mapa se descarta — el texto redactado **no** es
  reversible y `restore()` lanza `RuntimeError`.

```python
from src.security.pii_masking import PiiMaskingConfig, PiiMaskingHook

hook = PiiMaskingHook(PiiMaskingConfig(enabled=True))
safe = hook.process({"transcript": "Email anna@example.com about card 4111 1111 1111 1111"})
# ... enviar safe al LLM ...
plain = hook.placeholder_map.restore(safe["transcript"])
```

Sinks ya integrados: logging de fichero (`QALogger`, filtro global) y
construcción de prompts LLM (`LLMTestGenerator.build_prompt_for_ingest`).

## Límites de licencia

`@desert-ant-labs/redact` se distribuye bajo **DAL 1.0** (Desert Ant
License): uso gratuito hasta **100k MAU**. La card de origen hablaba de
">10k dispositivos/mes" — umbral conservador (×10) que conviene respetar
como umbral operativo interno. Por encima del límite hace falta acuerdo
comercial con el vendor.

## Plan B (si el vendor/licencia falla)

**[GLiNER-PII](https://huggingface.co/urchade/gliner_multi_pii-domains-v1)**
(OSS, Apache-2.0, multi-idioma) como motor sustituto: la interfaz del hook
(`PiiMaskingHook.process`) y el `PlaceholderMap` son independientes del
motor — solo habría que reemplazar `redact_bridge.py`/sidecar por un
worker GLiNER manteniendo el contrato `{redactedText, items}`.

## Tests

```bash
python3 -m pytest tests/security -q --cov=src/security/pii_masking --cov-report=term-missing
```

Cobertura actual del módulo: **92%** (>80% requerido). Los tests usan un
bridge falso determinista (`tests/security/fixtures/fake_redact_bridge.py`)
y nunca descargan el modelo real.
