# Microsoft Agent Governance Toolkit (AGT) â€” Architecture Analysis

> **Prepared for**: Citadel SDK Series A (September 2026)  
> **Analysis Date**: April 2026  
> **AGT Version**: v3.2.0 (Public Preview)  
> **License**: MIT (legal to port with attribution)  

---

## What This Is

This document analyzes Microsoft's Agent Governance Toolkit (AGT) to identify what CITADEL should **port**, **improve**, and **skip** during the 10-phase governance runtime build.

---

## AGT Architecture Overview

### Package Structure

| Package | Purpose | CITADEL Equivalent |
|---------|---------|-------------------|
| `agent-os` | Policy engine, capability model, audit logging, MCP gateway | `src/CITADEL/policy/`, `src/CITADEL/audit/` |
| `agent-mesh` | Zero-trust identity, trust scoring, A2A/MCP/IATP bridges | `src/CITADEL/identity/` |
| `agent-runtime` | Privilege rings, saga orchestration, termination control | `src/CITADEL/kernel/` |
| `agent-sre` | SLOs, error budgets, chaos engineering, circuit breakers | `src/CITADEL/sre/` |
| `agent-compliance` | OWASP verification, integrity checks, policy linting | `src/CITADEL/compliance/` |
| `agent-discovery` | Shadow AI discovery, inventory, risk scoring | Future â€” not in scope |
| `agent-hypervisor` | Reversibility verification, execution plan validation | Skip â€” too heavy for SDK |

### Key Patterns Identified

#### Pattern 1: Trust Policy Evaluator
- **Location**: `packages/agent-mesh/src/agentmesh/governance/policy_evaluator.py`
- **What it does**: Evaluates rules in priority order (lower number = higher priority). First match wins.
- **CITADEL adaptation**: Already have `PolicyResolver` + `PolicyEvaluator`. Keep and extend with YAML parser + conflict detection.

#### Pattern 2: Signed Audit Entries with Hash Chain
- **Location**: `packages/agent-mesh/src/agentmesh/governance/audit_backends.py`
- **What it does**: SHA-256 content hash + HMAC-SHA256 signature + `previous_hash` chain link.
- **CITADEL adaptation**: Already have hash-chained audit. Upgrade to two-layer (content + chain) with JCS canonicalization.

#### Pattern 3: Authority Resolver with Delegation
- **Location**: `packages/agent-mesh/src/agentmesh/governance/authority.py`
- **What it does**: Reputation-gated authority with delegation chains, trust scoring (0â€“1000).
- **CITADEL adaptation**: Port delegation + trust scoring to `src/CITADEL/identity/`.

#### Pattern 4: Trust Scoring (0â€“1000)
- **Location**: `packages/agent-mesh/src/agentmesh/governance/authority.py` (TrustInfo)
- **What it does**: Composite score from identity, behavior, network, compliance sub-scores.
- **CITADEL adaptation**: Port to `src/CITADEL/identity/trust_scorer.py`.

#### Pattern 5: Audit Backends (Pluggable Sinks)
- **Location**: `packages/agent-mesh/src/agentmesh/governance/audit_backends.py`
- **What it does**: Protocol-based audit sinks (FileSink, etc.) with integrity verification.
- **CITADEL adaptation**: Port to dual-write pipeline (S3 + Elasticsearch).

---

## What We Port (COPY)

| Pattern | Source File | Destination | Notes |
|---------|-------------|-------------|-------|
| Trust scoring (0â€“1000) | `authority.py` | `identity/trust_scorer.py` | Clean port, CITADEL conventions |
| Delegation chain | `authority.py` | `identity/agent_identity.py` | Simplified for SDK |
| Audit sink protocol | `audit_backends.py` | `pipeline/dual_writer.py` | Abstract interface |
| Policy rule priority | `policy_evaluator.py` | `policy/conflict_detector.py` | For conflict detection |
| OWASP mapping | `docs/OWASP-COMPLIANCE.md` | `compliance/owasp.py` | Adapt to CITADEL features |

## What We Improve (IMPROVE)

| AGT Pattern | CITADEL Improvement | Why Better |
|-------------|-------------------|------------|
| FileSink audit backend | S3 Object Lock COMPLIANCE mode | Immutable, root cannot delete |
| Single-layer hash chain | Two-layer (content + chain) with JCS | Deterministic canonicalization per RFC 8785 |
| Policy YAML (basic) | Policy YAML + conflict detection | Detect contradictory rules before deployment |
| Trust scoring (static) | Trust scoring with decay + anomaly | Time-decayed scores, anomaly detection |
| Audit in same schema | Separate `governance` schema | Physically separate compliance evidence |
| No token system | `gt_` governance tokens | Non-portable data gravity anchor |

## What We Skip (SKIP)

| AGT Feature | Why Skip |
|-------------|----------|
| `agent-hypervisor` | Too heavy for SDK â€” reversibility verification is overkill for MVP |
| `agent-marketplace` | Out of scope â€” plugin marketplace not needed for governance runtime |
| `agent-lightning` | RL training governance â€” niche use case |
| E2E encrypted messaging (Signal protocol) | Overkill for SDK â€” transport layer concern |
| Wire Protocol spec + MeshClient | Distributed agent mesh â€” CITADEL is SDK, not infrastructure |
| VS Code extension | IDE integration â€” not core governance |
| 9,500+ AGT tests | We write our own tests (156 target) â€” no code copy |

---

## Legal Basis

Microsoft AGT is released under the **MIT License**. This permits:
- âœ“ Commercial use
- âœ“ Modification
- âœ“ Distribution
- âœ“ Private use
- âœ“ Sublicensing

Requirement: **Preserve copyright notice and MIT license text** in `NOTICES.md`.

CITADEL's implementation:
- Reads AGT for architectural patterns (ideas, not code)
- Rewrites all code in CITADEL's conventions (async Python, PostgreSQL, strict RLS)
- Does NOT copy AGT source files directly
- Does NOT use AGT package names or trademarks

This is clean-room inspired implementation â€” legal and ethical.

---

## Integration Points

### Where AGT Patterns Connect to CITADEL

```
AGT Policy Evaluator â”€â”€â–º CITADEL PolicyResolver + conflict_detector.py
AGT Audit Backends â”€â”€â–º CITADEL pipeline/dual_writer.py
AGT Authority/Trust â”€â”€â–º CITADEL identity/trust_scorer.py
AGT SRE â”€â”€â–º CITADEL sre/slo.py + circuit_breaker.py
AGT Compliance â”€â”€â–º CITADEL compliance/matrix.py
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| AGT is Public Preview (breaking changes possible) | CITADEL pins to v3.2.0 patterns; doesn't depend on AGT package |
| Microsoft could relicense | MIT is perpetual; already-cloned copy remains valid |
| Patent concerns | MIT license includes implicit patent grant; no known AGT patents |
| Over-engineering | Strict "skip" list prevents scope creep |

---

## Next Steps

1. âœ… Phase 0 complete (this document)
2. Phase 1: `gt_` token system (data gravity anchor)
3. Phase 2: Audit separation (compliance lock-in)
4. Phase 3: Two-layer hash chaining (EU AI Act Article 12)

---

*Analysis based on Microsoft Agent Governance Toolkit v3.2.0 (MIT License).*
