# Governance Tokens (`gt_`)

## What you'll learn

- What governance tokens are and why they matter
- How `gt_` tokens create data gravity (the Stripe pattern)
- Token lifecycle from creation to archival
- Querying and verifying tokens in the audit trail

---

## Overview

Governance tokens (`gt_`) are runtime execution proofs linked to Citadel's durable decision records. Citadel is decision-first: it persists the governance decision before issuing a short-lived token.

Think of them like Stripe's `pm_` PaymentMethod tokens: they reference a record stored in Citadel's vault, are non-portable to other systems, and accumulate over time into compliance evidence. The decision record, not the token, is the source of authority.

---

## Token Format

```
gt_cap_{opaque-random-id}
```

Examples:
```
gt_cap_1Aa2Bb3Cc4Dd5Ee6Ff7Gg8Hh
gt_cap_7Xy9Za0Bc1De2Fg3Hi4Jk5Lm
```

- **Prefix**: `gt_cap_` identifies a scoped capability token
- **Body**: Opaque URL-safe random material
- **Linkage**: Every token resolves to exactly one `decision_id`
- **Lifetime**: Short-lived by default, with high-risk execution rights intended to last seconds to minutes

---

## Token Lifecycle

```
Agent requests action
    ↓
Citadel evaluates against policies
    ↓
Decision recorded (allow / deny / escalate / require_approval)
    ↓
If allowed, gt_cap_ token minted and linked to decision_id
    ↓
Runtime gateway introspects token before high-risk execution
    ↓
Expiry, revocation, scope, workspace, and kill-switch state checked
    ↓
Action executed only when introspection returns active=true
    ↓
Outcome recorded and linked to token, decision_id, trace_id, policy_version, and approval_state
```

---

## Decision-First Introspection

For high-risk operations, runtimes should call `POST /v1/introspect` or `POST /v1/governance/introspect` before executing the next protected operation.

Introspection validates:

- Token existence and format
- Token expiry and not-before time
- Token and decision revocation state
- Requested workspace, action, and resource scope
- Central kill-switch state

When a matching kill switch is active, introspection returns `active: false` with `reason: "kill_switch_active"`. This stops the next protected operation at the enforcement point. It does not retroactively interrupt arbitrary code already running unless that code cooperatively re-checks Citadel between critical steps.

---

## Why Tokens Matter: Data Gravity

As your agents run, they generate thousands of `gt_` tokens. Each token references:
- The exact action attempted
- The policy that evaluated it
- The decision (allow/deny/approval)
- The timestamp and context
- The agent identity
- The durable `decision_id`, `trace_id`, policy version, and approval state

**This accumulation creates data gravity.** Like Stripe's card tokens make migration painful (customers must re-enter cards), Citadel's governance tokens make migration legally hazardous — your entire audit history lives in Citadel's vault.

> 💡 **The moat:** After 6 months of operation, an enterprise has 10,000+ governance tokens forming a tamper-evident chain. Migrating to another system means losing that history — and regulators require continuous audit evidence.

---

## Querying Tokens

### By token ID

```python
record = citadel.audit.get("gt_1Aa2Bb3Cc4Dd5Ee6Ff7Gg8Hh")
```

### By agent

```python
records = citadel.audit.query(agent_id="email-agent-01", limit=100)
```

### By time range

```python
records = citadel.audit.query(
    agent_id="email-agent-01",
    start="2026-01-01T00:00:00Z",
    end="2026-01-31T23:59:59Z"
)
```

### By policy

```python
records = citadel.audit.query(policy_name="refund-approval-over-1000")
```

---

## Token Verification

Verify a token's integrity independently:

```python
# Fetch the token record
record = citadel.audit.get("gt_1Aa2Bb3Cc4Dd5Ee6Ff7Gg8Hh")

# Verify hash chain integrity
is_valid = citadel.audit.verify_chain(record)
print(f"Chain integrity: {is_valid}")  # True / False

# Verify individual record hash
is_tampered = citadel.audit.verify_hash(record)
print(f"Record integrity: {is_tampered}")  # True = not tampered
```

---

## Token Retention

| Tier | Retention | Use Case | Cost |
|------|-----------|----------|------|
| Hot | 90 days | Real-time dashboard queries | Included |
| Warm | 1-7 years | Compliance investigations | $0.01/GB/month |
| Cold | Indefinite | Regulatory audits, legal hold | $0.001/GB/month |

Configure in your organization settings:
```python
citadel.config.set_retention_policy({
    hot_days=90,
    warm_years=7,
    cold_indefinite=True
})
```

---

## Next steps

- [Policies](./policies.md) — Write policies that govern token creation
- [Audit Trail](./audit-trail.md) — Understand the full hash chain
- [Recipe: Compliance Proof Generation](../recipes/compliance-proof-generation.md) — Generate regulator-ready exports
