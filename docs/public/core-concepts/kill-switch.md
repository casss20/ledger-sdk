# Kill Switch and Emergency Stops

## What you'll learn

- How the kill switch works at the kernel level
- Three types of emergency stops
- Kill switch and trust band interaction
- EU AI Act Article 14 compliance
- Testing kill switches without disrupting production
- Role-based kill switch access control

---

## Overview

The kill switch is Citadel's emergency halt mechanism. It can stop any agent, any agent group, or all agents in an organization — within 100ms.

This isn't a monitoring alert or a dashboard button that "suggests" stopping. It's a kernel-level circuit breaker that physically prevents agent execution.

> 💡 **Regulatory context:** EU AI Act Article 14(4)(e) requires "a stop button or similar procedure" for high-risk AI systems. Citadel's kill switch satisfies this requirement architecturally — not as a bolt-on feature.

---

## Kill Switch Types

### 1. Agent-level kill switch

Stop a single agent:

```python
citadel.kill_switch.activate(
    agent_id="email-agent-01",
    reason="Suspicious activity detected",
    duration="1h"  # Auto-resume after 1 hour, or "indefinite"
)
```

### 2. Namespace-level kill switch

Stop all agents in a namespace:

```python
citadel.kill_switch.activate(
    namespace="payments",
    reason="Finance system maintenance",
    duration="4h"
)
```

### 3. Organization-wide kill switch

Emergency stop everything:

```python
citadel.kill_switch.activate(
    scope="organization",
    reason="Security breach investigation",
    duration="indefinite",
    require_cso_approval=True  # Chief Security Officer must approve reactivation
)
```

### 4. Trust-drop kill switch (automated)

When an agent's trust score drops below 0.20, the kill switch activates automatically:

```python
# Agent trust score drops to 0.15
# → Kill switch activates automatically
# → Agent band transitions to REVOKED
# → Audit event: TRUST_KILL_SWITCH_DROP
```

This is distinct from manual kill switches — it's a trust-driven circuit breaker that stages REVOKED status when scores collapse.

---

## How It Works

The kill switch operates at the **kernel level** — below your application code:

```
Agent requests action
    ↓
Kill Switch Check (first gate, <1ms)
    ↓
    [STOPPED?] → Return KillSwitchActivatedError
    [RUNNING?] → Continue to policy evaluation
    ↓
Trust Evaluation → Band, Score, Constraints
    ↓
Policy evaluation
    ↓
Action execution
```

Because the check happens before policy evaluation, a stopped agent cannot bypass governance by exploiting policy loopholes. Trust evaluation happens **after** the kill switch check, so trust never overrides emergency stops.

For high-risk `gt_cap_` execution paths, the kill switch is also enforced through centralized introspection. A runtime gateway calls `POST /v1/introspect` before the next protected operation. If a global, workspace, actor, action/tool, or resource kill switch matches the token's scope, introspection returns:

```json
{
  "active": false,
  "reason": "kill_switch_active",
  "kill_switch": true
}
```

This invalidates future protected operations without waiting for token expiry. It does not magically stop arbitrary in-flight code; long-running workers should re-check Citadel between critical steps.

---

## Trust Kill Switch Interaction

### Kill switch before trust

The kill switch is always the **first gate**. Even a HIGHLY_TRUSTED agent with a score of 0.95 will be blocked if the kill switch is active.

### Trust circuit breaker

When an agent's score drops below 0.15, the circuit breaker stages REVOKED status:

```
Score < 0.15
    └── STAGE: Prepare REVOKED
          ├── Score stays < 0.15 for 5 minutes → REVOKE + kill_switch
          └── Score recovers → Cancel staging
```

### Kill switch → trust drop

When a manual kill switch is activated:
- The agent's trust band transitions to **REVOKED**
- A `TRUST_KILL_SWITCH_DROP` audit event is recorded
- The previous band and score are preserved for restoration

### Restoring after kill switch

```python
# Deactivate kill switch
citadel.kill_switch.deactivate(
    agent_id="email-agent-01",
    reason="Investigation complete, false positive"
)

# Trust band is restored (operator sets target band)
citadel.trust.operator_override(
    agent_id="email-agent-01",
    target_band="PROBATION",
    operator_id="op-123",
    reason="Restored after kill switch — probation review"
)
```

---

## Activation Methods

### Via dashboard
Navigate to **Kill Switch Panel** → Select agent/namespace → Enter reason → Confirm with MFA.

### Via API
```python
citadel.kill_switch.activate(agent_id="...", reason="...")
```

### Via CLI
```bash
citadel kill-switch activate --agent-id email-agent-01 --reason "Suspicious patterns"
```

### Via webhook (automated)
Configure automatic kill switch triggers:
```yaml
automated_triggers:
  - condition: trust_band == "REVOKED"
    action: activate_kill_switch
    scope: agent
  - condition: trust_score < 0.20
    action: activate_kill_switch
    scope: agent
  - condition: anomaly_score > 0.95
    action: activate_kill_switch
    scope: namespace
```

---

## Deactivation

Resume an agent:

```python
citadel.kill_switch.deactivate(
    agent_id="email-agent-01",
    reason="Investigation complete, false positive"
)
```

> ⚠️ **Security note:** Organization-wide kill switches require CSO approval to deactivate. This prevents a single compromised admin account from reactivate a stopped system.

---

## Testing Kill Switches

Test in staging without affecting production:

```python
# Staging environment test
citadel = citadel.Client(
    api_key="ldk_test_...",
    environment="sandbox"
)

# Activate kill switch
citadel.kill_switch.activate(agent_id="test-agent", reason="Test")

# Attempt action (should fail)
try:
    action = citadel.govern(agent_id="test-agent", action="test.action")
    action.execute()
except citadel.KillSwitchActivatedError:
    print("Kill switch working correctly")

# Deactivate
citadel.kill_switch.deactivate(agent_id="test-agent", reason="Test complete")
```

> 💡 **Best practice:** Run kill switch tests monthly in staging. Add to your CI/CD pipeline.

---

## Audit Trail

Every kill switch activation/deactivation is recorded:

```python
records = citadel.audit.query(action="kill_switch.activate")
for record in records:
    print(f"{record.timestamp}: {record.actor} stopped {record.target}")
    print(f"  Reason: {record.reason}")
    print(f"  Previous trust band: {record.previous_trust_band}")
    print(f"  Previous trust score: {record.previous_trust_score}")
    print(f"  Token: {record.governance_token}")
```

---

## Role-Based Access

| Role | Activate Agent | Activate Namespace | Activate Organization | Deactivate |
|------|---------------|-------------------|----------------------|------------|
| Operator | Own agents only | No | No | Own agents only |
| Admin | Any agent | Yes | No | Any (except org-wide) |
| Executive | Any agent | Yes | Yes | Any |
| Auditor | View only | View only | View only | No |

---

## Next steps

- [Incident Response Guide](../guides/incident-response.md) — Full incident playbook
- [Trust Scoring](./trust-scoring.md) — How trust bands interact with kill switches
- [Recipe: Emergency Shutdown Procedure](../recipes/emergency-shutdown-procedure.md)
- [Recipe: Trust-Based Kill Switch Rules](../recipes/trust-based-kill-switch-rules.md)
