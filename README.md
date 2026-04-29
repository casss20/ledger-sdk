# Citadel SDK

**Cost enforcement and decision-first audit evidence for agent builders.**

Citadel is being simplified into a wedge-focused governance kernel. The active
product path is centered on pre-request LLM spend enforcement and cryptographic
decision evidence. The canonical active-core map is in [`citadel-core/`](citadel-core/).

Archived research, duplicate demos, and placeholder packages are preserved under
[`archive/`](archive/) so nothing is lost, but they are no longer presented as
current product surface.

## Active Core Capabilities

### 1. Runaway Spend Prevention
- **Pre-request budget checks**: Estimate cost before the LLM/API call and block, require approval, or record spend according to configured budgets.
- **Hierarchical budget records**: Tenant, project, agent, and API-key scopes are represented in the cost-control schema.
- **Audited top-ups**: Admin budget adjustments require a reason and write to `governance_audit_log`.
- **Spend attribution**: Spend events are attributed back to tenant/project/agent/API-key context.

### 2. Multi-Tenancy & Auth (Cloud Ready)
- **Strict Tenant Isolation**: Enforced via PostgreSQL Row-Level Security (RLS) and application-level filtering.
- **API Key Management**: Secure SHA-256 hashed keys with scoped permissions and automatic `last_used` tracking.
- **JWT Dashboard Auth**: Role-based access for operators and tenant admins.

### 3. Decision-First Audit Evidence
- **Policy Resolution**: Precedence-based rule matching (`ALLOWED`, `BLOCKED`, `PENDING_APPROVAL`, `RATE_LIMITED`).
- **No-Code Approval Thresholds**: Dashboard operators can configure a safe tenant-level risk threshold that generates a normal immutable runtime policy requiring human approval for actions above the selected score.
- **Tamper-Proof Audit**: Every decision is cryptographically hashed and linked in a PostgreSQL chain.
- **Human-in-the-Loop**: Integrated approval queue for high-risk actions.
- **Decision-First Runtime Governance**: Sensitive actions persist a durable governance decision before any execution proof is issued. Short-lived `gt_cap_` tokens then reference that `decision_id`, so runtime outcomes can be traced back to policy version, approval state, operator context, and audit evidence.
- **Runtime Introspection**: High-risk execution paths can call `/v1/introspect` before the next protected operation. Introspection validates token expiry, revocation, workspace/action/resource scope, and central kill-switch state instead of relying on token expiry alone.
- **Governance Tokens**: The active runtime execution proof token family is `gt_cap_`.

## Technical Design Pillars

Citadel is now organized around a smaller active architecture:

1. **Spend enforcement before execution**: budget decisions happen before the external API call.
2. **Decision-first execution rights**: runtime authorization starts with `governance_decisions`, then issues scoped `gt_cap_` proof.
3. **Cryptographic evidence**: `governance_audit_log` and audit hashes support replay and verification.
4. **Minimal operator control plane**: dashboard surfaces should support cost controls, approvals, audit evidence, and kill switches.

## 📁 Repository Structure

Citadel is organized as a monorepo with a wedge-first active core:

- **`citadel-core/`**: Canonical active-core map for the wedge-focused product.
- **`apps/runtime/`**: The core governance engine and control plane (**BSL 1.1**).
- **`apps/dashboard/`**: The React-based management interface.
- **`packages/sdk-python/`**: Public Python SDK for agent integration (**Apache 2.0**).
- **`packages/open-spec/`**: Governance schemas and token specifications (**Apache 2.0**).
- **`docs/`**: Technical documentation and public documentation site.
- **`archive/`**: Preserved legacy, research, duplicate demos, and placeholder packages that are not active product surface.
- **`tests/`**: Unit, integration, dashboard, token, and regression tests.
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

### 2. Point it at your Citadel runtime

```python
import citadel_governance as cg

cg.configure(
    base_url="http://localhost:8000",
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

Open the self-hosted dashboard for your runtime and log in with your operator credentials.

Every action your agent executes appears in the Activity feed in real time. High-risk actions land in the Approval Queue for human review.

The preserved standalone demo dashboard now lives in `archive/legacy/apps/dashboard-demo/`.

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
- **[Architecture](docs/ARCHITECTURE.md)** — Active wedge runtime and compatibility boundaries
- **[Compatibility](docs/COMPATIBILITY.md)** — Deprecated paths, compatibility-only exports, and migration guidance
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
- **Archived**: Legacy, research, duplicate demo, and placeholder package material lives in `archive/` and is not active product surface.

See [`LICENSING.md`](./LICENSING.md) for the full package-by-package breakdown.
