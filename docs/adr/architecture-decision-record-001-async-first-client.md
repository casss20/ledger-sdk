# ADR-001: Async-First Client Design

## Status
Accepted

## Context

The Citadel SDK is a governance layer for AI agents. Agents are inherently concurrent — they may execute multiple actions in parallel, stream responses, or run long-running tasks. The client library must handle:

- High-throughput action submission (batch agent operations)
- Streaming audit logs and real-time status updates
- Non-blocking governance checks that run inline with agent execution
- Integration with modern Python async ecosystems (FastAPI, asyncio, LangChain, etc.)

We needed to decide whether the SDK should be synchronous, asynchronous, or support both as first-class citizens.

## Options Considered

### Option A: Synchronous-Only SDK

Provide only blocking `requests`-based HTTP calls. Simple, familiar, works everywhere.

**Pros:**
- Zero learning curve for beginners
- Works in sync contexts (scripts, Jupyter notebooks) without `asyncio.run()`
- Smaller API surface

**Cons:**
- Terrible for agent use cases: every governance check blocks the event loop
- Cannot stream audit logs or status updates efficiently
- Forces users to wrap everything in `asyncio.to_thread()` when used in async apps
- Cannot leverage `httpx` connection pooling for concurrent agent actions

### Option B: Async-Only SDK

Provide only `async`/`await` APIs using `httpx.AsyncClient`.

**Pros:**
- Optimal for agent concurrency and streaming
- Natural fit for FastAPI, LangChain, and modern async frameworks
- Single code path to maintain
- Connection pooling and concurrent requests out of the box

**Cons:**
- Steep learning curve for users unfamiliar with asyncio
- Requires `asyncio.run()` boilerplate in simple scripts
- Jupyter notebooks need special handling (`await` in cells works, but not in plain `.py` scripts)

### Option C: Dual API (Sync + Async)

Provide both `CitadelClient` (sync) and `AsyncCitadelClient` (async), auto-generated from a single schema or maintained in parallel.

**Pros:**
- Best of both worlds for users
- Sync for scripts, async for production agents

**Cons:**
- **2× maintenance burden** — every method, every test, every docstring duplicated
- Risk of drift between sync and async implementations
- Larger bundle size / package complexity
- Auto-generation from async is possible but adds build tooling complexity

### Option D: Async-First with Optional Sync Wrapper (Chosen)

Core SDK is async-only. Provide a thin `CitadelClient` sync wrapper that internally runs `asyncio.run()` for simple use cases.

**Pros:**
- Single source of truth for core logic
- Optimal performance path is the default
- Sync wrapper is thin and auto-derived
- Can evolve to full dual API later without breaking changes

**Cons:**
- Sync wrapper has event-loop edge cases (nested loops in Jupyter, etc.)
- Still need to document two patterns

## Chosen Option

**Option D: Async-First with Optional Sync Wrapper**

The core `CitadelClient` is built on `httpx.AsyncClient`. All governance primitives (`submit`, `approve`, `audit`, `stream`) are async-native. A thin synchronous wrapper (`citadel.sync.CitadelClient`) delegates to the async implementation via `asyncio.run()` for convenience.

### Rationale

1. **Agent workloads are concurrent by nature.** An agent may need to submit 50 actions in parallel. Blocking each call is unacceptable.
2. **Streaming is a first-class requirement.** Real-time audit logs and status updates require async iterators.
3. **Python ecosystem has shifted.** FastAPI, LangChain, and modern frameworks are async-native. Being sync-only is a competitive disadvantage.
4. **Maintenance sanity.** We are a small team. Maintaining two full API surfaces is not feasible pre-Series A.
5. **Escape hatch exists.** The sync wrapper handles 80% of simple use cases without forcing asyncio knowledge.

## Consequences

### Positive

- SDK can handle thousands of concurrent agent actions without blocking
- Natural integration with FastAPI, LangChain, AutoGen, and other async frameworks
- Streaming audit logs and WebSocket-like status feeds are trivial to implement
- Single core implementation reduces bug surface area

### Negative

- Users writing simple scripts must either use `asyncio.run()` or the (slightly limited) sync wrapper
- Sync wrapper has known edge cases with nested event loops (e.g., inside Jupyter or existing async contexts)
- Documentation must cover both sync and async patterns
- Testing requires `pytest-asyncio` and careful fixture setup

### Mitigations

- Provide clear quick-start examples for both sync and async usage
- Document the nested event loop workaround (`nest_asyncio` for Jupyter)
- Ensure sync wrapper raises clear errors when called inside an existing loop

## Related Decisions

- ADR-002: Runtime Governance Enforcement (streaming audit requires async)
- ADR-004: SDK vs Runtime Split (async SDK talks to async runtime)

## Date
2026-04-15

## Authors
Anthony Cass, Citadel SDK Team
