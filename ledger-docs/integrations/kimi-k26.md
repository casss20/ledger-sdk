# Kimi K2.6 Integration

## What you'll learn

- Intercept Kimi tool-use calls with Ledger governance
- Govern streaming and batch completions
- Policy-based content filtering for Kimi outputs
- Audit trail for every Kimi API call

---

## Installation

```bash
pip install ledger-sdk[kimi]
```

---

## Basic Integration

```python
from openai import OpenAI
from ledger_sdk.integrations.kimi import LedgerKimiMiddleware

import ledger_sdk
ledger = ledger_sdk.Client(api_key="ldk_test_...")

middleware = LedgerKimiMiddleware(client=ledger, agent_id="kimi-agent-01")

client = OpenAI(api_key="sk-...", base_url="https://api.moonshot.cn/v1")

response = middleware.wrap_completion(
    client.chat.completions.create,
    model="kimi-k2.6",
    messages=[{"role": "user", "content": "Write an email to customer"}],
    tools=[send_email_function]
)
```

---

## Tool-Use Governance

Intercept tool calls before execution:

```python
tools = [{
    "type": "function",
    "function": {
        "name": "send_email",
        "parameters": {"to": {"type": "string"}, "subject": {"type": "string"}}
    }
}]

result = middleware.wrap_tools(tools=tools, policies=["email-approval-external"])
```

---

## Next steps

- [Recipe: PII Handling Policy](../recipes/pii-handling-policy.md)
- [Core Concepts: Policies](../core-concepts/policies.md)
