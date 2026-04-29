# Citadel Core

Citadel Core is the active wedge-focused product surface for this repo.

The current implementation still lives in the existing runtime package under
`apps/runtime/citadel`, but this directory is now the canonical map for what is
active product work versus preserved legacy or research code.

## Product Wedge

Citadel is being simplified around two jobs:

1. Stop runaway LLM spend before the API call is made.
2. Produce decision-first cryptographic evidence for governed actions.

Everything in the active path should directly support one of those jobs. Code
that is useful history, research, demonstration material, or future platform
surface belongs in `archive/`, not the default product path.

## Active Core

The active core currently consists of these implementation areas:

| Area | Current implementation | Why it stays active |
| --- | --- | --- |
| Spend enforcement | `apps/runtime/citadel/commercial/cost_controls.py` | Pre-request budget checks, spend attribution, budget actions, and audited top-ups. |
| Budget schema | `db/migrations/018_cost_controls.sql`, `db/migrations/019_cost_budget_topups.sql` | Durable budget, spend, and top-up records. |
| Decision records | `apps/runtime/citadel/tokens/governance_decision.py`, `apps/runtime/citadel/tokens/token_vault.py` | Durable `governance_decisions` records before execution proof. |
| Execution proof tokens | `apps/runtime/citadel/tokens/governance_token.py`, `apps/runtime/citadel/tokens/token_verifier.py` | Existing `gt_cap_` execution proof flow. |
| Governance audit | `apps/runtime/citadel/tokens/audit_trail.py`, `db/migrations/004_governance_audit.sql` | Append-only `governance_audit_log` with hash-chain verification. |
| Action lifecycle audit | `apps/runtime/citadel/services/audit_service.py`, `db/migrations/001_initial_schema.sql` | Existing `audit_events` table for action lifecycle records. |
| Emergency stop | `apps/runtime/citadel/tokens/kill_switch.py` | Fail-closed stop mechanism for governed execution. |
| Operator visibility | `apps/dashboard/`, `apps/runtime/citadel/api/routers/dashboard.py` | Cost controls, approval queue, activity stream, audit evidence, and kill-switch administration. |
| Python SDK | `packages/sdk-python/` | Current developer integration path. |

## Not Active Product Surface

Archived code is preserved for reference and can be revived deliberately, but it
must not be imported by the default runtime path or documented as current
product functionality.

See `archive/README.md` for the archived inventory.

## Reorganization Rule

When adding new code, use this filter:

- Does it prevent runaway spend before an LLM/API call?
- Does it strengthen decision-first cryptographic evidence?

If the answer is no, put it behind an explicit optional boundary or preserve it
in `archive/` instead of expanding the active core.
