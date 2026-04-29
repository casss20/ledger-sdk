# Project Structure

Citadel is being reorganized around a small active core:

1. Pre-request cost enforcement.
2. Decision-first cryptographic evidence.

The live runtime still uses the existing Python package under
`apps/runtime/citadel`. The canonical map for what is active product surface is
`citadel-core/`.

## Top-Level Layout

```text
citadel-sdk/
|-- citadel-core/        # Active wedge map and manifest
|-- apps/
|   |-- runtime/         # Current backend runtime package
|   |-- dashboard/       # Canonical operator dashboard
|   `-- landing/         # Landing page
|-- packages/
|   |-- sdk-python/      # Current Python SDK
|   `-- open-spec/       # Public schemas and token specifications
|-- db/
|   `-- migrations/      # Ordered SQL migrations
|-- docs/                # Active docs
|-- tests/               # Unit, integration, dashboard, token, and regression tests
|-- scripts/             # Development and administrative utilities
`-- archive/             # Preserved inactive code, demos, ops scaffolding, and research
```

## Active Core

The active core is documented in:

- `citadel-core/README.md`
- `citadel-core/MANIFEST.md`

Those files define the current wedge source map. New product work should update
that manifest when it changes what counts as active core.

## Archived During Wedge Refactor

| Old active-looking path | Preserved path | Status |
| --- | --- | --- |
| `apps/dashboard-demo/` | `archive/legacy/apps/dashboard-demo/` | Duplicate demo dashboard; not canonical. |
| `packages/sdk-typescript/` | `archive/legacy/packages/sdk-typescript/` | Placeholder package; not an active SDK. |
| `docs/sre/` | `archive/legacy/docs/sre/` | Pre-PMF SRE docs; not active wedge docs. |
| `docs/agt/` | `archive/research/agt/` | Competitive research, not product docs. |
| `apps/runtime/citadel/sre/` | `archive/legacy/runtime/sre/` | SRE runtime helpers; removed from default app wiring. |
| `apps/runtime/citadel/utils/telemetry.py` | `archive/legacy/runtime/utils/telemetry.py` | OpenTelemetry helper; removed from active runtime imports. |
| `monitoring/` | `archive/legacy/monitoring/` | Collector config; telemetry is not active product surface. |
| `apps/runtime/citadel/agent_identity/trust_policy.py` | `archive/legacy/runtime/agent_identity/trust_policy.py` | Broad trust action matrix; removed from active package exports. |
| `docs/internal/ORCHESTRATION.md` | `archive/legacy/docs/internal/ORCHESTRATION.md` | General orchestration architecture; not active wedge documentation. |
| `tests/test_orchestration_performance.py` | `archive/legacy/tests/test_orchestration_performance.py` | Orchestration benchmark suite; preserved with legacy orchestration docs. |
| `docs/public/guides/trust-architecture.md` | `archive/legacy/docs/public/guides/trust-architecture.md` | Broad trust guide superseded by the active three-factor trust model. |
| `docs/public/guides/monitoring-governance.md` | `archive/legacy/docs/public/guides/monitoring-governance.md` | Monitoring guide tied to archived telemetry/collector support. |
| `docs/public/recipes/agent-capability-downgrade.md` | `archive/legacy/docs/public/recipes/agent-capability-downgrade.md` | Broad trust recipe; not active wedge documentation. |
| `docs/public/recipes/ai-output-verification.md` | `archive/legacy/docs/public/recipes/ai-output-verification.md` | Output-verification recipe; not active wedge documentation. |
| `docs/ARCHITECTURE.md` | `archive/legacy/docs/ARCHITECTURE.md` | Legacy platform architecture replaced by active wedge architecture. |
| `docs/FORGE_ROADMAP.md` | `archive/legacy/docs/strategy/FORGE_ROADMAP.md` | Broad platform roadmap; not active product direction. |
| `docs/VISION.md` | `archive/legacy/docs/strategy/VISION.md` | Long-term universal platform vision; not active product direction. |
| `docs/public/integrations/crewai.md` | `archive/legacy/docs/public/integrations/crewai.md` | Broad crew orchestration integration. |
| `docs/public/integrations/openai-agents.md` | `archive/legacy/docs/public/integrations/openai-agents.md` | Broad handoff/orchestration integration. |
| `docs/public/integrations/langgraph.md` | `archive/legacy/docs/public/integrations/langgraph.md` | Graph orchestration integration. |
| `docs/public/recipes/multi-agent-coordination.md` | `archive/legacy/docs/public/recipes/multi-agent-coordination.md` | Multi-agent orchestration recipe. |

## Current Runtime Package

```text
apps/runtime/citadel/
|-- api/                 # FastAPI app and routers
|-- commercial/          # Cost controls, budgets, top-ups, and compatibility billing routes
|-- tokens/              # governance_decisions, gt_cap_ tokens, audit trail, kill switch
|-- services/            # Audit, approval, policy, and capability services
|-- core/                # Existing kernel/governor/router implementation
|-- dashboard/           # Dashboard backend helpers
|-- agent_identity/      # Current trust/identity implementation
|-- middleware/          # FastAPI/ASGI middleware
|-- security/            # Security middleware
|-- integrations/        # Existing integration code
`-- utils/               # Shared utilities
```

The runtime package is not fully extracted into an embeddable in-process kernel
yet. SRE, telemetry scaffolding, the broad trust action matrix, broad trust
docs, and orchestration performance material have been removed from the default
startup/package/docs path. Orchestration runtime, trust-band compatibility
states, and Stripe compatibility remain staged follow-ups because active routes
and tests still cover them.

## Dependency Rules

Allowed:

```text
sdk-python -> HTTP -> runtime API
dashboard -> HTTP -> runtime API
runtime/api -> runtime services/tokens/commercial modules
active docs -> citadel-core manifest for product classification
```

Forbidden:

```text
runtime default path -> archive/
tests for active runtime -> archive/
active docs -> archived code as current product capability
new active code -> duplicate token/audit/dashboard abstractions
```

## Public Interfaces

Stable or semi-stable interfaces:

| Surface | Location |
| --- | --- |
| Python SDK | `packages/sdk-python/citadel_governance/` |
| HTTP API | `apps/runtime/citadel/api/routers/` |
| Database migrations | `db/migrations/` |
| Active core map | `citadel-core/MANIFEST.md` |

Everything else is internal unless documented otherwise.
