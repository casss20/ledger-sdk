# Changelog

## Unreleased

### Added

- Added decision-first runtime governance metadata so sensitive actions persist a durable governance decision before a `gt_cap_` capability token is issued.
- Added short-lived scoped `gt_cap_` token metadata for `decision_id`, issuer, subject, audience, workspace, tool, action, resource scope, risk level, not-before, expiry, trace, and approval reference.
- Added RFC 7662-style introspection endpoints: `POST /v1/introspect` and `POST /v1/governance/introspect`.
- Added `GET /v1/governance/traceability` for dashboard-ready policy-to-execution lineage graphs.
- Added live dashboard traceability wiring with a reference fallback when no governance decisions exist yet.
- Added kill-switch-aware introspection so central emergency state returns `active: false` for affected runtime scopes.
- Added migration `010_decision_first_introspection.sql` for token/decision linkage, revocation fields, indexes, and active-token uniqueness per decision.
- Added tests for decision-before-token issuance, valid introspection, expired/revoked tokens, kill-switch blocking, scope mismatches, workspace mismatch, and audit linkage through `decision_id`.

### Changed

- `gt_cap_` tokens are now documented as short-lived execution proof linked to a durable decision record, not the source of governance authority.
- Runtime verification now reports `kill_switch_active` for token checks blocked by central emergency state.
