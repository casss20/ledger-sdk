# SCHEDULER.md — Ledger SDK Deferred Work Tracker

**Purpose:** Single source of truth for intentionally punted features.  
**Rule:** Nothing gets dropped without being recorded here first.  
**Review:** Check this file before declaring "we're done".

---

## 🚦 Status Legend

| Status | Meaning |
|--------|---------|
| `TODO` | Not started, no decision made |
| `DEFERRED` | Consciously postponed, needs revisit |
| `IN_PROGRESS` | Actively being worked |
| `WONTFIX` | Explicitly rejected, documented why |
| `DONE` | Complete, verified |

---

## 🔴 Critical Gaps (Block Production)

### Error Handling (Try/Catch for Governance)
**Status:** `DONE`  
**Priority:** HIGH  
**Completed:** 2026-04-19  
**Impact:** Governance actions now have resilient error handling  
**Acceptance:**
- [x] `@try_governed` decorator with retry logic
- [x] `@catch` decorator for error routing
- [x] Fallback handlers registered in GOVERNOR
- [x] Failed actions visible in dashboard

**File:** `src/ledger/error_handling.py`

---

### Subgraph Execution (Outputs as Endpoints)
**Status:** `DONE`  
**Priority:** MEDIUM  
**Completed:** 2026-04-19  
**Impact:** Can run "just the email part" without executing whole graph  
**Acceptance:**
- [x] `@executor.output()` decorator
- [x] Subgraph extraction from action dependencies
- [x] Selective execution API (`run_output()`, `run_outputs()`)
- [x] Per-output cost estimation

**File:** `src/ledger/subgraph.py`

---

## 🟡 Visibility Gaps (Operational Risk)

### GOVERNOR Integration
**Status:** `IN_PROGRESS`  
**Priority:** HIGH  
**Why deferred:** Just implementing now  
**Impact:** No visibility into skipped/deferred/pending actions  
**Acceptance:**
- [x] Governor class with ActionRecord tracking
- [x] State transitions (PENDING -> EXECUTING -> SUCCESS/FAILED)
- [x] Skip tracking (null propagation)
- [ ] Wire into `@governed` decorator
- [ ] Wire into `DurableApprovalQueue`
- [ ] Dashboard API endpoints

**Depends on:** Error handling (for FAILED state tracking)

---

### Cross-Action Analytics
**Status:** `TODO`  
**Priority:** MEDIUM  
**Why deferred:** Single-action tracking works for now  
**Impact:** Can't see "agent tried 50 emails in 1 minute" patterns  
**Acceptance:**
- [ ] Time-windowed rate analysis
- [ ] Anomaly detection (sudden spike in HIGH risk actions)
- [ ] Agent behavior profiling

---

## 🟢 Weft Patterns (Adopted or Rejected)

| Pattern | Status | File | Notes |
|---------|--------|------|-------|
| Durable execution | `DONE` | `durable.py` | Redis-backed promises |
| Recursive groups | `DONE` | `groups.py` | Collapsible action groups |
| Catalog pattern | `DONE` | `catalog.py` | Auto-discovery |
| Null propagation | `DONE` | `null_propagation.py` | SkipExecution exception |
| Native mocking | `DONE` | `mocking.py` | @mockable decorator |
| Compile validation | `DONE` | `validation.py` | Pydantic validation |
| Dense syntax | `DONE` | `dense.py` | gov.action() DSL |
| Sidecar pattern | `DONE` | `sidecar.py` | HTTP infrastructure bridge |
| Two native views | `DONE` | Dashboard | Table/Flow/Groups |
| User-defined types | `WONTFIX` | — | Pydantic covers this |
| Infrastructure+Consumer | `WONTFIX` | — | Overkill for library |
| Error handling | `DONE` | `error_handling.py` | @try_governed, Retry, Catch, Default |
| Subgraph execution | `DONE` | `subgraph.py` | @executor.output, selective execution |

---

## 📋 Review Checklist

Before declaring milestone complete:

- [ ] All `TODO` items in this file evaluated
- [ ] All `DEFERRED` items have revisit date
- [ ] All `WONTFIX` items have documented rationale
- [ ] GOVERNOR shows zero blind spots (all paths tracked)
- [ ] Dashboard displays all action states

---

## 📝 Decision Log

### 2026-04-19: User-defined types rejected
**Decision:** WONTFIX  
**Rationale:** Python has Pydantic/dataclasses. Adding @struct would be syntactic sugar over existing capability. Not worth the complexity.

### 2026-04-19: Infrastructure+Consumer rejected  
**Decision:** WONTFIX  
**Rationale:** Weft is a platform (provisions K8s). Ledger SDK is a library (connects to existing infra). K8s provisioning would turn library into platform — scope creep.

### 2026-04-19: Architectural Decision (Governor vs SDK)
**Decision:** Option B — Keep separation of concerns  
**Rationale:** Ledger owns execution, Governor owns visibility. Governor never controls execution; Ledger reports to Governor. Matches current implementation, keeps responsibilities clean.  
**File:** `docs/ARCHITECTURE_DECISION.md`

### 2026-04-19: Error handling implemented
**Decision:** DONE  
**Implementation:** `@try_governed` decorator with `Retry()`, `Catch()`, `Default()`, `DeadLetter()` strategies. Reports FAILED to Governor.  
**Unblocks:** All Phase 2 work.

### 2026-04-19: Subgraph execution implemented
**Decision:** DONE  
**Implementation:** `SubgraphExecutor` with `@executor.output()` decorator. Extracts subgraph upstream of selected outputs, runs only needed actions. Per-output cost estimation.  
**Pattern:** From Weft's "Outputs as endpoints, subgraph execution".

---

## 🎯 Next Actions

1. **Cross-action analytics** — Time-windowed rate analysis, anomaly detection
2. **Dashboard API** — Governor endpoints for UI consumption  
3. **PyPI prep** — Package for distribution
4. **Review SCHEDULER.md** — Every sprint, check for drift

---

*Last updated: 2026-04-19*  
*Owner: Ledger SDK maintainers*  
*Review cadence: Weekly until 1.0, then monthly*
