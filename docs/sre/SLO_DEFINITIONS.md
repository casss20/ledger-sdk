# SLO & SLA Definitions

**Document ID:** SRE-SLO-001  
**Version:** 1.0  
**Date:** 2026-04-26  

---

## Overview

Service Level Objectives (SLOs) define what "good" looks like for Citadel. Service Level Agreements (SLAs) are the customer-facing promises backed by those SLOs.

---

## SLO Framework

### Formula

```
SLO = (Good Events) / (Total Events) >= Target
Error Budget = 100% - SLO Target (allowed failures per window)
```

### Window

All SLOs are measured over a **30-day rolling window** unless specified otherwise.

---

## Core SLOs

### 1. API Availability

| Field | Value |
|-------|-------|
| **SLO** | 99.9% of requests return non-5xx status |
| **Target** | 99.9% |
| **Error Budget** | 43 minutes 49 seconds of downtime per 30 days |
| **Measurement** | `sum(rate(citadel_http_requests_total{status!="5.."}[30d])) / sum(rate(citadel_http_requests_total[30d]))` |
| **Alert** | `CitadelHighErrorRate` fires at > 0.1% over 5m |
| **Tier** | Critical |

**Why 99.9%?** Balances cost of 4-nines (expensive redundancy) with customer expectations for governance API.

---

### 2. API Latency

| Field | Value |
|-------|-------|
| **SLO** | p99 latency < 500ms for all API requests |
| **Target** | 99% of requests under 500ms |
| **Error Budget** | 1% of requests may exceed 500ms |
| **Measurement** | `histogram_quantile(0.99, sum(rate(citadel_http_request_duration_seconds_bucket[30d])))` |
| **Alert** | `CitadelHighLatency` fires at p99 > 500ms over 3m |
| **Tier** | Critical |

**Secondary target:** p95 < 200ms (measured but not SLO-bound)

---

### 3. Governance Decision Latency

| Field | Value |
|-------|-------|
| **SLO** | 99% of policy decisions complete in < 100ms |
| **Target** | 99% |
| **Error Budget** | 1% of decisions may exceed 100ms |
| **Measurement** | `histogram_quantile(0.99, sum(rate(citadel_policy_eval_duration_seconds_bucket[30d])))` |
| **Alert** | None (part of API latency alert) |
| **Tier** | Critical |

**Rationale:** Agents expect near-instantaneous policy decisions. 100ms is the threshold where agent workflows feel "snappy."

---

### 4. Audit Log Durability

| Field | Value |
|-------|-------|
| **SLO** | 100% of governance actions are logged within 10ms |
| **Target** | 99.99% |
| **Error Budget** | 0.01% of writes may fail (≈ 4 minutes/month) |
| **Measurement** | `sum(rate(citadel_audit_log_write_duration_seconds_bucket{le="0.01"}[30d])) / sum(rate(citadel_audit_log_write_duration_seconds_bucket[30d]))` |
| **Alert** | `CitadelDatabaseUnhealthy` |
| **Tier** | Critical |

**Rationale:** Audit is non-negotiable for compliance. Any missed audit log is a compliance failure.

---

### 5. Kill Switch Activation Latency

| Field | Value |
|-------|-------|
| **SLO** | Kill switch propagates to all nodes in < 1 second |
| **Target** | 99.9% |
| **Error Budget** | 0.1% of activations may exceed 1s |
| **Measurement** | `citadel_kill_switch_propagation_seconds` histogram |
| **Alert** | `CitadelKillSwitchActive` |
| **Tier** | Critical |

---

### 6. Agent Identity Verification

| Field | Value |
|-------|-------|
| **SLO** | 99% of challenge-response verifications complete in < 200ms |
| **Target** | 99% |
| **Error Budget** | 1% |
| **Measurement** | `histogram_quantile(0.99, sum(rate(citadel_identity_verify_duration_seconds_bucket[30d])))` |
| **Alert** | None (part of API latency) |
| **Tier** | Standard |

---

### 7. Trust Snapshot Freshness

| Field | Value |
|-------|-------|
| **SLO** | Trust snapshots are current within 1 hour of behavior change |
| **Target** | 95% |
| **Error Budget** | 5% of agents may have stale snapshots > 1 hour |
| **Measurement** | `citadel_trust_snapshot_age_seconds` histogram |
| **Alert** | `CitadelLowTrustScore` (indirect) |
| **Tier** | Standard |

**Rationale:** Trust decisions are only as good as the data they're based on. Stale trust snapshots can lead to incorrect band assignments.

---

### 8. Approval Queue Throughput

| Field | Value |
|-------|-------|
| **SLO** | 95% of approvals are processed within 1 hour of submission |
| **Target** | 95% |
| **Error Budget** | 5% may exceed 1 hour |
| **Measurement** | `histogram_quantile(0.95, sum(rate(citadel_approval_wait_duration_seconds_bucket[30d])))` |
| **Alert** | `CitadelApprovalQueueBacklog` at > 50 pending > 10m |
| **Tier** | Standard |

---

## SLA Summary (Customer-Facing)

| Tier | Monthly Uptime | Latency p99 | Support Response | Penalty |
|------|---------------|-------------|-----------------|---------|
| **Enterprise** | 99.99% | < 300ms | 15 minutes | 10% credit per 0.01% below |
| **Business** | 99.9% | < 500ms | 1 hour | 5% credit per 0.1% below |
| **Starter** | 99.5% | < 1000ms | 24 hours | None |

**SLA excludes:** Scheduled maintenance (max 4 hours/month), customer-caused issues, third-party outages.

---

## Error Budget Policy

### When error budget is above 50% (healthy)
- Deploy normally
- Feature launches allowed
- No special approval needed

### When error budget drops below 50% (caution)
- Deploys require SRE approval
- No experimental features
- Weekly review of burn rate
- Alert: Slack #sre-budget

### When error budget drops below 25% (critical)
- Freeze all non-essential deploys
- Daily burn rate review
- SEV2 severity for any new incident
- Page on-call for any alert
- Alert: PagerDuty + Slack #sre-critical

### When error budget exhausted (breach)
- Full deploy freeze
- All hands on SLO recovery
- Incident commander assigned
- Customer communication prepared
- Escalate to VP Engineering

---

## Burn Rate Alerts

| Burn Rate | Meaning | Alert |
|-----------|---------|-------|
| > 2x | Will exhaust in < 15 days | Warning |
| > 4x | Will exhaust in < 7 days | Critical |
| > 14x | Will exhaust in < 2 days | Emergency |

Formula:
```
burn_rate = (errors_this_hour / total_this_hour) / (1 - SLO_target)
```

---

## Dashboard

SLO dashboard panels (Grafana):

1. **Availability SLO** — Green/yellow/red gauge showing current 30d availability vs 99.9%
2. **Latency SLO** — p99 latency over 30d vs 500ms threshold
3. **Error Budget Burn** — Remaining budget % with burn rate projection
4. **SLO by Tenant** — Breakdown for multi-tenant visibility
5. **SLO by Endpoint** — Which endpoints are the biggest contributors to SLO misses

---

## Review Schedule

| Review | Frequency | Owner |
|--------|-----------|-------|
| SLO health | Weekly | SRE on-call |
| Error budget analysis | Monthly | SRE team |
| SLO/SLA revision | Quarterly | SRE + Product + Engineering |
| Customer SLA report | Monthly | Customer Success |

---

## History

| Date | Change | Reason |
|------|--------|--------|
| 2026-04-26 | Initial SLOs defined | Post-audit infrastructure hardening |

---

**Document Owner:** SRE Team  
**Review Cycle:** Quarterly
