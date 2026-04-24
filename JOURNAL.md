# CITADEL JOURNAL

## Entry 10: Cloud Tier â€” Tenant Isolation

### Context
The master prompt established that Option A (CITADEL Runtime) is the core product, with Assessment as an add-on and Option B as future evolution. After completing the hardening pass (Issues 1, 2, 2.5, 3) with all 28 kernel tests passing, the next phase is packaging the hardened kernel as a Cloud tier. Stream 1 is the foundation: without strict tenant isolation, multi-tenant subscription billing is impossible.

### Strategic Advice Received
From the master prompt: the CITADEL Runtime is the core product. A mid-market team subscribing at $299â€“$2K/month must have their data strictly isolated from other tenants. The definition of done for this phase is a developer signing up, getting an API key, and having their first governed action logged in the Cloud dashboard within 10 minutes. Tenant isolation is prerequisite to everything else in the Cloud tier.

### Decision Made
Implemented defense-in-depth tenant isolation using both application-level filtering AND PostgreSQL Row-Level Security (RLS):

1. **Schema migration** (`db/migrations/001_tenant_isolation.sql`): Added `tenant_id` to `capabilities`, `decisions`, `approvals`, and `execution_results` (already present on `actors`, `policies`, `kill_switches`, `actions`, `audit_events`). Created indexes on all new columns. Enabled RLS with `FORCE ROW LEVEL SECURITY` on all core tables. Created `set_tenant_context()` and `get_tenant_context()` helper functions. RLS policies allow NULL tenant context as admin bypass.

2. **Repository enforcement** (`src/CITADEL/repository.py`): Every read method (`get_action`, `get_decision`, `get_approval`, `get_capability`, `get_pending_approvals`, `find_decision_by_idempotency`) now accepts `tenant_id: Optional[str] = None` and adds explicit `WHERE tenant_id = $N` or JOIN-based tenant filtering. Every write method (`save_decision`, `create_approval`, `save_execution_result`) now includes `tenant_id`.

3. **Kernel propagation** (`src/CITADEL/execution/kernel.py`): `action.tenant_id` is propagated to all downstream records â€” decisions, approvals, execution results, audit events, and idempotency lookups.

4. **Service updates** (`src/CITADEL/approval_service.py`, `src/CITADEL/capability_service.py`): Both services now pass `tenant_id` through to repository calls.

5. **Decision model** (`src/CITADEL/actions/models.py`): Added `tenant_id: Optional[str] = None` to the `Decision` dataclass so it can be persisted with the correct tenant.

### Reasoning
- **Why RLS + application filtering?** Application-level filtering is testable, debuggable, and portable. RLS is defense-in-depth: even if a future developer forgets a WHERE clause, PostgreSQL blocks cross-tenant access. `FORCE ROW LEVEL SECURITY` ensures the table owner (the application DB user) is also subject to RLS, eliminating the superuser bypass risk.
- **Why denormalize tenant_id on child tables?** Decisions, approvals, and execution_results all reference actions which already have tenant_id. Denormalizing avoids JOIN overhead for the most common queries (dashboard listings, approval queues) and makes RLS policies simple and fast.
- **Why NULL tenant_id = admin bypass?** Some internal operations (schema migrations, analytics) may need to see all tenants. The RLS policy `tenant_id = get_tenant_context() OR get_tenant_context() IS NULL` allows this while still enforcing isolation when a tenant context is set.
- **Why not add tenant_id to policy_snapshots?** Policy snapshots reference policies which have tenant_id. Snapshots are immutable and queried by ID, not listed by tenant. The JOIN path through policies is sufficient.

### Files Changed
- `db/migrations/001_tenant_isolation.sql` â€” new migration
- `src/CITADEL/repository.py` â€” tenant filtering on all reads, tenant propagation on all writes
- `src/CITADEL/execution/kernel.py` â€” action.tenant_id propagated downstream
- `src/CITADEL/approval_service.py` â€” tenant_id passed to approval creation and queue queries
- `src/CITADEL/capability_service.py` â€” tenant_id passed to capability lookups
- `src/CITADEL/actions/models.py` â€” tenant_id added to Decision dataclass
- `tests/test_tenant_isolation.py` â€” 7 regression tests for cross-tenant access

### Tests
- `test_cross_tenant_action_read_blocked` â€” proves get_action with wrong tenant_id returns None
- `test_cross_tenant_decision_read_blocked` â€” proves get_decision with wrong tenant_id returns None
- `test_cross_tenant_approval_read_blocked` â€” proves get_approval with wrong tenant_id returns None
- `test_cross_tenant_capability_read_blocked` â€” proves get_capability with wrong tenant_id returns None
- `test_cross_tenant_kill_switch_blocked` â€” verifies kill_switch filtering by tenant
- `test_cross_tenant_policy_blocked` â€” verifies policy resolution scoped to tenant
- `test_kernel_action_carries_tenant` â€” end-to-end: action submitted with tenant_id has tenant_id in all downstream records (action, decision, audit)

### Invariants
- All 28 pre-existing kernel tests still pass âœ…
- Canonical Action interface unchanged âœ…
- KernelResult interface unchanged âœ…
- No experimental/ imports in src/CITADEL/ âœ…
- Tenant isolation holds âœ…


## Entry 11: Stream 2 Closed â€” Complete RLS Hardening + API Key Provisioning

### Context
Stream 2: API Key Provisioning and Cloud Tier Auth. Scope expanded mid-stream to enforce strict RLS across ALL tables (core + api_keys), not just new tables. Strategic advice: governance across the entire system means no NULL-as-admin-bypass fallback.

### Decision Made
Path B: Rewrite 001_tenant_isolation.sql with strict RLS on core tables. Write 002_api_keys.sql with strict RLS from the start. Update all tests to use tenant_id fixtures. Establish strict RLS as the enforced standard.

### Changes

**RLS Policy Rewrite (`001_tenant_isolation.sql`)**
- Removed `get_tenant_context() IS NULL` bypass from ALL policies
- New policy: `USING (tenant_id = get_tenant_context() OR admin_bypass_rls())`
- `admin_bypass_rls()` checks `current_setting('app.admin_bypass', TRUE) = 'true'`
- `set_tenant_context()` uses session-level `set_config(..., FALSE)` (not transaction-local) to survive asyncpg autocommit
- `FORCE ROW LEVEL SECURITY` enabled on all tables

**API Keys Migration (`002_api_keys.sql`)**
- New table: `api_keys` with `key_id`, `tenant_id`, `key_hash`, `name`, `scopes`, `expires_at`, `last_used_at`, `revoked`, `created_at`
- Strict RLS from creation â€” no NULL bypass

**Repository (`src/CITADEL/repository.py`)**
- Added `create_api_key()`, `get_api_key_by_hash()`, `list_api_keys()`, `revoke_api_key()`, `update_api_key_last_used()`
- Keys hashed with SHA-256 for storage

**Test Fixtures (`tests/conftest.py`)**
- `tenant_id` fixture: random `test_tenant_{uuid4 hex}` per test
- `clean_database` fixture (autouse=True): TRUNCATE all tables with `SET app.admin_bypass = 'true'`
- `db` fixture: direct connection with `set_tenant_context()` called
- `kernel` fixture: pool with `setup=setup_tenant` callback (runs on every `acquire()`, ensuring context survives pool return/reset)

**Test Updates**
- `test_kernel_conformance.py` â€” 10 tests updated with `tenant_id` param, all INSERTs include `tenant_id`, all `Action` constructors pass `tenant_id=tenant_id`
- `test_audit_chain_race_regression.py` â€” 3 tests updated
- `test_capability_race_regression.py` â€” 4 tests updated
- `test_idempotency_race_regression.py` â€” 3 tests updated
- `test_kernel_concurrency.py` â€” 5 tests updated
- `test_tenant_isolation.py` â€” 7 tests updated, cross-tenant setup uses admin bypass, assertions use tenant-scoped pools
- `test_api_keys.py` â€” 7 new tests: create, cross-tenant isolation, revocation, expiration, last_used tracking, name optional, list pagination
- `e2e_api_sdk.py` â€” updated to set tenant context

### Invariants
- 42 tests passing under strict RLS âœ…
- No NULL-as-admin-bypass pattern anywhere âœ…
- Admin operations explicitly authorized via `app.admin_bypass` âœ…
- Tenant context required on every test âœ…
- Canonical Action and KernelResult interfaces unchanged âœ…
- No experimental/ imports in src/CITADEL/ âœ…

### Commits
- `ec8fe58` â€” test: update all tests for strict RLS
- `2eeeeef` â€” fix: strict RLS on all tables + API key repository

### Risk Notes
- Admin bypass via `app.admin_bypass` is explicit but powerful â€” monitor for misuse
- Tenant context must be set on EVERY database connection â€” middleware must be airtight
- Future migrations must use admin bypass fixture if they touch tenant data

### Recommendation
PROCEED to Stream 3 (Onboarding Flow)

## Entry 12: Commercial Hardening & Repository Refactor

### Context
After establishing tenant isolation and auth, the focus shifted to **Monetization Readiness** and **Structural Refinement**. The system needed to handle Stripe-backed billing with robust entitlement enforcement, and the repository had reached a state of "structural debt" that required architectural arrangement for production scaling.

### Decision Made
Implemented a production-grade billing control plane and refactored the entire project structure for clarity:

1.  **Stripe-Backed Billing Engine**:
    *   Implemented `008_billing.sql` with tables for customers, plans, subscriptions, and usage.
    *   Created `BillingMiddleware` for request-time quota and payment enforcement.
    *   Added `Billing.tsx` and `useBilling.ts` to the dashboard for user self-service.
    *   Ensured **Middleware Order** is strictly `AuthMiddleware` -> `TenantContextMiddleware` -> `BillingMiddleware`.

2.  **Entitlement Hardening**:
    *   Developed a "Grace Period" logic allowing access during `past_due` status windows.
    *   Implemented atomic SQL usage increments to prevent race conditions during high-traffic billing periods.
    *   Verified Webhook Signature handling with raw request bodies for security.

3.  **Repository Arrangement**:
    *   Cleaned the root directory by moving all seeders and utilities to `scripts/`.
    *   Refactored `src/CITADEL` into logical sub-packages: `core/`, `services/`, `utils/`, and `billing/`.
    *   Tiered the test suite into `unit/`, `integration/`, `simulations/`, and `regression/`.

4.  **Verification Simulations**:
    *   Shipped `tests/simulations/` containing `lockout`, `downgrade`, and `grace_period` scripts to verify the commercial engine without live Stripe calls.

### Reasoning
- **Why refactor now?** The "flat" package structure in `src/CITADEL` was causing cognitive overhead. Organizing into `core/` and `services/` mirrors domain-driven design and makes the kernel easier to maintain as it moves toward the Cloud Tier.
- **Why simulation scripts?** Billing bugs are high-severity. Testing "Subscription Deleted" or "Card Failed" in production is dangerous. Simulations allow verifying the "Lockout" logic (402/429) safely and repeatedly.
- **Why atomic usage?** `ON CONFLICT DO UPDATE` in Postgres ensures that even under heavy parallel load, quota increments remain accurate and non-blocking.

### Files Changed
- `src/CITADEL/billing/*` â€” new billing and entitlement services
- `src/CITADEL/api/__init__.py` â€” core API integration and middleware ordering
- `src/CITADEL/__init__.py` â€” updated for sub-package stability
- `tests/simulations/*` â€” verification suite
- `scripts/*` â€” root utility consolidation
- `db/migrations/008_billing.sql` â€” billing schema

### Invariants
- 429 Quota Lockout: **VERIFIED** âœ…
- 402 Payment Grace Period: **VERIFIED** âœ…
- Webhook Signature Security: **HARDENED** âœ…
- Backend Package Structure: **CLEANED** âœ…
- API Stability maintained via `__init__.py` mapping âœ…

### Recommendation
PROCEED to Onboarding Flow and Production Deployment.
