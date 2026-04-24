# Agent Trust Scoring

## What you'll learn

- How CITADEL calculates real-time trust scores
- Factors that increase and decrease trust
- Using trust scores to reduce approval friction
- Trust-based policy conditions
- Building trust over time

---

## Overview

Every agent in CITADEL has a trust score from 0 to 1000. This score is a real-time measure of the agent's reliability, based on its action history, compliance rate, and anomaly detection.

Think of it like a credit score for agents:
- **800-1000**: Highly trusted, minimal oversight needed
- **500-799**: Standard oversight, typical for most agents
- **200-499**: Elevated monitoring, more approvals required
- **0-199**: Untrusted, high scrutiny or kill switch

---

## Score Components

| Factor | Weight | Description |
|--------|--------|-------------|
| Policy compliance rate | 30% | % of actions that passed policy checks |
| Approval success rate | 25% | % of requested approvals that were granted |
| Anomaly score | 20% | Statistical deviation from normal behavior |
| Human override frequency | 15% | How often humans override agent decisions |
| Time since last violation | 10% | Recency of any policy violation |

---

## Calculating Trust

```python
# Get an agent's current trust score
score = CITADEL.trust.get_score(agent_id="email-agent-01")
print(f"Trust score: {score.value} / 1000")
print(f"Tier: {score.tier}")  # highly_trusted, standard, elevated, untrusted
print(f"Factors: {score.factors}")
```

Example response:
```json
{
  "value": 847,
  "tier": "highly_trusted",
  "factors": {
    "compliance_rate": {"value": 0.98, "impact": +294},
    "approval_success_rate": {"value": 0.95, "impact": +238},
    "anomaly_score": {"value": 0.12, "impact": +160},
    "override_frequency": {"value": 0.03, "impact": +120},
    "time_since_violation": {"value": 45, "impact": +35}
  }
}
```

---

## Trust-Based Policies

Use trust scores in policy conditions:

```yaml
spec:
  trigger:
    action: database.write
    condition: environment == "production"
  enforcement:
    type: conditional
    conditions:
      - if: trust_score > 800
        then: allow
      - if: trust_score > 500
        then: require_approval
      - else: deny
```

---

## Building Trust

New agents start with a neutral score (500). Build trust by:

1. **Consistent compliance**: Follow all policies reliably
2. **Successful approvals**: When approval is required, provide good context
3. **Predictable patterns**: Maintain consistent behavior
4. **Long uptime**: Agents that run without issues gain trust over time

Trust gain/loss examples:

| Event | Score Change |
|-------|-------------|
| 100 consecutive allowed actions | +50 |
| 1 policy violation | -100 |
| 1 denied approval (legitimate) | -20 |
| 1 denied approval (fraudulent) | -200 |
| 30 days without violation | +25 |

---

## Trust Decay

Trust scores decay if agents become inactive:

```python
# After 7 days of inactivity, score decays by 5%
# After 30 days, score decays by 15%
# After 90 days, score resets to 500 (neutral)
```

Prevent decay with heartbeat:
```python
# Send periodic heartbeat
CITADEL.agents.heartbeat(agent_id="email-agent-01")
```

---

## Trust Alerts

Configure alerts for trust score changes:

```yaml
trust_alerts:
  - condition: score < 500
    notify:
      - slack: #agent-alerts
      - email: admin@company.com
  - condition: score drops by > 100 in 1h
    notify:
      - pagerduty: agent-oncall
      - action: activate_kill_switch
```

---

## Next steps

- [Policies](./policies.md) â€” Write trust-based conditional policies
- [Recipe: Agent Sandbox Isolation](../recipes/agent-sandbox-isolation.md)
- [Security Best Practices](../guides/security-best-practices.md)
