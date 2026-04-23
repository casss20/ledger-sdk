# Migrating from LangChain Callbacks

## What you'll learn

- Replace LangChain callbacks with Ledger governance
- Migrate existing agent monitoring
- Preserve audit history
- Gradual migration strategy

---

## Comparison

| Feature | LangChain Callbacks | Ledger |
|---------|-------------------|--------|
| Monitoring | Yes | Yes |
| Policy enforcement | No | Yes |
| Kill switch | No | Yes |
| Human approvals | No | Yes |
| Immutable audit | No | Yes |
| Compliance proof | No | Yes |

---

## Migration Steps

### Step 1: Install Ledger
```bash
pip install ledger-sdk[langchain]
```

### Step 2: Add Ledger handler alongside callbacks
```python
from langchain.callbacks import FileCallbackHandler
from ledger_sdk.integrations.langchain import LedgerCallbackHandler

# Keep existing callbacks
file_handler = FileCallbackHandler("agent.log")

# Add Ledger governance
ledger = ledger_sdk.Client(api_key="ldk_test_...")
ledger_handler = LedgerCallbackHandler(
    client=ledger,
    agent_id="migration-agent-01"
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    callbacks=[file_handler, ledger_handler]  # Both active
)
```

### Step 3: Configure policies
```yaml
apiVersion: ledger.gov/v1
kind: Policy
metadata:
  name: migration-policy
spec:
  trigger:
    action: "*"
  enforcement:
    type: alert_only  # Monitor first, don't block
```

### Step 4: Gradually enforce
After 2 weeks of monitoring:
```yaml
enforcement:
  type: conditional
  conditions:
    - if: action in ["email.send", "database.write"]
      then: require_approval
    - else: allow
```

### Step 5: Remove old callbacks
Once confident, remove legacy callbacks:
```python
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    callbacks=[ledger_handler]  # Only Ledger
)
```

---

## Preserving History

Export LangChain logs and import to Ledger:
```python
ledger.migration.import_logs(
    source="langchain",
    path="/path/to/callback/logs",
    agent_id="migration-agent-01"
)
```

---

## Next steps

- [Integration: LangChain](../integrations/langchain.md)
- [Core Concepts: Policies](../core-concepts/policies.md)
