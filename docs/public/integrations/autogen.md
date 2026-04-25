# AutoGen Integration

## What you'll learn

- Install CITADEL's AutoGen conversation interceptors
- Govern agent-to-agent messages
- Control tool access per agent in a group chat
- Audit entire agent conversations

---

## Installation

```bash
pip install citadel-governance[autogen]
# or
pip install citadel-governance pyautogen
```

---

## Basic Integration

```python
from autogen import ConversableAgent, GroupChat
from citadel.integrations.autogen import CITADELAgentInterceptor

# Initialize CITADEL
import citadel
CITADEL = citadel.Client(api_key="ldk_test_...")

# Create interceptor
interceptor = CITADELAgentInterceptor(
    client=CITADEL,
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
records = CITADEL.audit.query(
    conversation_id="planning-meeting-01"
)

for record in records:
    print(f"{record.agent}: {record.action} -> {record.decision}")
```

---

## Next steps

- [Recipe: Agent-to-Agent Authentication](../recipes/agent-to-agent-authentication.md)
- [Core Concepts: Audit Trail](../core-concepts/audit-trail.md)
