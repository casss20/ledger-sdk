# Third-Party Notices

This document contains attribution for third-party software and architectural patterns used in the Ledger SDK.

---

## Microsoft Agent Governance Toolkit

- **Source**: https://github.com/microsoft/agent-governance-toolkit
- **License**: MIT License
- **Copyright**: Copyright (c) Microsoft Corporation

Portions of the Ledger SDK's governance runtime are inspired by and adapted from Microsoft's Agent Governance Toolkit (AGT), released under the MIT license. The following patterns were analyzed and reimplemented in Ledger's architecture, conventions, and design principles:

- Trust scoring methodology (0–1000 scale with composite sub-scores)
- Delegation chain tracking for agent authority
- Audit sink protocol design (write / write_batch / verify_integrity)
- Policy rule priority evaluation (first-match-wins)
- OWASP Agentic Top 10 risk mapping

**Important**: No AGT source code was copied directly into the Ledger SDK. All implementation was written from scratch for Ledger's specific architecture (async Python, PostgreSQL with strict Row-Level Security, tenant isolation). AGT was used as an architectural reference only.

### MIT License Text

```
MIT License

Copyright (c) Microsoft Corporation

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Stripe, Inc. — Architectural Patterns

- **Source**: Public documentation and PCI Security Standards Council materials
- **License**: Architectural concepts are public knowledge; no code used

The Ledger SDK adapts the following **publicly documented** architectural pattern from Stripe:

- **PaymentMethod tokenization (`pm_` pattern)**: Adapted as `gt_` governance tokens. The concept of "open to store, proprietary to resolve" is a public architectural pattern documented in PCI SSC materials and Stripe's public API documentation. No Stripe source code was used.

---

## Datadog, Inc. — Architectural Patterns

- **Source**: Public documentation and blog posts
- **License**: Architectural concepts are public knowledge; no code used

The Ledger SDK adapts the following **publicly documented** architectural patterns from Datadog:

- **Audit Trail / Log Management separation**: Separate schema, RBAC, retention policies for governance audit vs. operational logs. Publicly documented in Datadog's product documentation.
- **Security Inbox pattern**: Prioritized governance violation queue. Publicly documented in Datadog security product materials.

---

## PostgreSQL Global Development Group

- **Source**: https://www.postgresql.org/
- **License**: PostgreSQL License (permissive, BSD-style)

Ledger uses PostgreSQL's native Row-Level Security (RLS) feature for tenant isolation. RLS is a built-in PostgreSQL feature used according to its public documentation.

---

## OpenTelemetry Project

- **Source**: https://opentelemetry.io/
- **License**: Apache License 2.0

The Ledger SDK adapts the following **publicly documented** architectural patterns from OpenTelemetry:

- **W3C Trace Context propagation**: For kill switch signal propagation across agent boundaries
- **Fan-out exporter pattern**: For dual-write pipeline (archive + index)
- **Immutable SpanContext**: As model for immutable governance audit entries

No OpenTelemetry source code was copied. Patterns were reimplemented for Ledger's specific use case.

---

## JSON Canonicalization Scheme (JCS/RFC 8785)

- **Source**: https://www.rfc-editor.org/rfc/rfc8785
- **License**: Public standard (IETF)

Ledger implements JSON Canonicalization Scheme as described in RFC 8785 for deterministic SHA-256 hashing of governance audit payloads.

---

## Additional Attributions

- **OWASP Foundation**: OWASP Agentic Top 10 risk framework used for compliance mapping. https://owasp.org/
- **EU AI Act**: Regulatory requirements referenced for compliance architecture. https://eur-lex.europa.eu/
- **NIST AI Risk Management Framework**: Referenced for governance controls. https://www.nist.gov/itl/ai-risk-management-framework

---

*This file is maintained as part of Ledger SDK open source compliance. For questions about third-party usage, contact the Ledger maintainers.*
