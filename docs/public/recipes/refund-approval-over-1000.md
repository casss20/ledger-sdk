# Recipe: Refund Approval Over $1,000

## What you'll learn

- Require human approval for refunds over $1,000
- Route approvals to finance managers
- Set escalation timeouts
- Audit every refund decision

---

## Use Case
Your customer service agent can process refunds automatically for small amounts, but large refunds need manager approval to prevent fraud and errors.

---

## Policy

```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: refund-approval-over-1000
  namespace: payments
spec:
  trigger:
    action: refund.create
    condition: amount > 1000
  enforcement:
    type: require_approval
    approvers: [role:finance-manager]
    timeout: 24h
    escalation: 48h
    notify:
      - slack: #finance-alerts
  audit:
    level: comprehensive
    retention: 7years
```

---

## SDK Implementation

```python
# Attempt refund
action = citadel.govern(
    agent_id="refund-agent-01",
    action="refund.create",
    params={"order_id": "ORD-123", "amount": 2500, "reason": "Defective product"}
)

try:
    result = action.execute()
    print(f"Refund processed: {result.governance_token}")
except CITADEL_sdk.ApprovalRequiredError as e:
    print(f"Approval required: {e.approval_url}")
    # Finance manager receives notification
```

---

## Testing

```python
# Test small refund (should auto-allow)
small = citadel.govern(agent_id="refund-agent", action="refund.create", params={"amount": 500})
assert small.execute().decision == "allowed"

# Test large refund (should require approval)
large = citadel.govern(agent_id="refund-agent", action="refund.create", params={"amount": 2500})
try:
    large.execute()
    assert False, "Should have required approval"
except CITADEL_sdk.ApprovalRequiredError:
    pass  # Expected
```

---

## Next steps

- [Core Concepts: Approvals](../core-concepts/approvals.md)
- [Core Concepts: Policies](../core-concepts/policies.md)
