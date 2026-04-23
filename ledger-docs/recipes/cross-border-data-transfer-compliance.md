# Recipe: Cross-Border Data Transfer Compliance

## What you'll learn

- Ensure data transfers comply with GDPR/CCPA
- Block transfers to non-compliant regions
- Log all cross-border transfers
- Generate transfer impact assessments

---

## Use Case
Your multi-national agents must not transfer EU customer data to non-adequate countries without safeguards.

---

## Policy

```yaml
apiVersion: ledger.gov/v1
kind: Policy
metadata:
  name: cross-border-transfer
spec:
  trigger:
    action: data.transfer
    condition: origin_region == "EU" AND destination_region not_in ["EU", "UK", "CH", "CA"]
  enforcement:
    type: require_approval
    approvers: [role:dpo]
    timeout: 72h
  audit:
    level: comprehensive
    retention: 10years
```

---

## Implementation

```python
action = ledger.govern(
    agent_id="global-agent",
    action="data.transfer",
    params={
        "data": "customer_records",
        "from": "EU",
        "to": "US"
    }
)

try:
    result = action.execute()
except ledger_sdk.ApprovalRequiredError:
    print("Transfer blocked - DPO approval required")
```

---

## Next steps

- [Core Concepts: Compliance](../core-concepts/compliance.md)
- [Core Concepts: Policies](../core-concepts/policies.md)
