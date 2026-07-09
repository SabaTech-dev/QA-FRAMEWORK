# Incident Response Playbook — QA-FRAMEWORK

**Version:** 1.0 | **Last Updated:** 2026-07-09 | **Owner:** Tech Lead

## Incident Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| **SEV-1** | Critical — service down or data breach | 15 min | Production outage, confirmed hack |
| **SEV-2** | High — major feature broken | 1 hour | API errors, AI features down |
| **SEV-3** | Medium — minor feature degraded | 4 hours | Slow performance, non-critical bugs |
| **SEV-4** | Low — cosmetic or minor | 24 hours | UI glitches, documentation |

## Response Team

| Role | Person | Contact |
|------|--------|---------|
| Incident Commander | Jose Manuel Sabarís | Telegram @LJokerL_TTV |
| Security Lead | Alfred (AI Agent) | OpenClaw session |
| DevOps | Alfred (AI Agent) | OpenClaw session |

## Playbooks

### P-01: Suspected Security Breach

1. **Detect:** Alert from monitoring, user report, or anomalous log entry
2. **Assess:** Determine scope — is data exfiltrated? Is production compromised?
3. **Contain:**
   ```bash
   # Isolate affected containers
   docker network disconnect qa-framework_default <container>
   # Preserve forensic evidence
   docker logs <container> --timestamps > /tmp/forensic-$(date +%s).log 2>&1
   # Block suspicious IPs at firewall level
   sudo ufw deny from <IP>
   ```
4. **Eradicate:** Remove malicious code, close vulnerabilities
5. **Recover:** Rebuild from clean images, rotate ALL secrets
6. **Post-Incident:** Within 48h, write incident report covering: timeline, root cause, impact, lessons learned

### P-02: Data Loss / Database Corruption

1. **Detect:** Application errors, query failures, health check fails
2. **Assess:** Which tables/data are affected?
3. **Restore:** Follow DR Plan Scenario 1
4. **Verify:** Run data integrity checks (`pytest tests/test_data_integrity.py`)
5. **Post-Incident:** Review backup frequency, consider point-in-time recovery

### P-03: LLM / AI Service Outage

1. **Detect:** LLM health check fails, AI features return errors
2. **Assess:** Is llama.cpp down? GPU failure? Model corrupted?
   ```bash
   curl http://192.168.1.39:8001/v1/models
   nvidia-smi
   docker logs llamacpp-main 2>&1 | tail -20
   ```
3. **Mitigate:** Enable degraded mode (disable AI features, show banner)
4. **Recover:** Restart llama.cpp, reload model, or switch to fallback model
5. **Post-Incident:** Review model loading stability, consider auto-failover

### P-04: DDoS / Rate Limit Abuse

1. **Detect:** Traffic spike, elevated error rates, Prometheus alerts
2. **Assess:** Is this legitimate traffic or attack?
3. **Mitigate:**
   ```bash
   # Enable rate limiting at nginx level
   # Block offending IPs
   sudo ufw deny from <IP>
   ```
4. **Escalate:** If sustained, enable Cloudflare "Under Attack" mode
5. **Post-Incident:** Review rate limit thresholds, add CAPTCHA if needed

### P-05: Dependency Vulnerability (Critical CVE)

1. **Detect:** Trivy scan, Dependabot alert, or manual CVE report
2. **Assess:** Is QA-FRAMEWORK affected? Is exploitation possible?
3. **Patch:**
   ```bash
   # Update vulnerable dependency
   pip install --upgrade <package>
   # Rebuild and redeploy
   docker compose -f docker-compose.unified.yml build --no-cache backend
   docker compose -f docker-compose.unified.yml up -d backend
   ```
4. **Verify:** Re-run Trivy scan, confirm CVE resolved
5. **Post-Incident:** Review dependency update cadence

## Communication Templates

### Internal Notification (Telegram)
```
🚨 INCIDENT [SEV-X]: <brief description>
Status: <investigating/contained/resolved>
Impact: <what's affected>
ETA: <if known>
```

### User Notification
```
We are investigating an issue with <service>. 
Affected features: <list>.
We expect to resolve this by <time>.
```

### Post-Incident Report
```
## Incident Report: <ID>
**Date:** <date>
**Severity:** <SEV-X>
**Duration:** <time>
**Impact:** <users/data affected>
**Root Cause:** <technical explanation>
**Resolution:** <what was done>
**Lessons Learned:** <improvements>
```

## Post-Incident Review

Every SEV-1 and SEV-2 incident requires:
1. **Within 24h:** Preliminary report
2. **Within 72h:** Full post-mortem
3. **Within 7 days:** Action items tracked in workboard
4. **Within 30 days:** All action items resolved

---

*This document is versioned in git. Changes require PR review.*
