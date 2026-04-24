# Recipe: Automated Compliance Reporting

## What you'll learn

- Schedule automated compliance reports
- Send to stakeholders automatically
- Format for different frameworks
- Archive reports for audit history

---

## Use Case
Generate and distribute weekly compliance reports to executives, auditors, and regulators without manual work.

---

## Implementation

```python
from datetime import datetime, timedelta

# Weekly report
@schedule("0 9 * * 1")  # Mondays at 9am
def weekly_compliance_report():
    last_week = datetime.now() - timedelta(days=7)

    report = CITADEL.compliance.generate_report(
        period_start=last_week,
        period_end=datetime.now(),
        frameworks=["eu_ai_act", "soc2"],
        format="pdf"
    )

    # Email to stakeholders
    report.email_to([
        "ceo@company.com",
        "compliance@company.com",
        "legal@company.com"
    ])

    # Store for audit history
    report.archive(
        retention="7years",
        classification="confidential"
    )
```

---

## Dashboard Widget

Add to your Stream 3b dashboard:
```python
CITADEL.dashboard.add_widget(
    type="compliance_report",
    schedule="weekly",
    recipients=["compliance@company.com"]
)
```

---

## Next steps

- [Core Concepts: Compliance](../core-concepts/compliance.md)
- [Recipe: Compliance Proof Generation](compliance-proof-generation.md)
