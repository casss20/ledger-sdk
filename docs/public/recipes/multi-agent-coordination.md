# Recipe: Multi-Agent Coordination

## What you'll learn

- Authenticate agent-to-agent communication
- Trace actions across agent chains
- Govern handoffs between agents
- Audit multi-agent workflows

---

## Use Case
Your customer support pipeline uses three agents: triage → resolution → follow-up. Each handoff must be authenticated and audited.

---

## Architecture

```
Triage Agent
    ↓ [gt_token + auth]
Resolution Agent
    ↓ [gt_token + auth]
Follow-up Agent
```

---

## Implementation

### Agent authentication

```python
# Triage agent authenticates resolution agent
auth_token = citadel.agents.authenticate(
    from_agent="triage-agent",
    to_agent="resolution-agent",
    task_id="ticket-123"
)

# Resolution agent verifies
is_valid = citadel.agents.verify_auth(
    agent_id="resolution-agent",
    token=auth_token
)

# Resolution agent completes task, passes to follow-up
next_token = citadel.agents.authenticate(
    from_agent="resolution-agent",
    to_agent="follow-up-agent",
    task_id="ticket-123"
)
```

### Trace context propagation

```python
# Start trace
trace = citadel.traces.start(name="customer-ticket-123")

# Triage agent
action1 = citadel.govern(
    agent_id="triage-agent",
    action="ticket.triage",
    trace_id=trace.id
)

# Resolution agent continues trace
action2 = citadel.govern(
    agent_id="resolution-agent",
    action="ticket.resolve",
    trace_id=trace.id
)

# View full trace
citadel.traces.get(trace.id)
```

---

## Next steps

- [Core Concepts: Governance Tokens](../core-concepts/governance-tokens.md)
- [Recipe: Agent-to-Agent Authentication](agent-to-agent-authentication.md)
