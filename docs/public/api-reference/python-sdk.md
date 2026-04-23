# Python SDK Reference

## Installation

```bash
pip install ledger-sdk
```

## Client

```python
import ledger_sdk

ledger = ledger_sdk.Client(
    api_key="ldk_test_...",
    environment="sandbox"  # or "production"
)
```

## Govern Actions

```python
action = ledger.govern(
    agent_id="agent-123",
    action="email.send",
    params={"to": "user@example.com", "subject": "Welcome"}
)

result = action.execute()
```

## Exception Handling

| Exception | When | Attributes |
|-----------|------|------------|
| `PolicyDeniedError` | Action blocked | `policy_name`, `reason` |
| `ApprovalRequiredError` | Needs human review | `approval_url`, `timeout` |
| `RateLimitError` | Too many requests | `retry_after`, `limit`, `window` |
| `KillSwitchActivatedError` | Agent stopped | `scope`, `reason` |
| `AuthenticationError` | Invalid credentials | `agent_id` |

## Audit

```python
# Query
records = ledger.audit.query(agent_id="agent-123", limit=100)

# Get by token
record = ledger.audit.get("gt_...")

# Verify chain
is_valid = ledger.audit.verify_chain(record)
```

## Kill Switch

```python
ledger.kill_switch.activate(agent_id="agent-123", reason="...", duration="1h")
ledger.kill_switch.deactivate(agent_id="agent-123", reason="...")
```

## Approvals

```python
pending = ledger.approvals.list(status="pending")
ledger.approvals.approve(approval_id="app_...", reason="Verified")
ledger.approvals.deny(approval_id="app_...", reason="Suspicious")
```

## Policies

```python
ledger.policies.create(policy_yaml)
ledger.policies.list(namespace="payments")
ledger.policies.delete(name="old-policy")
ledger.policies.test(policy=policy_yaml, sample_actions=[...])
```

## Trust Scoring

```python
score = ledger.trust.get_score(agent_id="agent-123")
ledger.trust.set_alert(threshold=500, notify=["#alerts"])
```
