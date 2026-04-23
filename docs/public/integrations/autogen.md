# AutoGen Integration

## What you'll learn

- Install Ledger's AutoGen conversation interceptors
- Govern agent-to-agent messages
- Control tool access per agent in a group chat
- Audit entire agent conversations

---

## Installation

```bash
pip install ledger-sdk[autogen]
# or
pip install ledger-sdk pyautogen
```

---

## Basic Integration

```python
from autogen import ConversableAgent, GroupChat
from ledger_sdk.integrations.autogen import LedgerAgentInterceptor

# Initialize Ledger
import ledger_sdk
ledger = ledger_sdk.Client(api_key="ldk_test_...")

# Create interceptor
interceptor = LedgerAgentInterceptor(
    client=ledger,
    conversation_id="planning-meeting-01"
)

# Create governed agents
planner = ConversableAgent(
    name="planner",
    system_message="You plan projects",
    interceptors=[interceptor]
)

coder = ConversableAgent(
    name="coder",
    system_message="You write code",
    tools=[code_tool],
    interceptors=[interceptor]
)

# Start conversation
planner.initiate_chat(coder, message="Build a login system")
```

---

## Conversation Governance

All messages and tool calls are logged:

```python
# Query conversation audit
records = ledger.audit.query(
    conversation_id="planning-meeting-01"
)

for record in records:
    print(f"{record.agent}: {record.action} -> {record.decision}")
```

---

## Next steps

- [Recipe: Agent-to-Agent Authentication](../recipes/agent-to-agent-authentication.md)
- [Core Concepts: Audit Trail](../core-concepts/audit-trail.md)
