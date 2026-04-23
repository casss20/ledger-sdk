# Kill Switch and Emergency Stops

## What you'll learn

- How the kill switch works at the kernel level
- Three types of emergency stops
- EU AI Act Article 14 compliance
- Testing kill switches without disrupting production
- Role-based kill switch access control

---

## Overview

The kill switch is Ledger's emergency halt mechanism. It can stop any agent, any agent group, or all agents in an organization — within 100ms.

This isn't a monitoring alert or a dashboard button that "suggests" stopping. It's a kernel-level circuit breaker that physically prevents agent execution.

> 💡 **Regulatory context:** EU AI Act Article 14(4)(e) requires "a stop button or similar procedure" for high-risk AI systems. Ledger's kill switch satisfies this requirement architecturally — not as a bolt-on feature.

---

## Kill Switch Types

### 1. Agent-level kill switch

Stop a single agent:

```python
ledger.kill_switch.activate(
    agent_id="email-agent-01",
    reason="Suspicious activity detected",
    duration="1h"  # Auto-resume after 1 hour, or "indefinite"
)
```

### 2. Namespace-level kill switch

Stop all agents in a namespace:

```python
ledger.kill_switch.activate(
    namespace="payments",
    reason="Finance system maintenance",
    duration="4h"
)
```

### 3. Organization-wide kill switch

Emergency stop everything:

```python
ledger.kill_switch.activate(
    scope="organization",
    reason="Security breach investigation",
    duration="indefinite",
    require_cso_approval=True  # Chief Security Officer must approve reactivation
)
```

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
Policy evaluation
    ↓
Action execution
```

Because the check happens before policy evaluation, a stopped agent cannot bypass governance by exploiting policy loopholes.

---

## Activation Methods

### Via dashboard
Navigate to **Kill Switch Panel** → Select agent/namespace → Enter reason → Confirm with MFA.

### Via API
```python
ledger.kill_switch.activate(agent_id="...", reason="...")
```

### Via CLI
```bash
ledger kill-switch activate --agent-id email-agent-01 --reason "Suspicious patterns"
```

### Via webhook (automated)
Configure automatic kill switch triggers:
```yaml
automated_triggers:
  - condition: trust_score < 200
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
ledger.kill_switch.deactivate(
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
ledger = ledger_sdk.Client(
    api_key="ldk_test_...",
    environment="sandbox"
)

# Activate kill switch
ledger.kill_switch.activate(agent_id="test-agent", reason="Test")

# Attempt action (should fail)
try:
    action = ledger.govern(agent_id="test-agent", action="test.action")
    action.execute()
except ledger_sdk.KillSwitchActivatedError:
    print("Kill switch working correctly")

# Deactivate
ledger.kill_switch.deactivate(agent_id="test-agent", reason="Test complete")
```

> 💡 **Best practice:** Run kill switch tests monthly in staging. Add to your CI/CD pipeline.

---

## Audit Trail

Every kill switch activation/deactivation is recorded:

```python
records = ledger.audit.query(action="kill_switch.activate")
for record in records:
    print(f"{record.timestamp}: {record.actor} stopped {record.target}")
    print(f"  Reason: {record.reason}")
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
- [Recipe: Emergency Shutdown Procedure](../recipes/emergency-shutdown-procedure.md)
- [Security Best Practices](../guides/security-best-practices.md)
