# Compatibility Boundaries

Citadel's active product surface is intentionally small:

1. Cost enforcement before execution
2. Decision-first audit and execution evidence
3. Compact trust context
4. Minimal runtime compatibility for existing callers

Anything outside that shape is compatibility-only or archived reference material.

## Active SDK Surface

Use the top-level Python SDK for wedge-facing flows:

```python
import citadel_governance as cg

cg.configure(base_url="https://api.example.com", api_key="...", actor_id="agent-1")

result = await cg.execute(
    action="llm.complete",
    resource="model:gpt",
    payload={"estimated_cost_usd": 0.42},
)
```

The top-level SDK should stay focused on:

- `configure`
- `execute`
- `decide`
- approval review helpers
- kill-switch read helpers
- audit verification and audit event reads
- `guard` / `wrap`
- core result, token, approval, and exception types

## SDK Compatibility Namespace

Broader helper APIs remain available under:

```python
import citadel_governance.compatibility as compat
```

This namespace preserves existing callers for agent management, policy
management, identity operations, dashboard stats, and broad trust-management
helpers. New public examples should not use these helpers unless the example is
explicitly about migration or legacy compatibility.

## Runtime Compatibility Namespace

Runtime orchestration symbols remain available under:

```python
from citadel.compatibility import OrchestrationRuntime
```

The `/v1/orchestrate/*` router also remains mounted for existing callers. It is
compatibility-only. New wedge-facing integrations should prefer normal decision
creation, `gt_cap_` execution proof, and `/v1/introspect`.

## Trust Compatibility

`PROBATION` and `HIGHLY_TRUSTED` remain valid trust band values for stored data
and API compatibility. The active operating model is `REVOKED`, `STANDARD`, and
`TRUSTED`, with trust represented as compact decision context rather than a
separate authorization system.

## Archived Material

Archived code and docs under `archive/legacy/` and `archive/research/` are
preserved for reference. They are not active product surface and should not be
imported by default runtime code or linked as current capabilities from active
docs.

To revive archived material, do a focused implementation pass that updates:

- active docs
- imports and exports
- tests and guardrails
- ownership in `citadel-core/MANIFEST.md`
