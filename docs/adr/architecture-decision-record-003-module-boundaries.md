# ADR-003: Module Boundaries and Package Layout

## Status
Accepted

## Context

Citadel is a monorepo containing multiple distinct components: SDKs in multiple languages, a governance runtime, web dashboards, and enterprise extensions. We needed a directory structure that:

- Makes license boundaries explicit (Apache 2.0 vs BSL vs proprietary)
- Allows independent versioning and release cycles
- Prevents accidental coupling between SDK and runtime internals
- Supports future expansion (new language SDKs, new runtime implementations)
- Works with standard tooling (pip, npm, PyPI, Docker, etc.)

## Options Considered

### Option A: Single Package (Flat Structure)

Everything in one Python package: `citadel`.

```
citadel/
├── __init__.py
├── client.py          # SDK
├── runtime/
│   ├── kernel.py      # Runtime internals
│   └── ...
├── dashboard/
│   └── ...
└── enterprise/
    └── ...
```

**Pros:**
- Simplest structure
- Single `pip install citadel`
- No cross-package import issues

**Cons:**
- Cannot release SDK independently from runtime
- Users who only want the SDK get the runtime code too (license confusion)
- Cannot have TypeScript SDK in same package
- Dashboard and runtime code bloat the SDK distribution
- Violates separation of concerns

### Option B: Separate Repositories

One repo per component:

```
citadel-sdk-python/
citadel-sdk-typescript/
citadel-runtime/
citadel-dashboard/
```

**Pros:**
- Cleanest separation
- Independent CI/CD, versioning, and release cycles
- No risk of leaking runtime internals into SDK

**Cons:**
- Cross-repo changes are painful (e.g., API change requires PRs in 3 repos)
- Harder to keep docs, issues, and milestones synchronized
- Onboarding requires cloning multiple repos
- Shared utilities (schemas, test fixtures) must be published as separate packages
- Lose atomic commits for cross-component features

### Option C: Monorepo with Clear Directory Boundaries (Chosen)

Single repository with top-level separation by component type:

```
citadel-sdk/
├── packages/              # Open-source SDKs and specs
│   ├── sdk-python/        # Apache 2.0
│   ├── sdk-typescript/    # Apache 2.0
│   └── open-spec/         # Apache 2.0
├── apps/                  # Source-available applications
│   ├── runtime/           # BSL 1.1
│   ├── dashboard/         # BSL 1.1
│   ├── dashboard-demo/    # BSL 1.1
│   └── landing/           # BSL 1.1
├── enterprise/            # Proprietary
│   └── ...
├── docs/                  # Apache 2.0 (root-level)
├── tests/                 # Cross-component integration tests
└── scripts/               # Build, deploy, and utility scripts
```

**Pros:**
- Atomic commits across components (e.g., API change + SDK update + test in one PR)
- Single source of truth for schemas, docs, and shared fixtures
- License boundaries are directory boundaries — impossible to miss
- Independent versioning per package (`packages/sdk-python` has its own `pyproject.toml`)
- Standard tooling works (each `pyproject.toml` / `package.json` is self-contained)
- Easy to add new language SDKs (`packages/sdk-go/`, `packages/sdk-rust/`)

**Cons:**
- Repo is larger (but `.git` handles this fine; users clone only what they need)
- CI must be smart about testing only changed components
- Need discipline to not import across license boundaries

### Option D: Monorepo with Workspace Tooling (nx, pnpm, pants)

Same as Option C but with heavy monorepo tooling for dependency graphs, incremental builds, and code generation.

**Pros:**
- Optimal CI (test only what changed)
- Shared build logic
- Code generation from schemas

**Cons:**
- Adds significant tooling complexity
- Steep learning curve for contributors
- Overkill for current team size (<10 engineers)
- Python monorepo tooling is immature compared to JS

## Chosen Option

**Option C: Monorepo with Clear Directory Boundaries**

We use a single repository with `packages/`, `apps/`, and `enterprise/` as top-level separators. Each component has its own build configuration (`pyproject.toml`, `package.json`, `Dockerfile`) and can be released independently.

### Rationale

1. **Velocity over scale.** At our current size, cross-repo overhead hurts more than monorepo size. We need to ship fast.
2. **License clarity is non-negotiable.** The `packages/` vs `apps/` split makes the open-source / source-available boundary physically obvious.
3. **Future-proof.** Adding `packages/sdk-go/` requires zero structural changes.
4. **Tooling simplicity.** Standard `pip`, `npm`, and `docker` work out of the box. No custom build systems.
5. **Contributor-friendly.** A single `git clone` gets you everything. One PR can update SDK, runtime, and tests together.

## Consequences

### Positive

- New language SDKs can be added without restructuring
- SDK releases are decoupled from runtime deployments
- License boundaries are enforced by directory structure (and CI checks)
- Shared schemas and test fixtures live in one place
- Contributors can see the full system in one repo

### Negative

- CI must implement path-based filtering to avoid testing unchanged components
- Repo size grows over time (mitigated by shallow clones and `.gitignore`)
- Risk of cross-boundary imports if not watched (mitigated by CI linting)
- Docker builds must be careful about build context size

### Mitigations

- **CI path filters:** GitHub Actions workflows trigger only when relevant paths change
- **Import linting:** Custom lint rule prevents `packages/sdk-python` from importing `apps/runtime`
- **CODEOWNERS:** Different teams own different directories
- **Documentation:** `PROJECT_STRUCTURE.md` explains the layout for new contributors

## Related Decisions

- ADR-004: SDK vs Runtime Split (enforced by `packages/` vs `apps/`)
- License model: `LICENSING.md` defines directory-level license rules

## Date
2026-04-05

## Authors
Anthony Cass, Citadel SDK Team
