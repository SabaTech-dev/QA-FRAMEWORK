# QA-FRAMEWORK - Deployment Guide

**Created:** 2026-03-10 07:50 UTC
**Author:** Alfred (CEO Agent)

---

## 🚀 Quick Start

### Development Setup
```bash
# Clone repository
git clone https://github.com/your-username/qa-framework.git
cd qa-framework

# Run setup script
./scripts/setup.sh

# Start development servers
# Backend (terminal 1)
cd dashboard/backend
source venv/bin/activate
uvicorn main:app --reload

# Frontend (terminal 2)
cd dashboard/frontend
npm run dev
```

---

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] All tests passing (`pytest` + `npm test`)
- [ ] Environment variables configured
- [ ] Database migrations ready
- [ ] Security headers verified
- [ ] SSL certificates valid
- [ ] Load testing passed

### Deployment Steps
- [ ] Run deployment script
- [ ] Verify health checks
- [ ] Monitor logs for errors
- [ ] Test critical flows
- [ ] Notify team

### Post-Deployment
- [ ] Monitor performance metrics
- [ ] Check error rates
- [ ] Verify backups running
- [ ] Update documentation

---

## 🛠️ Available Scripts

### 1. Setup Script
**File:** `scripts/setup.sh`
**Purpose:** Initialize development environment

```bash
./scripts/setup.sh
```

**What it does:**
- Creates Python virtual environment
- Installs all dependencies
- Creates .env files
- Runs database migrations
- Creates necessary directories

---

### 2. Deployment Script
**File:** `scripts/deploy.sh`
**Purpose:** Automated production deployment

```bash
# Set environment variables
export RAILWAY_TOKEN="your_railway_token"
export VERCEL_TOKEN="your_vercel_token"

# Run deployment
./scripts/deploy.sh
```

**What it does:**
- Runs all tests
- Builds frontend
- Deploys backend to Railway
- Deploys frontend to Vercel
- Runs database migrations
- Performs health checks

**Environment Variables:**
- `RAILWAY_TOKEN` - Railway deployment token
- `VERCEL_TOKEN` - Vercel deployment token
- `SKIP_DEPLOY=true` - Skip deployment (only test & build)

---

### 3. Backup Script
**File:** `scripts/backup.sh`
**Purpose:** Automated database backups

```bash
# Set database URL
export DATABASE_URL="postgresql://..."

# Run backup
./scripts/backup.sh
```

**What it does:**
- Creates SQL dump of database
- Compresses backup with gzip
- Stores in `backups/` directory
- Cleans up old backups (keeps 7 days)

**Schedule with cron:**
```bash
# Daily backup at 2 AM
0 2 * * * cd /path/to/qa-framework && ./scripts/backup.sh >> logs/backup.log 2>&1
```

---

## 🔧 Manual Deployment

### Backend (Railway)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link project
railway link

# Deploy
railway up

# Run migrations
railway run alembic upgrade head

# View logs
railway logs
```

---

### Frontend (Vercel)

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy to production
cd dashboard/frontend
vercel --prod

# View logs
vercel logs
```

---

## 🔐 Environment Variables

### Backend (.env)
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# Redis
REDIS_URL=redis://host:port

# Auth
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Stripe
STRIPE_API_KEY=sk_live_...

# AI/LLM
OPENAI_API_KEY=sk-...
# or
OPENROUTER_API_KEY=sk-or-...

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Frontend (.env.local)
```bash
VITE_API_URL=https://qa-framework-backend.railway.app
VITE_STRIPE_PUBLISHABLE_KEY=pk_live_...
```

---

## 📊 Monitoring

### Health Check Endpoints
- **Backend:** `GET /health`
- **API Docs:** `GET /docs`
- **Metrics:** `GET /metrics` (Prometheus)

### Log Aggregation
```bash
# Backend logs (Railway)
railway logs --follow

# Frontend logs (Vercel)
vercel logs --follow
```

### Performance Monitoring
- **Grafana:** https://your-grafana-instance.com
- **Prometheus:** http://localhost:9090
- **Alerts:** Configured in Alertmanager

---

## 🔄 Rollback

### Backend Rollback
```bash
# List deployments
railway status

# Rollback to previous
railway rollback
```

### Frontend Rollback
```bash
# List deployments
vercel list

# Rollback to previous
vercel rollback
```

### Database Rollback
```bash
# Rollback last migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>
```

---

## 🚨 Troubleshooting

### Common Issues

**Backend not starting:**
```bash
# Check logs
railway logs

# Common fixes:
# - Check DATABASE_URL
# - Verify migrations ran
# - Check environment variables
```

**Frontend build fails:**
```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install

# Check for TypeScript errors
npm run type-check
```

**Database connection errors:**
```bash
# Test connection
psql $DATABASE_URL

# Check if migrations need to run
alembic current
alembic upgrade head
```

---

## 📈 Performance Optimization

### Backend
- Enable Redis caching
- Optimize database queries
- Use async operations
- Enable connection pooling

### Frontend
- Enable Gzip compression
- Use CDN for static assets
- Implement lazy loading
- Optimize bundle size

---

## 🔒 Security

### Production Security Checklist
- [ ] HTTPS enabled
- [ ] Security headers configured
- [ ] CORS properly set
- [ ] Rate limiting active
- [ ] Input validation in place
- [ ] SQL injection protection
- [ ] XSS protection enabled
- [ ] CSRF tokens implemented
- [ ] Secrets in environment variables
- [ ] Database backups encrypted

---

## 📝 Maintenance

### Daily Tasks
- Monitor error rates
- Check backup status
- Review security alerts

### Weekly Tasks
- Update dependencies
- Review performance metrics
- Check SSL certificates

### Monthly Tasks
- Security audit
- Dependency updates
- Capacity planning

---

## 🆘 Support

**Documentation:**
- API Docs: https://qa-framework-backend.railway.app/docs
- Architecture: `docs/ARCHITECTURE.md`
- Testing Guide: `TESTING_GUIDE.md`
- Monitoring Setup: `MONITORING_SETUP.md`

**Monitoring:**
- Grafana Dashboard: https://grafana.example.com
- Prometheus: http://localhost:9090
- Alertmanager: http://localhost:9093

**Alerts:**
- Slack: #alerts
- Email: alerts@example.com
- Telegram: Configured in Alertmanager

---

*Deployment guide by Alfred (CEO Agent)*
*Date: 2026-03-10 07:50 UTC*
