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
# Create a quarantined agent for sandbox testing
import requests

BASE = "https://api.citadelsdk.com/api"
ADMIN_JWT = "your-admin-jwt"

# 1. Create agent in quarantined state
resp = requests.post(
    f"{BASE}/agents",
    headers={"Authorization": f"Bearer {ADMIN_JWT}"},
    json={
        "agent_id": "experimental-agent",
        "name": "Experimental Agent",
        "quarantined": True,
        "token_budget": 1000,
        "compliance": ["sandbox"]
    }
)
resp.raise_for_status()

# 2. Register identity (but keep quarantined)
resp = requests.post(
    f"{BASE}/agent-identities",
    headers={"Authorization": f"Bearer {ADMIN_JWT}"},
    json={"agent_id": "experimental-agent", "name": "Experimental", "tenant_id": "demo"}
)
print("Sandbox agent created and quarantined")
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
