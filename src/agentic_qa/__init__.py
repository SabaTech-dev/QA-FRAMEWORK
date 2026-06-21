"""Paquete del PoC de QA agéntico (Fase 1).

Agrupa los componentes deterministas y los adaptadores de herramientas
(Playwright Test Agents, Promptfoo y DeepEval) evaluados en el PoC.

Diseño:
- Sin dependencias pesadas (importable en cualquier entorno).
- Componentes deterministas primero (testeable herméticamente).
- Los adaptadores de herramientas se cargan bajo demanda.
"""
