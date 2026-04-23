# Monitoring Governance

## What you'll learn

- Set up governance monitoring
- Configure alerts for policy violations
- Build dashboards
- Track governance posture over time

---

## Prometheus Metrics

Ledger exposes these metrics at `/metrics`:

| Metric | Type | Description |
|--------|------|-------------|
| `ledger_governance_decisions_total` | Counter | Total decisions by type |
| `ledger_policy_eval_duration_ms` | Histogram | Policy evaluation latency |
| `ledger_approval_queue_size` | Gauge | Pending approvals |
| `ledger_kill_switch_active` | Gauge | Active kill switches |
| `ledger_trust_score_avg` | Gauge | Average trust score |

---

## Grafana Dashboard

Import dashboard `18674` from Grafana.com or use our JSON:

```bash
curl -L https://docs.ledger.dev/assets/grafana-dashboard.json > ledger-dashboard.json
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
  - name: ledger-alerts
    rules:
      - alert: HighDenialRate
        expr: rate(ledger_governance_decisions_total{decision="denied"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High policy denial rate"

      - alert: ApprovalQueueBacklog
        expr: ledger_approval_queue_size > 50
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Approval queue backing up"
```

---

## Log Aggregation

Forward audit events to your SIEM:

```python
ledger.config.set_webhook(
    url="https://splunk.company.com/ledger-events",
    events=["governance.action.denied", "governance.kill_switch.activated"]
)
```

---

## Next steps

- [Incident Response Guide](incident-response.md)
- [Security Best Practices](security-best-practices.md)
