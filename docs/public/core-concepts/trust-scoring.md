# Agent Trust Scoring

## What you'll learn

- How Citadel computes deterministic trust scores
- The five trust bands and what they mean
- How trust influences policy without replacing it
- Probation for new agents
- Circuit breakers and escalation
- Trust audit and replay

---

## Overview

Every agent in Citadel has a **trust score** from 0.00 to 1.00, computed from deterministic behavioral signals. The score maps to one of five **trust bands** that influence policy enforcement:

| Band | Score Range | Meaning |
|------|-------------|---------|
| **REVOKED** | 0.00 – 0.19 | Identity disabled. Emergency state. |
| **PROBATION** | 0.20 – 0.39 | Strict monitoring. New or low-trust agents. |
| **STANDARD** | 0.40 – 0.59 | Normal operation. Default for established agents. |
| **TRUSTED** | 0.60 – 0.79 | Elevated privileges. Demonstrated reliability. |
| **HIGHLY_TRUSTED** | 0.80 – 1.00 | Full privileges. Long history of reliability. |

Trust is **not authorization**. Trust is a governance signal that enriches the policy context. The policy engine remains the sole authority on ALLOW/DENY. Trust adds constraints (approval requirements, rate limits, action blocks) but never removes constraints or overrides a policy denial.

---

## How Trust Works

```
Agent requests action
    ↓
Kill Switch Check (first gate — trust never bypasses)
    ↓
Trust Evaluation → Band, Score, Constraints
    ↓
Policy Evaluation → ALLOW / DENY / REQUIRE_APPROVAL
    ↓
Merge Trust Constraints → May add approval, reduce quota
    ↓
Decision Recorded (with trust_snapshot_id for replay)
    ↓
Token Issued / Action Executed
```

Every decision stores `trust_snapshot_id` — the exact trust context active at decision time. Full replay capability for audit.

The dashboard uses that same `trust_snapshot_id` to show a decision-level factor breakdown. It reads the stored `actor_trust_snapshots.factors` JSON and raw inputs for the selected decision; it does not recompute trust in the browser.

---

## Score Components

Trust scores are computed deterministically from 9 weighted factors:

| Factor | Weight | What It Measures |
|--------|--------|-----------------|
| Identity verification | 0.25 | Has the agent completed cryptographic identity verification? |
| Health score | 0.20 | Agent operational health (0–100) |
| Identity age | 0.15 max | How long since agent creation (0.5% per day, capped at 30 days) |
| Compliance record | 0.15 | Policy violations in the last 7 days |
| Quarantine status | 0.10 | Major penalty (-0.30) if quarantined |
| Action rate | 0.10 | Daily action volume (suspicious if >1000) |
| Budget adherence | 0.05 | Token spend vs. budget ratio |
| Challenge reliability | 0.05 | Pass rate on cryptographic challenges |
| Score trend | 0.03 | Rapid improvement/drop bonus or penalty |

```python
# Get an agent's current trust snapshot
snapshot = citadel.trust.get_snapshot(agent_id="email-agent-01")
print(f"Score: {snapshot.score}")
print(f"Band: {snapshot.band}")  # REVOKED, PROBATION, STANDARD, TRUSTED, HIGHLY_TRUSTED
print(f"Factors: {snapshot.factors}")
print(f"Snapshot ID: {snapshot.snapshot_id}")  # For audit replay
```

Example response:
```json
{
  "score": 0.75,
  "band": "TRUSTED",
  "snapshot_id": "snap_550e8400-e29b-41d4-a716-446655440000",
  "factors": {
    "verification": 0.25,
    "health": 0.20,
    "age": 0.12,
    "compliance": 0.15,
    "action_rate": 0.05,
    "budget_adherence": 0.05,
    "challenge_reliability": 0.03,
    "quarantine": 0.0,
    "trend": 0.0
  },
  "computed_at": "2026-04-27T14:30:00Z"
}
```

In the Audit Explorer, selecting a decision-linked audit event shows:

- Snapshot ID used by the decision
- Score and trust band
- Computation timestamp and method
- Contributions for the 9 stored factors
- Raw inputs collapsed into the audit payload for replay

---

## Trust Bands and Policy

Each band has deterministic constraints:

| Band | Approval Required | Spend Multiplier | Rate Limit | Blocked Actions |
|------|-------------------|-----------------|------------|----------------|
| **REVOKED** | All actions | 0% | 0% | execute, delegate, handoff, gather |
| **PROBATION** | delegate, handoff, gather, destroy | 50% | 50% | delegate, handoff |
| **STANDARD** | destroy, revoke | 100% | 100% | — |
| **TRUSTED** | destroy | 150% | 200% | — |
| **HIGHLY_TRUSTED** | destroy only | 200% | 500% | — |

### Important Rules

1. **Kill switch is always checked first** — trust never bypasses emergency stop
2. **Trust can only ADD constraints** — it cannot remove a policy denial
3. **Even HIGHLY_TRUSTED requires approval for `destroy`** — no band bypasses destructive action controls
4. **Probation overrides band** — if `probation_until` > now, agent is treated as PROBATION regardless of score

---

## Building Trust

New agents start in **PROBATION** (score 0.30, 7-day default). To exit probation:

1. **Minimum 3 days** in probation
2. **Score >= 0.40** for 48 consecutive hours
3. **No violations** during probation
4. **Operator approval** (optional fast-track)

Trust gain/loss examples:

| Event | Impact |
|-------|--------|
| Verified identity | +0.25 (one-time) |
| 30 days uptime | +0.15 (age cap) |
| Health score 100 | +0.20 |
| Quarantined | -0.30 (major penalty) |
| 1000+ actions/day | -0.10 (suspicious rate) |
| 3+ violations in 7 days | -0.15 |
| Rapid score drop (>0.15) | -0.03 (trend penalty) |
| Rapid score rise (>0.15) | +0.02 (trend bonus) |

---

## Probation

Probation is the strictest monitoring state for new or recovered agents:

```python
# Check probation status
status = citadel.trust.get_probation_status(agent_id="new-agent-01")
print(f"Probation until: {status.probation_until}")
print(f"Reason: {status.probation_reason}")

# Extend probation (operator action)
citadel.trust.extend_probation(
    agent_id="new-agent-01",
    days=7,
    reason="Policy violation during probation"
)
```

**Probation rules:**
- All actions are logged at `INFO` level
- `execute` requires introspection
- `delegate`, `handoff`, `gather` are **blocked**
- `destroy` is **blocked**
- Quotas at 50%
- Max probation duration: 30 days (operator can extend)

---

## Circuit Breaker

When an agent's score drops below 0.15, the circuit breaker stages a REVOKED transition:

```
Score < 0.15
    └── STAGE: Prepare REVOKED
          ├── Score stays < 0.15 for 5 minutes → REVOKE
          └── Score recovers → Cancel staging
```

```python
# Check circuit breaker status
cb = citadel.trust.check_circuit_breaker(agent_id="agent-01")
if cb.staged:
    print(f"REVOKED staging: {cb.reason}")
```

---

## Trust-Based Policies

Use trust bands in policy conditions:

```yaml
spec:
  trigger:
    action: database.write
    condition: environment == "production"
  enforcement:
    type: conditional
    conditions:
      - if: trust_band == "HIGHLY_TRUSTED"
        then: allow
      - if: trust_band == "TRUSTED"
        then: require_approval
      - if: trust_band == "STANDARD"
        then: require_approval
      - if: trust_band in ["PROBATION", "REVOKED"]
        then: deny
```

---

## Operator Overrides

In emergencies, operators can manually set an agent's band:

```python
# Emergency revoke
citadel.trust.operator_override(
    agent_id="agent-01",
    target_band="REVOKED",
    operator_id="op-123",
    reason="Security incident — emergency stop"
)

# Restore to probation after investigation
citadel.trust.operator_override(
    agent_id="agent-01",
    target_band="PROBATION",
    operator_id="op-123",
    reason="Investigation complete — cleared for probation"
)
```

**Override rules:**
- Requires explicit reason
- Creates HIGH severity audit event
- Dual approval recommended for production
- 24h expiration unless renewed

---

## Trust Alerts

Configure alerts for trust changes:

```yaml
trust_alerts:
  - condition: band == "REVOKED"
    notify:
      - slack: #security-alerts
      - pagerduty: agent-oncall
  - condition: band changed from "TRUSTED" to "STANDARD"
    notify:
      - slack: #agent-alerts
      - email: admin@company.com
  - condition: probation extended
    notify:
      - slack: #agent-alerts
```

---

## Audit and Replay

Every trust change is recorded in the audit trail:

| Event Type | When | Data |
|---|---|---|
| `TRUST_BAND_CHANGED` | Band changes | before/after band, score, snapshot_id, reason |
| `TRUST_SCORE_COMPUTED` | Every computation | score, band, factors, raw_inputs |
| `TRUST_PROBATION_STARTED` | Probation begins | probation_until, reason |
| `TRUST_PROBATION_ENDED` | Probation expires | reason |
| `TRUST_PROBATION_EXTENDED` | Probation extended | new_until, reason |
| `TRUST_OVERRIDE` | Operator sets band | operator_id, from/to band, reason |
| `TRUST_CIRCUIT_BREAKER` | Emergency drop | from/to score/band, reason |
| `TRUST_KILL_SWITCH_DROP` | Kill switch → REVOKED | previous_band, kill_switch_reason |

Replay a decision's trust context:
```python
# Get the trust snapshot used for a decision
snapshot = citadel.trust.get_snapshot_by_id(
    snapshot_id="snap_550e8400..."  # from decision record
)
# Reconstruct exact policy evaluation context
```

---

## Next steps

- [Policies](./policies.md) — Write trust-based conditional policies
- [Approvals](./approvals.md) — How trust bands affect approval requirements
- [Kill Switch](./kill-switch.md) — Emergency stops and trust interaction
- [Audit Trail](./audit-trail.md) — Full audit event reference
- [Trust Architecture Guide](../guides/trust-architecture.md) — Deep-dive architecture documentation
- [Recipe: Agent Sandbox Isolation](../recipes/agent-sandbox-isolation.md)
