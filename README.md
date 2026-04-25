# Citadel SDK

**Commercial-grade AI Governance: Constitution + Audit for Agent Builders.**

Citadel is a hardened governance engine that intercepts agent actions, applies multi-tenant policies, requires human-in-the-loop approvals for risky tasks, and logs everything to a tamper-proof PostgreSQL audit chain.

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
- **Decision-First Runtime Governance**: Sensitive actions persist a durable governance decision before any execution proof is issued. Short-lived `gt_cap_` tokens then reference that `decision_id`, so runtime outcomes can be traced back to policy version, approval state, operator context, and audit evidence.
- **Runtime Introspection**: High-risk execution paths can call `/v1/introspect` before the next protected operation. Introspection validates token expiry, revocation, workspace/action/resource scope, and central kill-switch state instead of relying on token expiry alone.
- **Governance Tokens (GT)**: Advanced bypass and delegation system using signed, scoped tokens:
    - `gt_cap_`: Capability delegation for specific resources.
    - `gt_app_`: Pre-authorized approval tokens for automated high-risk tasks.
    - `gt_vlt_`: Secure vault tokens for governed credential access.

## Technical Design Pillars

The Citadel is built on three core architectural philosophies:

1. **Unified Commercial Identity**: We bridge Stripe billing, OAuth identity, and GT tokenization into a single, governed execution context.
2. **The Dual-Write Governance Pipeline**: A deterministic sequence that ensures every proposed action and its final decision are persisted in a tamper-proof, append-only audit chain.
3. **Decision-First Execution Rights**: Runtime authorization starts with an auditable decision record, then issues a narrowly scoped, short-lived `gt_cap_` token as execution proof.
4. **The Hardened Runtime (RLS + OTel + Kill Switch)**: Production-grade security combining PostgreSQL Row-Level Security, OpenTelemetry for full observability, centralized introspection, and Global Kill Switches for emergency intervention.

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

## Quick Start — 5 minutes

### 1. Install the SDK

```bash
pip install citadel-governance
```

### 2. Point it at the hosted API

```python
import citadel

citadel.configure(
    base_url="https://ledger-sdk.fly.dev",
    api_key="dev-key-for-testing",
    actor_id="my-agent",
)
```

### 3. Execute an action under governance

```python
import asyncio

async def main():
    result = await citadel.execute(
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

Open **[casss20-ledger-sdk-6nlu.vercel.app](https://casss20-ledger-sdk-6nlu.vercel.app)** and log in with `admin` / `admin123`.

Every action your agent executes appears in the Activity feed in real time. High-risk actions land in the Approval Queue for human review.

### Use as a decorator

```python
@citadel.guard(action="github.repo_delete", resource="repo:{name}")
async def delete_repo(name: str):
    # Only runs if governance allows it
    await github.repos.delete(name)
```

### Self-hosted setup

```bash
docker compose up -d postgres
pip install -e ".[all]"
uvicorn citadel.api:app --host 0.0.0.0 --port 8000
```

## Hardening & Verification

Citadel is tested against adversarial scenarios:
- **Simulation Scripts**: Run `python tests/simulations/simulate_lockout.py` to verify quota enforcement.
- **Audit Verification**: Call `await client.verify_audit()` to check the cryptographic integrity of the entire governance chain.
- **Race Condition Tests**: Extensive regression suite for concurrent action handling.
- **Capability Introspection Tests**: Runtime tests cover decision-before-token issuance, valid introspection, expired/revoked tokens, scope mismatch, workspace mismatch, kill-switch invalidation, and audit linkage through `decision_id`.

## Documentation

- [Architecture Schema](docs/ARCHITECTURE_SCHEMA.md) - Module dependency graph
- [Kernel Guarantees](docs/KERNEL_GUARANTEES.md) - Invariants and edge cases
- [API Reference](docs/public/api-reference/rest-api.md) - HTTP endpoints and schemas
- [Changelog](CHANGELOG.md) - Release notes for runtime governance changes

## Licensing

Citadel uses a mixed-license model to protect its core while enabling broad adoption:

- **Apache 2.0**: SDKs, public schemas, and integration-facing packages in `packages/`.
- **BSL 1.1 (Source-Available)**: The core self-hostable runtime in `apps/runtime/`.
- **Proprietary**: Enterprise-only and hosted-cloud-only modules in `enterprise/`.

See [`LICENSING.md`](./LICENSING.md) for the full package-by-package breakdown.
