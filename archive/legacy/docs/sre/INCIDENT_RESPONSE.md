# Incident Response Runbooks

**Document ID:** SRE-IR-001
**Version:** 1.0
**Date:** 2026-04-26

---

## Overview

Step-by-step runbooks for common Citadel incidents. Each runbook includes:

- **Detection** - How the alert fires
- **Impact** - What breaks
- **Response** - What to do now
- **Recovery** - How to restore service
- **Post-Incident** - What to document

---

## Severity Levels

| Level | Name | Response Time | Examples |
|-------|------|--------------|----------|
| SEV1 | Critical | 15 min | Kill switch triggered, API down, data breach |
| SEV2 | High | 30 min | High error rate, DB pool exhausted, mass agent revocation |
| SEV3 | Medium | 2 hr | Elevated latency, trust band degradation, queue backlog |
| SEV4 | Low | Next business day | Deprecation warnings, non-critical CVE |

---

## RB-001: Kill Switch Activated

**Alert:** `CitadelKillSwitchActive`
**Severity:** SEV1

### Detection
- Prometheus alert fires: `citadel_kill_switch_active > 0`
- Dashboard: Governance → Kill Switches panel turns red
- Possible Slack alert: "Kill switch ACTIVE on agent-X"

### Impact
- Target agent stops all actions immediately
- Any in-flight decisions from that agent are blocked
- Downstream services may experience disruption if the agent was critical

### Response (First 15 minutes)

```bash
# 1. Confirm which agent triggered the kill switch
curl -s https://api.citadelsdk.com/api/v1/agents/{agent_id} \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# 2. Check kill switch state
curl -s https://api.citadelsdk.com/api/v1/governance/kill-switch/status \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# 3. Review recent actions from that agent
curl -s "https://api.citadelsdk.com/api/v1/audit?agent_id={agent_id}&limit=20" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.events'

# 4. Check audit log for why it triggered
curl -s "https://api.citadelsdk.com/api/v1/audit?event_type=kill_switch_triggered" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.events[0]'
```

### Decision Tree

**If kill switch was triggered by human operator:**
- ✅ Expected. No action needed unless it was accidental.
- If accidental: contact the operator who triggered it.

**If kill switch was triggered by automated system:**
- ⚠️ Investigate root cause before clearing.
- Look at: anomaly detection, policy violation, rate limit breach.

**If kill switch was triggered by unknown cause:**
- 🔴 Treat as potential security incident.
- Page security team.
- Preserve logs before any recovery action.

### Recovery

```bash
# Only clear after root cause is understood

# Option A: Human operator clears
curl -X POST https://api.citadelsdk.com/api/v1/governance/kill-switch/clear \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-123",
    "reason": "False positive - pattern was expected traffic",
    "operator_id": "op-789"
  }'

# Option B: Restore from quarantine (if agent was quarantined)
curl -X POST https://api.citadelsdk.com/api/v1/agents/{agent_id}/unquarantine \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Post-Incident
1. Update incident ticket with root cause
2. If false positive: tune anomaly detection threshold
3. If policy violation: update policy or agent behavior
4. Schedule post-mortem within 48 hours for SEV1

---

## RB-002: High Error Rate

**Alert:** `CitadelHighErrorRate`
**Severity:** SEV2

### Detection
- Error rate > 0.1% for > 2 minutes
- Grafana panel: Error Rate (5m) crosses red threshold

### Response

```bash
# 1. Identify which endpoints are failing
curl -s https://api.citadelsdk.com/api/v1/metrics \
  | grep 'citadel_http_requests_total{status=~"5.."}'

# 2. Check recent logs
# Via Loki: {app="citadel-api", level="ERROR"}

# 3. Check DB health
curl -s https://api.citadelsdk.com/health/ready | jq

# 4. Check DB connection pool
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity WHERE datname='citadel';"
```

### Common Causes

| Cause | Check | Fix |
|-------|-------|-----|
| DB connection pool exhausted | `citadel_db_pool_connections_available < 1` | Restart API pods; check for connection leaks |
| Deadlock in governance | `approval_queue_size` flatlined | Restart decision engine; clear stuck approvals |
| Bad deployment | Recent deploy within alert window | Rollback to previous version |
| Dependency down | Check postgres, redis health | Restart dependency; fail over to replica |

### Recovery

```bash
# Rollback (if caused by bad deploy)
git revert HEAD
# or
docker compose -f docker-compose.yml pull
docker compose -f docker-compose.yml up -d

# Restart API (if transient)
docker compose -f docker-compose.yml restart api

# Scale up (if load-related)
docker compose -f docker-compose.yml up -d --scale api=4
```

---

## RB-003: Agent Identity Compromised

**Alert:** `CitadelAgentRevoked` or manual detection
**Severity:** SEV2 (if 1 agent), SEV1 (if multiple)

### Detection
- Operator reports suspicious agent behavior
- Security scan flags leaked credentials
- Unexpected high-privilege actions from known agent

### Response

```bash
# 1. Revoke immediately
curl -X POST https://api.citadelsdk.com/api/agent-identities/{agent_id}/revoke \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Credential leak detected - rotating all keys"}'

# 2. Check what the agent did recently
curl -s "https://api.citadelsdk.com/api/v1/audit?agent_id={agent_id}&since=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.events'

# 3. Check if other agents were affected
curl -s "https://api.citadelsdk.com/api/v1/audit?event_type=AGENT_IDENTITY_REVOKED&since=$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.events | length'
```

### Recovery

```bash
# 1. Rotate all credentials for the tenant
curl -X POST https://api.citadelsdk.com/api/v1/agents/rotate-all \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "tenant-456", "reason": "Security incident"}'

# 2. Force re-verification for all agents
curl -X POST https://api.citadelsdk.com/api/agent-identities/trust/evaluate-all \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## RB-004: Database Pool Exhausted

**Alert:** `CitadelDatabaseUnhealthy`
**Severity:** SEV2

### Response

```bash
# 1. Check current connections
psql $DATABASE_URL -c "
  SELECT state, count(*)
  FROM pg_stat_activity
  WHERE datname = 'citadel'
  GROUP BY state;
"

# 2. Check for idle connections
psql $DATABASE_URL -c "
  SELECT pid, state, query_start, query
  FROM pg_stat_activity
  WHERE datname = 'citadel'
    AND state = 'idle'
    AND NOW() - state_change > interval '5 minutes';
"

# 3. Kill idle connections (careful!)
psql $DATABASE_URL -c "
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE datname = 'citadel'
    AND state = 'idle'
    AND NOW() - state_change > interval '10 minutes';
"
```

### Recovery

```bash
# 1. Restart API pods to reset pools
docker compose -f docker-compose.yml restart api

# 2. Increase pool size temporarily
# Edit config: DB_MAX_SIZE=50 → 100
# Redeploy

# 3. Check for connection leaks in recent deploy
git log --oneline -5
# If suspicious commit: revert and redeploy
```

---

## RB-005: Approval Queue Backlog

**Alert:** `CitadelApprovalQueueBacklog`
**Severity:** SEV3 (can escalate to SEV2 if queue > 200)

### Response

```bash
# 1. Check queue depth
curl -s https://api.citadelsdk.com/api/v1/approvals/pending \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.count'

# 2. Check approver availability
curl -s https://api.citadelsdk.com/api/v1/approvers \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.[] | {id, last_active}'

# 3. Bulk approve low-risk items (if policy allows)
curl -X POST https://api.citadelsdk.com/api/v1/approvals/bulk-approve \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {"risk_level": "low", "older_than_minutes": 30},
    "operator_id": "emergency-op-1"
  }'
```

---

## RB-006: Trust Score Mass Event

**Alert:** `CitadelLowTrustScore`  
**Severity:** SEV3

### Response

```bash
# 1. Identify which agents dropped to PROBATION or REVOKED
curl -s "https://api.citadelsdk.com/api/v1/agents?trust_band=REVOKED,PROBATION" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.agents[] | {agent_id, trust_band, trust_score}'

# 2. Check for common pattern (same tenant? same action type?)
curl -s "https://api.citadelsdk.com/api/v1/audit?event_type=TRUST_BAND_CHANGED&since=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.events[] | {agent_id, details}'

# 3. Force recalculation
curl -X POST https://api.citadelsdk.com/api/agent-identities/trust/evaluate-all \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### If scores are correct (agents actually misbehaving):
- Quarantine affected agents
- Set trust band to REVOKED via operator override if kill switch not yet active
- Investigate root cause (bad code? external attack?)

### If scores are wrong (calculation bug):
- Rollback trust engine if recent deploy
- Open P1 ticket for trust algorithm team
- Temporarily disable circuit breaker until fix deployed

---

## On-Call Rotation

| Role | Primary | Secondary | Escalation |
|------|---------|-----------|------------|
| SRE | @sre-oncall | @sre-secondary | @sre-manager |
| Governance | @gov-oncall | @gov-secondary | @cto |
| Security | @sec-oncall | @sec-secondary | @ciso |

**PagerDuty services:**
- `citadel-sre-critical` → SRE team
- `citadel-governance-critical` → Governance team
- `citadel-security` → Security team (manual page only)

---

## Incident Commander Checklist

**Within 5 minutes of SEV1/SEV2:**
- [ ] Acknowledge alert in PagerDuty
- [ ] Join incident Slack channel: `#incident-{YYYY-MM-DD}-{name}`
- [ ] Open incident tracking doc from template
- [ ] Designate scribe (someone to document timeline)
- [ ] Assess severity (upgrade/downgrade if needed)

**Within 15 minutes:**
- [ ] Identify scope (which tenants? which agents? which endpoints?)
- [ ] Determine if rollback is appropriate
- [ ] Communicate status to stakeholders

**Resolution:**
- [ ] Verify all alerts cleared
- [ ] Run smoke tests against production
- [ ] Close incident in PagerDuty
- [ ] Schedule post-mortem (SEV1: 48h, SEV2: 1 week)

---

## Post-Mortem Template

```markdown
# Incident Post-Mortem: {INCIDENT_NAME}

## Metadata
- **Incident ID:** INC-{YYYY}-{NNNN}
- **Date:** {YYYY-MM-DD}
- **Severity:** SEV{N}
- **Duration:** {HH:MM}
- **Reporter:** {name}
- **IC:** {name}

## Summary
2-sentence summary of what happened and impact.

## Timeline
| Time | Event |
|------|-------|
| 09:15 | Alert fired |
| 09:17 | On-call acknowledged |
| ... | ... |

## Root Cause
What actually caused the incident.

## Impact
- {N} tenants affected
- {N} agents quarantined
- {N} requests failed
- {N} dollars in degraded service

## Resolution
What fixed it.

## Lessons Learned
- What went well
- What could have gone better
- What was confusing

## Action Items
| # | Owner | Due | Task |
|---|-------|-----|------|
| 1 | {name} | {date} | Fix X |
| 2 | {name} | {date} | Add test for Y |

## Follow-Up
- [ ] Runbook updated
- [ ] Alert threshold tuned
- [ ] Test added to CI
```

---

**Document Owner:** SRE Team
**Review Cycle:** After every SEV1 incident + Quarterly
