# Monitoring Governance

## What you'll learn

- Set up governance monitoring
- Configure alerts for policy violations
- Build dashboards
- Track governance posture over time

---

## Prometheus Metrics

CITADEL exposes these metrics at `/metrics`:

| Metric | Type | Description |
|--------|------|-------------|
| `citadel_governance_decisions_total` | Counter | Total decisions by type |
| `citadel_policy_eval_duration_ms` | Histogram | Policy evaluation latency |
| `citadel_approval_queue_size` | Gauge | Pending approvals |
| `citadel_kill_switch_active` | Gauge | Active kill switches |
| `citadel_trust_score_avg` | Gauge | Average trust score |
| `citadel_trust_band_count` | Gauge | Agents per trust band |
| `citadel_trust_snapshot_age` | Histogram | Trust snapshot staleness |

---

## Grafana Dashboard

Import dashboard from the Citadel repository:

```bash
curl -L https://raw.githubusercontent.com/casss20/ledger-sdk/main/monitoring/grafana/dashboards/citadel-overview.json > citadel-dashboard.json
```

Or manually create panels using these Prometheus queries:

**Request Rate:**
```promql
sum(rate(citadel_http_requests_total[5m])) by (method, path)
```

**Error Rate:**
```promql
sum(rate(citadel_http_requests_total{status=~"5.."}[5m])) 
/ sum(rate(citadel_http_requests_total[5m]))
```

**p99 Latency:**
```promql
histogram_quantile(0.99, 
  sum(rate(citadel_http_request_duration_seconds_bucket[5m])) by (le)
)
```

**Kill Switch Status:**
```promql
citadel_kill_switch_active
```

**Trust Score Average:**
```promql
avg(citadel_trust_score{band!="REVOKED"})
```

**Trust Band Distribution:**
```promql
citadel_trust_band_count
```

**Trust Snapshot Staleness:**
```promql
histogram_quantile(0.95, 
  sum(rate(citadel_trust_snapshot_age_bucket[5m])) by (le)
)
```

**Approval Queue Depth:**
```promql
citadel_approval_queue_size
```

Widgets:
- Governance decisions per minute
- Policy denial rate by agent
- Approval queue depth
- Kill switch status
- Trust score distribution

---

## Alerting Rules

```yaml
groups:
  - name: CITADEL-alerts
    rules:
      - alert: HighDenialRate
        expr: rate(citadel_governance_decisions_total{decision="denied"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High policy denial rate"

      - alert: ApprovalQueueBacklog
        expr: citadel_approval_queue_size > 50
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Approval queue backing up"
```

---

## Log Aggregation

Forward audit events to your SIEM:

```bash
curl -X POST https://api.citadelsdk.com/api/v1/webhooks \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://splunk.company.com/citadel-events",
    "events": ["governance.action.denied", "governance.kill_switch.activated"]
  }'
```

---

## Next steps

- [Incident Response Guide](incident-response.md)
- [Security Best Practices](security-best-practices.md)
