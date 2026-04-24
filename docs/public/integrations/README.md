# Framework Integrations

Citadel provides governed wrappers for popular AI agent frameworks. Each integration includes policy enforcement, approval workflows, and audit trails.

## Available Integrations

| Framework | Status | Description |
|-----------|--------|-------------|
| [K2.6 (Moonshot AI)](kimi-k26.md) | ✅ Stable | Governed agents, tasks, and workflows |
| [LangGraph](langgraph.md) | ✅ Stable | Governed nodes and state graphs |
| [Codex (OpenAI)](codex.md) | ✅ Stable | Code generation with security review |
| [Claude Code (Anthropic)](claude-code.md) | ✅ Stable | Agent actions with file controls |
| [LangChain](langchain.md) | ✅ Stable | Callback handler and chain governance |
| [CrewAI](crewai.md) | ✅ Stable | Role-based crew governance |
| [AutoGen](autogen.md) | ✅ Stable | Conversational agent governance |
| [OpenAI](openai-agents.md) | ✅ Stable | OpenAI client wrapper |

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
- **Policy enforcement** — Pre-flight checks on every action
- **Approval workflows** — Human-in-the-loop for sensitive operations
- **Audit trails** — Hash-chained, tamper-evident logs
- **Kill switches** — Emergency stop capability
- **Compliance reports** — SOC2, GDPR, NIST mappings

## Support

- [GitHub Issues](https://github.com/casss20/ledger-sdk/issues)
- [Discord Community](https://discord.com/invite/clawd)
