# Citadel Core Manifest

This manifest maps the wedge-focused active product to the live repository. It
is intentionally small. The repo remains the source of truth for code; this file
is the source of truth for what should be treated as active core.

## Active Wedge Source Map

| Wedge | Active source files |
| --- | --- |
| Pre-request spend enforcement | `apps/runtime/citadel/commercial/cost_controls.py`, `apps/runtime/citadel/commercial/routes.py`, `apps/dashboard/src/pages/Billing.tsx`, `apps/dashboard/src/hooks/useBilling.ts` |
| Spend/budget persistence | `db/migrations/018_cost_controls.sql`, `db/migrations/019_cost_budget_topups.sql` |
| Decision-first authority | `governance_decisions` in `apps/runtime/citadel/tokens/governance_decision.py`, `apps/runtime/citadel/tokens/token_vault.py`, `db/migrations/003_governance_tokens.sql` |
| Execution proof | `gt_cap_` tokens in `apps/runtime/citadel/tokens/governance_token.py`, `apps/runtime/citadel/tokens/token_verifier.py`, `apps/runtime/citadel/tokens/execution_middleware.py` |
| Cryptographic audit evidence | `governance_audit_log` in `apps/runtime/citadel/tokens/audit_trail.py`, `apps/runtime/citadel/audit_anchoring.py`, `db/migrations/004_governance_audit.sql` |
| Action lifecycle audit | `apps/runtime/citadel/services/audit_service.py`, `db/migrations/001_initial_schema.sql` |
| Emergency stop | `apps/runtime/citadel/tokens/kill_switch.py` |
| Minimal operator control plane | `apps/dashboard/`, `apps/runtime/citadel/api/routers/dashboard.py` |
| Developer integration — main SDK | `packages/sdk-python/` |
| Developer integration — minimal kernel SDK | `packages/sdk-python-kernel/`, `packages/sdk-python/` (dependency) |

## Archived This Pass

| Previous path | New path | Reason |
| --- | --- | --- |
| `apps/dashboard-demo/` | `archive/legacy/apps/dashboard-demo/` | Duplicate demo UI; not the canonical dashboard. |
| `packages/sdk-typescript/` | `archive/legacy/packages/sdk-typescript/` | Placeholder SDK package; preserve until a real minimal TypeScript SDK is built. |
| `docs/sre/` | `archive/legacy/docs/sre/` | Pre-PMF SRE documentation; not active wedge product surface. |
| `docs/agt/` | `archive/research/agt/` | Competitive research; not active product documentation. |
| `apps/runtime/citadel/sre/` | `archive/legacy/runtime/sre/` | SRE scaffolding removed from default runtime imports. |
| `apps/runtime/citadel/utils/telemetry.py` | `archive/legacy/runtime/utils/telemetry.py` | OpenTelemetry helper removed from default runtime imports. |
| `monitoring/` | `archive/legacy/monitoring/` | Collector configuration archived with telemetry support. |
| `tests/unit/test_otel_persistent_queue.py` | `archive/legacy/tests/unit/test_otel_persistent_queue.py` | Telemetry queue test preserved with archived collector config. |
| `apps/runtime/citadel/agent_identity/trust_policy.py` | `archive/legacy/runtime/agent_identity/trust_policy.py` | Broad trust action matrix archived; active scoring now uses three operational factors. |
| `tests/unit/test_trust_policy.py` | `archive/legacy/tests/unit/test_trust_policy.py` | Tests preserved with archived trust policy matrix. |
| `docs/internal/ORCHESTRATION.md` | `archive/legacy/docs/internal/ORCHESTRATION.md` | General orchestration architecture moved out of active docs. |
| `docs/internal/PERFORMANCE_REVIEW.md` | `archive/legacy/docs/internal/PERFORMANCE_REVIEW.md` | Orchestration benchmark review moved with archived performance material. |
| `docs/internal/HARDENING_PASS_REPORT.md` | `archive/legacy/docs/internal/HARDENING_PASS_REPORT.md` | Orchestration hardening report preserved as legacy context. |
| `tests/test_orchestration_performance.py` | `archive/legacy/tests/test_orchestration_performance.py` | General orchestration benchmark suite removed from active test path. |
| `docs/public/guides/trust-architecture.md` | `archive/legacy/docs/public/guides/trust-architecture.md` | Broad trust architecture guide replaced by the active three-factor model. |
| `docs/public/guides/monitoring-governance.md` | `archive/legacy/docs/public/guides/monitoring-governance.md` | Monitoring guide depended on archived telemetry/collector surface. |
| `docs/public/recipes/agent-capability-downgrade.md` | `archive/legacy/docs/public/recipes/agent-capability-downgrade.md` | Broad trust recipe moved out of the wedge docs. |
| `docs/public/recipes/ai-output-verification.md` | `archive/legacy/docs/public/recipes/ai-output-verification.md` | Output-verification recipe moved out of the wedge docs. |
| `docs/ARCHITECTURE.md` | `archive/legacy/docs/ARCHITECTURE.md` | Legacy three-layer/platform architecture replaced by wedge architecture. |
| `docs/FORGE_ROADMAP.md` | `archive/legacy/docs/strategy/FORGE_ROADMAP.md` | Broad platform roadmap moved out of active docs. |
| `docs/VISION.md` | `archive/legacy/docs/strategy/VISION.md` | Long-term universal platform vision moved out of active docs. |
| `docs/public/integrations/crewai.md` | `archive/legacy/docs/public/integrations/crewai.md` | Broad crew orchestration example moved out of active docs. |
| `docs/public/integrations/openai-agents.md` | `archive/legacy/docs/public/integrations/openai-agents.md` | Broad handoff/orchestration example moved out of active docs. |
| `docs/public/integrations/langgraph.md` | `archive/legacy/docs/public/integrations/langgraph.md` | Graph orchestration example moved out of active docs. |
| `docs/public/recipes/multi-agent-coordination.md` | `archive/legacy/docs/public/recipes/multi-agent-coordination.md` | Multi-agent orchestration recipe moved out of active docs. |

## Deleted This Pass (Repo Cleanup for Minimal Wedge)

The following directories and files were **deleted** (not archived) as part of preparing the repository for early alpha release of the minimal citadel-kernel wedge. These are explicitly not preserved because they are infrastructure configs or platform-level assets with no future reference value in the wedge-focused repo:

| Deleted | Reason |
| --- | --- |
| `demo/` | Demo scripts not needed for minimal wedge |
| `web/` (all static website files) | Marketing website, not part of wedge |
| `docs/ARCHITECTURE*.md`, `docs/COMPATIBILITY.md`, `docs/DEVELOPMENT.md`, `docs/MAINTAINER_GUIDE.md`, `docs/PROJECT_STRUCTURE.md`, `docs/ROADMAP.md` | Broad platform documentation not wedge-specific |
| `docs/adr/` (architectural decision records) | Platform-level ADRs, not wedge-specific |
| `docs/internal/` (internal documentation) | Internal platform docs, not wedge-specific |
| `docs/public/` (public platform guides) | Broad platform integration guides, not wedge-specific |
| `docs/recipes/` (orchestration recipes) | Multi-agent orchestration recipes, not wedge-specific |
| `tests/dashboard/`, `tests/integration/`, `tests/regression/`, `tests/security/`, `tests/simulations/` | Platform test suites not wedge-specific |
| `fly.toml`, `docker-compose.yml`, `Dockerfile`, `vercel.json` | Deployment infrastructure configs |
| `alembic.ini` | Database migration config (migrations themselves in `db/` remain) |
| `setup.py`, `MANIFEST.in` | Legacy build files (pyproject.toml is canonical) |

## Deferred Runtime Cleanup

These modules remain in place for now because they are imported by the current
runtime, tests, or dashboard. They should be simplified in later focused passes,
not moved blindly:

| Area | Current path | Follow-up |
| --- | --- | --- |
| Stripe/billing compatibility | `apps/runtime/citadel/commercial/adapters/stripe/`, `apps/runtime/citadel/billing/` | Collapse toward spend enforcement once compatibility impact is understood. |
| Dashboard analytics | `apps/runtime/citadel/dashboard/posture_score.py`, `apps/runtime/citadel/dashboard/coverage_heatmap.py` | Remove from active UI/API only after checking imports and tests. |
| Compatibility-only orchestration | `apps/runtime/citadel/execution/orchestration.py`, `apps/runtime/citadel/api/routers/orchestration.py`, `apps/runtime/citadel/compatibility.py` | Preserve for existing callers; do not present as the product surface. |
| Trust band compatibility states | `apps/runtime/citadel/agent_identity/trust_bands.py` | Collapse stored/API compatibility states after migrations and callers no longer reference PROBATION/HIGHLY_TRUSTED. |

## Naming Constraints

- Use Citadel for current package/runtime names.
- Use Ledger only for historical or strategic notes.
- Use `gt_cap_` for runtime execution proof tokens.
- Use `governance_decisions` for durable authority records.
- Use `audit_events` for action lifecycle audit.
- Use `governance_audit_log` for decision/token/execution-gating audit.
