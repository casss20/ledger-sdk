# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for the Citadel SDK project.

## What is an ADR?

An Architecture Decision Record (ADR) captures an important architectural decision made along with its context and consequences. ADRs help current and future team members understand *why* the system is built the way it is.

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [architecture-decision-record-001](architecture-decision-record-001-async-first-client.md) | Async-First Client Design | Accepted | 2026-04-15 |
| [architecture-decision-record-002](architecture-decision-record-002-runtime-governance.md) | Runtime Governance Enforcement | Accepted | 2026-04-10 |
| [architecture-decision-record-003](architecture-decision-record-003-module-boundaries.md) | Module Boundaries and Package Layout | Accepted | 2026-04-05 |
| [architecture-decision-record-004](architecture-decision-record-004-sdk-runtime-split.md) | SDK vs Internal Runtime Split | Accepted | 2026-04-12 |

## How to Add a New ADR

1. Copy the template from an existing ADR
2. Use the next sequential number
3. Include: Status, Context, Options Considered, Chosen Option, Consequences, Related Decisions, Date, Authors
4. Update this index
5. Submit a PR

## Status Definitions

- **Proposed:** Under discussion, not yet decided
- **Accepted:** Decision made, being implemented
- **Deprecated:** Decision was valid but is no longer relevant
- **Superseded:** Replaced by a newer ADR (link to replacement)
