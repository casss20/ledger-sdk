# Recipe: Emergency Shutdown Procedure

## What you'll learn

- Activate kill switch for all agents
- Verify shutdown propagation
- Handle in-flight actions
- Resume after incident resolution

---

## Use Case
A security breach is detected. You need to immediately halt all agent activity while investigating.

---

## Immediate Shutdown

```python
# Stop everything
CITADEL.kill_switch.activate(
    scope="organization",
    reason="Security breach investigation - unauthorized data access detected",
    duration="indefinite",
    require_cso_approval=True
)
```

---

## Verify Propagation

```python
# Check all agents are stopped
agents = CITADEL.agents.list()
for agent in agents:
    status = CITADEL.agents.get_status(agent.id)
    assert status.state == "stopped", f"Agent {agent.id} still running!"

print("All agents stopped successfully")
```

---

## Handle In-Flight Actions

In-flight actions at shutdown time are handled according to policy:
- **Allowed actions**: Complete normally
- **Approval-required actions**: Cancel, notify approvers
- **Pending actions**: Queue for post-incident review

---

## Gradual Resume

```python
# Resume low-risk agents first
CITADEL.kill_switch.deactivate(
    agent_id="monitoring-agent",
    reason="Low risk, monitoring only"
)

# Wait for confirmation
 time.sleep(300)

# Resume medium-risk
CITADEL.kill_switch.deactivate(
    namespace="customer-support",
    reason="Support queue backing up"
)

# Finally resume all
CITADEL.kill_switch.deactivate(
    scope="organization",
    reason="Investigation complete, no compromise confirmed"
)
```

---

## Next steps

- [Core Concepts: Kill Switch](../core-concepts/kill-switch.md)
- [Guide: Incident Response](../guides/incident-response.md)
