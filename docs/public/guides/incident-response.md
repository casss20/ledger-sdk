# Incident Response Guide

## What you'll learn

- Respond to governance incidents
- Investigate policy violations
- Use kill switch effectively
- Document and recover from incidents

---

## Incident Types

| Severity | Examples | Response Time |
|----------|----------|---------------|
| P0 | Kill switch triggered, data breach | 5 minutes |
| P1 | High denial rate, approval backlog | 30 minutes |
| P2 | Trust score drop, policy errors | 2 hours |
| P3 | Metric anomalies | 24 hours |

---

## Response Playbook

### Step 1: Assess
```python
# Check kill switch status
status = CITADEL.kill_switch.get_status()

# Check recent denials
denials = CITADEL.audit.query(
    decisions=["denied"],
    start="now-1h"
)
```

### Step 2: Contain
```python
# Activate kill switch if needed
CITADEL.kill_switch.activate(
    scope="organization",
    reason="Investigating unauthorized data access",
    duration="indefinite"
)
```

### Step 3: Investigate
```python
# Query audit trail for affected actions
records = CITADEL.audit.query(
    agent_id="compromised-agent",
    start="incident_start",
    end="incident_end"
)

# Generate incident report
report = CITADEL.compliance.generate_report(
    period_start=incident_start,
    period_end=incident_end,
    include_verification=True
)
```

### Step 4: Resolve
```python
# Fix root cause (e.g., update policy)
CITADEL.policies.update(name="fixed-policy", spec=new_spec)

# Gradually resume agents
CITADEL.kill_switch.deactivate(
    agent_id="low-risk-agent",
    reason="Root cause resolved"
)
```

### Step 5: Document
```python
# Archive incident report
CITADEL.incidents.create({
    id: "INC-2026-001",
    severity: "P1",
    summary: "...",
    root_cause: "...",
    remediation: "...",
    report: report
})
```

---

## Next steps

- [Kill Switch](../core-concepts/kill-switch.md)
- [Core Concepts: Audit Trail](../core-concepts/audit-trail.md)
