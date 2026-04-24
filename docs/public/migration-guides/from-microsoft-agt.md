# Migrating from Microsoft AutoGen

## What you'll learn

- Replace AutoGen's built-in logging with CITADEL
- Govern agent conversations
- Migrate group chat monitoring
- Maintain conversation history

---

## Migration Steps

### Step 1: Install CITADEL
```bash
pip install citadel-sdk[autogen]
```

### Step 2: Add CITADEL interceptor
```python
from autogen import ConversableAgent
from citadel_sdk.integrations.autogen import CITADELAgentInterceptor

CITADEL = citadel_sdk.Client(api_key="ldk_test_...")
interceptor = CITADELAgentInterceptor(
    client=CITADEL,
    conversation_id="migrated-chat-01"
)

# Wrap existing agents
agent = ConversableAgent(
    name="assistant",
    interceptors=[interceptor]
)
```

### Step 3: Migrate conversation history
```python
CITADEL.migration.import_conversations(
    source="autogen",
    path="/path/to/autogen/logs",
    conversation_id="migrated-chat-01"
)
```

### Step 4: Enable governance
```python
# Start with monitoring only
CITADEL.policies.create({
    name: "autogen-monitor",
    trigger: {"action": "*"},
    enforcement: {"type": "alert_only"}
})
```

---

## Next steps

- [Integration: AutoGen](../integrations/autogen.md)
- [Recipe: Multi-Agent Coordination](../recipes/multi-agent-coordination.md)
