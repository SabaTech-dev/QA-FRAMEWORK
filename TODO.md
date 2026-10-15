# TODO — Deuda técnica de dependencias

> Generada por Alfred el 2026-10-15 tras la ola de fixes de dependabot alerts (mandato: solo fixes in-range, sin romper).
> Lo siguiente son majors de toolchain dev — requieren migración con tests.

## vitest 0.34.6 → ≥ 3.2.6 (critical, alerta #84)
- Arrastra: @vitest/coverage-v8 (0.34.x) y @vitejs/plugin-react.
- Acción: migrar config de vitest a 3.x+, actualizar plugins y validar suite completa.

## tinypool → ≥ 2.1.2 (critical, alertas #180/#181)
- Transitivo de vitest 0.34 — se resuelve con la migración anterior.

## vite → versión con fix (high #93 / medium #94 / #40)
- Ranges `<= 6.4.2` / `<= 6.4.1` — sin fix completo publicado para 5.x/6.x a la fecha.
- Acción: monitorear y subir cuando haya release parcheada (probablemente 7.x major con vitest).

## esbuild ≤ 0.24.2 (medium, alerta #34)
- Sin fix publicado; alerta dev/build-only.

## Nota
Las alerts pip de python-jose/nltk/starlette/ecdsa ya no existen en requirements.txt de main — dependabot las cerrará al re-scan. dotenv/brace-expansion/source-map-js quedaron parcheados en PR #284 (merged).
