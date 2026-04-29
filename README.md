# Citadel SDK

**Hard cost enforcement + cryptographic audit evidence for AI agents.**

The minimal governance kernel is now live on PyPI: **[citadel-governance 0.2.2](https://pypi.org/project/citadel-governance/0.2.2/)**

Citadel provides two essential wedges: (1) pre-request budget checks that block LLM calls before they execute, and (2) tamper-evident decision audit bundles for regulatory compliance. The canonical active-core map is in [`citadel-core/`](citadel-core/).

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

## 📦 Packages (Early Alpha)

Citadel now focuses on a minimal kernel with two wedges:

| Package | Install | Purpose | License | Status |
|---|---|---|---|---|
| **citadel-governance 0.2.2** | `pip install citadel-governance` | Minimal SDK: cost enforcement + audit evidence | **Apache 2.0** | ✅ Live on PyPI |
| **citadel-governance 0.1.0** | `pip install citadel-governance==0.1.0` | Full SDK: governance + approval + introspection | **Apache 2.0** | 🔄 Archived |
| **citadel-runtime** | `pip install -e ".[all]"` (from repo) | Self-hosted backend service | **BSL 1.1** | 🔄 Dev only |

**New users: Install `citadel-governance` (0.2.2).** It's lightweight, embeddable, and provides hard cost enforcement + cryptographic audit evidence.

### Quick Start: Minimal Kernel (0.2.2 — Live on PyPI)

1. **Install the SDK**

```bash
pip install citadel-governance
```

2. **Set up the backend** — See [BACKEND_SETUP.md](BACKEND_SETUP.md) for Docker or local Python setup.

3. **Execute actions with cost enforcement and audit**

```python
import citadel_kernel as ck
import asyncio

async def main():
    client = ck.KernelClient(
        base_url="http://localhost:8000",
        api_key="your_key_here",
        actor_id="my-agent",
    )
    
    # Wedge A: Hard cost enforcement blocks before API call
    result = await client.execute(
        action="llm.generate",
        provider="anthropic",
        model="claude-opus-4-7",
        input_tokens=10000,
        output_tokens=2000,
    )
    print(f"Status: {result.status}")
    
    # Wedge B: Cryptographic audit evidence
    evidence = await client.export_evidence(result.action_id)
    verified = await client.verify_evidence(result.action_id)
    print(f"Evidence verified: {verified['verified']}")
    
    await client.close()

asyncio.run(main())
```

See [`packages/sdk-python-kernel/README.md`](packages/sdk-python-kernel/README.md) for full documentation, or check out the package on [PyPI](https://pypi.org/project/citadel-governance/0.2.2/).

### Legacy SDKs (Archived)

The full `citadel-governance` SDK and decorator patterns are preserved in the codebase but not recommended for new projects. They support the complete governance stack (approval workflows, introspection, etc.) but are more complex. Use `citadel-kernel` for new work.

### Backend Setup

**For local development and testing**, see [BACKEND_SETUP.md](BACKEND_SETUP.md) for:
- Quick Docker setup
- Local Python development
- Database setup (SQLite or PostgreSQL)
- Troubleshooting

**For production deployment**, configure PostgreSQL, environment secrets, reverse proxy, and monitoring as described in `apps/runtime/README.md`.

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
