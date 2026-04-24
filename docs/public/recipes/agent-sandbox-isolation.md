# Recipe: Agent Sandbox Isolation

## What you'll learn

- Run untrusted agents in sandboxed environments
- Restrict network and filesystem access
- Monitor sandbox escape attempts
- Clean up after sandbox execution

---

## Use Case
Test third-party or experimental agents without risking production systems.

---

## Implementation

```python
# Create sandboxed agent context
sandbox = CITADEL.agents.create_sandbox(
    agent_id="experimental-agent",
    restrictions={
        "network": "none",
        "filesystem": "read-only",
        "execution_time": "5m",
        "memory": "512MB"
    }
)

# Run agent in sandbox
with sandbox:
    action = citadel.govern(
        agent_id="experimental-agent",
        action="code.execute",
        params={"code": "print('hello')"}
    )
    result = action.execute()

# Sandbox is automatically destroyed
```

---

## Policy

```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: sandbox-policy
spec:
  trigger:
    action: "*"
    condition: agent.sandbox == true
  enforcement:
    type: allow
  audit:
    level: comprehensive
```

---

## Next steps

- [Security Best Practices](../guides/security-best-practices.md)
- [Core Concepts: Trust Scoring](../core-concepts/trust-scoring.md)
