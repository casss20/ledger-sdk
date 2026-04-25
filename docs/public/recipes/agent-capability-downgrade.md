# Recipe: Agent Capability Downgrade

## What you'll learn

- Automatically reduce agent permissions when trust drops
- Implement progressive restriction
- Restore capabilities after recovery
- Alert on capability changes

---

## Use Case
When an agent's trust score drops below threshold, automatically remove risky permissions instead of killing it.

---

## Implementation

```python
# Monitor trust score and downgrade capabilities
import requests

BASE = "https://api.citadelsdk.com/api"
ADMIN_JWT = "your-admin-jwt"

# Get current trust score
resp = requests.get(
    f"{BASE}/agent-identities/data-agent/trust",
    headers={"Authorization": f"Bearer {ADMIN_JWT}"}
)
trust = resp.json()
score = trust["trust_score"]

if score < 0.30:
    # Downgrade: quarantine agent (removes all capabilities)
    requests.post(
        f"{BASE}/agents/data-agent/quarantine",
        headers={"Authorization": f"Bearer {ADMIN_JWT}"}
    )
    # Alert
    print(f"ALERT: Agent data-agent quarantined. Trust score: {score}")
elif score > 0.60:
    # Restore: unquarantine if previously downgraded
    requests.post(
        f"{BASE}/agents/data-agent/quarantine",
        headers={"Authorization": f"Bearer {ADMIN_JWT}"}
    )
    print(f"Agent data-agent restored. Trust score: {score}")
```

---

## Policy

```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: auto-downgrade
spec:
  trigger:
    action: trust.score_changed
    condition: score < 300
  enforcement:
    type: alert_only
    actions:
      - downgrade_capabilities
      - notify_admin
```

---

## Next steps

- [Core Concepts: Trust Scoring](../core-concepts/trust-scoring.md)
- [Core Concepts: Kill Switch](../core-concepts/kill-switch.md)
