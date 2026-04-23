# Regulatory Compliance Guide

## What you'll learn

- Map Ledger to regulatory frameworks
- Generate compliance evidence
- Prepare for audits
- Handle regulatory inquiries

---

## Framework Quick Reference

| Framework | Ledger Features | Evidence |
|-----------|---------------|----------|
| EU AI Act | Hash audit, kill switch, approvals | Article 12, 14 compliance exports |
| SOC 2 | Immutable logs, RBAC, monitoring | CC7.1, CC7.2 evidence |
| HIPAA | Separate audit trail, BAA | §164.312(b) audit controls |
| NIST AI RMF | Trust scoring, policy-as-code | Govern 1.1, 2.1 evidence |

---

## EU AI Act Checklist

Before August 2, 2026:

- [ ] Automatic logging enabled (Article 12)
- [ ] Kill switch tested monthly (Article 14)
- [ ] Human approval workflows configured (Article 14)
- [ ] Technical documentation exported (Article 11)
- [ ] 6-month retention configured
- [ ] Compliance proof generated and archived

Generate checklist report:
```python
ledger.compliance.checklist(framework="eu_ai_act")
```

---

## Audit Preparation

```python
# Generate evidence package
package = ledger.compliance.export(
    framework="soc2",
    period="2026-Q1",
    include_verification=True,
    format="pdf"
)

# Grant auditor read-only access
ledger.users.create_auditor(
    email="auditor@firm.com",
    scope="2026-Q1",
    expiry="30d"
)
```

---

## Next steps

- [Core Concepts: Compliance](../core-concepts/compliance.md)
- [Recipe: Audit Export for Regulator](../recipes/audit-export-for-regulator.md)
