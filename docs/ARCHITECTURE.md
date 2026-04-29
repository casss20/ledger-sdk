# Citadel Architecture

Citadel's active product path is a compact governance kernel for AI actions.
The wedge is intentionally small:

1. Pre-request cost enforcement
2. Decision-first audit and execution evidence
3. Compact trust context
4. Compatibility-only orchestration for existing callers

Archived platform, SRE, telemetry, broad orchestration, and research material is
preserved under `archive/legacy/` or `archive/research/`. It is not active
product surface.

## Active Runtime Path

```text
agent/tool call
    |
cost and budget enforcement
    |
policy / approval decision
    |
governance_decisions record
    |
governance_audit_log evidence
    |
gt_cap_ execution proof or deterministic block
    |
optional /v1/introspect before protected execution
```

## Active Core

| Area | Source of truth |
| --- | --- |
| Spend enforcement | `apps/runtime/citadel/commercial/cost_controls.py` |
| Budget/top-up APIs | `apps/runtime/citadel/commercial/routes.py` |
| Decision records | `apps/runtime/citadel/tokens/governance_decision.py` |
| Execution proof tokens | `apps/runtime/citadel/tokens/governance_token.py` |
| Token vault / introspection | `apps/runtime/citadel/tokens/token_vault.py`, `apps/runtime/citadel/tokens/token_verifier.py` |
| Decision audit chain | `apps/runtime/citadel/tokens/audit_trail.py` |
| Action lifecycle audit | `apps/runtime/citadel/services/audit_service.py` |
| Compact trust context | `apps/runtime/citadel/agent_identity/trust_score.py` |
| Operator dashboard APIs | `apps/runtime/citadel/api/routers/dashboard.py` |

## Compatibility-Only Runtime

The following runtime pieces remain because current app wiring, tests, or stored
contracts still depend on them:

| Area | Current path | Rule |
| --- | --- | --- |
| Orchestration runtime | `apps/runtime/citadel/execution/orchestration.py` | Keep for existing callers; do not expand as a platform surface. |
| Orchestration router | `apps/runtime/citadel/api/routers/orchestration.py` | Mounted for compatibility under `/v1/orchestrate`. |
| Trust band enum breadth | `apps/runtime/citadel/agent_identity/trust_bands.py` | `PROBATION` and `HIGHLY_TRUSTED` are compatibility states. |
| Runtime compatibility exports | `apps/runtime/citadel/compatibility.py` | Explicit namespace for broad legacy symbols. |

Compatibility code must not be the default story in README, docs, examples, or
new public APIs.

See [Compatibility Boundaries](COMPATIBILITY.md) for migration guidance and the
current compatibility-only namespaces.

## Public API Shape

The top-level SDK should lead with:

- `configure`
- `execute`
- `decide`
- `approve` / `reject`
- `verify_audit`
- `list_audit_events`
- `guard` / `wrap`
- core models and exceptions needed by those operations

Broader dashboard, identity-management, policy-management, and framework helper
exports live behind `citadel_governance.compatibility`.

## Trust Context

Trust is deterministic decision context, not a second authorization system. The
active score uses three operational factors:

- `identity_verification`
- `operational_health`
- `governance_record`

Every trust-aware decision records a `trust_snapshot_id` for replay. Trust cannot
bypass cost enforcement, policy denial, token revocation, or kill-switch state.

## Archive Rule

If a module or doc primarily makes Citadel look like a broader platform, it
belongs under `archive/legacy/` until a focused implementation pass proves it is
needed for the wedge.
