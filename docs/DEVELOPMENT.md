# Development Guide

> **What this doc covers:** Your day-to-day workflow — how to run things, how to validate changes, how releases work, and how CI decides what gets deployed.

---

## 🚀 Quick Start (5 Minutes)

```bash
# 1. Clone
git clone https://github.com/casss20/citadel-sdk.git
cd citadel-sdk

# 2. Start PostgreSQL
docker compose up -d postgres

# 3. Install backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all,dev]"

# 4. Apply database schema
psql -h localhost -U citadel -d citadel -f db/schema.sql
for f in $(ls db/migrations/*.sql | sort); do
  psql -h localhost -U citadel -d citadel -f "$f"
done

# 5. Start the backend
uvicorn citadel.api:app --reload --host 0.0.0.0 --port 8000

# 6. In another terminal, start the dashboard
cd apps/dashboard && npm install && npm run dev
```

The backend is now at `http://localhost:8000` and the dashboard at `http://localhost:5173`.

---

## 🔧 Common Commands

### Backend

```bash
# Start with auto-reload
uvicorn citadel.api:app --reload --host 0.0.0.0 --port 8000

# Start without reload (closer to production)
uvicorn citadel.api:app --host 0.0.0.0 --port 8000

# Run with gunicorn (production)
gunicorn citadel.api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Run the demo script (no DB required)
python demo/citadel_demo.py
```

### Database

```bash
# Reset test database
psql -h localhost -U citadel -d citadel_test -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
psql -h localhost -U citadel -d citadel_test -f db/schema.sql
for f in $(ls db/migrations/*.sql | sort); do
  psql -h localhost -U citadel -d citadel_test -f "$f"
done

# Connect to database
psql -h localhost -U citadel -d citadel

# Check RLS policies
\dp+ actions
\dp+ decisions
\dp+ audit_events
```

### Testing

```bash
# Fast unit tests
CITADEL_TESTING=true pytest tests/unit/ tests/security/ tests/tokens/ -v

# Integration tests (requires PostgreSQL)
CITADEL_TESTING=true pytest tests/integration/ -v

# Regression / race condition tests
CITADEL_TESTING=true pytest tests/regression/ -v

# Simulation scripts
CITADEL_TESTING=true pytest tests/simulations/ -v

# SDK tests
cd packages/sdk-python && pytest tests/ -v

> **Note on AI security testing:** A `PromptInjectionDetector` is being added in a parallel workstream to provide dedicated detection of LLM prompt-injection attempts in action payloads. Once merged, add `pytest tests/security/test_prompt_injection.py -v` to your security validation routine. For now, prompt-injection patterns are already checked by `InputValidationMiddleware` in `apps/runtime/citadel/security/owasp_middleware.py`.

# Full test suite (what CI runs)
CITADEL_TESTING=true pytest tests/ -v --tb=short
```

### Linting & Formatting

```bash
# Format all Python code
black apps/runtime/ tests/ packages/sdk-python/

# Lint all Python code
ruff check apps/runtime/ tests/ packages/sdk-python/

# Type check
mypy apps/runtime/citadel/

# Check critical errors only (same as CI)
ruff check apps/runtime/ --select E9,F63,F7,F82
```

### Frontend

```bash
# Dashboard
cd apps/dashboard
npm install
npm run dev      # Dev server
npm run build    # Production build
npm run lint     # ESLint
npm run preview  # Preview production build

# Landing page
cd apps/landing
npm install
npm run dev
npm run build

# Dashboard demo
cd apps/dashboard-demo
npm install
npm run dev
npm run build
```

### Docker

```bash
# Build and run everything
docker compose up --build

# Build production image
docker build -t citadel-runtime .

# Run with custom env
docker run -p 8000:8000 --env-file .env citadel-runtime
```

---

## 🔄 Local Development Workflow

### Branch Naming

```
feature/description        # New feature
fix/description            # Bug fix
docs/description           # Documentation
refactor/description       # Code cleanup
chore/description          # Tooling/build
```

Example: `feat/sdk-retry-backoff`, `fix/rls-tenant-leak`

### Daily Workflow

```bash
# 1. Pull latest
git pull upstream master

# 2. Create branch
git checkout -b feature/my-change

# 3. Make changes, write tests

# 4. Run fast tests frequently
CITADEL_TESTING=true pytest tests/unit/ -v

# 5. Format and lint before committing
black apps/runtime/ tests/ packages/sdk-python/
ruff check apps/runtime/ tests/ packages/sdk-python/

# 6. Commit
git add .
git commit -m "feat(sdk): add retry with exponential backoff"

# 7. Push and open PR
git push origin feature/my-change
```

### Before Opening a PR

Run this checklist:

```bash
# 1. Lint passes
ruff check apps/runtime/ --select E9,F63,F7,F82

# 2. Unit tests pass
CITADEL_TESTING=true pytest tests/unit/ tests/security/ tests/tokens/ -v --tb=short

# 3. SDK tests pass
cd packages/sdk-python && pytest tests/ -v --tb=short

# 4. Frontend builds
cd apps/dashboard && npm run build
cd apps/landing && npm run build
cd apps/dashboard-demo && npm run build

# 5. No uncommitted changes
git status  # should be clean
```

---

## 🏭 How CI Works

Our GitHub Actions workflow (`.github/workflows/ci-cd.yml`) has 9 jobs:

### Test Jobs (run on every PR)

| Job | What it does | Approx time |
|---|---|---|
| `lint-backend` | Ruff critical checks (E9,F63,F7,F82) | ~30s |
| `test-backend` | Unit + integration tests with PostgreSQL | ~2-3 min |
| `test-sdk` | SDK unit tests | ~1 min |
| `build-frontend` | Dashboard + landing + demo builds | ~2 min |

### Deploy Jobs (run only on `master`/`main`)

| Job | What it deploys | Needs secret? |
|---|---|---|
| `deploy-api` | Backend to Fly.io | `FLY_API_TOKEN` |
| `deploy-dashboard` | Dashboard to Vercel | `VERCEL_TOKEN` |
| `deploy-landing` | Landing page to Vercel | `VERCEL_TOKEN` |
| `deploy-docs` | Docs site to Vercel | `VERCEL_TOKEN` |
| `deploy-sdk` | Python SDK to PyPI | `PYPI_API_TOKEN` |

### CI Dependencies

```
lint-backend
    ↓
test-backend ─────┬──→ deploy-api (master only)
                  │
test-sdk ─────────┼──→ deploy-sdk (master only)
                  │
build-frontend ───┼──→ deploy-dashboard (master only)
                  ├──→ deploy-landing (master only)
                  └──→ deploy-docs (master only)
```

### What Triggers CI

- **Every push** to any branch: lint + test + build
- **Every PR**: lint + test + build
- **Push to `master`/`main`**: lint + test + build + deploy

### Skipping CI

Add `[skip ci]` to your commit message to skip CI (use sparingly):
```bash
git commit -m "docs: fix typo [skip ci]"
```

---

## 📦 Release Workflow

### Versioning

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR** (`X.0.0`): Breaking API changes
- **MINOR** (`0.X.0`): New features, backward compatible
- **PATCH** (`0.0.X`): Bug fixes, backward compatible

### Release Process

Releases are currently **manual**. Here's the process:

```bash
# 1. Ensure everything is green on master
#    Check: https://github.com/casss20/citadel-sdk/actions

# 2. Update version numbers
#    - pyproject.toml (root): [project] version
#    - packages/sdk-python/pyproject.toml: [project] version
#    - apps/runtime/citadel/__init__.py: __version__

# 3. Update CHANGELOG.md
#    Add a new section at the top with the version and date

# 4. Commit version bump
git add -A
git commit -m "chore(release): bump version to 0.2.2"

# 5. Tag the release
git tag -a v0.2.2 -m "Release v0.2.2"
git push origin master --tags

# 6. CI will auto-deploy:
#    - Backend → Fly.io
#    - Dashboard → Vercel
#    - SDK → PyPI

# 7. Create GitHub Release
#    Go to: https://github.com/casss20/citadel-sdk/releases
#    Click "Draft a new release", select the tag, add release notes
```

### SDK Release Notes

When releasing the SDK, include:
- What's new
- What's fixed
- Breaking changes (if any)
- Migration guide (if needed)
- Minimum runtime version (if applicable)

---

## 🧪 Validating Changes Before PR

### Backend Changes

```bash
# Run the specific test file you're working on
CITADEL_TESTING=true pytest tests/unit/test_api_key.py -v

# Run with coverage to see what's untested
pytest tests/unit/test_api_key.py --cov=citadel.api_key_manager --cov-report=term-missing

# Check for type errors
mypy apps/runtime/citadel/api_key_manager.py

# Check for security issues
ruff check apps/runtime/citadel/api_key_manager.py --select S
```

### Frontend Changes

```bash
cd apps/dashboard

# Type check
npx tsc --noEmit

# Lint
npm run lint

# Build
npm run build

# Visual regression (manual)
npm run dev
# Open http://localhost:5173 and verify your changes
```

### SDK Changes

```bash
cd packages/sdk-python

# Run tests
pytest tests/ -v

# Check type hints
mypy citadel_governance/

# Test against local backend
export CITADEL_TEST_URL=http://localhost:8000
export CITADEL_TEST_API_KEY=test-key:admin
pytest tests/integration/ -v
```

### Database Changes

```bash
# Reset and re-apply schema
psql -h localhost -U citadel -d citadel_test -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
psql -h localhost -U citadel -d citadel_test -f db/schema.sql
for f in $(ls db/migrations/*.sql | sort); do
  psql -h localhost -U citadel -d citadel_test -f "$f"
done

# Run integration tests
CITADEL_TESTING=true pytest tests/integration/ -v
```

---

## 🐛 Common Issues & Fixes

### `ModuleNotFoundError: No module named 'citadel'`

The runtime is not installed in editable mode:
```bash
pip install -e ".[all,dev]"
```

### `asyncpg.exceptions.InvalidAuthorizationSpecificationError`

PostgreSQL user doesn't exist or password is wrong:
```bash
# Create the user
createuser -P citadel  # password: citadel
# Grant privileges
psql -c "GRANT ALL PRIVILEGES ON DATABASE citadel_test TO citadel;"
```

### `RuntimeError: CORS_ORIGINS must be configured in production`

You need to set CORS origins in `.env`:
```bash
echo "CITADEL_CORS_ORIGINS=http://localhost:5173,http://localhost:3000" >> .env
```

Or set `CITADEL_TESTING=true` for tests.

The actual error messages are:
- In production (`debug=False`): `RuntimeError: CORS_ORIGINS must be configured in production. Refusing to start without explicit origins.`
- With wildcard + credentials: `RuntimeError: CORS_ORIGINS / settings.allowed_cors_origins must be configured (comma-separated list). Refusing to start with wildcard + credentials.`

If you see the wildcard variant, ensure `CORS_ORIGINS` is not `*` when credentials (cookies / auth headers) are enabled.

### `npm run build` fails with TypeScript errors

```bash
# Clear node_modules and reinstall
cd apps/dashboard
rm -rf node_modules package-lock.json
npm install
```

### `pytest` hangs on async tests

Make sure `pytest-asyncio` is installed:
```bash
pip install pytest-asyncio
```

And `pyproject.toml` has:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

---

## 🔐 Environment Variables Reference

| Variable | Required? | Default | Purpose |
|---|---|---|---|
| `CITADEL_DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `CITADEL_JWT_SECRET` | Yes (prod) | `secret_key_change_me_in_prod` | JWT signing key |
| `CITADEL_API_KEYS` | Yes (prod) | `dev-key-for-testing:admin` | Comma-separated API keys with scopes |
| `CITADEL_CORS_ORIGINS` | Yes (prod) | — | Comma-separated allowed origins |
| `CITADEL_TESTING` | No | `false` | Disables startup validation (tests only) |
| `CITADEL_STRIPE_SECRET_KEY` | No | — | Stripe API key |
| `CITADEL_STRIPE_WEBHOOK_SECRET` | No | — | Stripe webhook signing secret |
| `CITADEL_OTEL_EXPORTER_OTLP_ENDPOINT` | No | — | OpenTelemetry OTLP endpoint |
| `CITADEL_REDIS_URL` | No | — | Redis for distributed rate limiting |
| `CITADEL_LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

See `.env.example` for a complete template.

### Redis (Optional)

Redis is **not required** for single-node development or self-hosting. Without it, the system uses in-memory fallbacks:

| Feature | With Redis | Without Redis |
|---|---|---|
| Rate limiting | Distributed token bucket across instances | In-memory token bucket (single-instance only) |
| Kill switch storage | Shared state (future) | In-memory (per-process) |
| Caching | Shared cache | In-memory dict (per-process) |

To enable Redis, start a Redis instance and set `CITADEL_REDIS_URL=redis://localhost:6379/0` in `.env`.

For Docker Compose, uncomment the `redis` service in `docker-compose.yml`.

---

## 📊 Performance Tips

### Backend

```bash
# Profile a specific test
pytest tests/unit/test_api_key.py --profile

# Benchmark with locust
locust -f scripts/locustfile.py --host http://localhost:8000

# Check for N+1 queries
# Enable SQL logging in .env:
LOG_LEVEL=DEBUG
# Then watch for repeated identical queries
```

### Frontend

```bash
# Analyze bundle size
cd apps/dashboard
npm run build
npx vite-bundle-visualizer
```

---

## 🔗 Related Docs

- [CONTRIBUTING.md](../CONTRIBUTING.md) — How to contribute
- [docs/PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) — Architecture overview
- [docs/MAINTAINER_GUIDE.md](MAINTAINER_GUIDE.md) — Maintainer processes
- [docs/ARCHITECTURE.md](ARCHITECTURE.md) — Deep-dive architecture
