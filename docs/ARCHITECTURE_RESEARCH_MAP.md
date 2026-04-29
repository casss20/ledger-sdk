# Ledger Governance Research Map

This document maps the Kimi research report, "Ledger Governance Architecture
Research: Cross-Domain Analysis", onto the live Citadel/Ledger repository.

The repository is the source of truth. When the report describes something that
already exists under a different name, use the existing repo name instead of
creating a duplicate abstraction.

## Repo Architecture Inventory

| Area | Repo source of truth | Current shape |
| --- | --- | --- |
| Runtime enforcement | `apps/runtime/citadel/execution/kernel.py` | `Kernel.handle()` normalizes actions, resolves policy, applies precedence, handles approvals, executes only after governance checks, and writes terminal decisions. |
| Decision-first governance | `apps/runtime/citadel/tokens/governance_decision.py`, `apps/runtime/citadel/tokens/decision_engine.py`, `db/migrations/003_governance_tokens.sql` | `GovernanceDecision` is the durable authority record. Tokens are optional execution proofs derived from allow decisions. |
| Governance tokens | `apps/runtime/citadel/tokens/governance_token.py`, `apps/runtime/citadel/tokens/token_vault.py` | Existing token format is `gt_cap_...`, a scoped capability token that resolves to one `decision_id`. |
| Operational audit | `db/schema.sql`, `apps/runtime/citadel/audit_service.py` | `audit_events` records the action lifecycle and is append-only, hash-chained, and indexed for action/actor/tenant queries. |
| Governance audit | `db/migrations/004_governance_audit.sql`, `apps/runtime/citadel/tokens/audit_trail.py` | `governance_audit_log` is a separated governance audit trail for decision, token, verification, and execution-gating events. |
| Tenant isolation | `db/migrations/001_tenant_isolation.sql`, `apps/runtime/citadel/middleware/tenant_context.py` | PostgreSQL RLS is enabled and forced on core governance tables. Tenant context is explicit; missing context fails through `TenantAwarePool`. |
| Kill switch | `apps/runtime/citadel/tokens/kill_switch.py`, `db/schema.sql`, `apps/runtime/citadel/dashboard/kill_switch_panel.py` | Kill switches exist at request, actor, tenant, and global scopes and are checked before policy/token execution paths. |
| Approval queue | `db/schema.sql`, `apps/runtime/citadel/approval_service.py`, `apps/runtime/citadel/dashboard/approval_queue.py` | Human-in-the-loop approval state is first-class and queryable. |
| Dashboard workflow | `apps/runtime/citadel/dashboard/*.py`, `apps/dashboard/src/pages/*.tsx` | Posture score, activity stream, approval queue, audit explorer, coverage heatmap, and kill switch panel all exist as Citadel dashboard surfaces. |
| Embeddable widgets | `packages/widget-library/src/index.ts` | The widget package currently exports ActivityStream, ApprovalQueue, and KillSwitch components. |
| Telemetry export | Archived under `archive/legacy/runtime/utils/telemetry.py` and `archive/legacy/monitoring/` | OpenTelemetry support is preserved as legacy reference material, but is no longer wired into the default runtime path. Telemetry is not an audit source of truth. |

## Report Claims Inventory

| Report claim | Existing repo mapping | Classification | Integration decision |
| --- | --- | --- | --- |
| Implement `gt_` governance tokens with non-portable resolution | Existing `gt_cap_` capability tokens, `governance_tokens`, `TokenVault`, `governance_decisions` | Already implemented | Use `gt_cap_` and decision-first terminology. Do not add a second `gt_` token model. |
| Make decisions the durable record behind execution rights | `GovernanceDecision`, `DecisionEngine`, `TokenVault.issue_token_for_decision()` | Already implemented | Keep decision-first flow. |
| Separate audit trail from operational logs | `audit_events` and `governance_audit_log` | Already implemented | Preserve the two audit tables and their different query patterns. |
| Datadog-style append-only audit API | DB append-only triggers and read/query endpoints | Already implemented | Strengthen docs around append-only evidence; no schema duplicate needed. |
| PostgreSQL RLS enforcement boundary | RLS migrations and tenant context tests | Already implemented | Keep RLS as the database enforcement layer. |
| Transaction-scoped governance isolation | `set_tenant_context()` and tenant middleware | Partially implemented | Existing tenant scoping is explicit. Broader transaction/session semantics should be evaluated separately. |
| Fail-secure default deny | RLS denies missing tenant context; kernel blocks policy resolution failures; kill switch denies | Partially implemented | Do not change global policy behavior in this patch. Default-deny across every missing policy is product-sensitive. |
| W3C trace context and baggage | `trace_id`, `session_id`; telemetry setup is archived | Partially implemented | Future integration should extend existing fields, not create a parallel provenance ID. |
| Dual-write audit archive to S3 Object Lock and search index | No implemented audit archive fan-out | Defer | Requires infrastructure, retention, legal/compliance, and recovery design. Do not route audit through telemetry collector by default. |
| Two-layer hash chaining | `audit_events`, `governance_audit_log`, `audit_merkle_roots`, token `chain_hash` | Partially implemented | Hashing exists in multiple layers; "collector gateway chain hash" is not implemented and should not be invented casually. |
| Kill switch as Article 14 stop button | `KillSwitch`, `kill_switches`, kill switch dashboard/docs | Already implemented | Use existing kill switch language. |
| Governance posture score | `PostureScoreService`, dashboard tests | Already implemented | Keep Citadel dashboard naming. |
| Activity stream / security inbox | `ActivityStreamService`, activity dashboard/widgets | Already implemented | Keep existing service and widget names. |
| Approval queue | Approval service/table/dashboard/widget | Already implemented | No duplicate queue. |
| Coverage heatmap | `CoverageHeatmapService`, dashboard tests | Already implemented | No duplicate heatmap. |
| Audit explorer with facet filtering | `AuditExplorerService`, dashboard tests | Already implemented | No duplicate audit browser. |
| Embeddable React widgets | `packages/widget-library` | Partially implemented | Future work can add posture/audit widgets inside the existing package. |
| Compliance framework matrix | `docs/COMPLIANCE_MAPPING.md`, `docs/public/guides/regulatory-compliance.md` | Should integrate now | Expand documentation to map report claims to implemented evidence. |

## What To Integrate Now

The safe integration is documentation and guardrails:

1. Capture the report-to-repo mapping in this document.
2. Expand the compliance mapping using existing Citadel primitives.
3. Add tests that keep future work from creating duplicate token, audit, or dashboard abstractions.

These changes are valuable because they turn the report into an implementation
index without destabilizing governance-critical code.

## Deferred Items

The following report recommendations should not be implemented until they have a
dedicated design review:

- Audit archive fan-out to S3 Object Lock, Glacier, Elasticsearch, or ClickHouse.
- Collector-level audit hash chaining.
- Global default-deny behavior for every missing policy.
- New `gt_` token families beyond the existing `gt_cap_` model.
- A second audit store or provenance graph that bypasses `audit_events` or `governance_audit_log`.
- New dashboard/workflow modules that duplicate existing posture, activity, approval, audit explorer, coverage heatmap, or kill switch surfaces.

## Naming Rules

- Use "Citadel" for current package/runtime names.
- Use "Ledger" only when referring to strategic/report language or historical positioning.
- Use `gt_cap_` for runtime execution proof tokens.
- Use `governance_decisions` for durable authority records.
- Use `audit_events` for action lifecycle audit.
- Use `governance_audit_log` for decision/token/execution-gating audit.

## Automated Guardrails

`tests/unit/test_research_architecture_mapping.py` protects this map by checking:

- The canonical mapping and compliance docs use existing Citadel names.
- The canonical token, audit, and dashboard implementation files still exist.
- The repo does not add duplicate implementation files for new `gt_` token
  families, second audit stores, provenance graphs, or duplicate dashboard
  workflow modules.

The guardrail is intentionally narrow. It blocks duplicate abstractions named
after the deferred report recommendations, while allowing normal changes inside
the existing canonical Citadel modules.
