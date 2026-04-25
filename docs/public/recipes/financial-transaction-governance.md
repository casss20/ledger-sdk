# Recipe: Financial Transaction Governance

## What you'll learn

- Govern payment processing
- Require dual approval for large transactions
- Audit all financial actions
- Integrate with payment processors

---

## Use Case
Your billing agent processes payments. Small payments auto-approve. Large payments need two managers. Failed payments trigger alerts.

---

## Policies

```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: payment-governance
spec:
  trigger:
    action: payment.charge
  enforcement:
    type: conditional
    conditions:
      - if: amount < 100
        then: allow
      - if: amount < 1000
        then: require_approval
        approvers: [role:billing-manager]
      - else: require_approval
        approvers: [role:cfo, role:ceo]
        require_all: true
  audit:
    level: comprehensive
    retention: 10years
```

---

## Implementation

```python
action = citadel.govern(
    agent_id="billing-agent",
    action="payment.charge",
    params={"amount": 5000, "customer": "CUST-123"}
)

try:
    result = action.execute()
except citadel.ApprovalRequiredError as e:
    print(f"Needs CFO + CEO approval: {e.approval_url}")
```

---

## Next steps

- [Core Concepts: Approvals](../core-concepts/approvals.md)
- [Recipe: Refund Approval Over $1,000](refund-approval-over-1000.md)
