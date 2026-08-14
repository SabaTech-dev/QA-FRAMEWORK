# OpenCode - Resolución de Problemas de Autonomía

**Fecha:** 2026-02-11 18:00 UTC  
**Autor:** Alfred

---

## 🐛 **Problemas Identificados**

### Problema 1: API Key Requerida
**Síntoma:** OpenCode requiere API key de pago para ciertos modelos  
**Causa:** Configuración en `~/.local/share/opencode/auth.json`  
**Estado:** Modelo configurado requiere pago

### Problema 2: Modo PLAN no Explícito
**Síntoma:** OpenCode no tiene modo `--plan` separado  
**Causa:** Planificación ocurre internamente en el modo TUI  
**Efecto:** Usuario no puede controlar cuándo OpenCode planifica vs construye

---

## 🔍 **Análisis de Modos**

### Modos Reales de OpenCode (TUI)

Basado en la documentación, OpenCode tiene:

1. **Modo TUI Principal**
   - Comando: `opencode`
   - Funcionalidad: Análisis + Planificación + Construcción en un flujo continuo
   - Modos internos:
     - **Planning Mode** - Análisis y creación de plan
     - **Build Mode** - Implementación según el plan
     - **Review Mode** - Revisión de código

2. **Modo de Comando `--prompt`**
   - Comando: `opencode --prompt "tu prompt"`
   - Funcionalidad: Ejecución directa sin pasar por modo planning

3. **Comando `--continue`**
   - Comando: `opencode --continue`
   - Funcionalidad: Continuar sesión anterior

4. **Configuración de Sesiones**
   - Comando: `opencode --session <id>`
   - Funcionalidad: Continuar sesión específica

---

## ✅ **Soluciones Aprobadas**

### Solución 1: Flujo TUI en Modo Planning

**Enfoque Correcto:**

En lugar de intentar ejecutar comandos específicos, usar el flujo natural de la TUI:

```
1. Abrir OpenCode en modo TUI
   opencode

2. En la TUI, seleccionar el modo deseado:
   - Planning Mode → Para crear planes
   - Build Mode → Para implementar

3. El modelo se selecciona en la TUI
   - Si el modelo requiere pago, aparecerá un aviso
   - Si el modelo es gratuito, funcionará correctamente

4. Enviar el prompt y dejar que OpenCode trabaje
   - OpenCode analizará, planificará y luego implementará
```

### Solución 2: Uso de Modelos Gratuitos

**Modelos Gratuitos Confirmados:**

| Modelo OpenCode | Tipo | Uso |
|---------------|------|------|
| `opencode/kimi-k2.5-free` | Chat Gratis | Preguntas rápidas, tareas simples |
| `opencode/minimax-m2.1-free` | Chat Gratis | Desarrollo básico |
| `opencode/kimi-k2-thinking` | Razonamiento Gratis | Análisis y diseño |
| `opencode/kimi-k2.5-free` | Balanceado Gratis | Desarrollo balanceado |

**Recomendación:**
Para autar que el modelo gratuito funcione, no forzar un modelo específico en la línea de comandos. Dejar que OpenCode use el modelo configurado por defecto.

---

## 🎯 **Workflow Recomendado para Autonomía**

### Opción A: Modo TUI Natural (Recomendado)

```bash
# 1. Abrir OpenCode en modo TUI
cd /home/ubuntu/.openclaw/workspace/QA-FRAMEWORK
opencode

# 2. En la TUI:
# - Esperar que cargue la interfaz
# - Seleccionar modelo gratuito (Kimi-k2.5-free, por ejemplo)
# - La interfaz detectará automáticamente el modo
# - Para tareas complejas, dejar que entre en "Planning Mode"
# - Para tareas simples, puede ir directo a implementación

# 3. Escribir el prompt en la interfaz
# - Dejar que OpenCode procese naturalmente
```

### Opción B: Comando Directo (Alternativa)

Si necesitas ejecución inmediata sin pasar por modo planning:

```bash
# Ejecutar directamente con prompt
opencode --prompt "Implementa X inmediatamente"

# Usar el modelo configurado por defecto
# OpenCode procesará en modo build sin planning explícito
```

---

## 📋 **Checklist para Uso Autónomo**

### ✅ **Configuración**
- [ ] Verificar que modelos gratuitos funcionan
- [ ] Usar flujo TUI natural
- [ ] No forzar modelos específicos que requieran pago
- [ ] Dejar que OpenCode gestione el modo automáticamente

### ✅ **Modos**
- [ ] Usar modo TUI para tareas complejas (Planning Mode)
- [ ] Usar modo build para implementación rápida
- [ ] Aprovechar los modos internos de OpenCode

### ✅ **Autonomía**
- [ ] Aceptar que OpenCode gestione el flujo de trabajo
- [ ] Revisar planes generados por OpenCode
- [ ] Aprobar o ajustar antes de implementar
- [ ] Monitorear el progreso en la TUI

---

## 🎯 **Estrategia Final**

**Principio Clave:** OpenCode está diseñado como una herramienta interactiva TUI, no como un script de línea de comandos.

**Enfoque Correcto:**
1. Usar la interfaz TUI naturalmente
2. Dejar que OpenCode gestione los modos internamente
3. Aprovechar las capacidades de planificación automática
4. Verificar que los modelos gratuitos estén disponibles en la TUI

**Prohibido:**
1. Intentar controlar OpenCode desde fuera de su interfaz
2. Forzar modelos o modos que no se correspondan a su interfaz
3. Reescribir la configuración interna de OpenCode

---

## 📚 **Recursos Consultados**

- Documentación oficial de OpenCode (si está disponible)
- Configuración en `~/.local/share/opencode/`
- Modelos disponibles en `opencode models`

---

**Actualizado:** 2026-02-11 18:00 UTC  
**Enfoque:** Uso correcto de la interfaz TUI de OpenCode  
**Recomendación:** Aceptar el flujo de trabajo natural de OpenCode en lugar de intentar controlarlo externamente
