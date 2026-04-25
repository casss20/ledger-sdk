# Anthropic SDK Integration

## What you'll learn

- Govern Anthropic Claude tool use
- Content moderation with CITADEL policies
- Streaming response governance
- Multi-turn conversation audit

---

## Installation

```bash
pip install citadel-governance[anthropic]
```

---

## Basic Integration

```python
from anthropic import Anthropic
from citadel.integrations.anthropic import CITADELAnthropicMiddleware

import citadel
CITADEL = citadel.Client(api_key="ldk_test_...")

middleware = CITADELAnthropicMiddleware(client=CITADEL, agent_id="claude-agent-01")

client = Anthropic(api_key="sk-ant-...")

response = middleware.wrap_message(
    client.messages.create,
    model="claude-3-opus-20240229",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Send refund email"}],
    tools=[refund_tool]
)
```

---

## Tool Governance

```python
middleware.register_tool_policy(tool_name="refund_tool", policy="refund-approval-over-1000")
middleware.register_default_policy(policy="all-tools-require-approval")
```

---

## Content Moderation

```python
middleware.add_output_guard(policy="harmful-content", action="block")
middleware.add_output_guard(policy="pii-redaction", action="redact")
```

---

## Next steps

- [Recipe: High-Risk Action Approval](../recipes/high-risk-action-approval.md)
- [Core Concepts: Approvals](../core-concepts/approvals.md)
