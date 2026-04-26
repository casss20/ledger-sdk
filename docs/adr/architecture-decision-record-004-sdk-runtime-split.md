# ADR-004: SDK vs Internal Runtime Split

## Status
Accepted

## Context

Citadel has two distinct but tightly coupled systems:

1. **The SDK** — Client libraries (Python, TypeScript) that developers import into their agent code to submit actions, receive decisions, and stream audit logs.
2. **The Runtime** — The governance engine (FastAPI server) that evaluates policies, manages approvals, enforces budgets, and writes audit trails.

We needed to decide how to draw the boundary between these two systems. Should the SDK be a thin HTTP client? Should it embed runtime logic? Should there be a local "mini runtime" for offline use?

## Options Considered

### Option A: Fat SDK with Embedded Runtime

The SDK includes a lightweight version of the governance kernel that runs in-process. No external runtime needed for basic use.

**Pros:**
- Works offline
- Zero latency for basic policy checks
- Simple deployment (just `pip install`)

**Cons:**
- SDK becomes huge (policy engine, database, audit logging all embedded)
- Cannot share state across multiple agent processes (each has its own embedded runtime)
- No central dashboard, approval queue, or global kill switch
- License contamination: SDK (Apache 2.0) would need to include runtime (BSL) logic
- Security: embedded runtime can be tampered with or bypassed

### Option B: Thin SDK — Pure HTTP Client

The SDK is only an HTTP client. All governance logic lives in the remote runtime.

**Pros:**
- SDK is tiny and fast to install
- Single source of truth for governance logic (the runtime)
- Centralized state, dashboard, and audit trail
- Clean license separation: SDK is pure Apache 2.0, no runtime code
- Runtime can be updated without touching deployed agents

**Cons:**
- Requires network access to runtime
- Adds HTTP latency to every action
- Cannot work offline
- Runtime is a single point of failure

### Option C: Thin SDK + Optional Local Cache (Chosen)

Core SDK is a thin HTTP client. Optional local components (policy cache, offline queue) are separate packages that enhance but do not replace the runtime.

**Pros:**
- Default path is simple and fast
- Power users can add local caching for latency-sensitive scenarios
- Runtime remains the source of truth
- Offline queue can buffer actions and sync when connectivity returns
- License separation is preserved

**Cons:**
- More packages to maintain (`sdk-python`, `sdk-cache`, `sdk-offline`)
- Users must understand when local cache is authoritative vs. advisory

### Option D: SDK with Compile-Time Policy Embedding

Policies are compiled into the agent at build time. Runtime only handles approvals and audit.

**Pros:**
- Fast local policy evaluation
- Reduces runtime load

**Cons:**
- Policy updates require agent redeployment
- Violates ADR-002 (runtime must be authoritative)
- Complex build-time tooling needed

## Chosen Option

**Option C: Thin SDK + Optional Local Cache**

The core SDK (`citadel-governance`) is a thin, async HTTP client. It knows how to:

- Serialize and submit actions to the runtime
- Stream responses and audit logs
- Handle retries, timeouts, and authentication

All governance logic (policy evaluation, approval routing, budget enforcement, audit writing) lives exclusively in the runtime.

Optional enhancements (future work, not current):
- `citadel-cache` — Local policy cache with TTL for reduced latency
- `citadel-offline` — Action queue that buffers and syncs when connectivity returns

### Rationale

1. **Source of truth.** The runtime must be the single source of truth for all governance decisions. Embedding logic in the SDK creates distributed state and trust issues.
2. **License purity.** The SDK is Apache 2.0 and contains zero BSL-licensed runtime code. This is legally clean and contributor-friendly.
3. **Operational simplicity.** Updating the runtime instantly updates behavior for all connected agents. No SDK redeployment needed.
4. **Security.** A compromised agent cannot bypass governance by modifying its local SDK. The runtime validates every request.
5. **Scalability.** The runtime can be horizontally scaled. A fat SDK cannot.

## Consequences

### Positive

- SDK install is fast and lightweight (`httpx` + pydantic models)
- Runtime can evolve independently — new policy features don't require SDK updates
- Centralized audit trail, dashboard, and approval queue
- Clean license separation enables open-source SDK contributions without BSL contamination
- Multiple agents share the same runtime state (global budgets, cross-agent policies)

### Negative

- Runtime is a hard dependency for all agent operations
- Network latency is added to every action (mitigated by async, connection pooling, and future edge caching)
- No offline mode by default (future `citadel-offline` package will address this)
- Users in air-gapped environments must self-host the runtime

### Mitigations

- **Async SDK** (ADR-001) minimizes latency via connection reuse and concurrent requests
- **Self-hosting:** Runtime is BSL-licensed and can be self-hosted for <5ms local latency
- **Graceful degradation:** SDK supports `fallback_mode=ALLOW_WITH_WARNING` for environments where runtime reachability is intermittent (opt-in, clearly documented as unsafe)
- **Future caching:** `citadel-cache` will allow local policy evaluation for pre-cached, non-critical paths

## Related Decisions

- ADR-001: Async-First Client Design (thin SDK uses async HTTP)
- ADR-002: Runtime Governance Enforcement (runtime is the authoritative enforcer)
- ADR-003: Module Boundaries (`packages/` vs `apps/` enforces the split)
- License model: `LICENSING.md` — SDK is Apache 2.0, runtime is BSL 1.1

## Date
2026-04-12

## Authors
Anthony Cass, Citadel SDK Team
