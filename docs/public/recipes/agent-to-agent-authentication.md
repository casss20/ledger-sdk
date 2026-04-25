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

```bash
# Register both agents
curl -X POST https://api.citadelsdk.com/api/agent-identities \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "agent-a", "name": "Processor", "tenant_id": "demo"}'

curl -X POST https://api.citadelsdk.com/api/agent-identities \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "agent-b", "name": "Validator", "tenant_id": "demo"}'
```

### Verify both agents

```bash
# Operator verifies both agents
curl -X POST https://api.citadelsdk.com/api/agent-identities/agent-a/verify \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{"verifier_id": "op-admin"}'

curl -X POST https://api.citadelsdk.com/api/agent-identities/agent-b/verify \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{"verifier_id": "op-admin"}'
```

### Issue capability token (Agent A → Agent B)

```bash
# Agent A requests capability to interact with Agent B's resource
curl -X POST https://api.citadelsdk.com/api/agent-identities/agent-a/capability \
  -H "Authorization: Bearer $AGENT_A_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "delegate",
    "resource": "agent-b",
    "context": {"permissions": ["read", "write"], "correlation_id": "task-123"}
  }'
```

### Verify on receipt (Agent B checks)

```bash
# Agent B checks trust of Agent A before accepting work
curl https://api.citadelsdk.com/api/agent-identities/agent-a/trust \
  -H "Authorization: Bearer $AGENT_B_API_KEY"
```

---

## Next steps

- [Core Concepts: Governance Tokens](../core-concepts/governance-tokens.md)
- [Core Concepts: Trust Scoring](../core-concepts/trust-scoring.md)
