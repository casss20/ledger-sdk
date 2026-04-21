# LEDGER JOURNAL

## Entry 10: Cloud Tier — Tenant Isolation

### Context
The master prompt established that Option A (Ledger Runtime) is the core product, with Assessment as an add-on and Option B as future evolution. After completing the hardening pass (Issues 1, 2, 2.5, 3) with all 28 kernel tests passing, the next phase is packaging the hardened kernel as a Cloud tier. Stream 1 is the foundation: without strict tenant isolation, multi-tenant subscription billing is impossible.

### Strategic Advice Received
From the master prompt: the Ledger Runtime is the core product. A mid-market team subscribing at $299–$2K/month must have their data strictly isolated from other tenants. The definition of done for this phase is a developer signing up, getting an API key, and having their first governed action logged in the Cloud dashboard within 10 minutes. Tenant isolation is prerequisite to everything else in the Cloud tier.

### Decision Made
Implemented defense-in-depth tenant isolation using both application-level filtering AND PostgreSQL Row-Level Security (RLS):

1. **Schema migration** (`db/migrations/001_tenant_isolation.sql`): Added `tenant_id` to `capabilities`, `decisions`, `approvals`, and `execution_results` (already present on `actors`, `policies`, `kill_switches`, `actions`, `audit_events`). Created indexes on all new columns. Enabled RLS with `FORCE ROW LEVEL SECURITY` on all core tables. Created `set_tenant_context()` and `get_tenant_context()` helper functions. RLS policies allow NULL tenant context as admin bypass.

2. **Repository enforcement** (`src/ledger/repository.py`): Every read method (`get_action`, `get_decision`, `get_approval`, `get_capability`, `get_pending_approvals`, `find_decision_by_idempotency`) now accepts `tenant_id: Optional[str] = None` and adds explicit `WHERE tenant_id = $N` or JOIN-based tenant filtering. Every write method (`save_decision`, `create_approval`, `save_execution_result`) now includes `tenant_id`.

3. **Kernel propagation** (`src/ledger/execution/kernel.py`): `action.tenant_id` is propagated to all downstream records — decisions, approvals, execution results, audit events, and idempotency lookups.

4. **Service updates** (`src/ledger/approval_service.py`, `src/ledger/capability_service.py`): Both services now pass `tenant_id` through to repository calls.

5. **Decision model** (`src/ledger/actions/models.py`): Added `tenant_id: Optional[str] = None` to the `Decision` dataclass so it can be persisted with the correct tenant.

### Reasoning
- **Why RLS + application filtering?** Application-level filtering is testable, debuggable, and portable. RLS is defense-in-depth: even if a future developer forgets a WHERE clause, PostgreSQL blocks cross-tenant access. `FORCE ROW LEVEL SECURITY` ensures the table owner (the application DB user) is also subject to RLS, eliminating the superuser bypass risk.
- **Why denormalize tenant_id on child tables?** Decisions, approvals, and execution_results all reference actions which already have tenant_id. Denormalizing avoids JOIN overhead for the most common queries (dashboard listings, approval queues) and makes RLS policies simple and fast.
- **Why NULL tenant_id = admin bypass?** Some internal operations (schema migrations, analytics) may need to see all tenants. The RLS policy `tenant_id = get_tenant_context() OR get_tenant_context() IS NULL` allows this while still enforcing isolation when a tenant context is set.
- **Why not add tenant_id to policy_snapshots?** Policy snapshots reference policies which have tenant_id. Snapshots are immutable and queried by ID, not listed by tenant. The JOIN path through policies is sufficient.

### Files Changed
- `db/migrations/001_tenant_isolation.sql` — new migration
- `src/ledger/repository.py` — tenant filtering on all reads, tenant propagation on all writes
- `src/ledger/execution/kernel.py` — action.tenant_id propagated downstream
- `src/ledger/approval_service.py` — tenant_id passed to approval creation and queue queries
- `src/ledger/capability_service.py` — tenant_id passed to capability lookups
- `src/ledger/actions/models.py` — tenant_id added to Decision dataclass
- `tests/test_tenant_isolation.py` — 7 regression tests for cross-tenant access

### Tests
- `test_cross_tenant_action_read_blocked` — proves get_action with wrong tenant_id returns None
- `test_cross_tenant_decision_read_blocked` — proves get_decision with wrong tenant_id returns None
- `test_cross_tenant_approval_read_blocked` — proves get_approval with wrong tenant_id returns None
- `test_cross_tenant_capability_read_blocked` — proves get_capability with wrong tenant_id returns None
- `test_cross_tenant_kill_switch_blocked` — verifies kill_switch filtering by tenant
- `test_cross_tenant_policy_blocked` — verifies policy resolution scoped to tenant
- `test_kernel_action_carries_tenant` — end-to-end: action submitted with tenant_id has tenant_id in all downstream records (action, decision, audit)

### Invariants
- All 28 pre-existing kernel tests still pass ✅
- Canonical Action interface unchanged ✅
- KernelResult interface unchanged ✅
- No experimental/ imports in src/ledger/ ✅
- Tenant isolation holds ✅
