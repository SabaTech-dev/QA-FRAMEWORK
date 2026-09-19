# T-UCI Capability — Update-Channel Integrity Testing (Design Doc)

**Fecha:** 2026-08-25
**Autor:** research agent (card `66afa12e`)
**Estado:** DRAFT — Pendiente GO/NO-GO Joker (implementación gated)
**Base:** Case study MoYu/BADBOX (`workspace-research/reports/research/moyu-badbox-update-channel-integrity-2026-08-25.md` §5-§6, card 3bb1f21e, reviewada) · Derivada R5

---

## 1. Goal

Convertir el test-pattern **T-UCI (Update-Channel Integrity)** — extraído del case study MoYu/BADBOX (grupo MoYu usó el updater de firmware legítimo `TWCore` de head units DoFun para distribuir malware: HTTP sin TLS, sin verificación de firma, updater con scope para instalar apps inexistentes, canal de control no autenticado) — en una **capability de producto de QA-FRAMEWORK**: una suite que valida automáticamente que el canal de updates de un sistema objetivo **falla cerrado** ante compromisos de integridad.

Vertical objetivo: **IoT/automotive** (interés directo DevSecOps/QA Minsait). Narrativa de mercado lista: BADBOX 2.0 = 10M+ dispositivos, demanda de Google (jul-2025), FBI PSA (jun-2025), primer malware para head units de coche (Kaspersky, ago-2026).

**Qué NO es este doc:** implementación. Es diseño + mapeo a componentes + estimación + recomendación con trade-offs. La decisión de implementar es de Joker.

---

## 2. Los 6 checks T-UCI (origen: §5.1 del case study)

| ID | Check | Estímulo | Criterio PASS |
|---|---|---|---|
| T-UCI-1 | Transporte íntegro | MITM interponiéndose en la descarga de updates | Update **falla cerrado** — nunca instala sobre canal interceptado no confiable |
| T-UCI-2 | Firma del artefacto | Inyectar: (a) binario sin firmar, (b) firmado con clave inesperada, (c) firmado válido | (a)/(b) → rechazo + alerta; (c) → instala. Sin excepciones silenciosas |
| T-UCI-3 | Scope del updater | Intento de instalar paquete que nunca existió en el sistema (analogo `installNotExists`) | Denegado + alerta — un updater no es un instalador arbitrario |
| T-UCI-4 | Canal de control autenticado | Mensaje de update no autenticado/no firmado en el canal (MQTT/queue/HTTP) | Ignorado. Solo emisores verificables |
| T-UCI-5 | Anti-rollback | Ofrecer versión inferior a la instalada | Rechazo o política explícita documentada |
| T-UCI-6 | Drift post-install | Comparar hash/SBOM del binario instalado vs manifiesto esperado | Coincidencia; mismatch → alerta + cuarentena |

Principio transversal (la lección del case study): **todos los checks son pruebas negativas sobre fail-closed** — se pasa cuando el sistema *rechaza*, no cuando *funciona*.

---

## 3. Arquitectura propuesta

Sigue los patrones existentes del framework (mismas convenciones que `accuracy_testing` y el adapter `NucleiScanner`).

```
src/
├── domain/update_integrity/          # entidades + lógica de verificación
│   ├── entities.py                   # TUCITarget, TUCICheckResult, TUCISession, TUCIPolicy
│   └── check_engine.py               # orquestación de los 6 checks, verdict aggregation
├── adapters/update_integrity/        # wrappers de herramientas (patrón NucleiScanner)
│   ├── mitm_proxy.py                 # T-UCI-1: wrapper mitmproxy (Docker, async)
│   ├── artifact_verifier.py          # T-UCI-2/5: cosign/sigstore verify + version policy
│   ├── channel_probe.py              # T-UCI-3/4: MQTT/HTTP publisher con credenciales controladas
│   └── sbom_drift.py                 # T-UCI-6: trivy fs → CycloneDX → diff vs manifiesto
├── infrastructure/update_integrity/  # persistencia de sesiones, reportes, integración test_runner
│   └── persistence.py                # patrón de accuracy_testing (sesiones + resultados)
└── api → endpoints /update-integrity/*  # patrón /accuracy/* (sessions, results, config)

tests/security/test_tuci_*.py         # unit + integration (marcadores inofensivos)
tests/e2e/test_update_channel_target.py  # E2E contra target simulado (harness propio)
```

**Entidades clave (sketch):**

```python
class TUCICheckType(str, Enum):
    TRANSPORT = "transport"            # T-UCI-1
    SIGNATURE = "signature"            # T-UCI-2
    UPDATER_SCOPE = "updater_scope"    # T-UCI-3
    CHANNEL_AUTH = "channel_auth"      # T-UCI-4
    ANTI_ROLLBACK = "anti_rollback"    # T-UCI-5
    POST_INSTALL_DRIFT = "drift"       # T-UCI-6

class TUCICheckResult:  # alineado con VulnScanResult/VulnSeverity existente
    check_type: TUCICheckType
    status: Literal["pass", "fail", "fail_closed_ok", "error"]  # fail_closed_ok = el rechazo esperado ocurrió
    evidence: dict      # transcript MITM, salida cosign, diff SBOM...
    raw_output: str
```

**Seguridad operativa:** los checks usan *marcadores inofensivos* (APK/binario dummy con huella detectable, ej. package name `com.qafw.tuci.canary`) contra **targets propiedad del cliente y autorizados** — mismo modelo de autorización que ya aplica Nuclei. Nunca payloads reales.

---

## 4. Mapeo de los 6 checks a componentes concretos (AC #2)

| Check | Domain (assertion) | Adapter (herramienta) | Suite de tests | Módulos existentes que reusa |
|---|---|---|---|---|
| **T-UCI-1 Transporte** | `check_engine`: install intentada durante interceptación → esperar `fail_closed_ok` | `mitm_proxy.py` (mitmproxy en Docker, modo transparente/reverse; captura transcript) | `tests/e2e/test_update_channel_transport.py` | Patrón Docker-wrapper de `adapters/vuln/nuclei_scanner.py`; red `qa-network` |
| **T-UCI-2 Firma** | 3 escenarios (sin firma / clave errónea / válida) → solo (c) instala | `artifact_verifier.py` (cosign verify, o `gh attestation verify`; claves de test generadas por check_engine) | `tests/security/test_tuci_signature.py` | **SLSA provenance ya en CI** (`slsa-provenance.yml`): el mismo mecanismo que el CI genera, T-UCI lo verifica en destino — sinergia directa con propuesta R3 (deploy gate) |
| **T-UCI-3 Scope updater** | intento de instalar paquete canary inexistente → denegado | `channel_probe.py` (publica orden de instalación legit-format en el canal del target: MQTT pub / POST endpoint) | `tests/security/test_tuci_updater_scope.py` | `adapters/vuln/wstg_scanner.py` (modelos de solicitud); patrón de `security_client.py` |
| **T-UCI-4 Canal autenticado** | mensaje no autenticado (sin firma / credencial inválida / emisor desconocido) → ignorado | `channel_probe.py` (mosquitto_pub/emqx client con matrix de credenciales) | `tests/security/test_tuci_channel_auth.py` | `adapters/security/auth_tester.py` (matriz de credenciales) como referencia de patrón |
| **T-UCI-5 Anti-rollback** | ofrecer v(N-1) con firma VÁLIDA → política (rechazar por defecto) | `artifact_verifier.py` (versión del paquete + política `min_version`) | `tests/security/test_tuci_rollback.py` | `domain/compliance` (estructura de políticas) como referencia |
| **T-UCI-6 Drift post-install** | SBOM/hash instalado vs manifiesto esperado → coincidencia | `sbom_drift.py` (trivy fs → CycloneDX; diff por componente) | `tests/security/test_tuci_drift.py` | **SBOM CycloneDX ya generado en CI** (`ci-cd.yml` stage 8b, Trivy) — formato y tooling idénticos; `adapters/vuln/vuln_parser.py` (normalización) |

**Integración con módulos existentes (AC alcance #2):**
- **Nuclei** (`adapters/vuln/nuclei_scanner.py`): pre-fase opcional — templates network/web sobre los endpoints del canal de update para superficie expuesta (puertos abiertos, TLS deprecado). Reuso directo del wrapper.
- **Trivy/SBOM**: T-UCI-6 es literalmente el pipeline SBOM existente apuntando al artefacto instalado del target en vez del repo.
- **SLSA provenance**: T-UCI-2 verifica attestations del mismo tipo que `slsa-provenance.yml` produce — QA-FW puede "comerse su propia comida" verificando sus propios artefactos como demo.
- **DAST/ZAP** (`tests/security/test_zap_tools.py`): passive scan del canal web como contexto del reporte.
- **OWASP suite existente** (`test_owasp_top10_2025.py`): T-UCI añade la dimensión de integridad de canal que esa suite no cubre (ella valida la app, no cómo llega el código a la app).

---

## 5. Dependencias y licencias

| Dependencia | Uso | Licencia (verificar en implementación) | Nota |
|---|---|---|---|
| mitmproxy (Docker image) | T-UCI-1 | Open source (verificar término exacto) | Mismo modelo container que Nuclei |
| cosign (Sigstore) | T-UCI-2 | Apache-2.0 | CLI en container; alternativa `gh attestation` |
| mosquitto-clients / EMQX test broker | T-UCI-3/4 | EPL/EDL, Apache-2.0 | Broker efímero en `qa-network` |
| trivy | T-UCI-6 | Apache-2.0 | **Ya presente** en el stack (CI) |
| Docker | todos los adapters | — | Ya requerido por Nuclei integration |

Sin dependencias de runtime nuevas para el backend (todo via containers efímeros, patrón Nuclei). [ESTIMACIÓN] Coste infra: images Docker (~500MB total) + red efímera por sesión.

---

## 6. Estimación de esfuerzo [ESTIMACIÓN]

| Fase | Contenido | Esfuerzo agente | Riesgo |
|---|---|---|---|
| **F0 — Core ligero** | T-UCI-2 + T-UCI-6 (adapters `artifact_verifier` + `sbom_drift`, entities, 2 suites tests, sin API/dash) | 2-3 días | Bajo — reuso casi total (cosign + trivy ya en stack) |
| **F1 — Capability completa** | T-UCI-1/3/4/5 (mitm_proxy, channel_probe, harness target simulado), check_engine agregación | 4-6 días | Medio — harness de target simulado (head unit fake con updater) es la pieza nueva más grande |
| **F2 — Productización** | API `/update-integrity/*` (patrón accuracy), persistencia sesiones, página dashboard, reporte PDF/markdown, multitenant | 3-5 días | Bajo — patrón accuracy_testing replicado |
| **Total MVP completo** | | **9-14 días agente** | |

El **harness de target simulado** (F1) merece nota: un mini-servidor que simula un updater compliant (rechaza todo lo que debe rechazar) + su variantes vulnerables, para que los 6 checks tengan contra qué probar en CI sin hardware. Es también el artifacto demo para ventas/charlas.

---

## 7. Trade-offs → GO/NO-GO (AC #3)

### Argumentos GO
1. **Diferenciador real**: ninguna suite QA SaaS estándar ofrece "update-channel integrity" como módulo (verificado en case study §5.3). Narrativa de mercado madura (BADBOX 2.0: 10M dispositivos, Google lawsuit, FBI PSA, Kaspersky automotive first).
2. **Reuso alto**: 4 de 6 checks se apoyan en tooling ya presente (Trivy/SBOM, SLSA/cosign, patrón Nuclei Docker, red qa-network). F0 es barato.
3. **Vertical concreto**: IoT/automotive Minsait — caso de uso demostrable con el harness propio, material de charla inmediato.
4. **Sinergia interna**: T-UCI-2/6 aplicados al propio pipeline QA-FW = el deploy gate propuesto en R3 (case study §6) con tests de producto encima.

### Argumentos NO-GO (o aplazar)
1. **Roadmap**: MVP→BETA es la prioridad declarada; esto es capability nueva, no deuda ni blocker. Meterte ahora = riesgo de foco pre-beta.
2. **Superficie de mantenimiento nueva**: 4 herramientas containerizadas más + harness propio.
3. **Demanda no validada**: ningún cliente beta ha pedido integridad de canal de update; el vertical IoT/automotive es hipótesis (bien fundamentada, pero hipótesis).
4. **Fidelity gap**: simulador ≠ dispositivo real; para automotive serio se necesitaría device farm (coste/futuro).

### Recomendación (research, para decisión Joker)

**GO escalonado, post-beta-launch:**
- **Ahora (pre-beta): NO-GO** — no implementar nada; mantener el patrón documentado (este doc + case study).
- **Post-beta, F0 (2-3 días): GO recomendado** — T-UCI-2+T-UCI-6 como "artifact integrity checks". Coste mínimo, reuso máximo, sirve al pipeline propio (refuerza R3) y da un demo story. No requiere API nueva si se expone como suite pytest con reporte.
- **F1+F2 (capability completa): GO condicionado a señal** — validación de demanda con ≥1 cliente/prospect beta del vertical IoT/automotive, o decisión estratégica de posicionamiento (QA-FW como "the supply-chain-aware QA platform"). Sin esa señal, F1+F2 espera.

Esta estructura protege el roadmap beta, captura el valor barato pronto, y evita invertir 9-14 días en una hipótesis sin validación de mercado.

---

## 8. Riesgos del diseño

| Riesgo | Mitigación |
|---|---|
| Fidelity simulador vs dispositivo real | Diseñar adapters contra interfaces abstractas (patrón core/interfaces) para poder añadir device farms reales sin tocar domain |
| Licencias de herramientas | Verificación explícita en F0 (tabla §5 marcada "verificar") |
| Scope creep hacia "malware lab" | Scope duro: 6 checks fail-closed, sin detonación de payloads, marcadores canary inofensivos |
| Docker-in-Docker en runners CI | Igual que Nuclei hoy: containers hermanos en `qa-network`, no DinD |
| Mantenimiento de images upstream | Pin de versions en adapters (lección del propio case study: no `@latest`) |

---

## 9. Trazabilidad de ACs (card 66afa12e)

- **AC1 Design doc completo en docs/internal/design/** → este documento (`docs/internal/design/t-uci-capability.md`).
- **AC2 6 tests mapeados a componentes concretos** → §4 (tabla check → domain/adapter/suite/módulos reusados, con paths existentes verificados en repo).
- **AC3 Recomendación clara con trade-offs** → §7 (GO/NO-GO argumentado + recomendación escalonada).
- Alcance extra del scope: mapeo con módulos existentes (§4), estimación + dependencias (§5-§6).

## 10. Referencias

- Case study base: `~/.openclaw/workspace-research/reports/research/moyu-badbox-update-channel-integrity-2026-08-25.md` (§5 patrón, §6 recomendaciones R1-R5)
- Securelist (ago-2026): https://securelist.com/android-head-unit-malware/121106/
- HUMAN BADBOX 2.0 (2025): https://www.humansecurity.com/learn/blog/satori-threat-intelligence-disruption-badbox-2-0/
- Google lawsuit (jul-2025): https://blog.google/innovation-and-ai/technology/safety-security/google-taking-legal-action-against-the-badbox-20-botnet/
- Patrones internos: `src/adapters/vuln/nuclei_scanner.py` · `src/infrastructure/accuracy_testing/` · `.github/workflows/slsa-provenance.yml` · `ci-cd.yml` stage 8b (SBOM)
