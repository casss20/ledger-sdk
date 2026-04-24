# CITADEL Core Hardening Pass Log

**Date:** 2026-04-21
**Author:** thonybot
**Runtime:** Python 3.12.3, PostgreSQL 14+, asyncpg
**Test suite:** 28 tests, all passing

---

## Issue 1: Policy Resolver Dict-Condition Bug

- **Red test commit:** `195ce28` â€” `test: reproduce policy resolver dict-condition crash (failing)`
- **Fix commit(s):** `9c3698a` â€” `fix: handle dict conditions in policy resolver + honor PENDING_APPROVAL effect (Issue 1)`
- **Files changed:**
  - `src/CITADEL/policy_resolver.py`
  - `src/CITADEL/approval_service.py`
- **Tests added:**
  - `tests/test_policy_resolver_regression.py`
    - `test_dict_condition_always_true`
    - `test_dict_condition_always_false`
    - `test_dict_condition_unknown_key`
    - `test_string_condition_still_works`
- **Category:** Policy resolver â€” schema deserialization + approval handoff
- **Root cause summary:** `_eval_condition()` called `.startswith()` on dict-typed conditions after JSONB deserialization, causing `AttributeError`. Separately, `ApprovalService` only checked `rule.get('requires_approval')`, missing rules with `effect: "PENDING_APPROVAL"`.

---

## Issue 2: Capability Double-Consumption Race

- **Red test commit:** `9d8990e` â€” `test: reproduce capability race and consumption semantic bugs (failing)`
- **Fix commit(s):**
  - `026f146` â€” `fix: capability scope matching for .* wildcard patterns`
  - `2a966df` â€” `fix: atomic capability consumption via PostgreSQL FOR UPDATE function (Issue 2)`
- **Files changed:**
  - `src/CITADEL/precedence.py`
- **Tests added:**
  - `tests/test_capability_race_regression.py`
    - `test_racing_capability_consumption_basic`
    - `test_capability_exhausted_stays_exhausted`
    - `test_consumption_before_execution_semantic`
    - `test_racing_capability_stress`
- **Category:** Capability â€” check-then-act without atomic compare-and-swap
- **Root cause summary:** `_check_capability()` read `uses` in a plain SELECT, then allowed execution. Two concurrent requests both read `uses < max_uses`, both proceeded. No atomic increment occurred, so all 5 concurrent requests succeeded instead of only 3.

---

## Issue 2.5: Idempotency Race (Bonus Finding)

- **Red test commit:** `4b86ef3` â€” `test: reproduce idempotency race â€” 10 concurrent requests insert duplicate actions (failing)`
- **Fix commit:** `f2fcd97` â€” `fix: atomic idempotent action insert with ON CONFLICT + retry lookup (Issue 2.5)`
- **Files changed:**
  - `src/CITADEL/repository.py`
  - `src/CITADEL/execution/kernel.py`
- **Tests added:**
  - `tests/test_idempotency_race_regression.py`
    - `test_racing_idempotency_basic`
    - `test_idempotency_without_key_allows_duplicates`
    - `test_idempotency_different_actors_same_key`
- **Category:** Action ingestion â€” check-then-act without atomic insert
- **Root cause summary:** The unique partial index `uq_actions_actor_idempotency` already existed, but `save_action()` used a plain `INSERT` without `ON CONFLICT`. Ten concurrent requests with the same idempotency key all passed the initial check, then raced on `INSERT`. One won, nine threw `UniqueViolationError`.

---

## Issue 3: Audit Chain Ordering Race

- **Red test commit:** `a99643a` â€” `test: reproduce audit chain hash integrity break under 50 concurrent actions (failing)`
- **Fix commit:** `a097ffe` â€” `fix: serialize audit chain appends with PostgreSQL advisory lock (Issue 3)`
- **Files changed:**
  - `src/CITADEL/repository.py`
- **Tests added:**
  - `tests/test_audit_chain_race_regression.py`
    - `test_audit_chain_integrity_under_load`
    - `test_audit_chain_stress_iterations`
- **Category:** Audit â€” shared mutable state (prev_hash) without lock
- **Root cause summary:** `save_audit_event()` did an unlocked `SELECT ... ORDER BY event_id DESC LIMIT 1` to read the previous hash, computed the new hash locally, then `INSERT`. Two concurrent requests both read the same tail hash, computed their own `prev_hash` pointing to the same parent, and both inserted. The second insert's `prev_hash` was wrong, breaking the chain.

---

## Design Decisions

### Capability consumption timing (Issue 2)
**Choice:** Consumption happens BEFORE execution.  
**Rationale:** Even failed executions consume a use. Safer against DoS where an attacker repeatedly requests with a limited-use capability and relies on executor failures to retry. The tradeoff is that transient failures waste uses, which is acceptable for safety. Documented in `Precedence._check_capability()`.

### Audit serialization (Issue 3)
**Choice:** PostgreSQL advisory lock (`pg_advisory_xact_lock(1)`)  
**Rationale:** Transaction-scoped lock auto-releases on commit, making it impossible to accidentally leave held across connection pool reuse. Keeps hash computation in application code (debuggable). Cleaner to reason about than `SELECT FOR UPDATE` on the tail row.
