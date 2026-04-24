# Regulatory Compliance

## What you'll learn

- How CITADEL maps to EU AI Act, SOC 2, HIPAA, and NIST AI RMF
- Compliance features by framework
- Generating audit exports for regulators
- The August 2026 EU AI Act deadline
- Proving compliance to auditors

---

## Framework Mapping

CITADEL's governance architecture is designed to satisfy multiple regulatory frameworks simultaneously:

| Framework | CITADEL Feature | Control / Article |
|-----------|---------------|-------------------|
| EU AI Act | Hash-chained audit trail | Article 12 (automatic logging) |
| EU AI Act | Kill switch | Article 14(4)(e) (stop button) |
| EU AI Act | Human approvals | Article 14(4)(b) (human oversight) |
| EU AI Act | Policy documentation | Article 11 (technical documentation) |
| SOC 2 | Permission-gated audit logs | CC7.2 (system monitoring) |
| SOC 2 | Immutable audit trail | CC7.1 (integrity verification) |
| HIPAA | Separate audit trail product | Â§164.312(b) (audit controls) |
| NIST AI RMF | Trust scoring | Govern 1.1 (risk management) |
| NIST AI RMF | Policy-as-code | Govern 2.1 (governance documentation) |
| ISO 42001 | Audit trail retention | 7.5 (documented information) |

---

## EU AI Act Readiness

**Critical deadline: August 2, 2026**

High-risk AI systems must have:
1. âœ… Automatic logging (Article 12) â€” CITADEL's hash-chained audit trail
2. âœ… Human oversight (Article 14) â€” Kill switch + approval workflows
3. âœ… Technical documentation (Article 11) â€” Policy-as-code YAML exports
4. âœ… 6-month log retention â€” Configurable retention policies
5. âœ… Accuracy and robustness â€” Trust scoring + anomaly detection

### Penalties
| Violation | Penalty |
|-----------|---------|
| Prohibited AI practices | â‚¬35M or 7% global turnover |
| High-risk non-compliance | â‚¬15M or 3% global turnover |
| Documentation failures | â‚¬7.5M or 1.5% global turnover |

> ðŸ’¡ **The CITADEL advantage:** 78% of enterprises are unprepared for the August 2026 deadline. CITADEL's kernel-level governance is the only architecture that satisfies both Articles 12 and 14 simultaneously.

---

## SOC 2 Compliance

### Trust Service Criteria mapping

| Criteria | CITADEL Control | Evidence |
|----------|---------------|----------|
| CC6.1 | RBAC with role-based access | Permission audit logs |
| CC6.2 | Policy enforcement | Policy evaluation records |
| CC7.1 | Immutable audit trail | Hash chain verification |
| CC7.2 | System monitoring | Real-time activity stream |
| CC7.3 | Incident response | Kill switch + approval workflows |

Generate SOC 2 evidence package:
```python
package = CITADEL.compliance.export_soc2(
    period="2026-Q1",
    trust_service_criteria=["CC6.1", "CC6.2", "CC7.1", "CC7.2", "CC7.3"]
)
```

---

## HIPAA Compliance

CITADEL's HIPAA-eligible services:
- Audit Trail with BAA signing
- Separate PHI access logs
- Role-based access (minimum necessary)
- 7-year retention for audit records

Sign BAA:
```python
CITADEL.compliance.sign_baa(
    organization="MyHealthcareOrg",
    contact="compliance@myhealth.org"
)
```

---

## Compliance Dashboard

Monitor compliance posture in real-time:

```python
posture = CITADEL.compliance.get_posture()
print(f"Overall score: {posture.score}%")
print(f"EU AI Act: {posture.frameworks.eu_ai_act.status}")
print(f"SOC 2: {posture.frameworks.soc2.status}")
print(f"HIPAA: {posture.frameworks.hipaa.status}")
```

---

## Audit Exports

### For regulators
```python
CITADEL.compliance.export(
    framework="eu_ai_act",
    period="2026-01-01 to 2026-03-31",
    format="pdf",
    language="en"
)
```

### For internal audit
```python
CITADEL.compliance.export(
    framework="soc2",
    period="2026-Q1",
    format="xlsx",
    include_evidence=True
)
```

### For external auditors
```python
CITADEL.compliance.export(
    framework="all",
    period="2026-01-01 to 2026-06-30",
    format="pdf",
    auditor_access=True  # Creates auditor-only read-only account
)
```

---

## Next steps

- [Audit Trail](./audit-trail.md) â€” Understand tamper-evident logging
- [Recipe: Compliance Proof Generation](../recipes/compliance-proof-generation.md)
- [Recipe: Audit Export for Regulator](../recipes/audit-export-for-regulator.md)
- [Guide: Regulatory Compliance](../guides/regulatory-compliance.md)
