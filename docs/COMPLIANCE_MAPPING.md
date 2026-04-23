# Ledger SDK Compliance Mapping

This document maps Ledger SDK's technical features to common regulatory controls and security frameworks.

## 1. SOC 2 Type II (Common Criteria)

| Control Category | Ledger Feature | Implementation Detail |
| :--- | :--- | :--- |
| **Access Control** (CC6.1) | API Key & JWT Auth | Secure SHA-256 key hashing and scoped permissions. |
| **Data Isolation** (CC6.1) | PostgreSQL RLS | Strict tenant isolation enforced at the database level. |
| **Audit Logging** (CC2.2) | Audit Chain | Tamper-proof, cryptographically linked event log. |
| **System Monitoring** (CC7.2) | OTel + Metrics | Full observability into governance decisions and latency. |
| **Change Management** (CC8.1) | Policy Snapshots | Immutable versioning of governance rules. |

## 2. GDPR (EU General Data Protection Regulation)

| Article | Requirement | Ledger Solution |
| :--- | :--- | :--- |
| **Article 25** | Data Protection by Design | RLS ensures developers cannot accidentally access other tenant data. |
| **Article 30** | Records of Processing | Automatic logging of every agent action and decision. |
| **Article 32** | Security of Processing | Kill Switches allow immediate suspension of risky processing. |

## 3. EU AI Act

| Section | Requirement | Ledger Solution |
| :--- | :--- | :--- |
| **Article 12** | Record-Keeping | Full audit trail of AI system decisions and human overrides. |
| **Article 14** | Human Oversight | Integrated Approval Queue for high-risk autonomous actions. |
| **Article 14(4)(e)** | Stop Button | Global and per-tenant Kill Switches for immediate intervention. |

## 4. ISO/IEC 27001:2022

| Annex A Control | Ledger Feature | Implementation Detail |
| :--- | :--- | :--- |
| **A.8.15** | Logging | Comprehensive event logging via the Governance Audit Trail. |
| **A.8.3** | Identity Management | Unified commercial identity linking billing, auth, and execution. |
| **A.8.26** | App Development | Secure SDK decorators (`@guard`) for consistent policy enforcement. |

---

*Note: This mapping is for informational purposes only and does not constitute legal advice or a guarantee of compliance.*
