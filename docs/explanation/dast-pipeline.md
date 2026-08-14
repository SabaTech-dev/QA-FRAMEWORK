# DAST Pipeline — OWASP ZAP Baseline Scan

Pipeline de Dynamic Application Security Testing (DAST) para `qa.sabatech.dev`.
Complementa los pipelines SAST (Semgrep), SCA y Container Scan (Trivy) y Secret
Scan (Gitleaks) ya existentes en el repositorio.

Mientras que SAST analiza el código fuente en reposo, DAST analiza la aplicación
**en ejecución**, detectando problemas que solo se manifiestan en runtime:

- Cabeceras de seguridad ausentes o mal configuradas (CSP, HSTS, X-Frame-Options).
- Políticas CORS excesivamente permisivas.
- Endpoints expuestos no documentados.
- Cookies sin flags `HttpOnly` / `Secure`.
- Fugas de información del servidor (versiones, stack traces).
- Configuraciones incorrectas del reverse proxy / CDN.

## Arquitectura

```
.github/workflows/dast-zap.yml
  |
  |--> Job: zap-scan
  |      1. zaproxy/action-baseline@v0.13.0  ->  zap_report.json (ZAP JSON)
  |      2. scripts/security/zap_to_sarif.py  ->  zap_report.sarif (SARIF 2.1.0)
  |      3. github/codeql-action/upload-sarif -> GitHub Security tab
  |
  |--> Job: zap-gate  (needs: zap-scan)
         Cuenta results con level "error" (HIGH) y falla el build si hay > 0
```

El conversor JSON → SARIF vive en `scripts/security/zap_to_sarif.py` porque la
action `zaproxy/action-baseline` no emite SARIF nativamente; solo HTML, Markdown
y JSON. El formato JSON de ZAP es estable y público, por lo que la conversión es
determinista y está cubierta por tests en `tests/security/test_zap_tools.py`.

## Mapeo de severidades

ZAP Baseline tiene cuatro tiers de riesgo. Se mapean a niveles SARIF siguiendo
la convención recomendada por el SARIF Technical Committee:

| ZAP riskcode | ZAP risk   | SARIF level | Comportamiento del gate |
|--------------|------------|-------------|-------------------------|
| 3            | High       | `error`     | **Falla el build**      |
| 2            | Medium     | `warning`   | Reportado, no falla     |
| 1            | Low        | `note`      | Reportado, no falla     |
| 0            | Info       | `none`      | Oculto por defecto      |

GitHub Security tab muestra `error` como errores, `warning` como advertencias,
`note` como notas y oculta `none` salvo que se cambie el filtro.

ZAP Baseline **no tiene** tier "Critical". El tier más alto es "High", que es lo
que el gate trata como fallo. Esta es la nomenclatura nativa de ZAP y se respeta.

## Triggers

| Evento          | Cuándo                                        |
|-----------------|-----------------------------------------------|
| `push` a `main` | En cada merge a main                          |
| `schedule`      | Lunes 06:00 UTC (baseline semanal automático) |
| `workflow_dispatch` | Manual, con input opcional `target`      |

El target por defecto es `https://qa.sabatech.dev`. Se puede apuntar a otro
entorno ejecutando el workflow manualmente y pasando una URL distinta.

## Reglas y exclusiones

El archivo `.github/zap-rules.tsv` controla qué alerts se excluyen del scan.
El formato es TSV: `pluginid<TAB>acción<TAB>(descripción)`. Las acciones
válidas son `IGNORE` (reportar pero no fallar), `FAIL` (tratar como error) y
`OUTOFSCOPE` (no escanear en absoluto).

### Exclusiones activas

| pluginid | Alerta                              | Acción       | Justificación                                                                                          |
|----------|-------------------------------------|--------------|---------------------------------------------------------------------------------------------------------|
| 10202    | Absence of Anti-CSRF Tokens         | `OUTOFSCOPE` | QA-FRAMEWORK usa JWT Bearer en la cabecera `Authorization` (stateless). CSRF no es aplicable cuando la autenticación no se basa en cookies que el navegador envía automáticamente. |

### Política de exclusión

No se excluyen alerts por "ruido". Toda exclusión debe:

1. Tener una justificación técnica verificable en este documento.
2. Referenciar el pluginid concreto (no patrones comodín).
3. Revisarse trimestralmente — lo que es falso positivo hoy puede dejar de serlo.

Para añadir una exclusión tras revisar un reporte:

1. Añadir la línea al archivo `.github/zap-rules.tsv`.
2. Añadir la fila a la tabla anterior con la justificación.
3. Commit con mensaje `docs(security): exclude ZAP <pluginid> — <razón>`.

## Interpretación de resultados

Tras cada ejecución, los findings aparecen en:

1. **GitHub Security tab** → categoría `zap-dast` (fuente de verdad).
2. **Artifacts** del workflow run → `zap-dast-results` (SARIF + JSON, 30 días).
3. **Step summary** del job `zap-scan` → tabla resumen con counts por severidad.

Si el job `zap-gate` falla, hay al menos un finding HIGH (riskcode 3). Revisar
el Security tab para detalle y remediar antes de re-ejecutar.

## Relación con el adapter ZAP existente

Existe un adaptador Python (`src/adapters/vuln/zap_scanner.py`, rama
`feat/zap-scanner-adapter`) que permite lanzar scans ZAP on-demand desde el
dashboard de QA-FRAMEWORK contra aplicaciones de los usuarios. Este pipeline
DAST es **ortogonal**: escanea la propia aplicación QA-FRAMEWORK (qa.sabatech.dev)
de forma automática en CI. No hay duplicación funcional.

## Troubleshooting

| Síntoma                                          | Causa probable                          | Solución                                          |
|--------------------------------------------------|-----------------------------------------|---------------------------------------------------|
| `zap_report.json` no se genera                   | Scan abortado o timeout (30 min)        | Re-ejecutar; revisar disponibilidad del target    |
| El gate pasa pero el Security tab muestra errores | El resultado se generó tras el gate    | Revisar orden de steps; el gate corre post-scan   |
| Conteos duplicados en el summary                 | `defaultConfiguration.level` en rules  | No debe añadirse; cada result lleva su propio level |
| `0 findings` en todas las severidades            | Target caído o spider bloqueado        | Verificar `https://qa.sabatech.dev` responde 200  |

## Mantenimiento

- **Versión de la action:** `zaproxy/action-baseline@v0.13.0`. Actualizar
  requiere re-validar que `cmd_options` y `rules_file_name` siguen siendo
  compatibles con la nueva versión.
- **Versión de ZAP:** la imagen por defecto (`ghcr.io/zaproxy/zaproxy:stable`).
  Para weekly builds, pasar `docker_name: 'ghcr.io/zaproxy/zaproxy:weekly'`.
- **Tests del conversor:** `python3 -m pytest tests/security/test_zap_tools.py`.
