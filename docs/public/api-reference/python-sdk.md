# Python SDK Reference

## Installation

```bash
pip install citadel-governance
```

## Client

```python
import citadel

CITADEL = citadel.Client(
    api_key="ldk_test_...",
    environment="sandbox"  # or "production"
)
```

## Govern Actions

```python
action = citadel.govern(
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
records = CITADEL.audit.query(agent_id="agent-123", limit=100)

# Get by token
record = CITADEL.audit.get("gt_...")

# Verify chain
is_valid = CITADEL.audit.verify_chain(record)
```

## Kill Switch

```python
CITADEL.kill_switch.activate(agent_id="agent-123", reason="...", duration="1h")
CITADEL.kill_switch.deactivate(agent_id="agent-123", reason="...")
```

## Approvals

```python
pending = CITADEL.approvals.list(status="pending")
CITADEL.approvals.approve(approval_id="app_...", reason="Verified")
CITADEL.approvals.deny(approval_id="app_...", reason="Suspicious")
```

## Policies

```python
CITADEL.policies.create(policy_yaml)
CITADEL.policies.list(namespace="payments")
CITADEL.policies.delete(name="old-policy")
CITADEL.policies.test(policy=policy_yaml, sample_actions=[...])
```

## Trust Scoring

```python
score = CITADEL.trust.get_score(agent_id="agent-123")
CITADEL.trust.set_alert(threshold=500, notify=["#alerts"])
```
