# Project Structure

> **What this doc covers:** What each directory and module does, how they relate to each other, and where the boundaries are. Read this before touching any code.

Citadel is organized as a **mixed-license monorepo** with clear separation between the open-source SDK, the source-available runtime, and proprietary enterprise modules.

---

## 📁 Top-Level Layout

```
citadel-sdk/
├── apps/
│   ├── runtime/          ← Backend governance engine (BSL 1.1)
│   ├── dashboard/        ← React management UI (BSL 1.1)
│   ├── dashboard-demo/   ← Standalone demo dashboard (BSL 1.1)
│   └── landing/          ← Marketing website (BSL 1.1)
├── packages/
│   ├── sdk-python/       ← Python SDK (Apache 2.0)
│   ├── sdk-typescript/   ← TypeScript SDK (planned, Apache 2.0)
│   └── open-spec/        ← Governance schemas & token specs (Apache 2.0)
├── db/
│   ├── schema.sql        ← Canonical database schema
│   └── migrations/       ← Ordered SQL migrations (source of truth)
├── docs/
│   ├── public/           ← Static docs site (HTML + Markdown)
│   └── *.md              ← Internal architecture docs
├── tests/
│   ├── unit/             ← Fast tests, no DB required
│   ├── integration/      ← DB-required integration tests
│   ├── regression/       ← Regression / race condition tests
│   ├── simulations/      ← Long-running scenario scripts
│   ├── security/         ← Security hardening tests
│   ├── tokens/           ← Token system conformance tests
│   └── dashboard/        ← Dashboard component tests
├── scripts/              ← Dev utilities and admin scripts
├── archive/              ← Historical research / experimental code (not maintained)
└── enterprise/           ← Proprietary modules (not open)
```

---

## `apps/runtime/` — The Governance Engine

This is the core backend. It is **source-available (BSL 1.1)**, not fully open source. You can read it, modify it, and self-host it. You cannot offer it as a competing hosted service.

### Module Map

```
apps/runtime/citadel/
├── __init__.py              # Package exports, version
├── config.py                # Pydantic Settings, env var validation
├── core/                    # GOVERNANCE KERNEL — enforcement layer
│   ├── governor.py          # Escalation levels, strategic oversight
│   ├── orchestrator.py        # Orchestration coordination
│   ├── repository.py          # Data access layer
│   ├── router.py            # Action routing logic
│   └── sdk.py               # SDK interface layer
├── execution/               # Action execution layer
│   ├── executor.py          # Executes allowed actions (canonical location)
│   ├── kernel.py            # Execution kernel
│   └── __init__.py
├── executor.py              # Backward-compat shim — re-exports from execution/
├── middleware/              # FastAPI / ASGI middleware
│   ├── auth_middleware.py   # Authentication middleware
│   ├── fastapi_middleware.py  # FastAPI-specific middleware
│   ├── rate_limit.py        # Token bucket rate limiting
│   ├── tenant_context.py    # Tenant context injection (DB RLS)
│   └── tenant_context_logger.py # Tenant-aware logging
├── api/                     # FastAPI application layer
│   ├── __init__.py          # App factory, router registration
│   ├── middleware.py        # CORS, rate limit, request size, security headers
│   └── routers/             # HTTP endpoint handlers
│       ├── actions.py       # Execute governed actions
│       ├── agents.py        # Agent management
│       ├── agent_identity.py # Agent identity / challenge-response
│       ├── approvals.py     # Approval queue management
│       ├── audit.py         # Audit log queries
│       ├── audit_rich.py    # Rich audit analytics
│       ├── connectors.py    # Integration connectors
│       ├── dashboard.py     # Dashboard API endpoints
│       ├── governance.py    # Policy CRUD
│       ├── health.py        # Health checks (live/ready)
│       ├── metrics.py       # Prometheus metrics
│       └── policies_crud.py # Policy CRUD (legacy compat)
├── auth/                    # Authentication & authorization
│   ├── api_key.py           # API key creation/validation
│   ├── jwt_token.py         # JWT token creation/validation
│   ├── operator.py          # Operator management
│   └── middleware.py        # AuthMiddleware (API key + JWT)
├── commercial/              # Provider-agnostic commercial entitlement layer
│   ├── models.py            # Billing data models (provider-agnostic)
│   ├── interface.py         # CommercialRepository port (protocol)
│   ├── entitlement_service.py # Entitlement logic
│   ├── usage_service.py     # Usage tracking
│   ├── events.py            # Commercial event processing
│   ├── middleware.py        # Quota & access enforcement
│   ├── routes.py            # Billing API endpoints
│   └── adapters/
│       └── stripe/          # Stripe adapter (first provider)
│           ├── client.py    # Stripe SDK wrapper
│           ├── repository.py # StripeCommercialRepository
│           ├── translator.py # Stripe events → CommercialEvent
│           └── webhooks.py  # Webhook handler with HMAC verification
├── billing/                 # Backward-compat shim → re-exports from commercial/
├── security/                # OWASP security controls
│   └── owasp_middleware.py  # Security headers, input validation, SSRF protection
├── tokens/                  # Governance Token (GT) system + kill switch
│   ├── token_vault.py       # Secure token storage
│   ├── token_issuer.py      # Token creation (gt_cap_, gt_app_, gt_vlt_)
│   ├── token_verifier.py    # Token introspection & validation
│   ├── decision_engine.py   # Decision-before-token issuance
│   ├── governance_decision.py # Decision types and scopes
│   ├── governance_token.py  # Token data models
│   ├── kill_switch.py       # Emergency stop, fail-closed
│   ├── audit_trail.py       # Governance audit trail (hash-chained)
│   └── execution_middleware.py # Token-aware execution middleware
├── dashboard/               # Dashboard-specific backend logic
│   ├── activity_stream.py
│   ├── approval_queue.py
│   ├── audit_explorer.py
│   ├── coverage_heatmap.py
│   ├── kill_switch_panel.py
│   ├── posture_score.py
│   └── __init__.py
├── services/                # Business logic services
│   ├── analytics.py         # Analytics aggregation
│   ├── approval_service.py  # Approval queue logic
│   ├── audit_service.py     # Audit event logging
│   ├── capability_service.py # Capability token logic
│   └── policy_resolver.py   # Policy resolution engine
├── utils/                   # Shared utilities
│   ├── telemetry.py         # OpenTelemetry setup (optional)
│   ├── error_handling.py    # Error handling utilities
│   ├── validation.py        # Input validation helpers
│   ├── schema.py            # Schema utilities
│   └── (other utilities)
├── integrations/            # Third-party connectors
│   ├── claude_code.py       # Anthropic Claude integration
│   ├── codex.py             # OpenAI Codex integration
│   ├── k2_6.py              # K2-6 integration
│   └── langgraph.py         # LangGraph integration
├── agent_identity/          # Agent identity / trust-score layer
│   ├── auth.py
│   ├── identity.py
│   ├── trust_score.py
│   └── verification.py
├── policy_resolver.py       # Top-level policy resolution (backward-compat)
├── capability_service.py    # Backward-compat shim → services/capability_service
├── approval_service.py      # Backward-compat shim → services/approval_service
├── audit_service.py         # Backward-compat shim → services/audit_service
├── audit_anchoring.py       # Merkle root / cryptographic anchoring
├── repository.py            # Backward-compat shim → core/repository
├── precedence.py            # Precedence rules
├── status.py                # Status management
└── sre/                     # Site reliability / observability
    ├── alerting.py
    ├── health_checks.py
    ├── prometheus_metrics.py
    ├── slos.py
    └── structured_logging.py
```

### Public API vs Internal Implementation

**Public API** (stable, documented, versioned):
- Everything in `packages/sdk-python/citadel_governance/` — the SDK
- FastAPI routes in `api/routers/` — the HTTP API
- Database schema in `db/schema.sql`

**Internal Implementation** (may change without notice):
- Everything in `core/`, `tokens/`, `services/` — these are implementation details
- Internal utilities in `utils/`
- Test helpers in `tests/conftest.py`

**Rule:** If you're building an integration, use the SDK or the HTTP API. Don't import from `citadel.core` or `citadel.tokens` directly.

### Commercial (Billing) Layer

Citadel's commercial layer is **provider-agnostic** with Stripe as the first concrete adapter.

```
citadel/commercial/
├── models.py            # Provider-agnostic data models
├── interface.py         # CommercialRepository port (Protocol)
├── entitlement_service.py  # Resolves tenant entitlements
├── usage_service.py     # Tracks and enforces usage quotas
├── events.py            # Provider-agnostic event processing
├── middleware.py        # Quota & access enforcement
├── routes.py            # Billing API endpoints
└── adapters/
    └── stripe/
        ├── client.py    # Stripe SDK wrapper
        ├── repository.py # StripeCommercialRepository (adapter)
        ├── translator.py # Stripe events → CommercialEvent
        └── webhooks.py  # Stripe webhook handler
```

**Core commercial logic** (`models`, `interface`, `entitlement_service`, `usage_service`, `events`) is 100% provider-agnostic. It depends only on the `CommercialRepository` port, never on Stripe SDK types.

**Stripe adapter** (`adapters/stripe/`) is the only place Stripe-specific code lives. It translates Stripe webhook events into provider-agnostic `CommercialEvent` objects before core processing.

**Backward compatibility:** `citadel/billing/` is a thin shim that re-exports from `citadel/commercial/`. Existing imports continue to work. New code should import from `citadel.commercial`.

**Why this structure:**
- Core identity/governance code depends only on `CommercialRepository` (the port), never on Stripe.
- Future providers (Paddle, Chargebee, custom billing) add a new `adapters/<provider>/` package that implements the same port.
- Tests for core commercial logic run against a `FakeCommercialRepository` — no Stripe SDK needed.
- Tests for Stripe adapter verify event translation and signature verification independently.
- Policy code sees only provider-agnostic commercial facts (`TenantEntitlements`, `UsageSnapshot`).

---

## `apps/dashboard/` — React Management UI

A Vite + React + Tailwind CSS dashboard for operators.

```
apps/dashboard/
├── src/
│   ├── api/
│   │   └── client.ts         # Axios/fetch wrapper with auth
│   ├── components/
│   │   ├── ui/               # Reusable UI primitives (Button, Card, Badge)
│   │   ├── approval-queue.tsx
│   │   ├── audit-log.tsx
│   │   ├── kill-switches.tsx
│   │   └── stats-grid.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Approvals.tsx
│   │   ├── Audit.tsx
│   │   └── Login.tsx
│   ├── lib/
│   │   └── utils.ts          # cn() helper for Tailwind
│   └── App.tsx
├── package.json
├── vite.config.ts            # Dev proxy to localhost:8000
└── tsconfig.json
```

The dashboard talks to the backend via the same HTTP API that external SDKs use. It is not a special admin interface — it consumes the public API with JWT authentication.

---

## `packages/sdk-python/` — Python SDK

The **public integration surface** for Python agents. Apache 2.0 licensed.

```
packages/sdk-python/
├── citadel_governance/       # Main package (import this)
│   ├── __init__.py           # Public API exports
│   ├── client.py             # CitadelClient (async + sync)
│   ├── guard.py              # @guard decorator
│   ├── exceptions.py         # Custom exception classes
│   └── __version__.py        # Version string
├── tests/
│   ├── test_sdk.py           # 43+ unit tests
│   └── integration/
│       └── conftest.py       # Integration test fixtures
├── pyproject.toml
└── README.md
```

**Public API:**
```python
import citadel_governance as cg

cg.configure(base_url="...", api_key="...", actor_id="...")
cg.execute(action="...", resource="...", payload={...})
cg.guard(action="...", resource="...")  # decorator
```

**Important:** The SDK is the only supported way to integrate with Citadel from Python. Do not import the backend runtime as a library.

---

## `db/` — Database

```
db/
├── schema.sql                # Canonical schema (source of truth)
├── migrations/               # Ordered SQL migrations (source of truth)
│   ├── 001_tenant_isolation.sql
│   ├── 002_api_keys.sql
│   └── ...
└── 00-init-test-db.sql       # Local dev helper (not used in CI or production)
```

**Rules:**
- `schema.sql` is the canonical schema. It must always represent the current state.
- `db/migrations/*.sql` are the source of truth for schema changes. The runtime applies them automatically on startup via `_run_migrations()`.
- Migrations are additive. Never modify an already-deployed migration.
- All tables must have RLS policies for tenant isolation.
- New migrations must be idempotent (`CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ADD COLUMN IF NOT EXISTS`, etc.).

---

## `tests/` — Test Suite

Organized by speed and dependency requirements:

| Directory | Speed | Needs DB? | Purpose |
|---|---|---|---|
| `tests/unit/` | Fast (< 1s each) | No | Isolated logic tests |
| `tests/tokens/` | Medium (< 5s each) | No | Token system conformance |
| `tests/security/` | Medium | No | Security hardening verification |
| `tests/integration/` | Slow | Yes | DB integration, middleware |
| `tests/regression/` | Slow | Yes | Race conditions, stress tests |
| `tests/simulations/` | Very slow | Yes | End-to-end scenario scripts |
| `tests/dashboard/` | Medium | No | Dashboard component tests |

**Key test files:**
- `tests/security/test_security_hardening.py` — CORS, rate limiting, body size, Stripe HMAC
- `tests/security/test_abuse_cases.py` — Prompt injection blocking, kill-switch bypass, TOCTOU
- `tests/tokens/test_runtime_introspection.py` — Token revocation, expiry, scope checks
- `tests/integration/test_rls_enforcement.py` — Row-level security isolation
- `tests/test_audit_anchoring.py` — Merkle root signing, cryptographic integrity

---

## `docs/` — Documentation

```
docs/
├── public/                   # Static docs site (deployed to Vercel)
│   ├── index.html            # Single-page docs app
│   ├── api-reference/        # REST API docs
│   ├── recipes/              # How-to guides
│   ├── guides/               # Tutorials
│   ├── getting-started/      # Onboarding docs
│   └── core-concepts/        # Architecture explainers
├── ARCHITECTURE.md           # Full architecture deep-dive
├── ARCHITECTURE_SCHEMA.md    # Module dependency graph
├── KERNEL_GUARANTEES.md      # Invariants and edge cases
├── SECURITY.md               # Tenant isolation & RLS
├── ROADMAP.md                # Future plans
└── FORGE_ROADMAP.md          # Forge / plugin system plans
```

The `docs/public/` site is a handcrafted HTML + Markdown site (not generated from a static site builder). It is deployed via Vercel on every push to `master`.

---

## `scripts/` — Development Utilities

```
scripts/
├── setup_dev.sh              # One-command dev environment setup
├── run_tests.sh              # Run all test tiers
└── db/                       # Database helpers
    ├── reset_test_db.sh
    └── migrate.sh
```

---

## `archive/` — Historical Code

```
archive/
├── research/                 # Early experiments and prototypes
└── experimental/             # Duplicate governance implementations
```

**Important:** Code in `archive/` is not maintained. It exists for historical reference only. Do not import from it.

---

## `enterprise/` — Proprietary

```
enterprise/
└── (proprietary modules)
```

Not open for contribution. See [LICENSING.md](LICENSING.md).

---

## Dependency Rules

These rules keep the codebase maintainable:

### ✅ Allowed Dependencies

```
sdk-python ──HTTP──► runtime API
dashboard ──HTTP──► runtime API
runtime/api ──imports──► runtime/core, runtime/services, runtime/tokens
runtime/core ──imports──► runtime/services (for enforcement)
runtime/services ──imports──► runtime/core (for primitives)
runtime/utils ──imports──► nothing internal (leaf utilities)
```

### ❌ Forbidden Dependencies

```
sdk-python ──X──► runtime/internal (use HTTP API only)
dashboard ──X──► runtime/internal (use HTTP API only)
runtime/api ──X──► enterprise/ (proprietary)
tests ──X──► archive/ (stale code)
```

### Circular Dependency Rule

If `A` imports from `B`, `B` must not import from `A`. Use dependency inversion (interfaces, protocols) or move shared code to `utils/`.

---

## Public API Surface

These are the **stable, versioned** interfaces. Changes here require a deprecation period or major version bump:

| Surface | Location | Stability |
|---|---|---|
| Python SDK | `packages/sdk-python/citadel_governance/` | Stable (semver) |
| HTTP REST API | `apps/runtime/citadel/api/routers/` | Stable (documented) |
| Database Schema | `db/schema.sql` | Stable (migrations) |
| Governance Token Spec | `packages/open-spec/` | Stable (versioned) |

Everything else is internal implementation detail and may change without notice.

---

## Adding a New Module

If you need to add a new top-level module to `apps/runtime/citadel/`:

1. **Ask first** — Open a discussion or issue explaining the need
2. **Follow the three-layer model** — Is it Kernel (`core/`), Service (`services/`), or Token (`tokens/`)?
3. **Add tests** — Every module needs tests in the appropriate `tests/` directory
4. **Add docs** — Update `docs/ARCHITECTURE.md` and `docs/public/` if user-facing
5. **Register in `__init__.py`** — If it exposes a public API

---

## Quick Reference: Where to Find Things

| I want to... | Look in... |
|---|---|
| Add a new HTTP endpoint | `apps/runtime/citadel/api/routers/` |
| Change policy evaluation logic | `apps/runtime/citadel/core/governor.py` |
| Change action execution | `apps/runtime/citadel/execution/executor.py` |
| Add a new token type | `apps/runtime/citadel/tokens/` + `packages/open-spec/` |
| Change the database schema | `db/schema.sql` + `db/migrations/` |
| Add an SDK method | `packages/sdk-python/citadel_governance/` |
| Add a dashboard component | `apps/dashboard/src/components/` |
| Fix a security issue | `apps/runtime/citadel/security/` + `tests/security/` |
| Add a how-to guide | `docs/public/recipes/` |
| Add a simulation | `tests/simulations/` |
