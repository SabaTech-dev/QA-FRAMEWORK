# OpenCode - Guía de Modelos y Uso Óptimo

**Fecha:** 2026-02-11 07:50 UTC  
**Autor:** Alfred

---

## 🎯 Clasificación de Modelos por Tipo de Tarea

### 🚀 **1. Tareas de Codificación (Coding/Development)**

**PRINCIPALES (Mejor calidad/velocidad)**

| Modelo | Calidad | Velocidad | Coste | Uso Recomendado |
|--------|---------|-----------|--------|-----------------|
| `openai/gpt-5.2-codex` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Medio | **PRINCIPAL** - Desarrollo, refactorización |
| `openai/gpt-5.1-codex` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Medio-Bajo | Desarrollo rápido, buen balance |
| `openai/gpt-5.3-codex` | ⭐⭐⭐⭐⭐ | ⭐⭐ | Medio-Alto | Código complejo, arquitectura |
| `openai/gpt-5.1-codex-max` | ⭐⭐⭐⭐⭐ | ⭐⭐ | Alto | Proyectos grandes, refactorización |
| `openai/codex-mini-latest` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Muy Bajo | Quick fixes, snippets pequeños |

**Modelos alternativos:**
- `opencode/gpt-5-codex` - Opción de OpenCode
- `openai/gpt-5.1-codex-mini` - Versión mini de Codex

---

### 💬 **2. Chat/Conversación General**

**MEJORES (Calidad + Coste)**

| Modelo | Calidad | Velocidad | Coste | Uso Recomendado |
|--------|---------|-----------|--------|-----------------|
| `openai/gpt-5.1-chat-latest` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Medio | **PRINCIPAL** - Chat general |
| `openai/gpt-5.2-chat-latest` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Medio-Alto | Chat de alta calidad |
| `openai/gpt-4o` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Medio-Bajo | Chat rápido y balanceado |
| `openai/gpt-4o-mini` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Muy Bajo | Chat muy rápido |
| `opencode/claude-sonnet-4-5` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Medio | Alternativa de alta calidad |

**Modelos alternativos:**
- `opencode/glm-4.7` - Buen balance
- `opencode/gemini-3-pro` - Opción de Google

---

### 🧠 **3. Razonamiento Complejo (Complex Reasoning)**

**MEJORES (Deep Thinking)**

| Modelo | Calidad | Velocidad | Coste | Uso Recomendado |
|--------|---------|-----------|--------|-----------------|
| `openai/o3-deep-research` | ⭐⭐⭐⭐⭐ | ⭐ | Muy Alto | **PRINCIPAL** - Investigación profunda |
| `openai/o3-pro` | ⭐⭐⭐⭐⭐ | ⭐ | Alto | Razonamiento complejo |
| `openai/o3` | ⭐⭐⭐⭐⭐ | ⭐⭐ | Alto | Tareas difíciles |
| `openai/o1-pro` | ⭐⭐⭐⭐⭐ | ⭐⭐ | Alto | Problemas complejos |
| `openai/o4-mini-deep-research` | ⭐⭐⭐⭐⭐ | ⭐⭐ | Alto | Deep research balanceado |

**Cuándo usar:**
- Diseño de arquitectura
- Resolución de bugs complejos
- Análisis de código legacy
- Investigación técnica

---

### ⚡ **4. Respuestas Rápidas (Fast/Quick)**

**MEJORES (Velocidad + Coste)**

| Modelo | Calidad | Velocidad | Coste | Uso Recomendado |
|--------|---------|-----------|--------|-----------------|
| `openai/gpt-4o-mini` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Muy Bajo | **PRINCIPAL** - Respuestas rápidas |
| `openai/gpt-5-nano` | ⭐⭐ | ⭐⭐⭐⭐⭐ | Muy Bajo | Respuestas ultrarrápidas |
| `openai/gpt-4.1-nano` | ⭐⭐ | ⭐⭐⭐⭐⭐ | Muy Bajo | Queries simples |
| `openai/gpt-5-mini` | ⭐⭐⭐ | ⭐⭐⭐⭐ | Muy Bajo | Respuestas rápidas |
| `opencode/gemini-3-flash` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Muy Bajo | Flash responses |

**Cuándo usar:**
- Preguntas simples
- Aclaraciones rápidas
- Tests unitarios simples
- Snippets de código pequeños

---

### 🔍 **5. Razonamiento Profundo (Deep Thinking Models)**

**SERIES "o" (OpenAI o-Series)**

| Modelo | Calidad | Velocidad | Coste | Especialidad |
|--------|---------|-----------|--------|--------------|
| `openai/o4-mini` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Medio | Deep thinking rápido |
| `openai/o4-mini-deep-research` | ⭐⭐⭐⭐⭐ | ⭐⭐ | Alto | Investigación profunda |
| `openai/o3` | ⭐⭐⭐⭐⭐ | ⭐⭐ | Alto | Razonamiento complejo |
| `openai/o3-mini` | ⭐⭐⭐⭐ | ⭐⭐⭐ | Medio-Bajo | Deep thinking rápido |
| `openai/o3-pro` | ⭐⭐⭐⭐⭐ | ⭐ | Alto | Razonamiento experto |
| `openai/o3-deep-research` | ⭐⭐⭐⭐⭐ | ⭐ | Muy Alto | Investigación exhaustiva |
| `openai/o1` | ⭐⭐⭐⭐ | ⭐⭐ | Medio | Razonamiento balanceado |
| `openai/o1-mini` | ⭐⭐⭐ | ⭐⭐⭐ | Medio-Bajo | Razonamiento rápido |
| `openai/o1-pro` | ⭐⭐⭐⭐ | ⭐ | Alto | Problemas difíciles |

**Cuándo usar:**
- Diseño de arquitectura de sistemas
- Optimización de algoritmos
- Análisis de seguridad
- Resolución de bugs complejos

---

### 🤖 **6. Modelos Claude (Anthropic)**

**SERIES CLAUDE**

| Modelo | Calidad | Velocidad | Coste | Uso Recomendado |
|--------|---------|-----------|--------|-----------------|
| `opencode/claude-opus-4-6` | ⭐⭐⭐⭐⭐ | ⭐⭐ | Medio-Alto | **TOP** - Alta calidad |
| `opencode/claude-opus-4-5` | ⭐⭐⭐⭐⭐ | ⭐⭐ | Medio-Alto | Alta calidad |
| `opencode/claude-sonnet-4-5` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Medio | **PRINCIPAL** - Balanceado |
| `opencode/claude-3-5-haiku` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Muy Bajo | Respuestas rápidas |
| `opencode/claude-haiku-4-5` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Muy Bajo | Queries simples |
| `opencode/claude-opus-4-1` | ⭐⭐⭐⭐ | ⭐⭐ | Medio | Alta calidad (versión anterior) |

**Ventajas de Claude:**
- Buen para análisis de código
- Excelente para documentación
- Respuestas bien estructuradas
- Alternativa a GPT

---

### 🔧 **7. Modelos GLM (Zhipu AI)**

**SERIES GLM**

| Modelo | Calidad | Velocidad | Coste | Uso Recomendado |
|--------|---------|-----------|--------|-----------------|
| `opencode/glm-4.7` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Bajo | **PRINCIPAL** - Desarrollo |
| `opencode/glm-4.6` | ⭐⭐⭐ | ⭐⭐⭐⭐ | Muy Bajo | Desarrollo rápido |
| `opencode/glm-4.7` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Bajo | Versión más reciente |

**Ventajas de GLM:**
- Coste muy bajo
- Bueno para código
- Alternativa a GPT

---

### 🌐 **8. Modelos Gemini (Google)**

**SERIES GEMINI**

| Modelo | Calidad | Velocidad | Coste | Uso Recomendado |
|--------|---------|-----------|--------|-----------------|
| `opencode/gemini-3-pro` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Bajo | **PRINCIPAL** - Desarrollo |
| `opencode/gemini-3-flash` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Muy Bajo | Respuestas rápidas |

**Ventajas de Gemini:**
- Bueno para código
- Coste bajo
- Alternativa a GPT/Claude

---

### 🧮 **9. Modelos Kimi (Moonshot AI)**

**SERIES KIMI**

| Modelo | Calidad | Velocidad | Coste | Uso Recomendado |
|--------|---------|-----------|--------|-----------------|
| `opencode/kimi-k2.5-free` | ⭐⭐⭐ | ⭐⭐⭐ | **GRATIS** | **GRATIS** - Desarrollo |
| `opencode/kimi-k2.5` | ⭐⭐⭐ | ⭐⭐⭐ | Bajo | Desarrollo |
| `opencode/kimi-k2.5-thinking` | ⭐⭐⭐⭐ | ⭐⭐ | Medio-Bajo | Razonamiento |
| `opencode/kimi-k2` | ⭐⭐⭐ | ⭐⭐⭐ | Muy Bajo | Desarrollo rápido |
| `opencode/kimi-k2-thinking` | ⭐⭐⭐ | ⭐⭐ | Muy Bajo | Razonamiento rápido |

**Ventajas de Kimi:**
- Versión gratuita disponible
- Bueno para código
- Coste muy bajo

---

### 🎯 **10. Modelos MiniMax**

**SERIES MINIMAX**

| Modelo | Calidad | Velocidad | Coste | Uso Recomendado |
|--------|---------|-----------|--------|-----------------|
| `opencode/minimax-m2.1-free` | ⭐⭐⭐ | ⭐⭐⭐ | **GRATIS** | **GRATIS** - Desarrollo |
| `opencode/minimax-m2.1` | ⭐⭐⭐ | ⭐⭐⭐ | Bajo | Desarrollo |

**Ventajas de MiniMax:**
- Versión gratuita
- Coste muy bajo
- Alternativa gratuita

---

### 🔤 **11. Embeddings (Vector Search)**

**MODELOS DE EMBEDDINGS**

| Modelo | Uso | Dimensiones | Coste |
|--------|------|-------------|--------|
| `openai/text-embedding-3-large` | **PRINCIPAL** | 3072 | Medio |
| `openai/text-embedding-3-small` | Embeddings rápidos | 1536 | Muy Bajo |
| `openai/text-embedding-ada-002` | Legacy embeddings | 1536 | Bajo |

**Cuándo usar:**
- Búsqueda semántica
- Recomendaciones
- Clustering de texto
- RAG (Retrieval Augmented Generation)

---

## 🎯 **Guía de Selección por Tipo de Tarea**

### 📝 **Tarea: Escribir Código / Desarrollo**

**Opción Principal:**
```bash
# Alta calidad, buen coste
opencode -m openai/gpt-5.2-codex "Tu prompt"
```

**Alternativas:**
```bash
# Más rápido
opencode -m openai/gpt-5.1-codex "Tu prompt"

# Código complejo
opencode -m openai/gpt-5.3-codex "Tu prompt"

# Muy rápido (baja calidad)
opencode -m openai/codex-mini-latest "Tu prompt"
```

---

### 💬 **Tarea: Chat / Consultas Generales**

**Opción Principal:**
```bash
# Alta calidad, buena velocidad
opencode -m openai/gpt-5.1-chat-latest "Tu pregunta"
```

**Alternativas:**
```bash
# Más rápido
opencode -m openai/gpt-4o-mini "Tu pregunta"

# Rápido y gratuito
opencode -m opencode/kimi-k2.5-free "Tu pregunta"
```

---

### 🧠 **Tarea: Razonamiento Complejo / Arquitectura**

**Opción Principal:**
```bash
# Deep research
opencode -m openai/o3-deep-research "Tu prompt"
```

**Alternativas:**
```bash
# Razonamiento complejo
opencode -m openai/o3-pro "Tu prompt"

# Balanceado
opencode -m openai/o3 "Tu prompt"
```

---

### ⚡ **Tarea: Respuestas Rápidas / Snippets**

**Opción Principal:**
```bash
# Muy rápido, bajo coste
opencode -m openai/gpt-4o-mini "Tu prompt"
```

**Alternativas:**
```bash
# Ultrarrápido
opencode -m openai/gpt-5-nano "Tu prompt"

# Gratuito
opencode -m opencode/gemini-3-flash "Tu prompt"
```

---

### 🔧 **Tarea: Análisis de Código / Refactorización**

**Opción Principal:**
```bash
# Alta calidad para análisis
opencode -m opencode/claude-opus-4-6 "Analiza este código"
```

**Alternativas:**
```bash
# Desarrollo con Claude
opencode -m opencode/claude-sonnet-4-5 "Refactoriza este código"

# Codex para refactorización
opencode -m openai/gpt-5.1-codex-max "Optimiza este código"
```

---

### 🆓 **Tarea: Desarrollo con Modelo Gratuito**

**Opción Principal:**
```bash
# Mejor modelo gratuito
opencode -m opencode/kimi-k2.5-free "Tu prompt"
```

**Alternativas:**
```bash
# Alternativa gratuita
opencode -m opencode/minimax-m2.1-free "Tu prompt"
```

---

## 📊 **Matriz de Decisión Rápida**

| Tarea | Modelo Principal | Alternativa 1 | Alternativa 2 |
|--------|----------------|---------------|---------------|
| **Codificación** | `openai/gpt-5.2-codex` | `openai/gpt-5.1-codex` | `opencode/claude-sonnet-4-5` |
| **Chat General** | `openai/gpt-5.1-chat-latest` | `openai/gpt-4o-mini` | `opencode/glm-4.7` |
| **Razonamiento** | `openai/o3-deep-research` | `openai/o3-pro` | `openai/o1-pro` |
| **Resp. Rápidas** | `openai/gpt-4o-mini` | `openai/gpt-5-nano` | `opencode/gemini-3-flash` |
| **Análisis Código** | `opencode/claude-opus-4-6` | `opencode/claude-sonnet-4-5` | `openai/gpt-5.2-codex` |
| **Gratuito** | `opencode/kimi-k2.5-free` | `opencode/minimax-m2.1-free` | `opencode/glm-4.7` |

---

## 🎯 **Recomendaciones Finales**

### Para Uso Cotidiano (Balance Calidad/Coste)
```bash
# Codificación
opencode -m openai/gpt-5.2-codex "prompt"

# Chat
opencode -m openai/gpt-5.1-chat-latest "pregunta"
```

### Para Desarrollo Rápido (Velocidad)
```bash
# Respuestas rápidas
opencode -m openai/gpt-4o-mini "prompt"
```

### Para Tareas Complejas (Calidad)
```bash
# Razonamiento profundo
opencode -m openai/o3-deep-research "prompt complejo"
```

### Para Desarrollo Gratuito
```bash
# Modelo gratuito
opencode -m opencode/kimi-k2.5-free "prompt"
```

---

## 📝 **Notas Importantes**

1. **Codex** (`*-codex`) está optimizado para tareas de programación
2. **o-series** (`o1`, `o3`, `o4`) están optimizados para razonamiento profundo
3. **Mini models** (`*mini`, `*nano`) son muy rápidos pero de menor calidad
4. **Claude** es excelente para análisis de código y documentación
5. **Kimi-free** y **Minimax-free** son las mejores opciones gratuitas
6. **GPT-5.2-codex** es el mejor balance calidad/coste para desarrollo

---

**Actualizado:** 2026-02-11 07:55 UTC  
**Modelos clasificados:** 60+ modelos de OpenCode
