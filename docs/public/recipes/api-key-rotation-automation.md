# Recipe: API Key Rotation Automation

## What you'll learn

- Automate API key rotation
- Govern key access
- Audit key usage
- Prevent key leakage

---

## Use Case
Rotate API keys every 90 days without breaking agent functionality.

---

## Implementation

```python
# Rotate key for an agent
new_key = ledger.agents.rotate_key(
    agent_id="payment-agent",
    grace_period="24h"  # Old key valid for 24h
)

# Update agent configuration
agent.update_key(new_key)

# Verify old key is invalidated
old_key_valid = ledger.keys.verify(old_key)
assert old_key_valid is False
```

---

## Policy

```yaml
apiVersion: ledger.gov/v1
kind: Policy
metadata:
  name: key-rotation
spec:
  trigger:
    action: key.rotate
  enforcement:
    type: allow
  audit:
    level: comprehensive
```

---

## Next steps

- [Security Best Practices](../guides/security-best-practices.md)
- [Core Concepts: Audit Trail](../core-concepts/audit-trail.md)
