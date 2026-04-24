# Citadel SDK - Code Architecture Schema

## High-Level Data Flow

```text
+---------------------------------------------------------------------------+
|                           EXTERNAL CLIENT                                 |
|                                                                           |
|  [Python SDK]   [Node.js SDK]   [AI Agent Tool]   [CLI Script]            |
|         \             |                |                 /                 |
|          \------------+----------------+----------------/                  |
|                               |                                           |
|                               v                                           |
|                         HTTP + JSON                                       |
+---------------------------------------------------------------------------+
|                         API LAYER (FastAPI)                               |
|                                                                           |
|  POST /v1/actions/execute   <- The ONE primitive                          |
|  GET  /v1/actions/{id}                                                    |
|  POST /v1/approvals/{id}/approve                                          |
|  POST /v1/approvals/{id}/reject                                           |
|  GET  /v1/audit/verify                                                    |
|  GET  /v1/health  /ready  /live                                           |
|  GET  /v1/metrics/summary                                                 |
|                                                                           |
|  MIDDLEWARE                                                               |
|  * Request ID tracing                                                     |
|  * API key auth                                                           |
|  * Error handling                                                         |
|  * CORS                                                                   |
+---------------------------------------------------------------------------+
|                    KERNEL LAYER (Governance Engine)                       |
|                                                                           |
|  Policy Resolver -> Precedence -> Decision                                |
|       |                 |              |                                  |
|       v                 v              v                                  |
|  Capabilities      Risk Scoring    Execution                              |
|  (token check)     (approval svc)  (side effects)                         |
|       \                 |              /                                  |
|        \----------------+-------------/                                   |
|                         v                                                 |
|                    Audit Service                                          |
|                    * Append-only chain                                    |
|                    * SHA-256 hash                                         |
|                    * Trigger-enforced integrity                           |
+---------------------------------------------------------------------------+
|                     DATABASE LAYER (Postgres 15+)                         |
|                                                                           |
|  actors   actions   decisions   policy_snapshots                          |
|  approvals audit_events kill_switches + capability_tokens                 |
|                                                                           |
|  TRIGGERS                                                                 |
|  * set_audit_prev_hash()  -> links event to previous                      |
|  * calculate_event_hash() -> SHA-256 of prev_hash + event_data            |
+---------------------------------------------------------------------------+
```

## Component Call Graph

```text
citadel.execute()                   # SDK entry point
    |
    +-> POST /v1/actions/execute    # FastAPI router
         |
         +-> require_api_key()      # Auth dependency
         |
         +-> get_kernel()           # Kernel factory
         |
         +-> kernel.handle(action)
              |
              +-> precedence.resolve(action, policy_snapshot)
              |    |
              |    +-> KillSwitch check        -> BLOCKED_KILL_SWITCH
              |    +-> Capability check        -> MISSING_CAPABILITY
              |    +-> Explicit allow rules    -> ALLOWED
              |    +-> Explicit deny rules     -> BLOCKED_POLICY
              |    +-> Hard deny rules         -> HARD_DENIED
              |    `-> Default deny            -> BLOCKED_DEFAULT
              |
              +-> approval_service.check_risk(action)
              |    |
              |    `-> high/critical risk -> CREATE pending approval
              |
              +-> executor.execute(action, decision)
              |    |
              |    +-> SidecarClient dispatch (async)
              |    `-> Return result or error
              |
              `-> audit_service.record(action, decision, result)
                   |
                   `-> INSERT INTO audit_events
                        -> set_audit_prev_hash()
                        -> calculate_event_hash()

    `-> CitadelResult(action_id, status, rule, reason, executed, result)
```

## Module Dependency Map

```text
src/citadel/
|
+-- __init__.py         # Re-exports: CitadelClient, execute, guard, wrap
|
+-- sdk.py              # HTTP client
|   `-- httpx.AsyncClient
|
+-- api/                # FastAPI package
|   +-- __init__.py     # App factory
|   +-- dependencies.py # get_kernel(), require_api_key()
|   +-- middleware.py   # LoggingMiddleware
|   `-- routers/
|       +-- actions.py
|       +-- approvals.py
|       +-- audit.py
|       +-- health.py
|       `-- metrics.py
|
+-- kernel.py           # Core engine
+-- repository.py       # DB only
+-- config.py           # Settings
+-- precedence.py       # Deterministic ordering
+-- policy_resolver.py  # Rule matching
+-- approval_service.py # Risk + approvals
+-- audit_service.py    # Hash chain
+-- executor.py         # Side effect runner
`-- core/
    +-- constitution.py
    +-- governor.py
    +-- executor.py
    `-- runtime.py
```

## Data Flow: Action Lifecycle

```text
[SUBMIT] -> [DECIDE] -> [EXECUTE] -> [AUDIT]

SUBMIT
* actor_id
* action
* resource
* payload
* context

DECIDE
* winning rule
* status
* reason

EXECUTE
* sidecar dispatch
* callback
* result

AUDIT
* event_id
* prev_hash
* event_hash
* action_id
* decision

Storage flow:
actions table -> decisions table -> external execution -> audit_events table
```

## State Machine: Decision Outcomes

```text
ACTION RECEIVED
|
+-- ALLOWED
|   |
|   `-- EXECUTE
|       `-- EXECUTED or FAILED
|
+-- BLOCKED
|   |
|   `-- REJECT (terminal)
|
`-- APPROVAL REQUIRED
    |
    `-- CREATE approval record
        |
        +-- APPROVED -> EXECUTE
        `-- REJECTED -> BLOCKED
```

## Key Invariants

| Invariant | Enforced By |
|-----------|-------------|
| Single DB access point | `repository.py` only |
| Append-only audit | Postgres triggers + no UPDATE/DELETE on `audit_events` |
| Deterministic precedence | `precedence.py` - fixed rule ordering |
| Audit chain integrity | `calculate_event_hash()` trigger with `prev_hash` linkage |
| API statelessness | All state in Postgres; API just orchestrates |
| Auth everywhere | `require_api_key()` dependency on all mutation routes |
