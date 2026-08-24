# QA-Framework Dashboard Monitoring & Alerting System

Sistema completo de monitoreo y alertas para el QA-Framework Dashboard utilizando Prometheus, Grafana y Alertmanager.

## Arquitectura

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Application   │────▶│   Prometheus    │────▶│     Grafana     │
│   (FastAPI)     │     │   (Metrics)     │     │ (Visualization) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │
         │              ┌────────▼────────┐
         │              │   Alertmanager  │
         │              │    (Alerts)     │
         │              └────────┬────────┘
         │                       │
┌────────▼────────┐              │
│  Health Checks  │              │
│  /health/*      │              ▼
└─────────────────┘     ┌─────────────────┐
                        │  Notifications  │
                        │ (Telegram)      │
                        └─────────────────┘
```

## Componentes

### 1. Prometheus (Puerto 9090)
- Recolección de métricas de todos los servicios
- Almacenamiento temporal de métricas (retención: 15 días)
- Evaluación de reglas de alerta
- Scraping cada 15 segundos

### 2. Grafana (Puerto 3001)
- Visualización de métricas en tiempo real
- Dashboards preconfigurados
- Alertas visuales
- Autenticación: admin/admin (configurable)

### 3. Alertmanager (Puerto 9093)
- Gestión de alertas
- Enrutamiento según severidad
- Notificaciones via Telegram (bot token como docker secret — ver Configuración)
- Deduplicación y agrupamiento de alertas

### 4. Exporters
- **PostgreSQL Exporter**: Métricas de base de datos
- **Redis Exporter**: Métricas de cache
- **Node Exporter**: Métricas del host
- **cAdvisor**: Métricas de contenedores Docker

## Endpoints de Health Check

La aplicación FastAPI expone los siguientes endpoints de monitoreo:

### `/api/v1/health/live` - Liveness Probe
- **Uso**: Kubernetes liveness probe
- **Retorna**: 200 si la aplicación está corriendo
- **Acción**: Si falla, Kubernetes reinicia el pod

### `/api/v1/health/ready` - Readiness Probe
- **Uso**: Kubernetes readiness probe
- **Verifica**: Base de datos, Redis, QA-FRAMEWORK integration
- **Retorna**: 200 si todos los servicios están saludables
- **Acción**: Si falla, Kubernetes remueve el pod del servicio

### `/api/v1/health/metrics` - Métricas Prometheus
- **Uso**: Endpoint para scraping de Prometheus
- **Formato**: Prometheus exposition format
- **Métricas incluidas**:
  - `http_requests_total`: Contador de requests HTTP
  - `http_request_duration_seconds`: Histograma de latencias
  - `db_connections_active`: Conexiones activas a DB
  - `cache_hits_total` / `cache_misses_total`: Estadísticas de cache
  - `active_test_executions`: Ejecuciones de tests activas

### `/api/v1/health/startup` - Startup Probe
- **Uso**: Kubernetes startup probe
- **Retorna**: 200 cuando la aplicación terminó de inicializar
- **Prevención**: Evita chequeos prematuros de liveness/readiness

### `/api/v1/health/status` - Estado Detallado
- **Uso**: Información completa del sistema
- **Incluye**: Métricas del sistema, estado de servicios, uptime

## Dashboards de Grafana

### 1. API Performance Dashboard (`api-performance`)
Métricas del rendimiento de la API:
- **Request Rate**: Solicitudes por segundo por endpoint
- **Response Time Percentiles**: P50, P90, P95, P99
- **HTTP Status Distribution**: Distribución de códigos de estado
- **Success Rate**: Porcentaje de respuestas 2xx
- **Error Rate**: Solicitudes 5xx por segundo
- **Active Test Executions**: Ejecuciones activas
- **Uptime**: Tiempo de actividad de la aplicación

### 2. Database Metrics Dashboard (`database-metrics`)
Métricas de PostgreSQL:
- **Active Connections**: Conexiones activas
- **Connection Pool Usage**: Uso del pool de conexiones
- **Transaction Rate**: Commits y rollbacks por segundo
- **Connection States**: Estados de las conexiones
- **Buffer Cache Activity**: Actividad del buffer cache
- **Cache Hit Ratio**: Ratio de aciertos del cache

### 3. Cache Performance Dashboard (`cache-performance`)
Métricas de Redis:
- **Cache Hit Rate**: Porcentaje de aciertos del cache
- **Memory Usage**: Uso de memoria en porcentaje
- **Connected Clients**: Clientes conectados
- **Rejected Connections**: Conexiones rechazadas
- **Total Keys**: Número total de claves
- **Command Rate**: Comandos por segundo
- **Network I/O**: Entrada/salida de red

### 4. Alerts Dashboard (`alerts-dashboard`)
Visualización de alertas:
- **Firing Alerts**: Alertas activas
- **Pending Alerts**: Alertas pendientes
- **DB Errors**: Errores de base de datos (1h)
- **HTTP 5xx**: Errores HTTP 5xx (1h)
- **Active Alerts Table**: Tabla de alertas activas con severidad
- **Alert Activity**: Actividad de alertas en el tiempo
- **Alerts by Severity**: Distribución por severidad

## Reglas de Alerta

### Alertas Críticas (Critical)
1. **HighErrorRate**: Tasa de error > 5% por 5 minutos
2. **APIDown**: API no responde por más de 1 minuto
3. **ServiceUnavailable**: Health check fallando por 2 minutos
4. **DatabaseDown**: PostgreSQL no responde
5. **RedisDown**: Redis no responde
6. **DiskSpaceLow**: Espacio en disco < 10%

### Alertas de Advertencia (Warning)
1. **HighLatency**: Latencia P95 > 2 segundos por 5 minutos
2. **DatabaseConnectionHigh**: Uso del pool > 80%
3. **DatabaseConnectionErrors**: > 5 errores de conexión en 5 minutos
4. **LowCacheHitRatio**: Ratio de aciertos < 95% en PostgreSQL
5. **RedisMemoryHigh**: Uso de memoria Redis > 90%
6. **RedisCacheHitRatioLow**: Ratio de aciertos Redis < 80%
7. **HighCPUUsage**: Uso de CPU > 80%
8. **HighMemoryUsage**: Uso de memoria > 85%

## Configuración

### Variables de Entorno

Añade estas variables a tu archivo `.env`:

```env
# Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your-secure-password
```

> Las notificaciones de alertas ya NO usan variables de entorno ni Slack/SMTP:
> el canal es Telegram-only vía docker secret (siguiente sección).

### Notificaciones Telegram (Alertmanager)

El bot token se inyecta como docker secret — nunca va en `.env` ni en el repo:

```bash
# 1. Copiar el template y rellenar el token real del bot
mkdir -p dashboard/monitoring/alertmanager/.secrets
cp dashboard/monitoring/alertmanager/telegram_token.example \
   dashboard/monitoring/alertmanager/.secrets/telegram_token
chmod 600 dashboard/monitoring/alertmanager/.secrets/telegram_token
# editar .secrets/telegram_token → "<bot_id>:<secret>" (una línea)

# 2. docker-compose.unified.yml monta ese archivo en el contenedor como
#    /run/secrets/alertmanager_telegram_token (referenciado por bot_token_file
#    en alertmanager.yml, receivers default/critical/warning)
```

`.secrets/` está gitignored — tras crear el archivo, `git status` debe mostrar
cero cambios. El `chat_id` de destino está fijado en `alertmanager.yml`.

### Iniciar el Sistema de Monitoreo

```bash
# Iniciar todos los servicios incluyendo monitoreo
docker-compose up -d

# Verificar que todos los servicios estén corriendo
docker-compose ps

# Ver logs de Prometheus
docker-compose logs -f prometheus

# Ver logs de Grafana
docker-compose logs -f grafana
```

### Acceso a las Interfaces

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)
- **Alertmanager**: http://localhost:9093

## Troubleshooting

### Prometheus no recolecta métricas

1. Verificar que el endpoint de métricas responda:
   ```bash
   curl http://localhost:8000/api/v1/health/metrics
   ```

2. Revisar configuración de scraping:
   ```bash
   docker-compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
   ```

3. Verificar targets en Prometheus UI:
   - Ir a http://localhost:9090/targets
   - Verificar que todos los targets estén UP

### Grafana no muestra datos

1. Verificar datasource:
   - Ir a Configuration > Data Sources
   - Verificar que Prometheus esté configurado y funcionando

2. Verificar dashboards:
   - Ir a Dashboards > Manage
   - Verificar que los dashboards estén importados

3. Verificar permisos de volúmenes:
   ```bash
   docker-compose exec grafana ls -la /etc/grafana/provisioning/dashboards/
   ```

### Alertmanager no envía notificaciones

1. Verificar configuración:
   ```bash
   docker-compose logs alertmanager
   ```

2. Probar el flujo de Telegram (round-trip del bot):
   ```bash
   TOKEN=$(grep -v '^#' dashboard/monitoring/alertmanager/.secrets/telegram_token | tail -1)
   curl -s "https://api.telegram.org/bot${TOKEN}/sendMessage" \
     -d chat_id=346997361 -d text="alertmanager healthcheck"
   # respuesta esperada: {"ok":true,...} en el chat de alertas
   ```
   Si falla: verificar que el bot pueda escribir al chat (iniciar /start con el
   bot) y que el token del archivo coincida con el del bot.

3. Verificar estado de alertas:
   - Ir a http://localhost:9093/#/status

### Health checks fallando

1. Verificar endpoint de health:
   ```bash
   curl http://localhost:8000/api/v1/health/ready
   ```

2. Revisar logs de la aplicación:
   ```bash
   docker-compose logs -f backend
   ```

3. Verificar conectividad a servicios:
   ```bash
   docker-compose exec backend nc -zv db 5432
   docker-compose exec backend nc -zv redis 6379
   ```

## Métricas Personalizadas

El sistema expone métricas personalizadas además de las estándar de Prometheus:

### Métricas de Aplicación
- `http_requests_total`: Total de requests HTTP por método, endpoint y código de estado
- `http_request_duration_seconds`: Duración de requests HTTP (buckets: 0.01s a 10s)
- `db_connections_active`: Número de conexiones activas a la base de datos
- `db_connection_errors_total`: Total de errores de conexión a la base de datos
- `cache_hits_total`: Total de aciertos del cache
- `cache_misses_total`: Total de fallos del cache
- `active_test_executions`: Número de ejecuciones de tests activas
- `test_executions_total`: Total de ejecuciones por estado
- `app_start_timestamp`: Timestamp de inicio de la aplicación

### Ejemplo de Uso

Para incrementar métricas personalizadas en tu código:

```python
from api.v1.health import cache_hits_total, test_executions_total

# Incrementar contador de aciertos de cache
cache_hits_total.inc()

# Incrementar contador con labels
test_executions_total.labels(status="success").inc()
```

## Mantenimiento

### Backup de datos de Grafana

```bash
# Backup de dashboards y datasources
docker-compose exec grafana tar czvf /tmp/grafana-backup.tar.gz /var/lib/grafana
docker cp qa-grafana:/tmp/grafana-backup.tar.gz ./backups/
```

### Limpieza de métricas antiguas

Prometheus retiene métricas por 15 días por defecto. Para cambiar:

```yaml
# En docker-compose.yml, modificar el comando de prometheus
command:
  - '--storage.tsdb.retention.time=30d'  # Cambiar a 30 días
```

### Actualizar reglas de alerta

Después de modificar reglas de alerta en `monitoring/prometheus/alerts/`:

```bash
# Recargar configuración sin reiniciar
curl -X POST http://localhost:9090/-/reload
```

## Referencias

- [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Alertmanager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [FastAPI Prometheus Client](https://github.com/prometheus/client_python)

## Soporte

Para reportar problemas o solicitar nuevas métricas, crear un issue en el repositorio del proyecto.
