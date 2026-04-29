# Archive

This directory preserves code, docs, demos, and research that are no longer part
of the active Citadel product path.

Archived material is not deleted, but it is also not current product surface:

- It must not be imported by the default runtime path.
- It must not be documented as an active capability.
- It may be revived only through a deliberate implementation pass that updates
  tests, docs, imports, and ownership.

## Current Archived Areas

| Path | Status |
| --- | --- |
| `archive/research/` | Research, exploratory prototypes, and competitive analysis. |
| `archive/research/agt/` | Microsoft AGT comparison material. |
| `archive/legacy/apps/dashboard-demo/` | Preserved duplicate dashboard demo. The active dashboard is `apps/dashboard/`. |
| `archive/legacy/packages/sdk-typescript/` | Preserved placeholder TypeScript SDK package. |
| `archive/legacy/docs/sre/` | Preserved SRE/monitoring documentation that is not active wedge documentation. |
| `archive/legacy/runtime/sre/` | Preserved SRE runtime helpers removed from the default app path. |
| `archive/legacy/runtime/utils/telemetry.py` | Preserved OpenTelemetry helper removed from active runtime imports. |
| `archive/legacy/monitoring/` | Preserved OpenTelemetry collector configuration. |
| `archive/legacy/tests/unit/test_otel_persistent_queue.py` | Preserved telemetry queue test with the archived collector config. |
| `archive/legacy/runtime/agent_identity/trust_policy.py` | Preserved broad trust action matrix removed from active package exports. |
| `archive/legacy/tests/unit/test_trust_policy.py` | Preserved tests for the archived trust policy matrix. |
| `archive/legacy/docs/internal/ORCHESTRATION.md` | Preserved general orchestration architecture document. |
| `archive/legacy/docs/internal/PERFORMANCE_REVIEW.md` | Preserved orchestration performance review. |
| `archive/legacy/docs/internal/HARDENING_PASS_REPORT.md` | Preserved orchestration hardening report. |
| `archive/legacy/tests/test_orchestration_performance.py` | Preserved orchestration benchmark suite. |
| `archive/legacy/docs/public/guides/trust-architecture.md` | Preserved broad trust architecture guide superseded by active trust-scoring docs. |
| `archive/legacy/docs/public/guides/monitoring-governance.md` | Preserved monitoring guide tied to archived telemetry/collector support. |
| `archive/legacy/docs/public/recipes/agent-capability-downgrade.md` | Preserved broad trust recipe removed from active docs. |
| `archive/legacy/docs/public/recipes/ai-output-verification.md` | Preserved output-verification recipe removed from active docs. |
| `archive/legacy/docs/ARCHITECTURE.md` | Preserved legacy three-layer/platform architecture. |
| `archive/legacy/docs/strategy/FORGE_ROADMAP.md` | Preserved broad platform roadmap. |
| `archive/legacy/docs/strategy/VISION.md` | Preserved long-term universal platform vision. |
| `archive/legacy/docs/public/integrations/crewai.md` | Preserved broad crew orchestration integration. |
| `archive/legacy/docs/public/integrations/openai-agents.md` | Preserved broad handoff/orchestration integration. |
| `archive/legacy/docs/public/integrations/langgraph.md` | Preserved graph orchestration integration. |
| `archive/legacy/docs/public/recipes/multi-agent-coordination.md` | Preserved multi-agent orchestration recipe. |

The active wedge map is maintained in `citadel-core/`.
