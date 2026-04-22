# AGT → Ledger Pattern Mapping

> **How to use this**: Every pattern from Microsoft AGT is bucketed into COPY, IMPROVE, or SKIP.  
> This is the implementation checklist for the 10-phase build.

---

## COPY (Port Directly)

### Pattern: Trust Scoring (0–1000 Scale)
- **AGT Source**: `packages/agent-mesh/src/agentmesh/governance/authority.py` (TrustInfo dataclass)
- **Ledger Destination**: `src/ledger/identity/trust_scorer.py`
- **What to copy**: Score composition formula (identity × 0.2 + behavior × 0.3 + network × 0.2 + compliance × 0.3)
- **What to change**: Make async, add PostgreSQL persistence, add time decay
- **Phase**: 7 (Agent Identity + Trust)

### Pattern: Delegation Chain
- **AGT Source**: `packages/agent-mesh/src/agentmesh/governance/authority.py` (DelegationInfo)
- **Ledger Destination**: `src/ledger/identity/agent_identity.py`
- **What to copy**: Parent-child relationship, depth tracking, capability inheritance
- **What to change**: Use UUIDs instead of DIDs (simpler for SDK), add RLS
- **Phase**: 7

### Pattern: Audit Sink Protocol
- **AGT Source**: `packages/agent-mesh/src/agentmesh/governance/audit_backends.py` (AuditSink)
- **Ledger Destination**: `src/ledger/pipeline/dual_writer.py`
- **What to copy**: Protocol/interface design (write, write_batch, verify_integrity)
- **What to change**: Make async, add S3 + Elasticsearch implementations
- **Phase**: 4 (Dual-Write Pipeline)

### Pattern: Rule Priority + First Match Wins
- **AGT Source**: `packages/agent-mesh/src/agentmesh/governance/policy_evaluator.py`
- **Ledger Destination**: `src/ledger/policy/conflict_detector.py`
- **What to copy**: Priority sorting, first-match evaluation
- **What to change**: Add conflict detection (warn when rules overlap)
- **Phase**: 1 (Policy extension)

---

## IMPROVE (Port + Enhance)

### Pattern: Single-Layer Hash Chain → Two-Layer Hash Chain
- **AGT**: SHA-256 content hash + previous_hash link
- **Ledger Upgrade**: 
  - Layer 1: Content hash with JCS canonicalization (RFC 8785)
  - Layer 2: Chain hash in separate aggregation layer
  - Why: Compromising one layer insufficient to forge trail
- **Phase**: 3

### Pattern: FileSink → S3 Object Lock COMPLIANCE
- **AGT**: File-based audit sink
- **Ledger Upgrade**: 
  - S3 Object Lock COMPLIANCE mode (irreversible)
  - Time-partitioned keys for efficient lifecycle
  - KMS encryption
- **Phase**: 4

### Pattern: Basic YAML Policy → YAML + Conflict Detection
- **AGT**: Simple YAML policy loader
- **Ledger Upgrade**:
  - YAML policy parser with schema validation
  - Conflict detector (overlapping rules)
  - Policy versioning with migration
- **Phase**: 1

### Pattern: Static Trust Score → Dynamic Trust Score
- **AGT**: Static 0–1000 score
- **Ledger Upgrade**:
  - Time decay (older events weighted less)
  - Anomaly detection (sudden score drops)
  - Trend tracking (improving vs degrading)
- **Phase**: 7

### Pattern: Audit in App Schema → Separate Governance Schema
- **AGT**: Audit entries in same database as operational data
- **Ledger Upgrade**:
  - Separate `governance` PostgreSQL schema
  - Separate roles (governance_admin, governance_read)
  - Separate retention (7 years)
  - No UPDATE/DELETE permissions
- **Phase**: 2

### Pattern: No Token System → gt_ Governance Tokens
- **AGT**: No equivalent
- **Ledger Innovation**:
  - Stripe `pm_` pattern adapted for governance
  - Non-portable tokens that only Ledger can resolve
  - Data gravity mechanism
- **Phase**: 1

---

## SKIP (Do Not Port)

### Agent Hypervisor
- **Why**: Reversibility verification, execution plan validation — overkill for SDK
- **Risk**: Would add 6+ months to timeline

### Agent Marketplace
- **Why**: Plugin lifecycle management — not governance core
- **Risk**: Scope creep into product marketplace

### Agent Lightning
- **Why**: RL training governance — extremely niche
- **Risk**: <1% of users would use this

### E2E Encrypted Messaging (Signal Protocol)
- **Why**: Transport-layer concern, not governance
- **Risk**: Complex crypto, legal export considerations

### Wire Protocol + MeshClient
- **Why**: Distributed agent mesh infrastructure — Ledger is SDK
- **Risk**: Would turn SDK into infrastructure product

### VS Code Extension
- **Why**: IDE integration — not core governance runtime
- **Risk**: Maintenance burden, separate release cycle

### .NET / Rust / Go SDKs
- **Why**: Ledger is Python-first; multi-language later
- **Risk**: 3× engineering effort for marginal gain

---

## Cross-Domain Patterns (from Kimi Research)

| Pattern | Source | Ledger Implementation | Lock-in Mechanism |
|---------|--------|----------------------|-------------------|
| `gt_` tokens | Stripe `pm_` | `src/ledger/tokens/` | Data gravity |
| Audit separation | Datadog Audit Trail | `governance` schema | Separate migration target |
| RLS enforcement | PostgreSQL native | All tables with `FORCE RLS` | Query rewriter enforcement |
| Immutable spans | OpenTelemetry W3C | `src/ledger/tracing/` | Immutable by specification |
| Kill switch | EU AI Act Art. 14 | `src/ledger/kernel/kill_switch.py` | Regulatory mandate |
| Dual-write pipeline | OTel Collector | `src/ledger/pipeline/` | Fan-out exporter pattern |

---

## Implementation Checklist

- [x] Phase 0: Research & Setup (this document)
- [ ] Phase 1: `gt_` tokens (15 tests)
- [ ] Phase 2: Audit separation (13 tests)
- [ ] Phase 3: Two-layer hash chain (9 tests)
- [ ] Phase 4: Dual-write pipeline (15 tests)
- [ ] Phase 5: Compliance matrix (10 tests)
- [ ] Phase 6: Kill switch upgrade (8 tests)
- [ ] Phase 7: Identity + trust (12 tests)
- [ ] Phase 8: SRE infrastructure (12 tests)
- [ ] Phase 9: Dashboard + widgets (10 tests)
- [ ] Phase 10: OWASP coverage (10 tests)

**Total new tests**: 114  
**Total tests**: 42 existing + 114 new = 156

---

*Pattern extraction from Microsoft AGT v3.2.0 (MIT License) + Kimi cross-domain research.*
