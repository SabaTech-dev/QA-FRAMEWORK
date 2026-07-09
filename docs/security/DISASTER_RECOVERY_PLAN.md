# Disaster Recovery Plan — QA-FRAMEWORK

**Version:** 1.0 | **Last Updated:** 2026-07-09 | **Owner:** Tech Lead

## Overview

This plan defines the procedures for recovering QA-FRAMEWORK from disasters including hardware failure, data corruption, security incidents, and prolonged outages.

## Objectives

| Metric | Target | Current |
|--------|--------|---------|
| **RTO** (Recovery Time Objective) | 4 hours | ✅ Achievable |
| **RPO** (Recovery Point Objective) | 24 hours | ✅ Daily backups |
| **MTTR** (Mean Time To Recovery) | <4 hours | TBD (first drill pending) |

## Infrastructure

| Component | Location | Backup Method |
|-----------|----------|--------------|
| Backend API | Docker container (qa-framework-backend) | Git repo + Docker image (GHCR) |
| Frontend | Docker container (qa-framework-frontend) | Git repo + Docker image |
| PostgreSQL | Docker container (qa-framework-db) | Daily pg_dump (30-day retention) |
| Redis | Docker container (qa-framework-cache) | In-memory only (no persistence needed) |
| Prometheus | Docker container | 15-day retention (rebuildable) |
| Grafana | Docker container | Dashboard JSON exports in git |
| Config | docker-compose.unified.yml | Versioned in git |

## Recovery Procedures

### Scenario 1: Database Loss / Corruption

1. **Detect:** Prometheus alert or manual check (`docker exec qa-framework-db pg_isready`)
2. **Stop:** `docker stop qa-framework-backend qa-framework-db`
3. **Restore:**
   ```bash
   # Find latest backup
   ls -t /home/joker/backups/qa-framework-db-*.sql.gz | head -1
   # Restore
   docker start qa-framework-db
   sleep 10  # Wait for PostgreSQL to be ready
   gunzip -c /home/joker/backups/qa-framework-db-LATEST.sql.gz | docker exec -i qa-framework-db psql -U qa_user qa_db
   ```
4. **Verify:** `docker exec qa-framework-db psql -U qa_user qa_db -c "SELECT COUNT(*) FROM tests;"`
5. **Restart:** `docker start qa-framework-backend`
6. **Validate:** `curl http://localhost:8010/health`

### Scenario 2: Full Server Loss (jokerserver)

1. **Provision:** New Ubuntu 24.04 server with Docker
2. **Clone:** `git clone https://github.com/SabaTech-dev/QA-FRAMEWORK.git`
3. **Restore Config:** Copy `.env` from secure backup (1Password/encrypted storage)
4. **Pull Images:** `docker compose -f docker-compose.unified.yml pull`
5. **Restore DB:** See Scenario 1
6. **DNS:** Update Cloudflare tunnel to new server IP
7. **Verify:** Health check on https://qa.sabatech.dev/api/health

### Scenario 3: Security Incident (Compromise)

1. **Isolate:** `docker network disconnect qa-framework_default qa-framework-backend`
2. **Preserve Evidence:** `docker logs qa-framework-backend > /tmp/forensic-backend.log 2>&1`
3. **Rotate Secrets:** All API keys, JWT secrets, database passwords
4. **Rebuild:** Destroy and rebuild containers from clean images
5. **Audit:** Check all logs for unauthorized access since breach time
6. **Document:** File incident report (see INCIDENT_RESPONSE_PLAYBOOK.md)

### Scenario 4: GPU Failure (LLM unavailable)

1. **Detect:** llama.cpp health check fails (`curl http://192.168.1.39:8001/v1/models`)
2. **Fallback:** QA-FRAMEWORK operates in degraded mode (manual testing only, no AI features)
3. **Notify:** Users see banner "AI features temporarily unavailable"
4. **Recover:** Hardware replacement or migrate to backup model on alternative GPU

## Backup Schedule

| Data | Method | Frequency | Retention | Location |
|------|--------|-----------|-----------|----------|
| PostgreSQL | pg_dump + gzip | Daily 03:00 | 30 days | ~/backups/ |
| Git repos | git push (GitHub) | Continuous | Infinite | GitHub |
| Docker images | GHCR push | On build | 10 versions | ghcr.io/sabatech |
| Config (.env) | Manual encrypted backup | Monthly | 90 days | 1Password |

## DR Drill

- **Frequency:** Quarterly
- **Method:** Restore DB backup to staging container, verify data integrity
- **Documentation:** Record RTO achieved, issues found, improvements

---

*This document is versioned in git. Changes require PR review.*
