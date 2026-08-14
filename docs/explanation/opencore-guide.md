# OpenCode - Documentación Oficial Estudiada y Resumen Completo

**Fecha:** 2026-02-11 18:05 UTC  
**Autor:** Alfred  
**Fuente:** https://opencode.ai/docs (Documentación Oficial)

---

## 🎯 Arquitectura de OpenCode (Comprendida)

### OpenCode ES una Aplicación TUI, No Script CLI

**IMPORTANTE:** OpenCode está diseñado como una **herramienta interactiva de Terminal** (como NeoVim, Vim), **NO como un script CLI** con flags como `--plan` o `--build`.

**Estructura:**
```
Interfaz TUI (Terminal)
├── Modos Integrados
│   ├── Planning Mode (Análisis + Planificación)
│   ├── Build Mode (Implementación)
│   └── Review Mode (Revisión)
├── Navegación entre secciones
├── Gestión de sesiones
└── Gestión de configuración
```

---

## 🚀 Instalación y Configuración

### Métodos Oficiales de Instalación

#### 1. Instalación Automática (Recomendada)
```bash
# Linux/macOS
curl -fsSL https://opencode.ai/install | bash

# Usando brew (Homebrew) - Mantenido oficial
brew install opencode
```

#### 2. Instalación Manual con npm
```bash
# Instalar globalmente
npm install -g opencode-ai

# Actualizar a la última versión
npm update -g opencode-ai

# Ver versión instalada
opencode --version
```

#### 3. Instalación Binaria
- **Linux:** Descargar binario desde releases
- **macOS:** `brew install opencode`
- **Windows:** `scoop install opencode` o `choco install opencode`

---

## 🎮 Modos de Trabajo de OpenCode

### 1. Planning Mode (Modo Planificación)
**Propósito:** Analizar código y crear planes detallados

**Cómo se activa en la TUI:**
1. Abrir OpenCode en el directorio del proyecto
2. Navegar a la sección de Planificación (indicated en TUI)
3. OpenCode analizará el proyecto automáticamente
4. Generará un plan detallado con:
   - Análisis del código existente
   - Pasos de implementación
   - Archivos a crear/modificar
   - Dependencias a añadir
   - Orden de ejecución

**Qué verás en la TUI:**
- Barra lateral con secciones (Planning, Build, Review, etc.)
- Área principal con el análisis del proyecto
- Lista de archivos del proyecto
- Sugerencias de pasos a seguir
- Chat/buffer para comunicarte con el modelo AI

**Comando equivalente:** N/A (se activa navegando en TUI)

### 2. Build Mode (Modo Implementación)
**Propósito:** Ejecutar e implementar según el plan

**Cómo se activa en la TUI:**
1. Abrir OpenCode (en el mismo proyecto o sesión)
2. Seleccionar el plan que se generó en Planning Mode
3. OpenCode usará el plan como guía
4. Implementará el código paso a paso
5. Notificará progreso en tiempo real
6. Permitirá revisión y ajustes

**Qué verás en la TUI:**
- Lista de archivos creados/modificados
- Consola con output de comandos
- Progreso de implementación
- Errores o advertencias
- Resumen final al terminar

**Comando equivalente:** N/A (se activa navegando en TUI)

### 3. Review Mode (Modo Revisión)
**Propósito:** Revisar y aprobar cambios

**Cómo se activa en la TUI:**
1. Navegar a la sección de Review
2. Ver cambios propuestos
3. Aprobar o rechazar cambios
4. Solicitar ajustes si es necesario

**Comando equivalente:** N/A (se activa navegando en TUI)

---

## 🔑 Autenticación y Configuración

### /connect - Comando de Autenticación

**Propósito:** Configurar múltiples providers y API keys

**Uso:**
```bash
# Abrir el diálogo de autenticación
opencode /connect

# En la TUI:
# 1. Seleccionar provider (OpenAI, Anthropic, etc.)
# 2. Pegar API key
# 3. Confirmar y guardar
```

**Características:**
- Configurar múltiples providers simultáneamente
- API keys separadas para cada provider
- Selección de modelo por defecto
- Sincronización de configuración

### Configuración de Modelos

**Modelos Disponibles:**
- **OpenAI:** gpt-5.2, gpt-5.1, gpt-5-codex
- **Anthropic:** claude-3.5, claude-3.5-haiku, claude-opus-4.1
- **Otros:** Google, DeepSeek, Grok, Llama, etc.

**Configuración:**
```bash
# Ver modelos disponibles
opencode models

# Seleccionar modelo principal
opencode --model <provider>/<model>

# Ejemplo
opencode --model openai/gpt-5.2
```

---

## 📁 Gestión de Sesiones

### Comandos de Sesiones

```bash
# Ver sesiones recientes
opencode session

# Continuar sesión anterior
opencode --session <session-id>

# Exportar sesión como JSON
opencode export <session-id>

# Importar sesión desde JSON
opencode import <file-o-archivo.json>
```

**Características:**
- Sesiones persistentes entre reinicios
- Compartir sesiones con el equipo (si está habilitado)
- Historial de conversaciones
- Exportación/Importación de sesiones

---

## 🤖 Comandos Especiales

### /github - Integración GitHub

```bash
# Hacer checkout de PR y abrir OpenCode
opencode pr <pr-number>

# Verá:
1. Checkout del PR en nuevo branch
2. OpenCode abierto en ese branch
3. Contexto del PR cargado
4. Puedes revisar y comentar el código
```

### /agents - Gestión de Agentes

```bash
# Ver y configurar agentes
opencode agent

# Verá:
1. Lista de agentes disponibles
2. Capacidades de cada agente
3. Configuración de agentes
```

### /mcp - Gestión de Servidores MCP

```bash
# Ver servidores MCP configurados
opencode mcp

# Verás:
1. Lista de servidores MCP activos
2. Herramientas disponibles en cada MCP
3. Estado de conexión
4. Configuración específica
```

### /stats - Estadísticas de Uso

```bash
# Ver estadísticas de tokens y costes
opencode stats

# Verás:
1. Token usage por provider
2. Costes por período
3. Tendencias de uso
4. Estadísticas de velocidad
```

---

## 🎯 Flujo de Trabajo Recomendado (AUTÓNOMO)

### Para Desarrollo de Software

```
1. Abrir OpenCode en el directorio del proyecto
   opencode

2. En la TUI, esperar a que cargue el workspace

3. Planning Mode (si es una tarea compleja)
   - Navegar a la sección de Planning
   - Escribir prompt claro: "Crea un plan para implementar feature X"
   - Revisar el análisis generado
   - Aprobar el plan si es correcto

4. Build Mode (para implementar)
   - Navegar a la sección de Build
   - Verificar que el plan esté cargado
   - Implementar según el plan
   - Monitorear el progreso en la consola TUI
   - Verificar que todos los archivos estén creados correctamente

5. Review Mode (si es necesario)
   - Navegar a la sección de Review
   - Ver cambios propuestos
   - Aprobar o rechazar
   - Solicitar ajustes
```

---

## 📊 Modos Integrados vs Comandos CLI

| Función | Modo TUI | Comando CLI (si existe) | Notas |
|---------|------------|---------------------|-------|
| **Planificación** | Planning Mode (sección en TUI) | `opencode` (abre TUI) | Planificación es integrada en la interfaz |
| **Implementación** | Build Mode (sección en TUI) | `opencode` (abre TUI) | Implementación es integrada en la interfaz |
| **Autenticación** | Config en TUI (/connect) | `opencode /connect` | Configuración es vía TUI |
| **Sesiones** | Sección en TUI | `opencode session` | Gestión es vía TUI |

---

## ⚠️ Conceptos Erróneos Comunes

### ❌ Concepto 1: "Comando --plan separado"
**Error:** Creer que OpenCode tiene un comando `--plan` para separar el modo
**Realidad:** OpenCode tiene Planning y Build Modes integrados en la TUI, no comandos CLI separados

**Uso Correcto:**
- Abrir OpenCode (`opencode`)
- Navegar a la sección de Planning en la TUI
- Escribir prompt de planificación en el chat/buffer
- Dejar que OpenCode genere el plan internamente

### ❌ Concepto 2: "Controlar OpenCode con comandos CLI externos"
**Error:** Intentar automatizar OpenCode usando scripts que simulan entrada de teclado
**Realidad:** OpenCode es una aplicación TUI que debe usarse interactivamente desde tu terminal

**Uso Correcto:**
- Usar OpenCode directamente en la terminal (PTY si es necesario)
- No intentar controlar desde fuera (no es como un script CLI)
- Navegar la TUI naturalmente

### ❌ Concepto 3: "Modelos se seleccionan con flags"
**Error:** Creer que puedes especificar el modelo con `--model <modelo>`
**Realidad:** Los modelos se seleccionan en la TUI o se configuran via `/connect`

**Uso Correcto:**
- Usar la TUI para seleccionar el modelo deseado
- Configurar modelos en `/connect` si lo necesitas
- No intentar forzar modelos desde scripts

---

## 🎯 Recomendaciones Finales para Uso Autónomo

### 1. Abrir OpenCode Naturalmente
```bash
# Ir al directorio del proyecto
cd /home/ubuntu/.openclaw/workspace/QA-FRAMEWORK

# Abrir OpenCode
opencode

# Usar la interfaz TUI para navegar
```

### 2. Dejar que OpenCode Cargue el Workspace

OpenCode necesita tiempo para analizar el proyecto completo. No intentes enviar múltiples prompts rápidos.

### 3. Comunicarse con OpenCode en el Chat/Buffer

En la TUI, hay un área de chat donde puedes escribir prompts y recibir respuestas del modelo AI.

**Ejemplos de prompts efectivos:**

#### Para Planning Mode:
```
Crea un plan detallado para implementar paralelización con pytest-xdist.

El plan debe incluir:
1. Configuración de pytest-xdist en pyproject.toml
2. conftest.py con hooks de paralelización
3. Fixtures thread-safe para recursos compartidos
4. Tests de ejemplo que demuestren paralelización
5. Documentación en README.md
6. Ejemplos de uso: pytest -n auto, pytest -n 4

Aplica Clean Architecture y SOLID principles.
Usa type hints 100% y docstrings Google style.
```

#### Para Build Mode:
```
Implementa el plan que generamos anteriormente.

Según el plan, debes:
1. Actualizar pyproject.toml con las opciones de pytest-xdist
2. Crear conftest.py con la configuración correcta
3. Crear fixtures thread-safe si es necesario
4. Actualizar README.md con la sección de paralelización
5. Crear tests de ejemplo que demuestren el uso
6. Verificar que las configuraciones son correctas
7. Ejecutar los tests para validar la implementación

Asegúrate de seguir Clean Architecture y SOLID principles.
Usa type hints 100% y docstrings Google style.
```

---

## 📋 Comparación: OpenCode vs Codex

| Aspecto | Codex | OpenCode |
|---------|--------|-----------|
| **Formato** | CLI con flags | TUI interactiva |
| **Modos** | `codex plan`, `codex build` | Planning/Build integrados en TUI |
| **Plan** | Exportable | Mantenido en memoria de sesión |
| **Control** | Scripts externos | Uso directo de terminal |
| **Flexibilidad** | Menos flexible | Más flexible y visual |

**Conclusión:**
OpenCode está diseñado como una herramienta interactiva, no como un script CLI. Esto ofrece una mejor experiencia de usuario pero requiere un enfoque diferente para automatización.

---

## 🚀 Uso Práctico para QA-FRAMEWORK

### Escenario 1: Implementar Nueva Feature

```bash
cd /home/ubuntu/.openclaw/workspace/QA-FRAMEWORK

# Abrir OpenCode
opencode

# En Planning Mode:
# 1. Seleccionar modelo gratuito (kimi-k2.5-free)
# 2. Escribir prompt claro de planificación
# 3. Revisar análisis generado
# 4. Aprobar el plan

# En Build Mode:
# 1. Verificar que el plan esté cargado
# 2. Implementar según el plan
# 3. Verificar archivos creados
# 4. Probar la implementación
```

### Escenario 2: Refactorización

```bash
cd /home/ubuntu/.openclaw/workspace/QA-FRAMEWORK

# Abrir OpenCode
opencode

# En Planning Mode:
# "Analiza el módulo src/adapters/http/httpx_client.py y refactorízalo para mejor mantenibilidad"

# En Build Mode:
# Implementar la refactorización
# Verificar que no se rompa nada
```

---

## 🔧 Configuración de Modelos Gratuitos

### Modelos Gratuitos Confirmados (Según Documentación Oficial)

| Modelo OpenCode | Estado | Descripción |
|---------------|--------|------------|
| `opencode/kimi-k2.5-free` | ✅ Disponible | Principal gratuito para desarrollo |
| `opencode/kimi-k2-thinking` | ✅ Disponible | Razonamiento gratuito |
| `opencode/minimax-m2.1-free` | ✅ Disponible | Alternativa gratuita |
| `opencode/kimi-k2.5-thinking` | ✅ Disponible | Razonamiento alternativo |

**Nota:** Algunos modelos gratuitos pueden tener límites de rate o calidad variable comparados con modelos de pago.

---

## 📚 Documentación Oficial

**Fuentes:**
- Documentación principal: https://opencode.ai/docs
- Comandos: https://opencode.ai/docs/commands
- Instalación: https://opencode.ai/docs/install
- Configuración: https://opencode.ai/docs/configure
- Proveedores: https://opencode.ai/docs/providers

---

## 🎯 Conclusión Final

OpenCode es una **aplicación TUI interactiva** con Planning y Build Modes integrados, **NO un script CLI** con flags separados.

**Principios Clave:**
1. ✅ Usar OpenCode directamente en la terminal (con PTY si es necesario)
2. ✅ Navegar la TUI naturalmente
3. ✅ Dejar que OpenCode analice y planifique automáticamente
4. ✅ Escribir prompts claros y detallados en el chat/buffer
5. ✅ Aprobar planes y revisiones en la TUI
6. ✅ No intentar controlar desde fuera con scripts externos
7. ✅ Configurar modelos en `/connect` si es necesario

**Para Uso Autónomo:**
- Abrir OpenCode en el directorio del proyecto
- Usar la TUI para navegar entre Planning y Build Modes
- Comunicarte con el modelo AI en el chat/buffer
- Revisar y aprobar planes e implementaciones
- Dejar que OpenCode trabaje según su diseño original

---

**Última actualización:** 2026-02-11 18:05 UTC  
**Basado en:** Documentación oficial de OpenCode (https://opencode.ai/docs)  
**Autor:** Alfred
