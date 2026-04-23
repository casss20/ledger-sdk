# Migrating from Microsoft AutoGen

## What you'll learn

- Replace AutoGen's built-in logging with Ledger
- Govern agent conversations
- Migrate group chat monitoring
- Maintain conversation history

---

## Migration Steps

### Step 1: Install Ledger
```bash
pip install ledger-sdk[autogen]
```

### Step 2: Add Ledger interceptor
```python
from autogen import ConversableAgent
from ledger_sdk.integrations.autogen import LedgerAgentInterceptor

ledger = ledger_sdk.Client(api_key="ldk_test_...")
interceptor = LedgerAgentInterceptor(
    client=ledger,
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
ledger.migration.import_conversations(
    source="autogen",
    path="/path/to/autogen/logs",
    conversation_id="migrated-chat-01"
)
```

### Step 4: Enable governance
```python
# Start with monitoring only
ledger.policies.create({
    name: "autogen-monitor",
    trigger: {"action": "*"},
    enforcement: {"type": "alert_only"}
})
```

---

## Next steps

- [Integration: AutoGen](../integrations/autogen.md)
- [Recipe: Multi-Agent Coordination](../recipes/multi-agent-coordination.md)
