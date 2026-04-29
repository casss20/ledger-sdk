# Agent Trust Scoring

Citadel keeps trust scoring in the active path as a small operational signal for
the governance kernel. It is not a second authorization system and it is not a
broad behavioral analytics layer.

Trust is evaluated before policy decisions so the decision record can preserve
the exact `trust_snapshot_id` used for audit replay. Policy still remains the
authority for allow, deny, approval, and spend enforcement.

## Active Model

The active trust score is deterministic and uses three operational factors:

| Factor | Weight | What it captures |
| --- | ---: | --- |
| `identity_verification` | 0.30 | Whether the agent identity is cryptographically verified. |
| `operational_health` | 0.35 | Current health score, quarantine status, and suspicious action volume. |
| `governance_record` | 0.35 | Recent policy violations and budget pressure. |

The dashboard trust breakdown reads these stored factors from
`actor_trust_snapshots.factors` for the selected decision. It does not recompute
trust in the browser.

Example stored factor payload:

```json
{
  "identity_verification": 0.3,
  "operational_health": 0.35,
  "governance_record": 0.25
}
```

## Compatibility Bands

The runtime still accepts the historical trust band enum values because they may
exist in stored records and API responses:

| Band | Score Range | Active meaning |
| --- | --- | --- |
| `REVOKED` | 0.00-0.19 | Identity disabled or emergency stop state. |
| `PROBATION` | 0.20-0.39 | Compatibility state for new or restricted agents. |
| `STANDARD` | 0.40-0.59 | Normal active operating state. |
| `TRUSTED` | 0.60-0.79 | Healthy active operating state. |
| `HIGHLY_TRUSTED` | 0.80-1.00 | Compatibility state for historical callers. |

The wedge-focused active model should be treated as `REVOKED`, `STANDARD`, and
`TRUSTED`. `PROBATION` and `HIGHLY_TRUSTED` remain compatibility states until
callers and stored data can be migrated safely.

## Decision Flow

```text
Agent requests action
    |
Kill switch check
    |
Trust snapshot computed or loaded
    |
Policy and spend enforcement
    |
Decision recorded with trust_snapshot_id
    |
gt_cap_ token issued or action blocked
```

Trust can only add constraints or context. It cannot override the kill switch,
remove a policy denial, bypass spend limits, or create execution authority by
itself.

## Audit And Replay

Every decision that uses trust should preserve:

- `trust_snapshot_id`
- score and band at decision time
- the three factor contributions
- raw inputs needed for deterministic replay when available

The audit explorer and dashboard should present trust as decision evidence, not
as a standalone scoring product.

## Archived Material

The previous broad trust action matrix and deep trust architecture guide are
preserved under `archive/legacy/` for reference. They are no longer active
product surface and should not be used as the source of truth for new runtime
work.
