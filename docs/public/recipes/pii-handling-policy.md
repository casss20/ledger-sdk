# Recipe: PII Handling Policy

## What you'll learn

- Detect PII in agent inputs and outputs
- Redact sensitive information
- Log PII access for compliance
- Block PII from being sent externally

---

## Use Case
Your customer support agent handles emails containing names, addresses, and phone numbers. Ensure PII is never logged in plaintext or sent to external APIs.

---

## Policy

```yaml
apiVersion: citadel.gov/v1
kind: Policy
metadata:
  name: pii-protection
spec:
  trigger:
    any:
      - action: email.send
      - action: api.call
      - action: log.write
  enforcement:
    type: content_filter
    filters:
      - type: pii_redaction
        entities: [email, phone, ssn, address]
      - type: block_external
        condition: contains_pii AND destination == "external"
  audit:
    level: comprehensive
```

---

## Implementation

```python
action = citadel.govern(
    agent_id="support-agent",
    action="email.send",
    params={
        "to": "customer@example.com",
        "body": "Hi John, your phone 555-1234 is updated."
    }
)

result = action.execute()
# Body is automatically redacted: "Hi [NAME], your phone [PHONE] is updated."
```

---

## Next steps

- [Core Concepts: Policies](../core-concepts/policies.md)
- [Core Concepts: Compliance](../core-concepts/compliance.md)
