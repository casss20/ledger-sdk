# Ledger SDK

**Commercial-grade AI Governance: Constitution + Audit for Agent Builders.**

Ledger is a hardened governance engine that intercepts agent actions, applies multi-tenant policies, requires human-in-the-loop approvals for risky tasks, and logs everything to a tamper-proof PostgreSQL audit chain.

## Core Capabilities

### 1. Multi-Tenancy & Auth (Cloud Ready)
- **Strict Tenant Isolation**: Enforced via PostgreSQL Row-Level Security (RLS) and application-level filtering.
- **API Key Management**: Secure SHA-256 hashed keys with scoped permissions and automatic `last_used` tracking.
- **JWT Dashboard Auth**: Role-based access for operators and tenant admins.

### 2. Commercial Entitlements & Billing
- **Stripe Integration**: Built-in support for Stripe Checkout and Customer Portal.
- **Quota Enforcement**: Request-time enforcement of API calls, agent counts, and retention limits.
- **Grace Period Logic**: Automated handling of `past_due` subscriptions to maintain access during payment recovery windows.
- **Atomic Usage Tracking**: High-concurrency Postgres counters for precise billing.

### 3. Governance Lifecycle
- **Policy Resolution**: Precedence-based rule matching (`ALLOWED`, `BLOCKED`, `PENDING_APPROVAL`, `RATE_LIMITED`).
- **Tamper-Proof Audit**: Every decision is cryptographically hashed and linked in a PostgreSQL chain.
- **Human-in-the-Loop**: Integrated approval queue for high-risk actions.
- **Capability Tokens**: Scoped, expiring bypass tokens for pre-authorized workflows.

## Directory Structure

The repository is organized into a clean, modular structure for production scaling:

```bash
src/ledger/
├── core/             # Governance Kernel, Repository, Orchestrator, SDK
├── services/         # Approval, Audit, Capability, Policy, Analytics
├── utils/            # Validation, Schema, Precedence, Status
├── billing/          # Stripe Client, Entitlements, Usage tracking
├── api/              # FastAPI Routers, Middleware, Dependencies
└── auth/             # JWT, API Key, and Operator services

tests/
├── unit/             # Core logic and Auth tests
├── integration/      # RLS, Tenant Isolation, and API flows
├── simulations/      # Billing verification (Lockout, Grace Period)
└── regression/       # Concurrency and Race-condition tests

research/             # Archived experimental agent logic and legacy docs
scripts/              # Admin utilities and database seeders
```

## Quick Start

### Installation
```bash
pip install ledger-sdk
```

### Usage
```python
import ledger

# Configure the universal client
client = ledger.LedgerClient(base_url="http://localhost:8000", api_key="your-key")

# Execute an action under governance
result = await client.execute(
    action="file.delete",
    resource="documents/sensitive.pdf",
    actor_id="agent-v1",
)

if result.status == "executed":
    print("Action permitted and logged.")
elif result.status == "pending_approval":
    print("Action is waiting for human review.")
```

## Hardening & Verification

Ledger is tested against adversarial scenarios:
- **Simulation Scripts**: Run `python tests/simulations/simulate_lockout.py` to verify quota enforcement.
- **Audit Verification**: Call `await client.verify_audit()` to check the cryptographic integrity of the entire governance chain.
- **Race Condition Tests**: Extensive regression suite for concurrent action handling.

## Documentation

- [Architecture Schema](docs/ARCHITECTURE_SCHEMA.md) — Module dependency graph
- [Kernel Guarantees](docs/KERNEL_GUARANTEES.md) — Invariants and edge cases
- [API Reference](docs/API.md) — HTTP endpoints and schemas

## License

MIT - See [NOTICES.md](NOTICES.md) for third-party attributions.
