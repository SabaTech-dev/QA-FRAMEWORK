# 🧪 Onboarding para Beta Testers — QA Framework

Bienvenido al programa beta de **QA Framework** de SabaTech. Esta guía te llevará desde cero hasta tu primer ciclo de testing.

---

## 1. Acceso al Dashboard

| Recurso | URL |
|---------|-----|
| Dashboard (Frontend) | https://qa.sabatech.dev |
| API Docs (OpenAPI) | https://qa.sabatech.dev/api/docs |
| Health Check | https://qa.sabatech.dev/api/health |

> **Estado actual:** ⚠️ El dashboard puede experimentar intermitencias (HTTP 502) durante la fase beta. Si no puedes acceder, espera 5 minutos e inténtalo de nuevo.

### Requisitos
- Navegador moderno (Chrome 120+, Firefox 120+, Safari 17+, Edge 120+)
- Conexión a internet estable
- JavaScript habilitado

---

## 2. Credenciales de Acceso

### Cuenta de Prueba Demo
Para acceso inmediato durante la beta, puedes usar la cuenta demo:

| Campo | Valor |
|-------|-------|
| Email | `beta-tester@sabatech.dev` |
| Password | `BetaTest2026!` |

> ⚠️ **Esta cuenta es de solo lectura.** No puede modificar configuraciones ni ejecutar acciones destructivas.

### Solicitar Cuenta Personal
Si necesitas una cuenta con permisos adicionales o quieres probar funcionalidades específicas:

1. Abre un issue en [GitHub](https://github.com/SabaTech-dev/QA-FRAMEWORK/issues/new)
2. Usa el template **"Beta Access Request"** (si disponible) o el label `beta-access`
3. Incluye: tu nombre, caso de uso principal, y permisos que necesitas
4. Tiempo de respuesta estimado: **24-48h hábiles**

---

## 3. Casos de Uso Principales a Testear

### 🔍 Prioridad Alta (Core Features)

#### 3.1 Dashboard de Monitoreo
- [ ] Visualizar métricas en tiempo real (latencia, throughput, error rate)
- [ ] Cambiar el rango de tiempo (1h, 24h, 7d, 30d)
- [ ] Filtrar por servicio o endpoint
- [ ] Exportar datos en CSV

#### 3.2 Gestión de Test Suites
- [ ] Crear una nueva test suite
- [ ] Ejecutar una suite existente
- [ ] Ver resultados detallados (pasados, fallidos, omitidos)
- [ ] Filtrar resultados por severidad

#### 3.3 Alertas y Notificaciones
- [ ] Configurar una alerta nueva
- [ ] Verificar que las alertas se disparan correctamente
- [ ] Configurar canales de notificación (email, webhook)

### 🧩 Prioridad Media

#### 3.4 Reportes
- [ ] Generar reporte HTML de una ejecución
- [ ] Comparar resultados entre dos ejecuciones
- [ ] Descargar histórico de reportes

#### 3.5 API Endpoints
- [ ] Probar autenticación vía API token
- [ ] Listar proyectos vía `GET /api/v1/projects`
- [ ] Crear un proyecto vía `POST /api/v1/projects`
- [ ] Ejecutar tests vía `POST /api/v1/suites/{id}/run`

### 🎯 Prioridad Baja (Nice-to-have)

#### 3.6 Integraciones
- [ ] Conectar con Slack
- [ ] Conectar con Jira
- [ ] Webhooks personalizados

---

## 4. Cómo Reportar Bugs

### Antes de Reportar
1. **Busca issues existentes** en [GitHub Issues](https://github.com/SabaTech-dev/QA-FRAMEWORK/issues) para evitar duplicados
2. **Reproduce el bug** al menos 2 veces para confirmar que no es transitorio
3. **Anota los pasos exactos** que seguiste

### Crear un Issue

Ve a: [https://github.com/SabaTech-dev/QA-FRAMEWORK/issues/new](https://github.com/SabaTech-dev/QA-FRAMEWORK/issues/new)

#### Información Obligatoria
Incluye siempre:

```
**Descripción del bug**
Descripción clara y concisa del problema.

**Pasos para reproducir**
1. Ir a '...'
2. Click en '...'
3. Ver error

**Comportamiento esperado**
Qué esperabas que pasara.

**Comportamiento actual**
Qué pasó realmente.

**Entorno**
- OS: [ej. macOS Sonoma 14.5]
- Navegador: [ej. Chrome 125]
- Tipo de cuenta: [demo / personal]
- URL donde ocurrió: [ej. https://qa.sabatech.dev/dashboard]

**Screenshots / Logs**
Adjunta capturas de pantalla o logs relevantes.
```

#### Labels Sugeridos
- `bug` — para cualquier mal funcionamiento
- `ui/ux` — para problemas visuales o de usabilidad
- `performance` — para lentitud o cuelgues
- `beta` — para issues específicos de la versión beta

### Severidad
Usa esta escala al describir la severidad:

| Nivel | Descripción | Ejemplo |
|-------|-------------|---------|
| 🔴 Crítica | Servicio inutilizable | Dashboard no carga |
| 🟠 Alta | Función principal rota | No se pueden ejecutar tests |
| 🟡 Media | Función secundaria con workaround | Filtros no funcionan pero datos sí cargan |
| 🟢 Baja | Cosmético o menor | Texto mal alineado |

---

## 5. FAQ

### ❓ ¿El dashboard está caído?
Verifica primero en [https://qa.sabatech.dev/api/health](https://qa.sabatech.dev/api/health). Si responde `{"status":"healthy"}`, el backend está bien pero puede haber un problema con el frontend. Si también falla, espera 5-10 min (puede estar reiniciándose).

### ❓ ¿Puedo usar mis propios datos de prueba?
Sí. La cuenta demo tiene un entorno aislado (sandbox). Puedes crear proyectos, suites y ejecuciones sin afectar a otros testers.

### ❓ ¿Cada cuánto se reinicia el servicio?
Los servicios se reinician automáticamente si detectan problemas de salud. No hay ventana de mantenimiento programada durante la beta.

### ❓ ¿Cómo sé si una funcionalidad está rota o es una limitación de la beta?
Consulta el [changelog de la beta](https://github.com/SabaTech-dev/QA-FRAMEWORK/blob/main/CHANGELOG.md). Las limitaciones conocidas están listadas ahí.

### ❓ ¿Puedo sugerir nuevas funcionalidades?
¡Por supuesto! Abre un issue con el label `enhancement` o `feature-request`. Valoramos mucho tu feedback.

### ❓ ¿Qué pasa con mis datos cuando termine la beta?
Todos los datos del entorno beta serán eliminados al final del programa. Haz backup de cualquier configuración que quieras conservar.

### ❓ ¿Cómo contacto al equipo directamente?
- **GitHub Issues**: [Crear issue](https://github.com/SabaTech-dev/QA-FRAMEWORK/issues/new) — preferido para bugs técnicos
- **Email**: `devops@sabatech.dev` — para temas de acceso o privados
- **Discord/Slack**: Canal `#qa-framework-beta` (si estás en el workspace)

---

## 6. Próximos Pasos

1. ✅ Lee esta guía completa
2. ✅ Accede al dashboard con la cuenta demo
3. ✅ Explora las funcionalidades de prioridad alta
4. ✅ Reporta cualquier bug o mejora
5. ✅ Únete al canal de feedback

¡Gracias por ayudar a mejorar QA Framework! 🚀

---

*Última actualización: 2026-07-02*
