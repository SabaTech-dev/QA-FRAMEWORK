---
created: 2026-11-11
owner: devops
status: snapshot
card: 920fb238
---

# Jubilación del preview local (deploy-backend/frontend-preview)

## Qué pasó

- El panel Coolify LOCAL de jokerserver (127.0.0.1:8000) fue **jubilado el 22-oct** — prod Coolify vive en vnic (único panel de la flota desde entonces, INFRA.md §puertos).
- El repo var `COOLIFY_CONFIGURED` quedó en `true` residual → los jobs deploy-backend/frontend-preview corrieron contra la API local muerta → fallo en TODOS los PRs desde ~9-nov.

## Fix (11-nov, card 920fb238)

- `COOLIFY_CONFIGURED` → `false` (gh variable set): los jobs deploy-preview ahora se **SKIPPED limpiamente** (skipped-by-design, no failed) en todos los PRs.
- El gate ya existía en el workflow (`if: ... vars.COOLIFY_CONFIGURED == 'true'`) — solo el var estaba desalineado.

## Re-enable futuro

Cuando exista infraestructura de previews en vnic (GO Joker): re-set `COOLIFY_CONFIGURED=true` + retarget de la API Coolify al endpoint vnic en el runner. Mientras tanto, los previews de PR están desacoplados por diseño.
