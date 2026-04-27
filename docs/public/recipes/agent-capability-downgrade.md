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
# Monitor trust band and downgrade capabilities
import requests

BASE = "https://api.citadelsdk.com/api"
ADMIN_JWT = "your-admin-jwt"

# Get current trust snapshot
resp = requests.get(
    f"{BASE}/agent-identities/data-agent/trust",
    headers={"Authorization": f"Bearer {ADMIN_JWT}"}
)
trust = resp.json()
band = trust["band"]
score = trust["score"]
snapshot_id = trust["snapshot_id"]

if band in ["REVOKED", "PROBATION"]:
    # Downgrade: quarantine agent (removes all capabilities)
    requests.post(
        f"{BASE}/agents/data-agent/quarantine",
        headers={"Authorization": f"Bearer {ADMIN_JWT}"}
    )
    # Alert
    print(f"ALERT: Agent data-agent quarantined. Trust band: {band}, score: {score}")
elif band in ["TRUSTED", "HIGHLY_TRUSTED"]:
    # Restore: unquarantine if previously downgraded
    requests.post(
        f"{BASE}/agents/data-agent/unquarantine",
        headers={"Authorization": f"Bearer {ADMIN_JWT}"}
    )
    print(f"Agent data-agent restored. Trust band: {band}, score: {score}")
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
    action: trust.band_changed
    condition: band in ["REVOKED", "PROBATION"]
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
