# Recipe: Audit Export for Regulator

## What you'll learn

- Export audit trail for regulatory review
- Generate tamper-evidence proof
- Format exports for specific frameworks
- Handle auditor access

---

## Use Case
A regulator requests your AI system's audit trail for Q1 2026 under EU AI Act Article 12.

---

## Generate Export

```python
package = CITADEL.compliance.export(
    framework="eu_ai_act",
    period_start="2026-01-01",
    period_end="2026-03-31",
    format="pdf",
    include_verification=True
)

# Download
package.download("/exports/eu-ai-act-q1-2026.pdf")
```

---

## Contents

The export includes:
1. All governance decisions (allow/deny/approval)
2. Hash chain verification report
3. Policy snapshots at time of each decision
4. Agent identity certificates
5. Kill switch activation log
6. Approval workflow records

---

## Grant Auditor Access

```python
# Create read-only auditor account
CITADEL.users.create_auditor(
    email="auditor@regulator.eu",
    scope="eu_ai_act_q1_2026",
    expiry="30d"
)
```

---

## Next steps

- [Core Concepts: Audit Trail](../core-concepts/audit-trail.md)
- [Core Concepts: Compliance](../core-concepts/compliance.md)
