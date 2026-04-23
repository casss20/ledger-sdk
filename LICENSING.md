# Licensing

Ledger uses a mixed-license model to balance broad ecosystem adoption with commercial sustainability.

This repository contains components under different license terms. You should assume that **license terms are defined at the package or application level** unless explicitly stated otherwise.

## Open-source components

The following components are licensed under the **Apache License 2.0**:

- `packages/sdk-python`
- `packages/sdk-typescript`
- `packages/open-spec`

These components are open source under an OSI-approved license and are intended for broad adoption, integration, and contribution. They provide the "public interface" to the Ledger ecosystem.

## Source-available components

The following component is licensed under a **Business Source License 1.1** (BSL):

- `apps/runtime`

This component is publicly visible and source-available, but it is **not open source in the OSI sense**. Internal use, evaluation, modification, and self-hosting are permitted. However, offering the runtime as a competing hosted or managed service is not permitted except under a separate commercial agreement.

## Proprietary components

The following components are proprietary unless stated otherwise:

- `enterprise/*`
- Any private cloud-only or enterprise-only modules not explicitly released under an open-source or source-available license.

These components are not licensed for public use, redistribution, or commercial hosting unless covered by a separate written agreement.

## Documentation and examples

Documentation (in `docs/`), examples, and snippets are licensed according to the license file in their directory. If no more specific file is present, refer to the nearest applicable directory-level license notice.

## Historical note

Some earlier Ledger code may have been released under MIT. Those earlier releases remain available under the terms under which they were originally published. Newer releases use the structured licensing model defined above.

## Questions

For commercial use, OEM embedding, managed-service rights, or enterprise licensing questions, contact: `licensing@ledger.example`
