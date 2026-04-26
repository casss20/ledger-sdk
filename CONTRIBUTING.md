# Contributing to Citadel

Thank you for your interest in Citadel! This document will get you from zero to your first contribution — whether you're fixing a typo, adding a test, or building a new feature.

> **New to open source?** Scroll down to [Good First Contributions](#-good-first-contributions) for safe, welcoming starting points.

---

## 📋 Table of Contents

1. [Security](#security)
2. [Getting Started](#getting-started)
3. [Development Environment](#development-environment)
4. [Running Tests](#running-tests)
5. [Linting & Type Checking](#linting--type-checking)
6. [Coding Standards](#coding-standards)
7. [Commit & PR Guidelines](#commit--pr-guidelines)
8. [How to Report Bugs](#how-to-report-bugs)
9. [How to Propose Features](#how-to-propose-features)
10. [Choosing Issues to Work On](#choosing-issues-to-work-on)
11. [Good First Contributions](#-good-first-contributions)

---

## Security

Citadel is a governance SDK that enterprises and AI agents depend on. Security is not optional.

### Quick Security Rules

- **Never hardcode secrets** — passwords, API keys, JWT secrets must come from environment variables
- **Never log sensitive data** — redact `password`, `token`, `api_key`, `secret` from all logs
- **Always use parameterized queries** — never f-strings or `.format()` for SQL values
- **Validate all input** — Pydantic models, FastAPI `Query()` validators, length limits
- **Fail closed** — if enforcement logic crashes, default to `deny`, not `allow`
- **Catch specific exceptions** — `except Exception` masks security issues; be specific and re-raise

### Reporting Security Issues

**Do NOT open a public issue.**

Email: `security@citadelsdk.com` with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

See [docs/SECURITY_GUIDE.md](docs/SECURITY_GUIDE.md) for the full security development guide. See [SECURITY.md](SECURITY.md) for the project security policy.

---

## Getting Started

### 1. Fork & Clone

```bash
# Fork the repo on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/citadel-sdk.git
cd citadel-sdk

# Add upstream remote
git remote add upstream https://github.com/casss20/citadel-sdk.git
```

### 2. Understand the License Model

Citadel is a **mixed-license monorepo**. Before contributing, know which license applies to your changes:

| Directory | License | Can I contribute? |
|---|---|---|
| `packages/sdk-python/` | **Apache 2.0** | ✅ Yes — fully open source |
| `packages/sdk-typescript/` | **Apache 2.0** | ✅ Yes — fully open source |
| `packages/open-spec/` | **Apache 2.0** | ✅ Yes — fully open source |
| `apps/runtime/` | **BSL 1.1** | ✅ Yes — source-available, contributions welcome |
| `apps/dashboard/` | **BSL 1.1** | ✅ Yes — source-available, contributions welcome |
| `enterprise/` | **Proprietary** | ❌ No — not open for contribution |

> **What BSL 1.1 means:** You can read, modify, and self-host the runtime. You cannot offer it as a competing hosted service without a commercial agreement. See [LICENSING.md](LICENSING.md) for details.

### 3. Read the Architecture

Before diving into code, read these two docs:
- [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md) — what each module does
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — the three-layer design (Kernel → Framework → Intelligence)

---

## Development Environment

### Prerequisites

| Tool | Minimum Version | Check with |
|---|---|---|
| Python | 3.10 | `python3 --version` |
| Node.js | 20 | `node --version` |
| PostgreSQL | 15 | `psql --version` |
| Git | 2.30 | `git --version` |

### Backend Setup

```bash
# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install the runtime in editable mode with all extras
pip install -e ".[all,dev]"

# Copy example environment file
cp .env.example .env
# Edit .env and set your secrets (see .env.example comments)
```

### Database Setup

```bash
# Start PostgreSQL (use docker, homebrew, or your system package manager)
docker compose up -d postgres

# Create the database and apply schema
psql -h localhost -U citadel -d citadel -f db/schema.sql

# Apply migrations
for f in $(ls db/migrations/*.sql | sort); do
  echo "Applying $f"
  psql -h localhost -U citadel -d citadel -v ON_ERROR_STOP=1 -f "$f"
done
```

### Frontend Setup

```bash
# Dashboard
cd apps/dashboard
npm install
npm run dev        # http://localhost:5173

# Landing page
cd apps/landing
npm install
npm run dev        # http://localhost:5174

# Dashboard demo
cd apps/dashboard-demo
npm install
npm run dev        # http://localhost:5175
```

### SDK Setup

```bash
cd packages/sdk-python
pip install -e ".[dev]"
```

---

## Running Tests

### Quick Test Commands

```bash
# Backend unit tests (fast, no DB required)
CITADEL_TESTING=true pytest tests/unit/ tests/security/ tests/tokens/ -v

# Backend integration tests (requires PostgreSQL)
CITADEL_TESTING=true pytest tests/integration/ tests/regression/ -v

# SDK tests
cd packages/sdk-python
pytest tests/ -v

# Frontend lint
cd apps/dashboard && npm run lint
cd apps/landing && npm run lint

# Frontend build verification
cd apps/dashboard && npm run build
cd apps/landing && npm run build
```

### Full Test Suite (what CI runs)

```bash
# 1. Lint
ruff check apps/runtime/ --select E9,F63,F7,F82

# 2. Backend unit tests
CITADEL_TESTING=true pytest tests/unit/ tests/tokens/ tests/security/ tests/test_api_key_manager.py tests/test_billing.py tests/test_audit_anchoring.py -v --tb=short

# 3. Backend integration tests
CITADEL_TESTING=true pytest tests/integration/ tests/regression/ tests/simulations/ -v --tb=short

# 4. SDK tests
cd packages/sdk-python && pytest tests/ -v --tb=short

# 5. Frontend builds
cd apps/dashboard && npm ci && npm run build
cd apps/landing && npm ci && npm run build
cd apps/dashboard-demo && npm ci && npm run build
```

### Test Database Tips

If you see `asyncpg.exceptions.InvalidAuthorizationSpecificationError`, your PostgreSQL isn't configured:

```bash
# Create test DB and user
createdb citadel_test
createuser -P citadel  # password: citadel
psql -c "GRANT ALL PRIVILEGES ON DATABASE citadel_test TO citadel;"
```

---

## Linting & Type Checking

### Python

```bash
# Auto-format code
black apps/runtime/ tests/ packages/sdk-python/

# Lint (catches style issues, unused imports, etc.)
ruff check apps/runtime/ tests/ packages/sdk-python/
ruff check apps/runtime/ --select E9,F63,F7,F82  # critical errors only

# Type check (catches type errors before runtime)
mypy apps/runtime/citadel/
```

### TypeScript / Frontend

```bash
cd apps/dashboard
npm run lint          # ESLint
tsc -b --noEmit       # Type check without emitting
cd apps/landing
npm run lint
tsc -b --noEmit
```

### Pre-Commit (Optional but Recommended)

```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

---

## Coding Standards

### Python

- **Line length:** 100 characters (enforced by Black + Ruff)
- **Type hints:** Required for all public functions. Use `mypy --strict`.
- **Async:** The backend is fully async. Use `async def` for I/O-bound code.
- **Docstrings:** Google-style docstrings for all public APIs.
- **Imports:** Grouped as stdlib → third-party → local. Ruff sorts them automatically.
- **Error handling:** Never swallow exceptions. Log with structured JSON logging.

Example:
```python
async def resolve_policy(
    action: str,
    resource: str,
    tenant_id: str,
    context: Optional[dict] = None,
) -> Decision:
    """Resolve governance policy for an action.

    Args:
        action: The action being requested (e.g., "stripe.refund").
        resource: The resource being acted upon.
        tenant_id: The tenant requesting the action.
        context: Optional additional context for policy evaluation.

    Returns:
        A Decision object with status and reason.

    Raises:
        TenantNotFoundError: If the tenant does not exist.
    """
    ...
```

### TypeScript / React

- Use functional components with hooks
- Prefer explicit types over `any`
- Use `clsx` + `tailwind-merge` for conditional class names
- Follow the existing component patterns in `apps/dashboard/src/components/`

### Database Changes

If you modify the schema:
1. Update `db/schema.sql`
2. Create a new migration in `db/migrations/YYYY-MM-DD-description.sql`
3. Add/update tests for the new schema
4. Document the change in CHANGELOG.md

---

## Commit & PR Guidelines

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat` — New feature
- `fix` — Bug fix
- `docs` — Documentation only
- `style` — Formatting (no code change)
- `refactor` — Code change that neither fixes nor adds
- `perf` — Performance improvement
- `test` — Adding or fixing tests
- `chore` — Build/tooling changes

**Scopes:** `sdk`, `runtime`, `dashboard`, `landing`, `docs`, `db`, `ci`

**Examples:**
```
feat(sdk): add retry with exponential backoff
fix(runtime): handle null tenant_id in RLS context
docs: clarify tenant isolation in CONTRIBUTING
test(runtime): add race condition test for kill switch
```

### Security-Specific Checklist

- [ ] No hardcoded secrets (passwords, API keys, JWT secrets)
- [ ] No `print()` or `logging.info()` of sensitive data (passwords, tokens, API keys)
- [ ] All SQL uses parameterized queries (asyncpg `$1`, `$2` — no f-strings or `.format()`)
- [ ] Input validation on all API endpoints (Pydantic models, FastAPI `Query()` validators)
- [ ] Rate limiting on sensitive endpoints (auth, billing, admin)
- [ ] Tests cover both success and failure paths (including auth failures)
- [ ] Security tests pass (`pytest tests/security/`)
- [ ] Bandit scan passes (`bandit -r apps/runtime/citadel/`)

### Before You Submit — Final Checklist

Run this before opening every PR (it catches 90% of review rejects):

```bash
# 1. Syntax check on modified Python files
python3 -m py_compile <your_modified_file.py>

# 2. Run the specific test file you modified
CITADEL_TESTING=true pytest tests/path/to/test_file.py -v

# 3. Run lint on critical errors
ruff check apps/runtime/ --select E9,F63,F7,F82

# 4. Run security tests (if you touched auth, tokens, kernel, or security)
pytest tests/security/ -v

# 5. Run SDK tests (if you touched packages/sdk-python/)
cd packages/sdk-python && pytest tests/ -v
```

**Code review self-check:**
- [ ] `datetime.utcnow()` replaced with `datetime.now(timezone.utc)` anywhere it compares to DB timestamps
- [ ] `logger` and `asyncpg` imported in any file that references them
- [ ] `execute()` method calls match the actual class (use `run()` if no `execute()` exists, or check the shim)
- [ ] All new SQL uses parameterized queries (`$1`, `$2`) — no f-strings for values
- [ ] No `print()` or `logging.info()` of passwords, tokens, API keys
- [ ] Broad `except Exception` blocks log with `logger.exception()` and re-raise or return controlled errors
- [ ] Monorepo changes: `apps/runtime/` edits need tests in `tests/`; `packages/sdk-python/` edits need SDK tests

### Monorepo Notes

Citadel is a mixed-license monorepo. Keep your changes in the right place:

| Directory | License | Test Location |
|---|---|---|
| `apps/runtime/` | BSL 1.1 | `tests/` |
| `packages/sdk-python/` | Apache 2.0 | `packages/sdk-python/tests/` |
| `db/` | BSL 1.1 | `tests/integration/` |
| `docs/` | BSL 1.1 | n/a (manual review) |

**Rule:** If you change a runtime module, update or add a test in `tests/`. If you change the SDK, update or add a test in `packages/sdk-python/tests/`.

### Pull Request Checklist

Before opening a PR, verify:

- [ ] I have read [CONTRIBUTING.md](CONTRIBUTING.md)
- [ ] I have read [docs/SECURITY_GUIDE.md](docs/SECURITY_GUIDE.md) (for security-related changes)
- [ ] My code follows the style guidelines (Black, Ruff, MyPy)
- [ ] I have added tests for my changes
- [ ] All tests pass locally (`pytest tests/...`)
- [ ] I have run security scans (`bandit -r apps/runtime/citadel/`)
- [ ] I have updated the CHANGELOG.md (if user-facing)
- [ ] I have updated relevant documentation
- [ ] My commit messages follow Conventional Commits
- [ ] I have rebased on the latest `master`

### PR Template

When you open a PR, include:

```markdown
## What
One-line description of what changed.

## Why
Why this change is needed. Link to issue if applicable.

## How
Brief technical explanation.

## Testing
How you tested this. Commands run, edge cases considered.

## Checklist
- [ ] Tests added/updated
- [ ] Lint passes
- [ ] Type checks pass
- [ ] CHANGELOG updated (if needed)
- [ ] Documentation updated (if needed)
```

### Review Process

1. All PRs need at least **one approving review** from a maintainer
2. CI must pass (lint + tests + builds)
3. PRs that touch `apps/runtime/` **security code** need **two approvals**
4. PRs that touch `apps/runtime/citadel/security/`, `citadel/auth/`, `citadel/tokens/`, `citadel/billing/`, or `db/schema.sql` require **2 maintainer approvals**
5. We aim to review within **48 hours** on weekdays

---

## How to Report Bugs

### Before Reporting

- [ ] Search [existing issues](https://github.com/casss20/citadel-sdk/issues) first
- [ ] Check if the bug is already fixed on `master`
- [ ] Try to reproduce with the latest version

### Bug Report Template

```markdown
**Describe the bug**
A clear description of what went wrong.

**To Reproduce**
Steps to reproduce:
1. Run `...`
2. Call `...`
3. See error

**Expected behavior**
What you expected to happen.

**Environment**
- OS: [e.g., macOS 14, Ubuntu 22.04]
- Python version: [e.g., 3.12.3]
- Citadel version: [e.g., 0.2.1]
- PostgreSQL version: [e.g., 15]

**Logs / Stack Trace**
```
Paste relevant logs here
```

**Additional context**
Anything else that might help.
```

### Security Bugs

**Do not open a public issue for security vulnerabilities.**

Instead, email: `security@citadelsdk.com` with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

We will respond within 48 hours and work with you on a responsible disclosure timeline.

---

## How to Propose Features

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
A clear description of what the problem is.

**Describe the solution you'd like**
What you want to happen.

**Describe alternatives you've considered**
Other approaches you thought about.

**Additional context**
Mockups, use cases, or references.
```

### What Makes a Good Feature Request

- **Specific:** "Add webhook retries" is better than "Make webhooks better"
- **Motivated:** Explain *why* you need this, not just *what*
- **Scoped:** One feature per request. Big ideas → discussion first

---

## Choosing Issues to Work On

### Issue Labels

| Label | Meaning | Good for newcomers? |
|---|---|---|
| `good first issue` | Simple, well-defined | ✅ Yes |
| `help wanted` | Maintainer-approved, needs contributor | ✅ Yes |
| `bug` | Something is broken | ⚠️ Check complexity |
| `enhancement` | New feature | ⚠️ Discuss first |
| `refactor` | Code cleanup | ✅ Often yes |
| `documentation` | Docs improvement | ✅ Yes |
| `security` | Security-related | ❌ Needs expertise |
| `breaking change` | Changes public API | ❌ Maintainer only |

### Workflow

1. **Browse issues** at https://github.com/casss20/citadel-sdk/issues
2. **Comment on the issue** saying you'd like to work on it
3. **Wait for assignment** (prevents duplicate work)
4. **Fork, branch, implement, test**
5. **Open PR** referencing the issue: `Fixes #123`

---

## ✅ Before You Submit

Run through this checklist before opening a pull request. It catches the most common issues that slow down review.

### Quick Checklist

```bash
# 1. Compile-check every Python file you modified
python3 -m py_compile apps/runtime/citadel/your_module.py

# 2. Run the specific test file you modified
CITADEL_TESTING=true pytest tests/unit/test_your_file.py -v

# 3. Check for deprecated datetime.utcnow() in your changes
# (Use datetime.now(timezone.utc) instead — datetime.utcnow() is deprecated)
grep -n "utcnow()" apps/runtime/citadel/your_module.py

# 4. Check for missing imports (especially logger, asyncpg)
python3 -c "import apps.runtime.citadel.your_module"

# 5. Check that execute() method calls match the actual class methods
# (Signature drift is common after refactors)
```

### Common Gotchas

| Check | Why It Matters | How to Fix |
|---|---|---|
| `datetime.utcnow()` | Deprecated in Python 3.12+; behaves differently in newer runtimes | Replace with `datetime.now(timezone.utc)` |
| Missing `logger` import | Runtime crashes on first log line | `from citadel.utils.telemetry import logger` |
| Missing `asyncpg` import | Database queries fail silently in tests | Add `import asyncpg` at the top |
| `execute()` signature mismatch | Refactors change method names; callers break | Run `mypy` or grep for the method |
| No test update for runtime change | Regression risk | See Monorepo note below |

### Monorepo Test Coordination

Citadel is a monorepo. Changes in one app or package often need corresponding test updates in another:

| If you changed... | You must also update... |
|---|---|
| `apps/runtime/citadel/` (backend logic) | `tests/` — add or update tests for the modified module |
| `packages/sdk-python/citadel_governance/` (SDK) | `packages/sdk-python/tests/` — SDK tests must pass |
| `db/schema.sql` or `db/migrations/` | `tests/integration/` — DB integration tests must pass |
| `apps/runtime/citadel/api/routers/` (API routes) | `tests/security/` + `tests/integration/` — security and integration |

**Rule:** If CI fails because of a missing test update in another package, the PR is blocked regardless of how small the change is.

---

## 🌱 Good First Contributions

> **Never contributed to open source before?** Start here. These are safe, valuable, and we'll help you through the process.

### Documentation (Zero Code)

- Fix typos in README, docs, or docstrings
- Add missing docstring examples
- Improve error message clarity
- Add a recipe to `docs/public/recipes/`

**Why start here:** You learn the PR workflow without risking production code.

### Tests (Low Risk)

- Add a test for an uncovered edge case
- Add integration test for a documented recipe
- Add a simulation script for a new scenario

**Why start here:** You learn the codebase structure while adding value.

### SDK Improvements (Well-Scoped)

- Add a new convenience method to the SDK
- Improve error messages in the SDK
- Add type stubs or better type hints

**Why start here:** The SDK is Apache 2.0 and has a smaller surface area than the runtime.

### Refactoring (Code Quality)

- Extract duplicated code into a shared utility
- Rename unclear variable names
- Add missing type hints to internal functions

**Why start here:** Low risk, high learning value.

### What NOT to Start With

- ❌ Changes to `apps/runtime/` security code (needs deep review)
- ❌ Database schema changes (affects all tenants)
- ❌ Breaking API changes (needs RFC process)
- ❌ Changes to `enterprise/` (proprietary, not open)

---

## Getting Help

- **Discord:** https://discord.gg/clawd (community chat)
- **GitHub Discussions:** For questions, ideas, and show-and-tell
- **GitHub Issues:** For bugs and feature requests
- **Email:** `hello@citadelsdk.com` for private inquiries

---

## Code of Conduct

We follow the [Contributor Covenant](https://www.contributor-covenant.org/) Code of Conduct. Be respectful, be patient, and assume good intent. Harassment or discrimination of any kind is not tolerated.

---

Thank you for contributing to Citadel! 🛡️
