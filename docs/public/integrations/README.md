# Framework Integrations

Citadel's active integration story is runtime spend enforcement and decision evidence for agent actions. Broader framework orchestration examples are preserved under archive/legacy as compatibility/reference material.

## Available Integrations

| Framework | Status | Description |
|-----------|--------|-------------|
| [K2.6 (Moonshot AI)](kimi-k26.md) | âœ… Stable | Governed agents, tasks, and workflows |
| [Codex (OpenAI)](codex.md) | âœ… Stable | Code generation with security review |
| [Claude Code (Anthropic)](claude-code.md) | âœ… Stable | Agent actions with file controls |
| [LangChain](langchain.md) | âœ… Stable | Callback handler and chain governance |
| [AutoGen](autogen.md) | âœ… Stable | Conversational agent governance |

## Common Patterns

All integrations follow these patterns:

### 1. Citadel Client

```python
import citadel

client = citadel.CitadelClient(
    base_url="http://localhost:8000",
    api_key="your-api-key",
)
```

### 2. Governed Wrapper

```python
from citadel.integrations.k2_6 import GovernedK26Agent

agent = GovernedK26Agent(
    citadel_client=client,
    name="my-agent",
    description="What it does",
)
```

### 3. Execute with Governance

```python
result = await agent.execute(...)

# Result is always a dict with:
# - status: "executed" | "blocked" | "pending_approval"
# - reason: str (if blocked)
# - approval_id: str (if pending)
# - result: any (if executed)
```

### 4. Handle All Outcomes

```python
if result["status"] == "executed":
    return result["result"]
elif result["status"] == "blocked":
    logger.warning(f"Blocked: {result['reason']}")
    return None
elif result["status"] == "pending_approval":
    await notify_approver(result["approval_id"])
    return {"status": "awaiting_approval"}
```

## Creating Custom Integrations

See [Custom Integration Guide](custom-integration.md) for building your own governed wrappers.

## Compliance

All integrations provide:
- **Policy enforcement** â€” Pre-flight checks on every action
- **Approval workflows** â€” Human-in-the-loop for sensitive operations
- **Audit trails** â€” Hash-chained, tamper-evident logs
- **Kill switches** â€” Emergency stop capability
- **Compliance reports** â€” SOC2, GDPR, NIST mappings

## Support

- [GitHub Issues](https://github.com/casss20/ledger-sdk/issues)
- [Discord Community](https://discord.com/invite/clawd)
