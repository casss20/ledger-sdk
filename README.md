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
- **Governance Tokens (GT)**: Advanced bypass and delegation system using signed, scoped tokens:
    - `gt_cap_`: Capability delegation for specific resources.
    - `gt_app_`: Pre-authorized approval tokens for automated high-risk tasks.
    - `gt_vlt_`: Secure vault tokens for governed credential access.

## Technical Design Pillars

The Citadel is built on three core architectural philosophies:

1. **Unified Commercial Identity**: We bridge Stripe billing, OAuth identity, and GT tokenization into a single, governed execution context.
2. **The Dual-Write Governance Pipeline**: A deterministic sequence that ensures every proposed action and its final decision are persisted in a tamper-proof, append-only audit chain.
3. **The Hardened Runtime (RLS + OTel + Kill Switch)**: Production-grade security combining PostgreSQL Row-Level Security, OpenTelemetry for full observability, and Global Kill Switches for emergency intervention.

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

## Quick Start

### Installation
```bash
pip install citadel-sdk
```

### Local Development Setup

To run the Citadel SDK locally (or run the test suite), you must have a PostgreSQL database running with the correct schema.

**1. Start the Database**
We provide a `docker-compose.yml` to instantly spin up the required PostgreSQL instance and apply the schema:
```bash
docker compose up -d postgres
```

**2. Install Dependencies**
Install the core runtime dependencies:
```bash
pip install -e .
```

**3. Run the API Server**
Start the FastAPI server:
```bash
uvicorn citadel.api:app --reload
```

### Quick Usage
```python
import citadel

# Configure the universal client
client = citadel.CitadelClient(base_url="http://localhost:8000", api_key="your-key")

# Execute an action under governance
result = await client.execute(
    action="file.delete",
    resource="documents/sensitive.pdf",
    actor_id="agent-v1",
    capability_token="gt_cap_xyz..." # Optional: Bypass policy via GT token
)

if result.status == "executed":
    print("Action permitted and logged.")
elif result.status == "pending_approval":
    print("Action is waiting for human review.")
```

## Hardening & Verification

Citadel is tested against adversarial scenarios:
- **Simulation Scripts**: Run `python tests/simulations/simulate_lockout.py` to verify quota enforcement.
- **Audit Verification**: Call `await client.verify_audit()` to check the cryptographic integrity of the entire governance chain.
- **Race Condition Tests**: Extensive regression suite for concurrent action handling.

## Documentation

- [Architecture Schema](docs/ARCHITECTURE_SCHEMA.md) — Module dependency graph
- [Kernel Guarantees](docs/KERNEL_GUARANTEES.md) — Invariants and edge cases
- [API Reference](docs/API.md) — HTTP endpoints and schemas

## Licensing

Citadel uses a mixed-license model to protect its core while enabling broad adoption:

- **Apache 2.0**: SDKs, public schemas, and integration-facing packages in `packages/`.
- **BSL 1.1 (Source-Available)**: The core self-hostable runtime in `apps/runtime/`.
- **Proprietary**: Enterprise-only and hosted-cloud-only modules in `enterprise/`.

See [`LICENSING.md`](./LICENSING.md) for the full package-by-package breakdown.
