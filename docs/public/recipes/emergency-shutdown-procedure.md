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

```bash
# Activate kill switch for entire tenant
curl -X POST https://api.citadelsdk.com/api/v1/governance/kill-switch \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "tenant",
    "reason": "Security breach investigation - unauthorized data access detected"
  }'
```

---

## Verify Propagation

```bash
# Check all agents are stopped
curl https://api.citadelsdk.com/api/agents \
  -H "Authorization: Bearer $ADMIN_JWT" | jq '.agents[] | {agent_id, quarantined}'
```

---

## Handle In-Flight Actions

In-flight actions at shutdown time are handled according to policy:
- **Allowed actions**: Complete normally
- **Approval-required actions**: Cancel, notify approvers
- **Pending actions**: Queue for post-incident review

---

## Gradual Resume

```bash
# Clear kill switch for a specific agent (requires admin)
curl -X POST https://api.citadelsdk.com/api/v1/governance/kill-switch/clear \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "monitoring-agent",
    "reason": "Low risk, monitoring only"
  }'

# Then unquarantine
curl -X POST https://api.citadelsdk.com/api/agents/monitoring-agent/quarantine \
  -H "Authorization: Bearer $ADMIN_JWT"
```

---

## Next steps

- [Core Concepts: Kill Switch](../core-concepts/kill-switch.md)
- [Guide: Incident Response](../guides/incident-response.md)
