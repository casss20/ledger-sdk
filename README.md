# Ledger SDK

**Governed action execution with audit trails.**

A governance engine that intercepts actions, applies policy, requires approval for risky ones, executes the allowed ones, and logs everything to a tamper-evident audit chain.

## What Core Does Today

The production core is a **stateless governance pipeline** backed by PostgreSQL:

1. **Policy Resolution** — Rules match on actor, action, resource, and context. Rules resolve in precedence order. The winning rule decides: `ALLOWED`, `BLOCKED_*`, `PENDING_APPROVAL`, `RATE_LIMITED`.

2. **Capability Tokens** — Scoped, expiring, use-limited tokens that bypass policy for pre-authorized actions.

3. **Approval Queue** — Human-in-the-loop for actions that match `PENDING_APPROVAL` rules. Approvers get a queue; decisions are recorded with reasons.

4. **Execution** — Allowed actions execute through a configurable executor. Results are captured or failures are logged.

5. **Audit Chain** — Every action and decision is hashed and linked in Postgres. The chain is append-only (triggers block UPDATE/DELETE). A `verify_audit_chain()` function checks integrity.

6. **Idempotency** — Duplicate requests with the same `idempotency_key` return the original result without re-executing.

7. **FastAPI API** — `POST /v1/actions/execute` runs an action through the full pipeline. `GET /v1/audit/verify` checks chain integrity. `GET /health/ready` reports database connectivity. API key auth via `X-API-Key`.

8. **Universal SDK** — `LedgerClient(base_url, api_key)` works from Python with `httpx`. `execute()`, `guard()`, `wrap()`, `approve()`, `reject()`, `verify_audit()` are the surface.

9. **Orchestrator** — `Orchestrator(kernel, executor)` runs a goal through a loop: plan → govern → execute → review → cleanup. Planner, critic, and prune are injected; stubs are used by default.

### Directory Layout (Core)

```
src/ledger/
├── actions/          # Canonical Action, Decision, KernelStatus, KernelResult models
├── execution/        # Kernel (governance pipeline) + Executor (action runner)
├── audit/            # AuditService + audit chain verification
├── api/              # FastAPI app, routers, middleware, dependencies
├── sdk/              # LedgerClient (httpx-based universal client)
├── policies/         # PolicyResolver, Precedence, PolicyEvaluator
├── repository.py     # All DB access (actions, decisions, audit, capabilities, actors, policies)
├── approval_service.py
├── capability_service.py
├── orchestrator.py
└── config.py         # Pydantic Settings, .env support
```

## What Experimental Is Building Toward

The `experimental/agent_runtime/` directory contains aspirational modules for an **autonomous agent governance runtime** — a different system from the core action-authorization engine. These modules are isolated from core; nothing in `src/ledger/` imports them.

**Modules in experimental:**

- `planner.py` (~520 lines) — Goal decomposition and action sequencing
- `critic.py` (~450 lines) — Post-execution review and feedback loops
- `prune.py` (~400 lines) — State cleanup and memory management
- `focus.py` (~470 lines) — Attention routing and mode selection
- `constitution.py` (~250 lines) — Agent self-governance rules

**What would need to happen for experimental to integrate with core:**

1. **Shared model** — `experimental/planner.py` must output `ledger.actions.Action` objects so the core kernel can govern them.

2. **State contract** — `experimental/critic.py` and `experimental/prune.py` must accept `ledger.orchestrator.OrchestratorState` instead of their own state types.

3. **Policy bridge** — `experimental/constitution.py` rules must map to `ledger.policies.Policy` objects so the kernel's `PolicyResolver` can evaluate them.

4. **Execution wiring** — `experimental/planner.py` → `ledger.orchestrator.Orchestrator.run()` → `ledger.execution.Kernel.handle()` → `ledger.execution.Executor.execute()`.

5. **Test isolation** — Experimental tests live in `experimental/tests/` and run separately from core tests.

**Status:** Experimental is not wired to core. The Orchestrator accepts planner/critic/prune as constructor arguments, so they *can* be injected, but the experimental modules do not yet conform to the core interfaces. The README will be updated when that wiring is complete.

## Installation

```bash
pip install ledger-sdk
```

Requires PostgreSQL 14+ for the audit chain and policy storage.

## Quick Start

```python
import ledger

# Via API
client = ledger.LedgerClient(base_url="http://localhost:8000", api_key="your-key")
result = await client.execute(
    action="email.send",
    resource="user:123",
    payload={"to": "user@example.com"},
    actor_id="agent-1",
)
print(result.status)  # "executed", "blocked", "pending_approval"
```

## Documentation

- [Architecture Schema](docs/ARCHITECTURE_SCHEMA.md) — Module dependency graph
- [Kernel Guarantees](docs/KERNEL_GUARANTEES.md) — Invariants and edge cases
- [API Reference](docs/API.md) — HTTP endpoints and request/response schemas

## License

MIT
