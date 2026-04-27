# Recipe: AI Output Verification

## What you'll learn

- Verify AI-generated outputs before delivery
- Flag hallucinations and inconsistencies
- Require human review for critical outputs
- Build output trust scoring

---

## Use Case
Your content generation agent writes customer-facing emails. Verify outputs for accuracy and brand compliance before sending.

---

## Policy

```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: output-verification
spec:
  trigger:
    action: content.generate
    condition: destination == "customer-facing"
  enforcement:
    type: conditional
    conditions:
      - if: agent.trust_band == "HIGHLY_TRUSTED" AND output.quality_score > 0.90
        then: allow
      - if: agent.trust_band in ["TRUSTED", "HIGHLY_TRUSTED"] AND output.quality_score > 0.60
        then: require_approval
        approvers: [role:content-review]
      - if: agent.trust_band == "STANDARD"
        then: require_approval
        approvers: [role:content-review, role:team-lead]
      - else: deny
  audit:
    level: comprehensive
```

---

## Implementation

```python
# Generate content
action = citadel.govern(
    agent_id="content-agent",
    action="content.generate",
    params={"type": "email", "destination": "customer-facing"}
)

result = action.execute()

if result.decision == "require_approval":
    print(f"Output needs review: {result.approval_url}")
    # Content reviewer checks output before customer sees it
```

---

## Verification Pipeline

```python
# Custom verification
verifier = CITADEL.verification.create_pipeline([
    {"check": "fact_accuracy", "threshold": 0.95},
    {"check": "brand_compliance", "threshold": 0.90},
    {"check": "toxicity", "threshold": 0.01}
])

score = verifier.run(output_text)
print(f"Output trust score: {score}")
```

---

## Next steps

- [Core Concepts: Trust Scoring](../core-concepts/trust-scoring.md)
- [Core Concepts: Approvals](../core-concepts/approvals.md)
