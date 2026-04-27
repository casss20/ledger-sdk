# Citadel SDK

**Commercial-grade AI Governance: Constitution + Audit for Agent Builders.**

Citadel is a hardened governance engine that intercepts agent actions, applies multi-tenant policies, requires human-in-the-loop approvals for risky tasks, and logs everything to a tamper-proof PostgreSQL audit chain.

## Core Capabilities

### 1. Trust-Aware Governance
- **Five Trust Bands**: Deterministic scoring (0.00-1.00) maps to REVOKED, PROBATION, STANDARD, TRUSTED, HIGHLY_TRUSTED. Trust influences policy without replacing it.
- **Deterministic Score Computation**: 9 weighted behavioral factors (verification, health, compliance, action rate, etc.) computed at decision time.
- **Probation & Circuit Breakers**: New agents start in PROBATION. Circuit breaker stages REVOKED when scores drop below 0.15.
- **Operator Override**: Manual band adjustment with dual approval, auditable reason, and time-bounded expiration.
- **Trust-Aware Decisions**: Every governance decision stores `trust_snapshot_id` for deterministic replay and audit.

### 2. Multi-Tenancy & Auth (Cloud Ready)
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
- **Decision-First Runtime Governance**: Sensitive actions persist a durable governance decision before any execution proof is issued. Short-lived `gt_cap_` tokens then reference that `decision_id`, so runtime outcomes can be traced back to policy version, approval state, operator context, and audit evidence.
- **Runtime Introspection**: High-risk execution paths can call `/v1/introspect` before the next protected operation. Introspection validates token expiry, revocation, workspace/action/resource scope, and central kill-switch state instead of relying on token expiry alone.
- **Governance Tokens (GT)**: Advanced bypass and delegation system using signed, scoped tokens:
    - `gt_cap_`: Capability delegation for specific resources.
    - `gt_app_`: Pre-authorized approval tokens for automated high-risk tasks.
    - `gt_vlt_`: Secure vault tokens for governed credential access.

## Technical Design Pillars

The Citadel is built on five core architectural philosophies:

1. **Unified Commercial Identity**: We bridge Stripe billing, OAuth identity, and GT tokenization into a single, governed execution context.
2. **The Dual-Write Governance Pipeline**: A deterministic sequence that ensures every proposed action and its final decision are persisted in a tamper-proof, append-only audit chain.
3. **Decision-First Execution Rights**: Runtime authorization starts with an auditable decision record, then issues a narrowly scoped, short-lived `gt_cap_` token as execution proof.
4. **The Hardened Runtime (RLS + OTel + Kill Switch)**: Production-grade security combining PostgreSQL Row-Level Security, OpenTelemetry for full observability, centralized introspection, and Global Kill Switches for emergency intervention.
5. **Trust-Aware Enforcement**: Deterministic trust scoring (9 weighted factors, 5 bands) enriches policy context without replacing policy authority. Trust adds constraints (approval, quotas, action blocks) but never removes them.

## 📁 Repository Structure

Citadel is organized as a **mixed-license monorepo** to separate the open ecosystem from the core runtime:

- **`apps/runtime/`**: The core governance engine and control plane (**BSL 1.1**).
- **`apps/dashboard/`**: The React-based management interface.
- **`packages/sdk-python/`**: Public Python SDK for agent integration (**Apache 2.0**).
- **`packages/open-spec/`**: Governance schemas and token specifications (**Apache 2.0**).
- **`docs/`**: Technical documentation and public documentation site.
- **`enterprise/`**: Proprietary modules and premium policy packs.
- **`tests/`**: Tiered test suite (unit, simulation, hardening).
- **`scripts/`**: Development and administrative utilities.

## 📦 Packages

Citadel publishes two distinct Python packages:

| Package | Install | Purpose | License |
|---|---|---|---|
| **citadel-governance** | `pip install citadel-governance` | Client SDK for agent integration | **Apache 2.0** |
| **citadel-runtime** | `pip install -e ".[all]"` (from repo) | Self-hosted governance backend | **BSL 1.1** |

> **Note:** The backend runtime (`citadel-runtime`) is not published to PyPI. It is meant to be deployed as a service (Docker, Fly.io, etc.). The SDK (`citadel-governance`) is the only PyPI package for agent integration.

### 1. Install the SDK

```bash
pip install citadel-governance
```

### 2. Point it at the hosted API

```python
import citadel_governance as cg

# Get your API key from https://dashboard.citadelsdk.com/settings
cg.configure(
    base_url="https://api.citadelsdk.com",
    api_key="YOUR_API_KEY_HERE",
    actor_id="my-agent",
)
```

### 3. Execute an action under governance

```python
import asyncio

async def main():
    result = await cg.execute(
        action="stripe.refund",
        resource="charge:ch_123",
        payload={"amount": 5000},
    )

    if result.status == "executed":
        print("Permitted and logged.")
    elif result.status == "pending_approval":
        print("Queued for human review.")
    else:
        print(f"Blocked: {result.reason}")

asyncio.run(main())
```

### 4. Watch it in the dashboard

Open **[dashboard.citadelsdk.com](https://dashboard.citadelsdk.com)** and log in with your credentials.

Every action your agent executes appears in the Activity feed in real time. High-risk actions land in the Approval Queue for human review.

> **Demo Environment**: For a quick walkthrough without credentials, try the **[live demo](https://dashboard.citadelsdk.com/demo)** with pre-loaded sample data.

### Use as a decorator

```python
@cg.guard(action="github.repo_delete", resource="repo:{name}")
async def delete_repo(name: str):
    # Only runs if governance allows it
    await github.repos.delete(name)
```

### Self-hosted setup (Quick Dev)

Run PostgreSQL in Docker, then start the API locally:

```bash
# 1. Start PostgreSQL
docker compose up -d postgres

# 2. Copy and edit environment variables
cp .env.example .env
# Edit .env — set CITADEL_JWT_SECRET and CITADEL_API_KEYS

# 3. Install backend locally
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"

# 4. Start the backend
uvicorn citadel.api:app --reload --host 0.0.0.0 --port 8000
```

### Self-hosted setup (Full Docker)

Run everything in containers:

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env — set CITADEL_JWT_SECRET, CITADEL_API_KEYS, and CITADEL_ADMIN_BOOTSTRAP_PASSWORD

# 2. Start the full stack
docker compose up --build -d

# 3. Verify readiness
curl http://localhost:8000/v1/health/ready
```

### Optional: Redis for distributed features

Redis is **optional** for single-node deployments. Without Redis, the system falls back to in-memory implementations:

| Feature | Without Redis | With Redis |
|---|---|---|
| Rate limiting | In-memory token bucket (single-instance only) | Distributed token bucket across all instances |
| Kill switch | In-memory storage | Distributed state (planned) |
| Caching | In-memory dict (per-process) | Shared cache across instances |

To enable Redis, uncomment the `redis` service in `docker-compose.yml` and set `CITADEL_REDIS_URL=redis://redis:6379/0` in `.env`.

## Hardening & Verification

Citadel is tested against adversarial scenarios:
- **Simulation Scripts**: Run `python tests/simulations/simulate_lockout.py` to verify quota enforcement.
- **Audit Verification**: Call `await client.verify_audit()` to check the cryptographic integrity of the entire governance chain.
- **Race Condition Tests**: Extensive regression suite for concurrent action handling.
- **Capability Introspection Tests**: Runtime tests cover decision-before-token issuance, valid introspection, expired/revoked tokens, scope mismatch, workspace mismatch, kill-switch invalidation, and audit linkage through `decision_id`.

## Documentation

- **[Contributing](CONTRIBUTING.md)** — How to get started, coding standards, and PR workflow
- **[Development Guide](docs/DEVELOPMENT.md)** — Local dev setup, commands, and CI
- **[Project Structure](docs/PROJECT_STRUCTURE.md)** — Architecture and module map
- **[Maintainer Guide](docs/MAINTAINER_GUIDE.md)** — Review, release, and quality processes
- **[Architecture Deep-Dive](docs/ARCHITECTURE.md)** — The three-layer design
- **[Architecture Schema](docs/ARCHITECTURE_SCHEMA.md)** — Module dependency graph
- **[Kernel Guarantees](docs/KERNEL_GUARANTEES.md)** — Invariants and edge cases
- **[API Reference](docs/public/api-reference/rest-api.md)** — HTTP endpoints and schemas
- **[Changelog](CHANGELOG.md)** — Release notes

## Contributing

We welcome contributions! Whether you're fixing a typo, adding a test, or building a feature, here's how to start:

1. Read **[CONTRIBUTING.md](CONTRIBUTING.md)** — your guide to the codebase
2. Check **[good first issues](https://github.com/casss20/citadel-sdk/labels/good%20first%20issue)** — safe starting points
3. Join our **[Discord](https://discord.gg/clawd)** — ask questions, get help

See also:
- [Development Guide](docs/DEVELOPMENT.md) — day-to-day workflow
- [Project Structure](docs/PROJECT_STRUCTURE.md) — what each module does
- [Maintainer Guide](docs/MAINTAINER_GUIDE.md) — how we review and release

## Licensing

Citadel uses a mixed-license model to protect its core while enabling broad adoption:

- **Apache 2.0**: SDKs, public schemas, and integration-facing packages in `packages/`.
- **BSL 1.1 (Source-Available)**: The core self-hostable runtime in `apps/runtime/`.
- **Proprietary**: Enterprise-only and hosted-cloud-only modules in `enterprise/`.

See [`LICENSING.md`](./LICENSING.md) for the full package-by-package breakdown.
