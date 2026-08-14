# QA-FRAMEWORK - Monitoring Setup

**Preparado por:** Alfred (CEO Agent)
**Fecha:** 2026-03-10
**Estado:** ✅ Completado

---

## 📊 Sistema de Monitoring Completo

QA-FRAMEWORK tiene un sistema de monitoring completo con:

- ✅ **Prometheus** - Métricas y alertas
- ✅ **Grafana** - Dashboards de visualización
- ✅ **Alertmanager** - Notificaciones (Slack, Email, Telegram)
- ✅ **26 Alert Rules** - Monitoreo de API, Database, Redis, Sistema
- ✅ **6 Dashboards** - Business, API Performance, Database, Cache, Alerts, Performance

---

## 🏗️ Arquitectura

```
┌─────────────────┐
│  FastAPI Backend│ (Metrics endpoint: /metrics)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Prometheus   │ (Scrapes metrics every 15s)
│  (port 9090)   │
└────────┬────────┘
         │
         ├──────────────┬──────────────┐
         ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│   Grafana    │ │Alertmanager  │ │  Prometheus UI   │
│  (port 3000) │ │  (port 9093) │ │   (port 9090)    │
│ - Dashboards │ │ - Slack      │ │   - Metrics      │
│ - Visualize  │ │ - Email      │ │   - Queries      │
└──────────────┘ │ - Telegram   │ └──────────────────┘
                └──────────────┘
```

---

## 📁 Estructura de Directorios

```
dashboard/monitoring/
├── prometheus.yml                    # Configuración principal
├── prometheus/
│   └── alerts/
│       └── qa-framework-alerts.yml   # 26 alert rules
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/datasources.yml
│   │   └── dashboards/dashboards.yml
│   └── dashboards/
│       ├── business-metrics.json     # Dashboard negocio (NUEVO)
│       ├── alerts-dashboard.json     # Dashboard alertas
│       ├── api-performance.json      # Performance API
│       ├── cache-performance.json    # Performance Redis
│       ├── database-metrics.json    # Métricas PostgreSQL
│       └── performance.json         # Performance general
└── alertmanager/
    └── alertmanager.yml              # Configuración notificaciones
```

---

## 🚀 Configuración Rápida

### 1. Variables de Entorno

```bash
# Alertmanager (notificaciones)
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
export TELEGRAM_API_URL="https://api.telegram.org"

export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

export ALERT_EMAIL="alerts@example.com"
export SMTP_HOST="smtp.example.com:587"
export SMTP_USER="user@example.com"
export SMTP_PASSWORD="password"
```

### 2. Iniciar Services con Docker

```bash
cd /home/ubuntu/.openclaw/workspace/QA-FRAMEWORK/dashboard/monitoring

# Crear network
docker network create monitoring

# Iniciar Prometheus
docker run -d \
  --name prometheus \
  --network monitoring \
  -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  -v $(pwd)/prometheus/alerts:/etc/prometheus/alerts \
  prom/prometheus:latest \
  --config.file=/etc/prometheus/prometheus.yml \
  --web.enable-lifecycle

# Iniciar Grafana
docker run -d \
  --name grafana \
  --network monitoring \
  -p 3000:3000 \
  -v $(pwd)/grafana/provisioning:/etc/grafana/provisioning \
  -v $(pwd)/grafana/dashboards:/var/lib/grafana/dashboards \
  -e GF_SECURITY_ADMIN_PASSWORD=admin \
  grafana/grafana:latest

# Iniciar Alertmanager
docker run -d \
  --name alertmanager \
  --network monitoring \
  -p 9093:9093 \
  -v $(pwd)/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml \
  prom/alertmanager:latest
```

### 3. Iniciar Exporters (Opcional)

```bash
# PostgreSQL Exporter
docker run -d \
  --name postgres-exporter \
  --network monitoring \
  -p 9187:9187 \
  -e DATA_SOURCE_NAME="postgresql://user:password@postgres-exporter:5432/dbname" \
  prometheuscommunity/postgres-exporter

# Redis Exporter
docker run -d \
  --name redis-exporter \
  --network monitoring \
  -p 9121:9121 \
  -e REDIS_ADDR="redis-exporter:6379" \
  oliver006/redis_exporter

# Node Exporter (system metrics)
docker run -d \
  --name node-exporter \
  --network monitoring \
  -p 9100:9100 \
  -v /proc:/host/proc:ro \
  -v /sys:/host/sys:ro \
  -v /:/rootfs:ro \
  prom/node-exporter
```

---

## 📊 Dashboards de Grafana

### 1. Business Metrics (NUEVO)
**UID:** `qa-framework-business`
**Acceso:** http://localhost:3000/d/qa-framework-business

Métricas de negocio:
- Active Test Runs
- Test Success Rate
- Error Rate
- P95 Latency
- Requests Last Hour
- Active Users
- Request Rate (2xx, 5xx)
- Response Time Percentiles (P50, P95, P99)
- Test Runs by Type (Daily)
- Service Status (API, PostgreSQL, Redis)
- Top 5 Endpoints by Requests
- System Memory Usage

### 2. API Performance
**UID:** `api-performance`
Métricas de performance:
- Request duration percentiles
- Error rate by endpoint
- Request rate
- Slowest endpoints

### 3. Database Metrics
**UID:** `database-metrics`
Métricas PostgreSQL:
- Connection pool usage
- Query performance
- Cache hit ratio
- Transaction throughput
- Locks and deadlocks

### 4. Cache Performance
**UID:** `cache-performance`
Métricas Redis:
- Memory usage
- Hit/miss ratio
- Key count
- Operations per second
- Evictions

### 5. Alerts Dashboard
**UID:** `alerts-dashboard`
Estado de alertas:
- Active alerts
- Alert history
- Alert firing patterns
- Most common alerts

### 6. Performance (General)
**UID:** `performance`
Performance general:
- CPU, Memory, Disk
- Network I/O
- Process count

---

## 🚨 Alertas Configuradas (26 rules)

### API Health (4)
- ✅ **HighErrorRate** - Error rate >5% (5min)
- ✅ **HighLatency** - P95 latency >2s (5min)
- ✅ **APIDown** - API down (1min)
- ✅ **ServiceUnavailable** - Readiness probe failing (2min)

### Database (5)
- ✅ **DatabaseConnectionHigh** - Connections >80% (5min)
- ✅ **DatabaseDown** - PostgreSQL down (1min)
- ✅ **DatabaseConnectionErrors** - >5 errors in 5min
- ✅ **LowCacheHitRatio** - Cache hit <95% (10min)
- ✅ **ConnectionPoolExhaustion** - Pool exhausted

### Redis (4)
- ✅ **RedisDown** - Redis down (1min)
- ✅ **RedisMemoryHigh** - Memory >90% (5min)
- ✅ **RedisCacheHitRatioLow** - Hit ratio <80% (10min)
- ✅ **RedisRejectedConnections** - Rejecting connections

### System (3)
- ✅ **HighCPUUsage** - CPU >80% (5min)
- ✅ **HighMemoryUsage** - Memory >85% (5min)
- ✅ **DiskSpaceLow** - Disk <10% (5min)

### Application (2)
- ✅ **TestExecutionQueueHigh** - >50 active tests (5min)
- ✅ **HealthCheckFailures** - Health checks failing (2min)

### Prometheus (2)
- ✅ **PrometheusTargetMissing** - Target down (5min)
- ✅ **PrometheusRuleEvaluationFailures** - Rules failing (1min)

---

## 📱 Configurar Notificaciones

### Telegram (Recomendado)

1. Crear bot con [@BotFather](https://t.me/botfather)
2. Obtener `BOT_TOKEN`
3. Obtener `CHAT_ID`:
   ```bash
   curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
4. Configurar variables de entorno
5. Reiniciar Alertmanager

### Slack

1. Crear Incoming Webhook en Slack
2. Configurar `SLACK_WEBHOOK_URL`
3. Reiniciar Alertmanager

### Email

1. Configurar SMTP server
2. Configurar `ALERT_EMAIL`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`
3. Reiniciar Alertmanager

---

## 🔧 Comandos Útiles

### Prometheus
```bash
# Ver targets
curl http://localhost:9090/api/v1/targets

# Ver alertas
curl http://localhost:9090/api/v1/alerts

# Ver config
curl http://localhost:9090/api/v1/status/config

# Reload config (sin restart)
curl -X POST http://localhost:9090/-/reload
```

### Grafana
```bash
# Login (default)
Username: admin
Password: admin (cambiar al primer login)

# URL: http://localhost:3000
```

### Alertmanager
```bash
# Ver status
curl http://localhost:9093/api/v1/status

# Ver alertas activas
curl http://localhost:9093/api/v1/alerts

# Ver config
curl http://localhost:9093/api/v1/status/config

# Reload config
curl -X POST http://localhost:9093/-/reload
```

---

## 📈 Queries Útiles de Prometheus

### API Performance
```promql
# Request rate
sum(rate(http_requests_total[5m]))

# P95 latency
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# Error rate
sum(rate(http_requests_total{status_code=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))
```

### Database
```promql
# Active connections
pg_stat_activity_count{state="active"}

# Cache hit ratio
pg_stat_database_blks_hit / (pg_stat_database_blks_hit + pg_stat_database_blks_read)

# Connection pool usage
pg_stat_activity_count / pg_settings_max_connections
```

### Redis
```promql
# Memory usage
redis_memory_used_bytes / redis_memory_max_bytes * 100

# Hit ratio
redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)

# Operations per second
rate(redis_commands_processed_total[1m])
```

---

## 🎯 Checklist de Producción

### Antes del Deploy
- [ ] Prometheus corriendo y scraping targets
- [ ] Grafana accesible con dashboards importados
- [ ] Alertmanager configurado con notificaciones
- [ ] Todas las alertas verificadas (no falsos positivos)
- [ ] Thresholds ajustados para producción
- [ ] Documentation actualizada

### Durante el Deploy
- [ ] Monitorear `/health` endpoint
- [ ] Verificar Prometheus targets status
- [ ] Verificar Alertmanager notificaciones
- [ ] Monitorear error rate en Grafana

### Después del Deploy
- [ ] Verificar todas las métricas normales
- [ ] Verificar no hay alertas firing
- [ ] Verificar performance (latency, throughput)
- [ ] Verificar database y Redis healthy

---

## 🔍 Troubleshooting

### Prometheus no scrapea targets
```bash
# Ver targets
curl http://localhost:9090/api/v1/targets

# Si target está "down", verificar:
# 1. Target URL correcta
# 2. Network connectivity
# 3. Firewall rules
# 4. Metrics endpoint habilitado
```

### Alertas no disparan
```bash
# Ver alert rules
curl http://localhost:9090/api/v1/rules

# Ver alertas activas
curl http://localhost:9090/api/v1/alerts

# Verificar:
# 1. Rules syntax correcta
# 2. Expression evalúa a true
# 3. `for` duration cumplida
```

### Notificaciones no llegan
```bash
# Verificar Alertmanager config
curl http://localhost:9093/api/v1/status/config

# Verificar notificaciones
curl http://localhost:9093/api/v1/alerts

# Verificar:
# 1. Bot credentials correctos
# 2. Chat ID correcto
# 3. API URL accesible
# 4. Alertmanager corriendo
```

### Grafana no muestra datos
```bash
# Verificar datasource en Grafana UI
# Configuration > Data Sources > Prometheus

# Verificar:
# 1. URL correcta (http://localhost:9090)
# 2. Access mode: Server (default)
# 3. Test connection button funciona

# Si no funciona, verificar:
# 1. Prometheus corriendo
# 2. Network connectivity
# 3. Firewall rules
```

---

## 📚 Recursos Adicionales

- **Prometheus Docs:** https://prometheus.io/docs/
- **Grafana Docs:** https://grafana.com/docs/
- **Alertmanager Docs:** https://prometheus.io/docs/alerting/latest/alertmanager/
- **PromQL Guide:** https://prometheus.io/docs/prometheus/latest/querying/basics/

---

## ✨ Próximas Mejoras

- [ ] Integrar con PagerDuty para alertas on-call
- [ ] Configurar alertas por tenant (multi-tenant)
- [ ] Añadir machine learning para anomaly detection
- [ ] Integrar con New Relic o Datadog (opcional)
- [ ] Configurar retention de métricas (días, meses)
- [ ] Añadir dashboards por tenant

---

**Preparado por:** Alfred (CEO Agent)
**Fecha:** 2026-03-10 05:55 UTC
**Estado:** ✅ Monitoring Setup Completado
