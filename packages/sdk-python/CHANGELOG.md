# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] – 2026-04-26

### Added
- Full API surface coverage: actions, approvals, agent identities, agents, policies, kill switches, dashboard, audit, trust scores, capabilities
- `CitadelClient` class with async context-manager support
- **Synchronous client** (`citadel_governance.sync.CitadelClient`) — wraps async client for sync usage
- `@client.guard()` and `@client.wrap()` decorators for wrapping functions with governance (both sync and async)
- Module-level convenience API (`import citadel_governance as cg; cg.configure(...); cg.execute(...)`)
- `decide()` method for dry-run policy evaluation without executing actions
- Retry logic with exponential backoff + jitter on 429 and 5xx errors
- Respects `Retry-After` header for rate-limit retries
- Configurable `max_retries` (default 3)
- Connection customization: `timeout`, `proxies`, `limits`, `event_hooks`
- Expanded exception hierarchy: `AuthenticationError`, `RateLimitError`, `ValidationError`, `ServerError`
- `py.typed` marker for PEP 561 type-checking support
- Full test suite (43 tests) with `respx` HTTP mocking + integration test scaffolding
- Backward-compatible `import citadel` shim with `DeprecationWarning`

### Changed
- Package import path renamed from `citadel` → `citadel_governance` (avoids namespace collision with backend)
- Python requirement bumped from `>=3.9` to `>=3.10`
- `requires-python` now `>=3.10` to match `|` union syntax usage
- Models made flexible with sensible defaults (`Approval`, `Agent`, `Policy`)

### Fixed
- Namespace collision between SDK (`citadel`) and backend runtime (`citadel`) in monorepo
- `README.md` install instructions now show correct `pip install citadel-governance`
- PyPI version sync (`0.1.0` → `0.2.0`)

## [0.1.0] – 2024-11-24

### Added
- Initial skeleton release with basic `CitadelClient`
- `execute()`, `approve()`, `reject()` methods
- Minimal `CitadelResult`, `Approval`, `AgentIdentity` models
