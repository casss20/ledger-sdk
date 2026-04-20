# Ledger SDK — Code Architecture Schema

## High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL CLIENT                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ Python   │  │ Node.js  │  │ AI Agent │  │  CLI     │                      │
│  │ SDK      │  │ SDK      │  │ Tool     │  │  Script  │                      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘                      │
│       │             │             │             │                              │
│       └─────────────┴─────────────┴─────────────┘                              │
│                     │                                                          │
│                     ▼  HTTP + JSON                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                         API LAYER (FastAPI)                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  POST /v1/actions/execute   ←── The ONE primitive                       │  │
│  │  GET  /v1/actions/{id}                                                │  │
│  │  POST /v1/approvals/{id}/approve                                      │  │
│  │  POST /v1/approvals/{id}/reject                                       │  │
│  │  GET  /v1/audit/verify                                                │  │
│  │  GET  /v1/health  /ready  /live                                       │  │
│  │  GET  /v1/metrics/summary                                             │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                     │                                                        │
│  ┌──────────────────┴──────────────────────────────────────────────────────┐   │
│  │  MIDDLEWARE                                                           │   │
│  │  • Request ID tracing  • API key auth  • Error handling  • CORS      │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                     │                                                        │
└─────────────────────┼────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      KERNEL LAYER (Governance Engine)                        │
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐        │
│  │  Policy Resolver │───▶│  Precedence      │───▶│  Decision          │        │
│  │  (rules engine)  │    │  (deterministic) │    │  (terminal state)  │        │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘        │
│           │                      │                      │                    │
│           ▼                      ▼                      ▼                    │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐        │
│  │  Capabilities    │    │  Risk Scoring    │    │  Execution         │        │
│  │  (token check)   │    │  (approval svc)  │    │  (side effects)    │        │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘        │
│           │                      │                      │                    │
│           └──────────────────────┼──────────────────────┘                    │
│                                  ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Audit Service                                                       │   │
│  │  • Append-only chain  • SHA-256 hash  • Trigger-enforced integrity   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                  │                                         │
└──────────────────────────────────┼─────────────────────────────────────────┘
                                   │
                                   ▼  asyncpg pool
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DATABASE LAYER (Postgres 15+)                           │
│                                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────────┐     │
│  │   actors   │  │  actions   │  │  decisions │  │  policy_snapshots  │     │
│  │  (who)     │  │  (what)    │  │  (outcome) │  │  (versioned rules) │     │
│  └────────────┘  └────────────┘  └────────────┘  └────────────────────┘     │
│                                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────────────────┐     │
│  │ approvals  │  │ audit_events│  │  kill_switches + capability_tokens │     │
│  │ (pending)  │  │ (hash chain)│  │  (controls)                        │     │
│  └────────────┘  └────────────┘  └────────────────────────────────────┘     │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │  TRIGGERS                                                           │     │
│  │  • set_audit_prev_hash()  →  links event to previous               │     │
│  │  • calculate_event_hash() →  SHA-256 of prev_hash + event_data   │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Call Graph

```
ledger.execute()                    # SDK entry point
    │
    ├──▶ POST /v1/actions/execute   # FastAPI router
    │       │
    │       ├──▶ require_api_key()  # Auth dependency
    │       │
    │       ├──▶ get_kernel()       # Kernel factory (singleton per app)
    │       │
    │       └──▶ kernel.handle(action)
    │               │
    │               ├──▶ precedence.resolve(action, policy_snapshot)
    │               │       │
    │               │       ├──▶ KillSwitch check       → BLOCKED_KILL_SWITCH
    │               │       ├──▶ Capability check      → MISSING_CAPABILITY
    │               │       ├──▶ Explicit allow rules    → ALLOWED
    │               │       ├──▶ Explicit deny rules    → BLOCKED_POLICY
    │               │       ├──▶ Hard deny rules       → HARD_DENIED
    │               │       └──▶ Default deny           → BLOCKED_DEFAULT
    │               │
    │               ├──▶ approval_service.check_risk(action)
    │               │       │
    │               │       └──▶ high/critical risk → CREATE pending approval
    │               │
    │               ├──▶ executor.execute(action, decision)
    │               │       │
    │               │       ├──▶ SidecarClient dispatch (async)
    │               │       └──▶ Return result or error
    │               │
    │               └──▶ audit_service.record(action, decision, result)
    │                       │
    │                       └──▶ INSERT INTO audit_events
    │                               (trigger: set_audit_prev_hash)
    │                               (trigger: calculate_event_hash)
    │
    └──▶ LedgerResult(action_id, status, rule, reason, executed, result)
```

## Module Dependency Map

```
src/ledger/
│
├── __init__.py          # Re-exports: LedgerClient, execute, guard, wrap
│
├── sdk.py               # HTTP client (depends on: none)
│   └── httpx.AsyncClient
│
├── api/                 # FastAPI package (depends on: kernel, config)
│   ├── __init__.py      # App factory (depends on: all routers)
│   ├── dependencies.py  # get_kernel(), require_api_key() (depends on: kernel, config)
│   ├── middleware.py    # LoggingMiddleware (depends on: config)
│   └── routers/
│       ├── actions.py   # (depends on: kernel)
│       ├── approvals.py # (depends on: kernel.repo)
│       ├── audit.py     # (depends on: kernel.audit)
│       ├── health.py    # (depends on: kernel.repo.pool)
│       └── metrics.py   # (depends on: kernel.repo)
│
├── kernel.py            # Core engine (depends on: repository, precedence, executor, approval_service, audit_service)
│
├── repository.py        # DB ONLY (depends on: asyncpg, json)
│
├── config.py            # Settings (depends on: pydantic-settings)
│
├── precedence.py        # Deterministic ordering (depends on: repository)
│
├── policy_resolver.py     # Rule matching (depends on: precedence)
│
├── approval_service.py    # Risk + approvals (depends on: repository)
│
├── audit_service.py       # Hash chain (depends on: repository)
│
├── executor.py            # Side effect runner (depends on: repository, sidecar)
│
└── core/                # Subpackage (constitution, governor, runtime, executor)
    ├── constitution.py
    ├── governor.py
    ├── executor.py
    └── runtime.py
```

## Data Flow: Action Lifecycle

```
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│  SUBMIT    │────▶│  DECIDE    │────▶│  EXECUTE   │────▶│  AUDIT     │
│            │     │            │     │            │     │            │
│  actor_id  │     │  winning   │     │  sidecar   │     │  event_id  │
│  action    │     │  rule      │     │  dispatch  │     │  prev_hash │
│  resource  │     │  status    │     │  callback  │     │  event_hash│
│  payload   │     │  reason    │     │  result    │     │  action_id │
│  context   │     │            │     │            │     │  decision  │
└────────────┘     └────────────┘     └────────────┘     └────────────┘
     │                   │                   │                   │
     ▼                   ▼                   ▼                   ▼
  actions table     decisions table    (external)         audit_events table
  (FK → actors)     (FK → actions)                         (trigger-protected)
```

## State Machine: Decision Outcomes

```
                    ┌─────────────────┐
                    │  ACTION RECEIVED │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  ALLOWED    │  │   BLOCKED   │  │  APPROVAL   │
    │             │  │   (deny)    │  │  REQUIRED   │
    └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
           │                │                │
           ▼                ▼                ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  EXECUTE    │  │  REJECT     │  │  CREATE     │
    │  sidecar    │  │  (terminal) │  │  approval   │
    │  dispatch   │  │             │  │  record     │
    └──────┬──────┘  └─────────────┘  └──────┬──────┘
           │                                │
           ▼                                ▼
    ┌─────────────┐                  ┌─────────────┐
    │  EXECUTED   │                  │  PENDING    │
    │  or FAILED  │                  │  APPROVAL   │
    │             │                  │             │
    └─────────────┘                  └──────┬──────┘
                                            │
                              ┌─────────────┴─────────────┐
                              │                             │
                              ▼                             ▼
                       ┌─────────────┐              ┌─────────────┐
                       │  APPROVED   │              │  REJECTED   │
                       │  → EXECUTE  │              │  → BLOCKED  │
                       └─────────────┘              └─────────────┘
```

## Key Invariants

| Invariant | Enforced By |
|-----------|-------------|
| Single DB access point | `repository.py` only |
| Append-only audit | Postgres triggers + no UPDATE/DELETE on audit_events |
| Deterministic precedence | `precedence.py` — fixed rule ordering |
| Audit chain integrity | `calculate_event_hash()` trigger with `prev_hash` linkage |
| API statelessness | All state in Postgres; API just orchestrates |
| Auth everywhere | `require_api_key()` dependency on all mutation routes |
