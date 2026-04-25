# Changelog

All notable changes to the Citadel SDK and Runtime.

## [0.2.1] — 2026-04-26

### Fixed (Architecture Review Remediation)
- **Security**: Governor now PostgreSQL-backed (no in-memory dicts)
- **Security**: API keys are SHA-256 hashed with scoped permissions (`read`/`write`/`admin`)
- **Security**: Startup validation blocks production deploy with default secrets
- **Security**: CORS hardened — no wildcard in debug mode with credentials
- **Security**: Hardcoded bootstrap password removed; uses `secrets.token_urlsafe(16)` dev fallback
- **Database**: Alembic migrations initialized with baseline migration
- **Database**: PostgreSQL RLS policies with full tenant isolation
- **Database**: Merkle root signing for audit chain external anchoring
- **Reliability**: Dead letter queue with DB persistence
- **Reliability**: Circuit breaker state tracking (`closed`/`open`/`half-open`)
- **Reliability**: Smart subgraph input mapping (dict merge + parameter matching)
- **Code Quality**: All `print()` calls replaced with structured logging
- **Code Quality**: All TODOs implemented or removed
- **Code Quality**: Removed deprecated `datetime.utcnow()` usage
- **Tests**: 14 billing tests with `FakeBillingRepository`
- **Tests**: 20 API key manager tests
- **Tests**: 9 audit anchoring tests
- **Tests**: SDK retry logic verified working (exponential backoff)
- **CI/CD**: Blocking lint gates, proper job dependencies
- **CI/CD**: Removed `|| true` from test commands

### Added
- `AuditAnchorService` for Merkle root computation and signing
- `APIKeyService` with full CRUD (create, validate, revoke, rotate)
- `CITADEL_TESTING=true` mode for test environments
- `PRODUCTION_AUDIT.md` with full enterprise readiness review

## [0.2.0] — 2026-04-25

### Added
- Synchronous `CitadelClient` for non-async codebases
- Full test suite (43 SDK tests)
- `import citadel_governance as cg` recommended import path
- `import citadel` backward-compatible shim (deprecated)
- PyPI release: `citadel-governance`

### Changed
- All URLs migrated from `ledger-sdk.fly.dev` to `api.citadelsdk.com`
- Dashboard URL: `dashboard.citadelsdk.com`
- Repo renamed from `ledger-sdk` to `citadel-sdk`

## [0.1.0] — 2026-04-24

### Added
- Initial release of Citadel governance runtime
- FastAPI backend with PostgreSQL persistence
- Policy resolution with precedence-based matching
- Kill switches and capability tokens
- Human-in-the-loop approval queue
- Append-only audit chain with cryptographic hashing
- Stripe billing integration
- React dashboard

[0.2.1]: https://github.com/casss20/citadel-sdk/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/casss20/citadel-sdk/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/casss20/citadel-sdk/releases/tag/v0.1.0
