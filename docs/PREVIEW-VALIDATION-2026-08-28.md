# Validación de previews Coolify — 2026-08-28

PR dummy para validar el pipeline end-to-end de previews (card 52a85645):

1. Deploy de apps backend+frontend en Coolify vía API (runner `coolify-deploy`).
2. Probes in-container (backend `/health`, frontend `:5173`).
3. Cleanup automático al cerrar este PR (se cerrará SIN merge).

Este fichero es efímero: solo existe para disparar el pipeline.
