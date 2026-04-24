# Recipe: Agent-to-Agent Authentication

## What you'll learn

- Issue governance tokens for agent identity
- Verify agent credentials
- Implement mutual authentication
- Audit agent trust relationships

---

## Use Case
When Agent A calls Agent B, both must prove their identity to prevent spoofing and unauthorized delegation.

---

## Implementation

### Register agents

```python
# Register both agents
CITADEL.agents.register(agent_id="agent-a", role="processor")
CITADEL.agents.register(agent_id="agent-b", role="validator")
```

### Issue auth token

```python
# Agent A requests permission to call Agent B
auth_token = CITADEL.agents.authenticate(
    from_agent="agent-a",
    to_agent="agent-b",
    permissions=["read", "write"],
    expiry="1h"
)
```

### Verify on receipt

```python
# Agent B verifies the token
claims = CITADEL.agents.verify_auth(
    agent_id="agent-b",
    token=auth_token
)

print(claims.from_agent)  # "agent-a"
print(claims.permissions)  # ["read", "write"]
print(claims.expiry)  # ISO timestamp
```

### Mutual authentication

```python
# Agent B responds with its own token
response_token = CITADEL.agents.authenticate(
    from_agent="agent-b",
    to_agent="agent-a",
    permissions=["respond"],
    correlation_id=auth_token.id
)
```

---

## Next steps

- [Core Concepts: Governance Tokens](../core-concepts/governance-tokens.md)
- [Core Concepts: Trust Scoring](../core-concepts/trust-scoring.md)
