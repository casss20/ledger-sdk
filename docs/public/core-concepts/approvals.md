# Human Approvals and Oversight

## What you'll learn

- How approval workflows integrate with agent execution
- Configuring approvers, timeouts, and escalations
- Approval via dashboard, API, email, and Slack
- EU AI Act Article 14 human oversight requirements
- Audit trail for every approval decision

---

## Overview

CITADEL's approval system implements human-in-the-loop oversight for high-risk agent actions. When a policy triggers `require_approval`, the action pauses until a human explicitly approves or denies it.

This satisfies EU AI Act Article 14(4)(b): "natural persons overseeing high-risk AI systems are enabled to correctly interpret the outputs."

---

## How Approvals Work

```
Agent requests action
    â†“
Policy evaluation: require_approval
    â†“
Action PAUSED
    â†“
Notifications sent to approvers
    â†“
Approver reviews context
    â†“
    â”œâ”€ APPROVE â†’ Action resumes and executes
    â”œâ”€ DENY â†’ Action rejected, agent notified
    â””â”€ TIMEOUT â†’ Auto-rejected after timeout
    â†“
Decision recorded in audit trail
```

---

## Configuring Approvers

### Single approver
```yaml
enforcement:
  type: require_approval
  approvers:
    - user: alice@company.com
```

### Role-based approvers
```yaml
enforcement:
  type: require_approval
  approvers:
    - role: finance-manager
    - role: cto
  require_any: true  # Any one approver is sufficient
```

### All must approve
```yaml
enforcement:
  type: require_approval
  approvers:
    - role: finance-manager
    - role: compliance-officer
  require_all: true  # Both must approve
```

### Conditional approvers
```yaml
enforcement:
  type: require_approval
  approvers:
    - condition: amount > 10000
      users: [cfo@company.com]
    - condition: amount <= 10000
      roles: [finance-manager]
```

---

## Approval Channels

### Dashboard
Approvers see pending approvals in the **Approval Queue** widget:
- Action context and parameters
- Agent history and trust score
- Risk assessment summary
- One-click approve/deny

### Email
```yaml
enforcement:
  type: require_approval
  notify:
    - email: finance@company.com
    template: approval-request
```

### Slack
```yaml
enforcement:
  type: require_approval
  notify:
    - slack: #finance-alerts
    template: approval-request-slack
```

### Mobile push
```yaml
enforcement:
  type: require_approval
  notify:
    - push: approver_mobile_app
```

---

## Timeouts and Escalation

```yaml
enforcement:
  type: require_approval
  timeout: 24h          # Auto-deny after 24 hours
  escalation: 48h       # Escalate to manager after 48h
  reminder: 4h          # Remind approver every 4h
```

Escalation chain:
```
0h: Initial notification
4h: First reminder
8h: Second reminder
24h: Timeout â†’ Auto-deny
48h: Escalation notification to manager
```

---

## Approval Context

Approvers see rich context before deciding:

```python
approval_context = {
    "action": "refund.create",
    "params": {"amount": 5000, "order_id": "ORD-123"},
    "agent_id": "refund-agent-01",
    "agent_trust_score": 847,
    "agent_history": "97% approval rate, last violation 30 days ago",
    "policy": "refund-approval-over-1000",
    "similar_approvals": [
        {"gt_token": "gt_xxx", "decision": "approved", "time": "2h ago"},
        {"gt_token": "gt_yyy", "decision": "approved", "time": "1d ago"}
    ],
    "risk_factors": ["High amount", "International customer", "First-time order"]
}
```

---

## Approving via API

```python
# List pending approvals
pending = CITADEL.approvals.list(status="pending")

# Approve an action
CITADEL.approvals.approve(
    approval_id="app_123e4567",
    reason="Verified customer, legitimate refund"
)

# Deny an action
CITADEL.approvals.deny(
    approval_id="app_123e4567",
    reason="Suspicious pattern, requires investigation"
)
```

---

## Audit Trail

Every approval is recorded:

```python
records = CITADEL.audit.query(action="approval.decided")
for record in records:
    print(f"{record.approver} {record.decision} {record.action}")
    print(f"  Reason: {record.reason}")
    print(f"  Time to decision: {record.decision_time - record.request_time}")
```

---

## Delegation

Temporarily delegate approval authority:

```python
CITADEL.approvals.delegate(
    from_user="alice@company.com",
    to_user="bob@company.com",
    start="2026-05-01",
    end="2026-05-15",
    policies=["refund-approval-over-1000"]
)
```

---

## Next steps

- [Kill Switch](./kill-switch.md) â€” Emergency stops when approvals aren't enough
- [Trust Scoring](./trust-scoring.md) â€” Reduce approval burden for trusted agents
- [Recipe: High-Risk Action Approval](../recipes/high-risk-action-approval.md)
