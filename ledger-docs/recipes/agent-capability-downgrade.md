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
# Monitor trust score
score = ledger.trust.get_score(agent_id="data-agent")

if score.value < 300:
    # Downgrade: remove write access
    ledger.agents.update_capabilities(
        agent_id="data-agent",
        remove=["database.write", "api.delete"]
    )

    # Alert
    ledger.alerts.send(
        channel="#agent-ops",
        message=f"Agent data-agent downgraded. Trust score: {score.value}"
    )
elif score.value > 600 and agent.is_downgraded:
    # Restore capabilities
    ledger.agents.restore_capabilities(agent_id="data-agent")
```

---

## Policy

```yaml
apiVersion: ledger.gov/v1
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
