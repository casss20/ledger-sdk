# Recipe: Data Exfiltration Prevention

## What you'll learn

- Detect and block unauthorized data transfers
- Monitor outbound data volume
- Alert on anomalous transfer patterns
- Implement egress policies

---

## Use Case
Prevent agents from leaking sensitive data to external systems or exfiltrating customer databases.

---

## Policies

### Block large exports
```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: block-large-exports
spec:
  trigger:
    action: data.export
    condition: size > 100_000_000 OR row_count > 100_000
  enforcement:
    type: deny
```

### Alert on external transfers
```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: external-transfer-alert
spec:
  trigger:
    action: api.call
    condition: domain not_in ["company.com", "internal.net"]
  enforcement:
    type: alert_only
    notify:
      - slack: #security-alerts
```

---

## Implementation

```python
# Attempt export
try:
    action = citadel.govern(
        agent_id="analytics-agent",
        action="data.export",
        params={"table": "customers", "format": "csv"}
    )
    result = action.execute()
except CITADEL_sdk.PolicyDeniedError:
    print("Export blocked - exceeds size limit")
    # Escalate to security team
```

---

## Next steps

- [Core Concepts: Policies](../core-concepts/policies.md)
- [Security Best Practices](../guides/security-best-practices.md)
