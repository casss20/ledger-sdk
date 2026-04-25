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
# Rotate credentials for an agent (revoke + re-register)
import requests

BASE = "https://api.citadelsdk.com/api"
ADMIN_JWT = "your-admin-jwt"

# 1. Revoke old credentials
resp = requests.post(
    f"{BASE}/agent-identities/payment-agent/revoke",
    headers={"Authorization": f"Bearer {ADMIN_JWT}"},
    json={"reason": "Scheduled 90-day rotation"}
)
resp.raise_for_status()

# 2. Re-register to get new credentials
resp = requests.post(
    f"{BASE}/agent-identities",
    headers={"Authorization": f"Bearer {ADMIN_JWT}"},
    json={"agent_id": "payment-agent", "name": "Payment Agent", "tenant_id": "demo"}
)
new_creds = resp.json()
print(f"New API key: {new_creds['api_key']}")
print(f"New secret (STORE ONCE): {new_creds['secret_key']}")

# 3. Update agent configuration
agent.update_key(new_creds['api_key'])
```

---

## Policy

```yaml
apiVersion: citadel.gov/v1
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
