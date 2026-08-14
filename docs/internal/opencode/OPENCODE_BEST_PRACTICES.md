# OpenCode - Configuración Óptima para Agentes Autónomos

**Fecha:** 2026-02-11 15:30 UTC  
**Autor:** Alfred

---

## 🎯 Modelos Configurados (Solo Gratuitos)

### Modelos Primarios de OpenClaw (Disponibles en OpenCode)

| Modelo OpenClaw | Modelo OpenCode | Calidad | Velocidad | Uso Recomendado |
|---------------|----------------|---------|-----------|-----------------|
| `zai/glm-4.7` | `opencode/glm-4.7` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **PRINCIPAL** - Desarrollo |
| `zai/glm-4.7-flash` | `opencode/glm-4.7` (flash) | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **RÁPIDO** - Tareas rápidas |
| `nvidia/moonshotai/kimi-k2.5` | `opencode/kimi-k2.5` | ⭐⭐⭐⭐ | ⭐⭐⭐ | Balanceado |
| `minimax-portal/MiniMax-M2.1` | `opencode/minimax-m2.1` | ⭐⭐⭐ | ⭐⭐⭐⭐ | **GRATIS** - Desarrollo |
| `ollama/huihui_ai/baronllm-abliterated` | `opencode/kimi-k2.5-free` | ⭐⭐⭐ | ⭐⭐⭐ | **GRATIS** - Desarrollo |

### Modelos Alternativos Gratuitos Disponibles en OpenCode

| Modelo | Calidad | Velocidad | Coste | Uso |
|--------|---------|-----------|--------|------|
| `opencode/kimi-k2.5-free` | ⭐⭐⭐ | ⭐⭐⭐ | **GRATIS** | Desarrollo |
| `opencode/kimi-k2.5-thinking` | ⭐⭐⭐ | ⭐⭐⭐ | **GRATIS** | Razonamiento |
| `opencode/kimi-k2-thinking` | ⭐⭐⭐ | ⭐⭐⭐ | **GRATIS** | Razonamiento rápido |
| `opencode/minimax-m2.1-free` | ⭐⭐⭐ | ⭐⭐⭐ | **GRATIS** | Desarrollo |

---

## 🚀 Configuración de Agentes (Best Practices)

### 1. Permisos de Agentes

```bash
# Ver permisos actuales
opencode agent list

# Configurar permisos para build (primary)
# - Permitir plan/exit para que pueda completar planes
# - Permitir edición de archivos necesarios
# - Permitir external_directories para output
```

### 2. Permisos Óptimos por Tipo de Agente

#### **build (Primary)**
```json
{
  "permissions": {
    "*": "allow",                    // Permitir todo por defecto
    "plan_exit": "allow",              // Permitir salir de plan
    "question": "allow"                 // Permitir preguntas
  }
}
```

#### **explore (Subagent)**
```json
{
  "permissions": {
    "*": "allow",                    // Permitir todo
    "plan_exit": "allow",              // Permitir salir de plan
    "grep": "allow",                   // Permitir grep
    "glob": "allow",                   // Permitir glob
    "list": "allow",                   // Permitir list
    "bash": "allow",                   // Permitir bash
    "webfetch": "allow",                // Permitir webfetch
    "websearch": "allow",               // Permitir websearch
    "codesearch": "allow",              // Permitir codesearch
    "question": "deny"                  // Bloquear preguntas automáticas
  }
}
```

#### **general (Subagent)**
```json
{
  "permissions": {
    "*": "allow",                    // Permitir todo
    "plan_exit": "allow",              // Permitir salir de plan
    "question": "deny",                 // Bloquear preguntas
    "todoread": "deny",                // Bloquear lectura de todos
    "todowrite": "deny",               // Bloquear escritura en todos
  }
}
```

---

## 🔧 Configuración de Skills

### Skills Disponibles en OpenClaw

Los skills de OpenClaw se pueden integrar con OpenCode mediante MCPs.

### Skills Configurados

Debido a que no tenemos la versión de pago de Zen, usaremos los skills instalados localmente.

---

## 🔌 Configuración de MCPs (Model Context Protocol)

### MCPs Configurados en OpenClaw

```bash
# Listar MCPs disponibles
mcporter list
```

### MCPs Activos

1. **tavily** (5 tools) - Búsqueda web mejorada
2. **deepwiki** (3 tools) - Consulta de código/docs
3. **memory** (9 tools) - Sistema de memoria semántica
4. **filesystem** (14 tools) - Operaciones de sistema de archivos
5. **playwright** (33 tools) - Automatización de navegador

### Configuración MCP para OpenCode

OpenCode puede usar MCPs integrados. Para habilitar MCPs:

```bash
# Configurar MCPs en OpenCode
opencode mcp list

# Agregar MCP específico
opencode mcp add <mcp-name>
```

---

## 📚 Configuración de Spec-Kit

Spec-Kit permite especificar especificaciones y requerimientos para el desarrollo.

### Usar Spec-Kit en OpenCode

```bash
# Ejemplo de uso con spec
opencode run --spec my-spec.md "Implementa esta feature"
```

### Estructura de Spec

```markdown
# Feature: User Authentication

## Requirements
- Users must be able to login with email/password
- Passwords must be hashed
- Session management required
- Rate limiting on login attempts

## Technical Stack
- Backend: Python + FastAPI
- Database: PostgreSQL
- Auth: JWT tokens
- Password: bcrypt

## Acceptance Criteria
- Given valid credentials, login succeeds
- Given invalid credentials, login fails with error
- After 5 failed attempts, account locked for 15min
- Passwords are not stored in plain text
```

---

## 🎯 Configuración para Creación Autónoma de Skills

OpenCode puede crear skills de forma autónoma si tiene los permisos correctos.

### Permisos Necesarios para Crear Skills

```json
{
  "permissions": {
    "bash": "allow",                  // Permitir ejecución de comandos
    "read": "allow",                   // Permitir lectura de archivos
    "edit": "allow",                   // Permitir edición de archivos
    "external_directory": "allow",      // Permitir acceso a directorios externos
    "codesearch": "allow",             // Permitir búsqueda de código
    "websearch": "allow",               // Permitir búsqueda web
    "webfetch": "allow"                 // Permitir fetch de web
  }
}
```

### Proceso de Creación de Skills

1. **Solicitar especificación** del skill
2. **Analizar requisitos** del skill
3. **Generar código** del skill
4. **Crear estructura** de directorios
5. **Implementar SKILL.md** con documentación
6. **Implementar scripts** necesarios
7. **Añadir metadata** (metadata.openclaw)
8. **Validar** el skill
9. **Instalar/Registrar** el skill

---

## 🚀 Ejemplos de Uso Autónomo

### Ejemplo 1: Crear Skill Nuevo

```bash
# Solicitar a OpenCode crear un skill
opencode run -m opencode/kimi-k2.5-free "Crea un nuevo skill para automatizar backups de bases de datos MySQL.

El skill debe:
1. Listar todas las bases de datos
2. Realizar backup de cada base
3. Comprimir los backups
4. Guardar en directorio con timestamp
5. Limpiar backups antiguos (>7 días)

Usa SOLID principles, type hints 100%, docstrings Google style.
Crea estructura completa de skill con SKILL.md y scripts."

# Permisos necesarios:
# - bash: allow
# - read: allow
# - edit: allow
# - websearch: allow (para buscar mejores prácticas)
```

### Ejemplo 2: Configurar MCP Nuevo

```bash
# Solicitar a OpenCode configurar MCP
opencode run -m opencode/glm-4.7 "Configura el servidor MCP de GitHub para poder acceder a repositorios y hacer PRs.

Usa mcporter para:
1. Autenticar con GitHub PAT
2. Listar repositorios disponibles
3. Crear ejemplo de uso

Documenta el proceso en OPENCODE_MCP_SETUP.md"
```

### Ejemplo 3: Crear Subagentes

```bash
# Solicitar a OpenCode crear configuración de subagentes
opencode run -m opencode/glm-4.7-flash "Crea una configuración óptima de subagentes para OpenCode.

La configuración debe incluir:
1. explore agent: para investigación y descubrimiento
2. general agent: para tareas genéricas
3. plan agent: para planificación
4. summary agent: para resúmenes

Cada subagent debe tener permisos óptimos para su rol.
Guarda la configuración en OPENCORE_SUBAGENTS_CONFIG.md"
```

---

## 📊 Matriz de Decisiones por Tipo de Tarea

| Tarea | Modelo | Subagent | MCPs | Permisos |
|--------|---------|----------|----------|
| **Crear Skill** | `opencode/kimi-k2.5-free` | No necesarios | edit, bash, read |
| **Configurar MCP** | `opencode/glm-4.7` | mcporter | edit, bash, websearch |
| **Desarrollo** | `opencode/glm-4.7` | filesystem, memory | edit, read, bash |
| **Investigación** | `opencode/glm-4.7-flash` | tavily, webfetch | websearch, grep, glob |
| **Planificación** | `opencode/glm-4.7` | memory | plan_exit, question |
| **Refactorización** | `opencode/kimi-k2.5-free` | codesearch, filesystem | edit, read, codesearch |

---

## 🎯 Recomendaciones Finales

### 1. Modelos Gratuitos
- **PRINCIPAL:** `opencode/glm-4.7` (desarrollo general)
- **RÁPIDO:** `opencode/kimi-k2.5-free` (tareas rápidas)
- **ALTERNATIVAS:** `opencode/minimax-m2.1-free`, `opencode/kimi-k2.5-thinking`

### 2. Permisos de Agentes
- **Primary (build):** Permisos completos, permitir plan_exit
- **Subagentes:** Especializados según función, bloquear question
- **Crear skills:** Permisos de edición, bash, websearch

### 3. MCPs
- **Activos:** tavily, deepwiki, memory, filesystem, playwright
- **Gestión:** Usar mcporter para configurar
- **Estrategia:** Activar según necesidad de tarea

### 4. Skills
- **Creación autónoma:** Permisos de edit, bash, websearch necesarios
- **Proceso:** Especificación → Análisis → Código → Documentación → Validación
- **Instalación:** Requiere permisos de bash y edición

### 5. Spec-Kit
- **Uso:** Para especificaciones detalladas de features
- **Formato:** Markdown con requirements, stack, criteria
- **Comando:** `opencode run --spec spec.md "prompt"`

---

## 🔧 Comandos Útiles

### Gestión de Modelos
```bash
# Listar todos los modelos
opencode models

# Usar modelo específico
opencode -m opencode/glm-4.7 "tu prompt"

# Usar modelo gratuito
opencode -m opencode/kimi-k2.5-free "tu prompt"
```

### Gestión de Agentes
```bash
# Listar agentes y permisos
opencode agent list

# Ver configuración específica
opencode agent get <agent-name>
```

### Gestión de MCPs
```bash
# Listar MCPs
opencode mcp list

# Autenticar MCP
mcporter auth <mcp-name>

# Llamar herramienta MCP
mcporter call <mcp-name> <tool-name>
```

### Creación de Skills
```bash
# Solicitar creación de skill
opencode run "Crea un skill para [descripción]"

# Con modelo gratuito
opencode -m opencode/kimi-k2.5-free "Crea un skill para [descripción]"
```

---

**Actualizado:** 2026-02-11 15:35 UTC  
**Modelos gratuitos configurados:** 5+ modelos  
**Mejores prácticas aplicadas:** Agentes, Subagentes, Skills, MCPs, Spec-Kit
