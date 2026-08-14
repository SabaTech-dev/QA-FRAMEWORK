# OpenCode - Guía de Uso Correcto para QA-FRAMEWORK

**Fecha:** 2026-02-11  
**Autor:** Alfred

---

## 🎯 Entendiendo OpenCode

OpenCode **NO tiene** modos `plan` y `build` como Codex. Es un TUI interactivo que:

1. **Analiza el proyecto** automáticamente
2. **Genera un plan** internamente
3. **Implementa el código** basándose en ese plan

La diferencia principal es que Codex requiere pasos explícitos, mientras que OpenCode hace todo automáticamente.

---

## 🚀 Formas Correctas de Usar OpenCode

### Forma 1: Ejecutar con Prompt (One-Shot)

```bash
# En el directorio del proyecto
cd /home/ubuntu/.openclaw/workspace/QA-FRAMEWORK

# Ejecutar OpenCode con un prompt
/home/ubuntu/.npm-global/bin/opencode run "Implementa el módulo de UI Testing con Playwright"
```

Esto hace:
1. Análisis del proyecto actual
2. Generación del plan interno
3. Implementación del código
4. Salida automática

### Forma 2: Ejecutar en Background (Para Tareas Largas)

```bash
# Usar exec para ejecutar en background
cd /home/ubuntu/.openclaw/workspace/QA-FRAMEWORK

# Ejecutar en background
/home/ubuntu/.npm-global/bin/opencode run "Implementa el módulo de UI Testing con Playwright" &
```

### Forma 3: Ejecutar con PTY (Método Correcto)

```bash
# Importante: Usar PTY para OpenCode
exec pty:true workdir:/home/ubuntu/.openclaw/workspace/QA-FRAMEWORK command:"opencode run 'Implementa el módulo de UI Testing con Playwright'"
```

**¿Por qué PTY?** OpenCode es una aplicación interactiva que necesita un terminal pseudo para funcionar correctamente.

---

## 🎨 Simulando Modo Plan y Build

Si quieres simular el comportamiento de Codex (plan → build), hazlo en dos pasos:

### Paso 1: Solicitar Plan

```bash
exec pty:true workdir:/home/ubuntu/.openclaw/workspace/QA-FRAMEWORK command:"opencode run 'Por favor, primero genera un plan detallado para implementar el módulo de UI Testing con Playwright. NO escribas código todavía, solo el plan con los pasos, archivos a crear y estructura. Espera mi confirmación antes de continuar.'"
```

### Paso 2: Ejecutar Implementación

```bash
# Después de revisar y aprobar el plan
exec pty:true workdir:/home/ubuntu/.openclaw/workspace/QA-FRAMEWORK command:"opencode run 'Ahora implementa el plan que generamos anteriormente: <insertar plan aquí>. Escribe todo el código, crea todos los archivos, y asegúrate de que todo esté correctamente implementado.'"
```

---

## 📊 Diferencias OpenCode vs Codex

| Característica | Codex | OpenCode |
|--------------|--------|-----------|
| **Modo Plan** | `codex plan "prompt"` | No existe (planea internamente) |
| **Modo Build** | `codex build "prompt"` | No existe (implementa automáticamente) |
| **Interacción** | TUI interactivo | TUI interactivo |
| **PTY requerido** | ✅ Sí | ✅ Sí |
| **One-shot** | `codex exec` | `opencode run` |
| **Background** | `&` o `background:true` | `&` o `background:true` |

---

## ✅ Ejemplos Prácticos

### Ejemplo 1: Implementar Módulo UI Testing

```bash
exec pty:true workdir:/home/ubuntu/.openclaw/workspace/QA-FRAMEWORK command:"opencode run 'Implementa el módulo de UI Testing con las siguientes características:

1. Crea src/adapters/ui/playwright_page.py con:
   - Page Object Model base class
   - Métodos: goto, click, fill, wait_for_selector
   - Soporte para async/await

2. Crea examples/ui_testing_example.py con:
   - Ejemplo de login page
   - Ejemplo de búsqueda
   - Aserciones visuales

3. Actualiza requirements.txt si es necesario
4. Crea tests básicos en tests/ui/

Aplica principios SOLID, usa type hints 100%, y añade docstrings Google style.'"
```

### Ejemplo 2: Implementar Reporting System

```bash
exec pty:true workdir:/home/ubuntu/.openclaw/workspace/QA-FRAMEWORK command:"opencode run 'Implementa el sistema de reporting con Allure:

1. Crea src/adapters/reporting/allure_reporter.py con:
   - Clase AllureReporter
   - Métodos para reportar pruebas
   - Soporte para screenshots/videos

2. Actualiza pyproject.toml con configuración de Allure

3. Crea examples/allure_reporting_example.py

Sigue Clean Architecture y SOLID principles.'"
```

### Ejemplo 3: Implementar Paralelización

```bash
exec pty:true workdir:/home/ubuntu/.openclaw/workspace/QA-FRAMEWORK command:"opencode run 'Implementa soporte para paralelización de pruebas:

1. Crea conftest.py con configuración de pytest-xdist
2. Añade fixtures que soporten paralelización
3. Actualiza config/qa.yaml con opción parallel_workers
4. Crea documentación sobre cómo usar pytest -n

Usa pytest-xdist y asegura que los tests sean thread-safe.'"
```

---

## 🐛 Debugging OpenCode

### Si OpenCode no genera código:

**Posibles causas:**
1. **No hay un repositorio git** - OpenCode requiere git
2. **PTY no se usó** - Salida rota
3. **Prompt muy vago** - OpenCode no sabe qué hacer

**Soluciones:**
```bash
# 1. Asegúrate de que hay un repo git
cd /home/ubuntu/.openclaw/workspace/QA-FRAMEWORK
git status

# 2. Usa PTY
exec pty:true workdir:/path/to/project command:"opencode run 'prompt'"

# 3. Sé específico en el prompt
exec pty:true workdir:/path/to/project command:"opencode run 'Crea el archivo src/example.py con una función hello_world que retorne \"Hello, World\".'"
```

### Si OpenCode se cuelga:

**Posibles causas:**
1. **Esperando input** - Necesita confirmación
2. **Proceso bloqueado** - PTY necesario
3. **Timeout** - Tarea muy larga

**Soluciones:**
```bash
# 1. Verificar si está corriendo
process action:list

# 2. Ver logs
process action:log sessionId:XXX

# 3. Si está esperando input, enviarlo
process action:submit sessionId:XXX data:"y"
```

---

## 🎯 Recomendaciones Finales

1. **Siempre usa PTY** con OpenCode
2. **Sé específico** en los prompts
3. **Asegúrate de tener un repo git**
4. **Usa workdir** para limitar el contexto
5. **Monitorea con process:log** en background
6. **No esperes modos plan/build** - OpenCode los maneja internamente

---

**Actualizado:** 2026-02-11 07:45 UTC
