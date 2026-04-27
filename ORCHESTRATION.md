# Citadel Orchestration Architecture

## One Governance Kernel, All Patterns

Citadel does not run three separate orchestration systems. It runs one.

The governance kernel is decision-first: every action that crosses a trust boundary begins as a `Decision`, is evaluated by policy, and produces an auditable record. Supervisor/Worker, Handoff, and Planner/Worker/Solver are not distinct subsystems. They are **usage patterns** of the same four primitives: `delegate`, `handoff`, `gather`, and `introspect`. The kernel remains the single source of truth for authority, scope, revocation, and audit.

If an engineer calls `cg.delegate()`, `cg.handoff()`, or `cg.gather()`, they are invoking the same lineage engine, the same token vault, the same audit service, and the same kill switch. The differences between patterns are in *who holds active authority* and *how the tree branches* — not in which code paths execute.

---

## Shared Primitives

### `cg.delegate(parent_decision_id, actor, scope)`

Creates a **child decision** under an existing parent authority. The child receives a narrower scope than the parent; the kernel enforces this narrowing at decision time. The parent retains its authority; the child receives a new `CapabilityToken` linked to the parent's lineage.

Use when a supervisor assigns a task to a worker without surrendering control.

**Scope narrowing is mandatory.** A child may not receive a scope that exceeds its parent. If the request violates this, the kernel rejects it with `ScopeViolation` and emits an audit record.

### `cg.handoff(from_actor, to_actor, scope)`

**Transfers active authority** from one actor to another. The prior actor's token is marked superseded. The new actor receives active authority for the specified scope. The handoff is atomic: there is no window where both actors hold active authority for the same scope.

Use when control must move from one agent to another — for example, a planner yielding to a solver, or a primary failing over to a secondary.

### `cg.gather(root_decision_id, branches[])`

Creates **parallel child branches** under a single root decision. Each branch receives its own child `decision_id`, its own actor, and its own narrowed scope. Branches are independent but share a `root_decision_id` and `trace_id`, making them joinable for audit and trace.

Use when a task splits into concurrent workstreams — for example, a planner spawning multiple workers to solve subproblems in parallel.

Each branch is independently auditable. A kill switch at the root applies to all branches. A kill switch on a single branch applies only to that branch.

### `cg.introspect(token_or_decision_id)`

**Runtime safety check.** Validates:

- **Active state** — is the decision still open?
- **Expiry** — has the token or decision exceeded its time bound?
- **Revocation** — has the token or decision been revoked?
- **Scope** — does the requested action fit within the granted scope?
- **Kill switch** — is an emergency stop active for this lineage?
- **Actor boundary** — is the calling actor the one currently authorized?

`introspect()` is not a static check. It queries the kernel's current state at call time. Every protected action should call it. It is fast, but it is not free — it is a round-trip to the token vault and audit spine.

---

## Lineage Model

Every governance decision carries an ancestry chain. This chain is the backbone of audit, trace, and revocation.

| Field | Meaning |
|-------|---------|
| `decision_id` | Unique identifier for this governance decision. UUIDv4. |
| `root_decision_id` | The topmost decision in this orchestration tree. Never changes once set. |
| `parent_decision_id` | The immediate parent that authorized this decision. `null` for root decisions. |
| `trace_id` | Cross-cutting trace identifier for distributed request correlation. Shared across all decisions in a single user request or workflow trigger. |
| `parent_actor_id` | The actor that performed the `delegate` or `handoff` that created this decision. |
| `workflow_id` | Optional workflow or session identifier. Useful for joining related orchestration trees. |

### Lineage Flow

```
Action (user request)
  └── Decision (root_decision_id = self)
        └── child Action (delegated or handed off)
              └── child Decision (parent_decision_id = parent)
                    └── CapabilityToken (carries parent_decision_id, parent_actor_id, workflow_id)
```

The token vault persists this lineage alongside every token. The audit service records every transition. A query on `root_decision_id` or `trace_id` can reconstruct the entire tree.

---

## Authority Model

Authority in Citadel is not a flat permission bit. It is a **tree of scoped grants**, with explicit state transitions.

### Root Authority

The initial decision for an incoming request. Holds the broadest scope. No `parent_decision_id`. All orchestration trees descend from a root.

### Delegated Child Authority

Created by `delegate()`. Narrower scope than parent. Parent remains active. Child is subordinate. The child may further delegate, but each level must narrow.

**Rule: child execution right may never exceed parent scope.** This is enforced by the kernel at decision time, not by the caller. Attempts to broaden scope are rejected with `ScopeViolation`.

### Handed-Off Active Authority

Created by `handoff()`. The new actor receives active authority. The prior actor's authority is marked **superseded**. There is always exactly one actor with active authority for a given scope within a lineage branch.

A superseded actor cannot resurrect its authority. A new handoff from the superseded actor is rejected.

### Parallel Branch Authority

Created by `gather()`. Each branch is independent but traceable. Branches do not share authority — they share only root and trace lineage. A branch may delegate, hand off, or gather further. The root may kill all branches; a branch may be killed individually.

### Superseded / Inactive Authority

An authority that has been handed off, revoked, expired, or killed. Superseded authorities are retained in the token vault for audit but cannot be used for new actions. `introspect()` returns `inactive` for these.

---

## Kill Switch Semantics

The kill switch is a first-class emergency mechanism. It is not a side effect of token expiry or a client-side timeout.

### How It Works

When a kill switch is triggered on a `decision_id`, the kernel enters **emergency state** for that lineage. The next `introspect()` or protected action in any branch of that tree returns `killed`. The kernel blocks the action. No token is consumed. An audit record is emitted.

### Coverage

- **Delegated branches:** A kill at the parent propagates to all descendants. A kill at a child does not propagate upward.
- **Handed-off authority:** Killing the active authority stops the new actor. The superseded actor remains superseded; it does not regain authority.
- **Gathered branches:** A kill at the root applies to all branches. A kill on a single branch applies only to that branch.

### Why Not Just Expiry?

Token expiry is passive: a token becomes invalid after its deadline. Kill switch is active: it blocks the *next* protected action at check time. This means a long-running operation that holds a valid token can still be stopped mid-flight if the kill switch fires before its next `introspect()` call.

---

## Audit Spine

Every orchestration action produces a durable audit record. The audit spine is not an afterthought — it is the source of truth for what happened, when, and under what authority.

### What Is Recorded

- **Decision creation** — `decision_id`, `parent_decision_id`, `root_decision_id`, `trace_id`, `actor_id`, `scope`, timestamp
- **Delegation** — parent and child decision IDs, scope delta, narrowing validation result
- **Handoff** — from and to actor IDs, superseded decision ID, new active decision ID
- **Gather** — root decision ID, list of branch decision IDs, per-branch actors and scopes
- **Introspection** — decision ID checked, result (pass / fail / killed), reason, timestamp
- **Kill switch** — trigger decision ID, affected decision IDs, actor who triggered, timestamp
- **Token issuance and revocation** — token ID, decision lineage, expiry, revocation reason

### Joinability

All records carry `trace_id` and `root_decision_id`. A single query on either field reconstructs the full orchestration tree. Actor transitions are recorded explicitly, so authority chains are auditable even after handoffs.

### Distinct Audit Signatures

Each primitive has a distinct event type:

- `ORCHESTRATE_DELEGATE`
- `ORCHESTRATE_HANDOFF`
- `ORCHESTRATE_GATHER`
- `ORCHESTRATE_INTROSPECT`
- `ORCHESTRATE_KILL`

This allows downstream systems to filter, alert, or route by orchestration event type.

---

## Token / Grant Lineage

Capability tokens carry more than a scope and expiry. They carry **lineage metadata** that binds them to the orchestration tree.

### Token Fields

| Field | Purpose |
|-------|---------|
| `parent_decision_id` | The decision that authorized this token. Used for scope validation and kill-switch propagation. |
| `parent_actor_id` | The actor that held authority at the time this token was issued. Used for actor-boundary checks. |
| `workflow_id` | Optional. Links this token to a broader workflow or session. |

### Token Vault

The token vault persists lineage alongside every token. When `introspect()` is called, the vault validates:

1. Token exists and is not expired.
2. Parent decision is still active (not revoked, not killed).
3. Requested scope fits within token scope.
4. Calling actor matches `parent_actor_id` (unless handoff has occurred, in which case the active actor is checked).

### Introspection Validation

`cg.introspect()` performs a full lineage check against the current authority state. It is not enough for a token to be cryptographically valid — its governance lineage must also be valid.

---

## API Surface

### REST Endpoints

```
POST /v1/orchestrate/delegate
  Body: { parent_decision_id, actor_id, scope, workflow_id? }
  Response: { decision_id, token, scope, expiry }

POST /v1/orchestrate/handoff
  Body: { from_decision_id, to_actor_id, scope, workflow_id? }
  Response: { decision_id, token, scope, expiry, superseded_decision_id }

POST /v1/orchestrate/gather
  Body: { root_decision_id, branches: [{ actor_id, scope }] }
  Response: { branch_decisions: [{ decision_id, token, scope }] }

POST /v1/orchestrate/introspect
  Body: { token or decision_id, requested_scope, actor_id }
  Response: { valid: boolean, reason?: string, state: active | expired | revoked | killed | superseded }
```

### SDK

All methods are available on `CitadelClient` and as module-level convenience functions.

```python
from citadel import CitadelClient

cg = CitadelClient(api_key="...")

# Delegate
child = cg.delegate(
    parent_decision_id="dec-123",
    actor="worker-1",
    scope={"resource": "db", "actions": ["read"]},
    workflow_id="wf-456"
)

# Handoff
handed = cg.handoff(
    from_decision_id="dec-123",
    to_actor="solver-1",
    scope={"resource": "db", "actions": ["read", "write"]}
)

# Gather
branches = cg.gather(
    root_decision_id="dec-123",
    branches=[
        {"actor": "worker-a", "scope": {"resource": "cache", "actions": ["read"]}},
        {"actor": "worker-b", "scope": {"resource": "queue", "actions": ["write"]}},
    ]
)

# Introspect
check = cg.introspect(token=child.token, requested_scope={"actions": ["read"]})
```

Module-level convenience functions are also provided for environments where a single global client is sufficient:

```python
import citadel

token = citadel.delegate(parent_decision_id="...", actor="...", scope={...})
```

---

## Integration Points

### Decision-First Kernel

Orchestration hooks into the existing kernel at the `Decision` layer. `delegate`, `handoff`, and `gather` are not new decision types — they are **orchestration actions** that create new decisions through the same policy engine that evaluates all other Citadel decisions. The policy engine sees an `ORCHESTRATE_*` action, evaluates it against governance rules, and emits a `Decision` record.

This means:

- All orchestration decisions are policy-governed.
- Custom policy rules can restrict who may delegate, to whom, and with what scope.
- The same `Decision` table holds root, delegated, handed-off, and gathered decisions.

### Token Vault

Tokens issued by orchestration primitives flow through the existing `TokenVault`. The vault stores the additional lineage fields (`parent_decision_id`, `parent_actor_id`, `workflow_id`) in the same table as other capability tokens. No separate token system is created.

`introspect()` calls the vault's existing validation logic, extended with lineage checks.

### Audit Service

All orchestration events flow through the existing `AuditService`. The service receives the standard `AuditEvent` structure, with `event_type` set to one of the `ORCHESTRATE_*` variants. The audit writer does not need to know that these events come from orchestration — it writes them the same way it writes `ACCESS_GRANT` or `POLICY_VIOLATION` events.

### Kill Switch

Kill switch checks reuse the existing `KillSwitch` infrastructure. When `introspect()` queries token validity, it also queries the kill switch table by `root_decision_id`. If an emergency stop is active for that root, `introspect()` returns `killed`.

The kill switch implementation does not need to understand orchestration patterns. It only needs to know which `decision_id` values are roots, and which child decisions descend from them. The lineage table provides this mapping.

---

## Migration

Schema additions for orchestration lineage are in `db/migrations/015_orchestration_lineage.sql`.

This migration adds:

- `parent_decision_id` and `root_decision_id` columns to the `decisions` table
- `parent_actor_id` and `workflow_id` columns to the `tokens` table
- A `lineage_index` on `(root_decision_id, trace_id)` for efficient tree reconstruction
- `superseded_by` column to the `tokens` table for handoff tracking
- `event_type` enum values for `ORCHESTRATE_DELEGATE`, `ORCHESTRATE_HANDOFF`, `ORCHESTRATE_GATHER`, `ORCHESTRATE_INTROSPECT`, and `ORCHESTRATE_KILL`

Run this migration before enabling orchestration features. The migration is backward-compatible: existing rows receive `null` for new columns, and old codepaths continue to function.

---

## Backward Compatibility

Existing `cg.execute()` callers continue to work without modification.

`cg.execute()` creates a **root decision** with no `parent_decision_id`. It receives a token with no `parent_actor_id` or `workflow_id`. Lineage fields are **optional** at the API level: the REST endpoints and SDK methods accept calls that omit them, and the kernel treats missing lineage as a root decision.

No existing token is invalidated by the migration. No existing decision is orphaned. The orchestration layer is additive.

If an older client calls `cg.execute()` and a newer client later calls `cg.delegate()` on the resulting decision, the lineage chain starts at that point. The root decision retroactively becomes the root of a tree.

---

## Summary

Citadel's orchestration is one governance kernel with four primitives. `delegate`, `handoff`, `gather`, and `introspect` all flow through the same decision engine, token vault, audit spine, and kill switch. The differences between Supervisor/Worker, Handoff, and Planner/Worker/Solver are in how authority branches and transfers — not in which systems execute the rules.

Engineers integrating Citadel into agent systems should use these primitives directly. The kernel enforces scope narrowing, records lineage, audits every transition, and provides a unified kill switch. Build your patterns on top of this foundation. The foundation does not change.
