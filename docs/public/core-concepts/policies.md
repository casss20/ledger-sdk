# Policies and YAML Syntax

## What you'll learn

- Policy structure and YAML syntax
- All enforcement types and when to use them
- Trigger conditions and matching patterns
- Policy composition and inheritance
- Testing policies before deployment

---

## Policy Structure

Every Citadel policy is a YAML document with four sections:

```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: refund-approval-over-1000
  namespace: payments
  labels:
    team: finance
    risk: high
spec:
  trigger:
    action: refund.create
    condition: amount > 1000
  enforcement:
    type: require_approval
    approvers: [finance-manager]
    timeout: 24h
  audit:
    level: comprehensive
    retention: 7years
```

---

## Trigger Types

### Action-based trigger
```yaml
trigger:
  action: email.send
```

### Condition-based trigger
```yaml
trigger:
  action: refund.create
  condition: amount > 1000 AND currency == "USD"
```

### Parameter-based trigger
```yaml
trigger:
  action: database.write
  condition: table == "users" AND environment == "production"
```

### Regex matching
```yaml
trigger:
  action: api.call
  condition: path matches "^/admin/.*"
```

### Composite triggers
```yaml
trigger:
  any:
    - action: email.send
      condition: recipient_domain not_in ["company.com"]
    - action: file.upload
      condition: size > 10_000_000
```

---

## Enforcement Types

| Type | Behavior | Use Case |
|------|----------|----------|
| `allow` | Pass through, log only | Low-risk, frequent actions |
| `deny` | Block action, raise error | Prohibited actions |
| `require_approval` | Hold for human review | High-risk, irreversible actions |
| `rate_limit` | Throttle to N per window | API calls, resource-intensive ops |
| `require_auth` | Demand re-authentication | Sensitive data access |
| `alert_only` | Log and notify, don't block | Monitoring suspicious patterns |

### Rate limit configuration
```yaml
enforcement:
  type: rate_limit
  limit: 100
  window: 1h
  burst: 20
```

### Approval configuration
```yaml
enforcement:
  type: require_approval
  approvers: [role:finance-manager, user:alice@company.com]
  timeout: 24h
  escalation: 48h
  notify:
    - slack: #finance-alerts
    - email: finance@company.com
```

---

## Policy Composition

### Namespace isolation
Policies in different namespaces don't interact:
```yaml
metadata:
  namespace: payments   # Only affects payment agents
```

### Policy priority
```yaml
metadata:
  annotations:
    priority: "100"  # Higher number = evaluated first
```

### Default policies
```yaml
metadata:
  annotations:
    default: "true"  # Applied to all agents unless overridden
```

---

## Testing Policies

Test before deploying:

```python
result = citadel.policies.test(
    policy=policy_yaml,
    sample_actions=[
        {"action": "refund.create", "params": {"amount": 500}},
        {"action": "refund.create", "params": {"amount": 1500}},
    ]
)
print(result.outcomes)  # [allow, require_approval]
```

---

## Policy Versioning

Policies are versioned automatically:
```
refund-approval-over-1000@v1  # Initial policy
refund-approval-over-1000@v2  # Updated threshold
```

Roll back:
```python
citadel.policies.rollback("refund-approval-over-1000", to_version="v1")
```

---

## Next steps

- [Kill Switch](./kill-switch.md) — Emergency override for policies
- [Trust Scoring](./trust-scoring.md) — Dynamic policy based on agent behavior
- [Recipe: Refund Approval Over $1,000](../recipes/refund-approval-over-1000.md)
