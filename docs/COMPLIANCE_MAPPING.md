# Citadel SDK Compliance Mapping

This document maps Citadel SDK's technical features to common regulatory controls and security frameworks.
It is also the repo-level mapping for research claims about Ledger/Citadel governance architecture.

The repository is the source of truth. Strategic research may call the product "Ledger" or use generic
phrases such as "governance token system" or "audit trail separation"; in this repo those map to concrete
Citadel primitives such as `gt_cap_` tokens, `governance_decisions`, `audit_events`, and
`governance_audit_log`.

## 1. SOC 2 Type II (Common Criteria)

| Control Category | Citadel Feature | Implementation Detail |
| :--- | :--- | :--- |
| **Access Control** (CC6.1) | API Key & JWT Auth | Secure SHA-256 key hashing and scoped permissions. |
| **Data Isolation** (CC6.1) | PostgreSQL RLS | Strict tenant isolation enforced at the database level. |
| **Audit Logging** (CC2.2) | Audit Chain | Tamper-proof, cryptographically linked `audit_events` and `governance_audit_log` records. |
| **System Monitoring** (CC7.2) | OTel + Metrics | Full observability into governance decisions and latency. |
| **Change Management** (CC8.1) | Policy Snapshots | Immutable versioning of governance rules. |
| **Evidence Integrity** (CC7.2) | Governance Audit Separation | Decision/token verification events are separated from operational action lifecycle events. |

## 2. GDPR (EU General Data Protection Regulation)

| Article | Requirement | CITADEL Solution |
| :--- | :--- | :--- |
| **Article 25** | Data Protection by Design | RLS ensures developers cannot accidentally access other tenant data. |
| **Article 30** | Records of Processing | Automatic logging of every agent action and decision. |
| **Article 32** | Security of Processing | Kill Switches allow immediate suspension of risky processing. |

## 3. EU AI Act

| Section | Requirement | CITADEL Solution |
| :--- | :--- | :--- |
| **Article 12** | Record-Keeping | Full audit trail of AI system decisions and human overrides. |
| **Article 14** | Human Oversight | Integrated Approval Queue for high-risk autonomous actions. |
| **Article 14(4)(e)** | Stop Button | Global and per-tenant Kill Switches for immediate intervention. |
| **Article 13** | Transparency / Traceability | `governance_decisions`, `gt_cap_` tokens, policy snapshots, and audit hashes link decisions to runtime evidence. |

## 4. ISO/IEC 27001:2022

| Annex A Control | CITADEL Feature | Implementation Detail |
| :--- | :--- | :--- |
| **A.8.15** | Logging | Comprehensive event logging via the Governance Audit Trail. |
| **A.8.3** | Identity Management | Unified commercial identity linking billing, auth, and execution. |
| **A.8.26** | App Development | Secure SDK decorators (`@guard`) for consistent policy enforcement. |

---

## Research Claim Mapping

| Research phrase | Repo primitive | Status |
| :--- | :--- | :--- |
| `gt_` governance token system | `gt_cap_` capability tokens in `governance_tokens`, resolved through `TokenVault` and linked to `governance_decisions` | Implemented under existing Citadel names |
| Physically separate audit trail | `audit_events` for action lifecycle, `governance_audit_log` for decision/token/execution-gating evidence | Implemented |
| Query-rewriter-style enforcement | `Kernel.handle()`, precedence checks, execution middleware, and RLS | Implemented across runtime layers |
| Fail-secure database isolation | Forced PostgreSQL RLS plus explicit tenant context | Implemented |
| Kill switch / stop button | `KillSwitch`, `kill_switches`, dashboard kill switch panel | Implemented |
| W3C trace correlation | `trace_id`, `session_id`; OpenTelemetry setup is archived legacy material | Partially implemented |
| S3 Object Lock / 7-year cold archive | No live archive fan-out in repo | Deferred |
| Collector-level audit hash chain | Telemetry collector is export-only; audit remains DB-backed | Deferred |

*Note: This mapping is for informational purposes only and does not constitute legal advice or a guarantee of compliance.*
