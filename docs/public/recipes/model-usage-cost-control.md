# Recipe: Model Usage Cost Control

## What you'll learn

- Track LLM API spend per agent
- Set budget limits
- Alert on cost spikes
- Optimize model selection

---

## Use Case
Your agents call GPT-4, Claude, and other models. Costs can spiral. Set per-agent budgets and enforce cost-efficient model selection.

---

## Policy

```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: cost-control
spec:
  trigger:
    action: llm.call
  enforcement:
    type: conditional
    conditions:
      - if: daily_cost > 100
        then: require_approval
        approvers: [role:engineering-manager]
      - if: daily_cost > 500
        then: deny
  audit:
    level: standard
```

---

## Implementation

```python
# Track cost per call
action = citadel.govern(
    agent_id="research-agent",
    action="llm.call",
    params={"model": "gpt-4", "tokens": 2000}
)

result = action.execute()
print(f"Call cost: ${result.metadata.cost}")
print(f"Daily spend: ${result.metadata.daily_total}")
```

---

## Next steps

- [Core Concepts: Policies](../core-concepts/policies.md)
- [Guide: Scaling to Millions of Agents](../guides/scaling-to-millions-of-agents.md)
