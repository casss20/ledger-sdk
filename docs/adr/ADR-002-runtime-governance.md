# ADR-002: Runtime Governance Enforcement

## Status
Accepted

## Context

Citadel's core value proposition is enforcing governance over AI agent actions. A critical architectural decision is *when* governance rules are evaluated:

- **Compile-time / build-time:** Static analysis of agent code, policy linting, schema validation before deployment.
- **Runtime:** Intercepting and evaluating every agent action as it executes, with real-time policy resolution, human approvals, and kill switches.

This decision affects the threat model, latency, flexibility, and implementation complexity of the entire system.

## Options Considered

### Option A: Compile-Time Enforcement Only

Validate agent behavior statically before deployment. Policies are checked via linting, schema validation, and code analysis. Once deployed, the agent runs ungoverned.

**Pros:**
- Zero runtime overhead
- Simple implementation (static analyzers, linters)
- No infrastructure required at execution time

**Cons:**
- Cannot stop dynamic behavior (agents that generate code, call APIs, or use tools unpredictably)
- No human-in-the-loop for novel situations
- No kill switch for runaway agents
- Useless against prompt injection that changes agent behavior post-deployment
- Cannot enforce quotas, rate limits, or budget controls dynamically

### Option B: Runtime Enforcement Only

Every agent action is intercepted at runtime, sent to the governance kernel, evaluated against live policies, and only then approved or blocked.

**Pros:**
- Full control over every action
- Dynamic policy updates without redeployment
- Human-in-the-loop for edge cases
- Kill switch works immediately
- Budget, quota, and rate limit enforcement in real time

**Cons:**
- Adds latency to every agent action (mitigatable with caching and async)
- Requires infrastructure (hosted API or self-hosted runtime)
- Higher complexity (distributed systems, consistency, failure modes)

### Option C: Hybrid — Compile-Time Lint + Runtime Gate (Chosen)

Static analysis catches obvious issues at build time. Runtime enforcement catches everything else. The runtime is the *source of truth*; compile-time checks are advisory optimizations.

**Pros:**
- Defense in depth
- Fast feedback loop for developers (lint catches errors before deploy)
- Runtime still protects against all dynamic threats
- Can skip expensive runtime checks for pre-verified patterns

**Cons:**
- More complex system to maintain
- Risk of users relying only on compile-time and disabling runtime
- Two policy formats to keep in sync (lint rules + runtime rules)

### Option D: Agent-Side Library Enforcement

Embed governance logic directly in the agent's environment (e.g., monkey-patch OpenAI client, LangChain callback). No external runtime.

**Pros:**
- Lowest latency (in-process)
- Works offline
- Simple deployment

**Cons:**
- Agent can bypass governance (just don't import the library)
- No central audit trail if multiple agents run in different processes
- Cannot enforce cross-agent policies or global budgets
- Kill switch is per-process, not global

## Chosen Option

**Option C: Hybrid — Compile-Time Lint + Runtime Gate**

Runtime enforcement is the **authoritative** governance layer. Every action flows through the governance kernel at execution time. Compile-time linting (`citadel lint`, policy pre-checks) exists as a developer convenience but cannot override or replace runtime decisions.

### Rationale

1. **Agents are dynamic.** LLM-based agents generate behavior at runtime. Static analysis cannot predict what an agent will do after a prompt injection or tool call.
2. **Trust but verify.** Even well-behaved agents need runtime guardrails for novel inputs, new tools, or adversarial environments.
3. **Regulatory requirements.** Future compliance standards (EU AI Act, NIST AI RMF) will require auditable runtime decisions, not just pre-deployment checks.
4. **Kill switch must be real-time.** A compile-time kill switch is an oxymoron.
5. **Compile-time is still valuable.** Catching policy violations at `git push` is a better developer experience than catching them in production. But it is *supplemental*, not *sufficient*.

## Consequences

### Positive

- Maximum protection against dynamic and adversarial agent behavior
- Audit trail captures every runtime decision with full context
- Policies can be updated instantly without redeploying agents
- Human-in-the-loop works for truly novel situations
- Budget and quota enforcement is accurate and real-time

### Negative

- Every action incurs network latency to the governance runtime (mitigated with async, caching, and edge deployment)
- Runtime becomes a critical dependency — if it's down, agents are blocked (or must degrade gracefully)
- More infrastructure to operate (the runtime itself)
- Need to maintain both lint rules and runtime policy schemas

### Mitigations

- **Async SDK** (ADR-001) minimizes latency overhead
- **Local caching** of policy rules with TTL reduces round-trips for repeat actions
- **Graceful degradation:** SDK can be configured to `ALLOW` with warning if runtime is unreachable (opt-in, not default)
- **Edge deployment:** Runtime can be self-hosted close to agents for <5ms latency

## Related Decisions

- ADR-001: Async-First Client Design (streaming runtime responses)
- ADR-003: Module Boundaries (runtime is separate deployable unit)
- ADR-004: SDK vs Runtime Split (runtime is the enforcement engine)

## Date
2026-04-10

## Authors
Anthony Cass, Citadel SDK Team
