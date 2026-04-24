# Recipe: High-Risk Action Approval

## What you'll learn

- Define high-risk actions
- Require multi-person approval
- Set emergency override procedures
- Audit high-risk decisions

---

## Use Case
Transferring funds, deleting user accounts, or accessing sensitive data are high-risk actions that need multiple approvals.

---

## Policy

```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: high-risk-actions
spec:
  trigger:
    any:
      - action: funds.transfer
        condition: amount > 10000
      - action: user.delete
      - action: admin.access
      - action: data.export
  enforcement:
    type: require_approval
    approvers: [role:manager, role:security]
    require_all: true
    timeout: 4h
    notify:
      - email: security@company.com
      - slack: #security-alerts
  audit:
    level: comprehensive
    retention: 10years
```

---

## Emergency Override

```python
# In true emergencies, executive can override
CITADEL.approvals.override(
    approval_id="app_123",
    executive_id="ceo@company.com",
    reason="Critical system outage, emergency patch required",
    requires_second_approval=True  # CFO must also approve
)
```

---

## Next steps

- [Core Concepts: Approvals](../core-concepts/approvals.md)
- [Core Concepts: Kill Switch](../core-concepts/kill-switch.md)
