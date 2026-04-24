# Recipe: Compliance Proof Generation

## What you'll learn

- Generate mathematically verifiable compliance proof
- Include hash chain verification
- Create regulator-ready packages
- Automate periodic proof generation

---

## Use Case
Prove to auditors that your AI governance audit trail has not been tampered with.

---

## Generate Proof

```python
proof = CITADEL.compliance.generate_proof(
    start="2026-01-01",
    end="2026-03-31",
    include_hash_verification=True,
    include_chain_integrity=True
)

proof.download("/compliance/proof-q1-2026.pdf")
```

---

## Verification

Independent verification without trusting CITADEL:

```python
records = CITADEL.audit.query(start="2026-01-01", end="2026-03-31")

prev_hash = None
for record in records:
    content_hash = sha256(record.content)
    assert content_hash == record.content_hash

    if prev_hash:
        chain_hash = sha256(prev_hash + content_hash)
        assert chain_hash == record.chain_hash

    prev_hash = record.chain_hash

print(f"Verified {len(records)} records. Chain intact.")
```

---

## Automation

```python
# Monthly automated proof generation
@schedule("0 0 1 * *")  # First of each month
def generate_monthly_proof():
    last_month = get_last_month()
    proof = CITADEL.compliance.generate_proof(
        start=last_month.start,
        end=last_month.end
    )
    proof.email_to("compliance@company.com")
```

---

## Next steps

- [Core Concepts: Audit Trail](../core-concepts/audit-trail.md)
- [Core Concepts: Compliance](../core-concepts/compliance.md)
