# Production-Readiness Audit — Citadel SDK

**Auditor:** thonybot (enterprise reviewer mode)
**Repo:** casss20/citadel-sdk @ master (314f31b)
**Scope:** Full codebase — structure, dependencies, API surface, naming, tests, CI, release artifacts

---

## 🔴 CRITICAL (Block production)

### C1. No LICENSE file at repo root
**Severity:** 🔴 CRITICAL  
**Location:** Root directory  
**Issue:** `pyproject.toml` declares `license = {text = "MIT"}` for both root and SDK packages, but no `LICENSE` or `LICENSE-MIT` file exists at the repo root. The SDK package `pyproject.toml` references `"/LICENSE"` in its `[tool.hatch.build.targets.sdist]` include list, but the file is missing. This is a legal blocker for any downstream consumer — PyPI will reject or flag the package, and enterprise legal teams will refuse adoption.  
**Fix:** Add a `LICENSE` file with MIT text. Verify the `packages/sdk-python/LICENSE` symlink or copy is valid.

### C2. Root `pyproject.toml` has wrong package name
**Severity:** 🔴 CRITICAL  
**Location:** `./pyproject.toml` line 6  
**Issue:** Root project is named `citadel-sdk` (0.1.0) but the actual Python package inside is `citadel` (the runtime). Meanwhile, the published SDK on PyPI is `citadel-governance` (0.2.1) from `packages/sdk-python/`. This creates a naming collision risk and confusion about what `pip install citadel-sdk` vs `pip install citadel-governance` means.  
**Fix:** Rename root project to `citadel-runtime` or similar. Clarify in README that `pip install citadel-governance` is the client SDK and `citadel-sdk` (or better, `citadel-runtime`) is the backend.

### C3. `docker-compose.yml` ships with hardcoded production API keys
**Severity:** 🔴 CRITICAL  
**Location:** `./docker-compose.yml:28`  
**Issue:** `API_KEYS: prod-key-change-me-now,dev-key-for-testing` is a credential leak in version control. Even with comments saying "change me," this will be copy-pasted by users and deployed. The `prod-key-change-me-now` key is also referenced nowhere in docs as a default, making it a silent security trap.  
**Fix:** Remove the `API_KEYS` line entirely and rely on `.env` file. Add `.env` to `.dockerignore`. Document that operators must set `API_KEYS` via environment.

### C4. `__pycache__` and `*.pyc` files committed to repo
**Severity:** 🔴 CRITICAL  
**Location:** 442 `__pycache__` directories, 4,172 `.pyc` files  
**Issue:** These are build artifacts that bloat the repo, cause merge conflicts, and can leak local file paths or system details. The `.gitignore` exists but wasn't respected historically.  
**Fix:** `git rm -rf $(find . -name "__pycache__" -type d)` and commit. Ensure `.gitignore` covers `__pycache__/`, `*.pyc`, `*.pyo`.

### C5. `fly.toml` CORS origins include a stale/dead Vercel URL
**Severity:** 🔴 CRITICAL  
**Location:** `./fly.toml:18`  
**Issue:** `CORS_ORIGINS = 'https://dashboard-qfx06pd4e-casss20s-projects.vercel.app,...'` includes a Vercel preview URL tied to the old `ledger-sdk` project name. This URL is likely dead or controlled by someone else. If an attacker registers that Vercel project, they can make authenticated cross-origin requests to the production API.  
**Fix:** Remove the stale Vercel URL immediately. Only keep `https://citadelsdk.com` and `https://dashboard.citadelsdk.com`.

---

## 🟡 HIGH (Fix before v1.0)

### H1. SDK and backend package names collide on import
**Severity:** 🟡 HIGH  
**Location:** `apps/runtime/citadel/` vs `packages/sdk-python/citadel/`  
**Issue:** Both the backend runtime and the SDK shim install a top-level `citadel` package. If a user installs both `citadel-governance` (which includes the `citadel` shim) and the backend runtime in the same environment, the second install overwrites the first. This is exactly why the deprecation warning exists, but the root cause (namespace collision) is still present.  
**Fix:** Rename the backend package from `citadel` to `citadel_runtime` or `citadel_server`. Keep `citadel` as a pure SDK namespace.

### H2. Root `pyproject.toml` version (0.1.0) doesn't match SDK (0.2.1)
**Severity:** 🟡 HIGH  
**Location:** `./pyproject.toml:7` vs `packages/sdk-python/pyproject.toml:7`  
**Issue:** The root project says 0.1.0, the SDK says 0.2.1. They should either be independently versioned (with clear separation) or kept in sync via a monorepo version bump tool. Currently it's unclear if the backend is 0.1.0 or 0.2.1.  
**Fix:** Use a single source of truth for versions (e.g., `bump2version` or `hatch-vcs`). Or clearly document that `apps/runtime/` and `packages/sdk-python/` are independently versioned.

### H3. SDK README example uses `api_key="dev-key-for-testing"`
**Severity:** 🟡 HIGH  
**Location:** `./README.md:73` and `./packages/sdk-python/README.md`  
**Issue:** The quickstart example shows `api_key="dev-key-for-testing"` which is a default credential. Users will copy-paste this into production code. The README is the first thing people see — it should show a placeholder like `"YOUR_API_KEY_HERE"`.  
**Fix:** Change example to `api_key="YOUR_API_KEY_HERE"` with a comment above it: `# Get your API key from dashboard.citadelsdk.com/settings`.

### H4. `packages/sdk-python/tests/integration/conftest.py` references dead URL
**Severity:** 🟡 HIGH  
**Location:** `packages/sdk-python/tests/integration/conftest.py:6`  
**Issue:** Contains `export CITADEL_TEST_URL=https://ledger-sdk.fly.dev` — a dead URL. Integration tests run against a ghost endpoint.  
**Fix:** Update to `https://api.citadelsdk.com` or add a `pytest.skip()` guard if no test server is available.

### H5. `ARCHITECTURE_REVIEW.md` still has old URLs
**Severity:** 🟡 HIGH  
**Location:** `./ARCHITECTURE_REVIEW.md:250, 275, 276, 462`  
**Issue:** This document references `https://ledger-sdk.fly.dev` and `casss20-ledger-sdk-6nlu.vercel.app` in its findings. Since this is an internal architecture review, having stale references makes it unreliable for future audits.  
**Fix:** Run a find-and-replace on the entire file, or add a header: "Historical document — URLs were fixed in PR #9."  
**Note:** `WIRING_AUDIT.md` has the same issue but is explicitly labeled as a historical audit.

### H6. Backend `pyproject.toml` includes SDK dependencies in `[project.dependencies]`
**Severity:** 🟡 HIGH  
**Location:** `./pyproject.toml:29-50`  
**Issue:** The root/backend `pyproject.toml` declares `opentelemetry-api>=1.20.0`, `opentelemetry-sdk>=1.20.0`, `opentelemetry-instrumentation-fastapi>=0.41b0`, and `opentelemetry-exporter-otlp>=1.20.0` as core dependencies. But `telemetry.py` already handles graceful degradation when OTel is missing. These should be optional extras, not required — they bloat the install for users who just want the local runtime.  
**Fix:** Move OTel packages to `[project.optional-dependencies]` (e.g., `otel = [...]`).

### H7. Backend `pyproject.toml` `[tool.hatch.build.targets.wheel]` points to wrong package
**Severity:** 🟡 HIGH  
**Location:** `./pyproject.toml:78`  
**Issue:** `packages = ["apps/runtime/citadel"]` means `pip install -e .` installs the `citadel` package from the runtime directory. But the runtime is not meant to be installed as a library — it's a server application. The wheel target should either be removed or pointed at a server entrypoint, not a library package.  
**Fix:** Remove `[tool.hatch.build.targets.wheel]` or change it to build a `citadel-runtime` CLI tool, not a library.

### H8. No `requirements.txt` or lockfile for the backend
**Severity:** 🟡 HIGH  
**Location:** Root directory  
**Issue:** There's no `requirements.txt`, `requirements-dev.txt`, or `poetry.lock` / `pipenv.lock` for reproducible installs. The `pyproject.toml` uses loose version bounds (`>=`) which means two installs on different days can pull different dependency versions. This is a supply-chain risk.  
**Fix:** Generate a `requirements.txt` with pinned hashes (`pip-compile` or `poetry export`). Commit it. Update it on dependency changes.

### H9. SDK `pyproject.toml` includes `[tool.hatch.build.targets.wheel].packages = ["citadel_governance", "citadel"]`
**Severity:** 🟡 HIGH  
**Location:** `packages/sdk-python/pyproject.toml:65`  
**Issue:** The wheel builds two top-level packages: `citadel_governance` (the main SDK) and `citadel` (the legacy shim). The `citadel` shim shadows any other `citadel` package installed in the same environment. This is the root cause of H1.  
**Fix:** Remove `"citadel"` from the wheel packages. The shim should be a single file or a subpackage, not a top-level namespace.

---

## 🟠 MEDIUM (Clean up before broad adoption)

### M1. `MANIFEST.in` is nearly empty
**Severity:** 🟠 MEDIUM  
**Location:** `./MANIFEST.in`  
**Issue:** Only contains `include README.md`. The source distribution won't include `LICENSE` (already missing — see C1), `CHANGELOG.md`, or other docs. PyPI page will be sparse.  
**Fix:** Add `include LICENSE`, `include CHANGELOG.md`, `recursive-include docs *.md`.

### M2. `CHANGELOG.md` is a stub
**Severity:** 🟠 MEDIUM  
**Location:** `./CHANGELOG.md`  
**Issue:** Only says "Keep a changelog." No actual version history. For a project with this much churn, the changelog is a trust signal for users evaluating stability.  
**Fix:** Populate with at least the 0.2.0 and 0.2.1 releases, listing the major changes from this audit session.

### M3. `final_test_count.txt` (238 KB) committed to repo root
**Severity:** 🟠 MEDIUM  
**Location:** `./final_test_count.txt`  
**Issue:** This appears to be a generated artifact (probably `pytest --collect-only` output). It's 238 KB of noise in the repo.  
**Fix:** Delete and add to `.gitignore`.

### M4. `demo/` directory has no clear purpose
**Severity:** 🟠 MEDIUM  
**Location:** `./demo/`  
**Issue:** Contains a `README.md` with setup instructions but no actual demo code. It's referenced in `Dockerfile` (`COPY demo/ ./demo/`) which bloats the container with an empty directory.  
**Fix:** Either populate with a real demo or remove from the repo and Dockerfile.

### M5. `research/` directory contains experimental code in production repo
**Severity:** 🟠 MEDIUM  
**Location:** `./research/`  
**Issue:** Experimental notebooks, scratch scripts, and alignment prototypes are in the same repo as production code. They reference old project names (`ledger_sdk`) and have no tests. This bloats the repo and confuses contributors.  
**Fix:** Move to a separate `casss20/citadel-research` repo, or at minimum add a `README.md` stating "Not production code — do not import."

### M6. `experimental/` directory duplicates governance code
**Severity:** 🟠 MEDIUM  
**Location:** `./experimental/`  
**Issue:** Contains another copy of governance runtime code (`experimental/agent_runtime/governance/`). This is a maintenance hazard — fixes in `apps/runtime/` won't propagate here.  
**Fix:** Delete or archive. If it's needed for reference, move to `research/` or a gist.

### M7. `templates/` directory has unknown purpose
**Severity:** 🟠 MEDIUM  
**Location:** `./templates/`  
**Issue:** Contains HTML templates (`base.html`, `index.html`) but the backend is a FastAPI JSON API, not a server-rendered app. These templates appear unused.  
**Fix:** Verify usage. If unused, delete.

### M8. `src/` directory at root duplicates package structure
**Severity:** 🟠 MEDIUM  
**Location:** `./src/`  
**Issue:** Contains `src/citadel/` which appears to be an older or alternate layout of the runtime. If this is the actual source of truth, then `apps/runtime/` is a duplicate. If it's stale, it's dead code.  
**Fix:** Determine which is canonical. Delete the other. Having two `citadel` packages at different paths is a recipe for import confusion.

### M9. `apps/dashboard/vite.config.ts` proxies to `http://127.0.0.1:8000`
**Severity:** 🟠 MEDIUM  
**Location:** `apps/dashboard/vite.config.ts:26-35`  
**Issue:** The Vite dev server proxies `/api`, `/v1`, and `/auth` to `localhost:8000`. This is fine for local dev but the config doesn't document that this only works when the backend is running locally. The `__API_URL__` define uses an empty string in dev mode, which assumes same-origin — but if the frontend is served from Vite's dev server (port 5173), the proxy handles it. This is fragile and undocumented.  
**Fix:** Add a comment in the config explaining the proxy setup. Consider adding a `.env.local.example` file.

### M10. `fly.toml` has duplicate `memory` key
**Severity:** 🟠 MEDIUM  
**Location:** `./fly.toml:44-45`  
**Issue:** `memory = '512mb'` and `memory_mb = 256` are both present. Fly.io may ignore one or throw an error.  
**Fix:** Remove the duplicate. Use `memory_mb = 512` for consistency.

### M11. No health check endpoint in CI verification
**Severity:** 🟠 MEDIUM  
**Location:** `.github/workflows/ci-cd.yml:deploy-api`  
**Issue:** The deploy step runs `curl -sf https://api.citadelsdk.com/v1/health/live` but this is AFTER Fly.io deploy. If the deploy fails, the health check gives a misleading error. There should be a pre-deploy health check on the existing instance, then a post-deploy smoke test.  
**Fix:** Add a `pre-deploy` health check and a `post-deploy` smoke test that validates at least one write operation.

### M12. CI `test-backend` runs ALL tests including DB-dependent ones
**Severity:** 🟠 MEDIUM  
**Location:** `.github/workflows/ci-cd.yml:82`  
**Issue:** `pytest tests/` runs integration, regression, simulation, and dashboard tests that all require a live database. Some of these tests (e.g., `test_rls_enforcement.py`, `test_tenant_isolation.py`) are heavy and may have race conditions in CI. The job should be split: unit tests (fast, no DB), integration tests (slower, with DB), and simulations (longest, nightly).  
**Fix:** Split into `pytest tests/unit tests/tokens tests/security -m "not integration"` for the fast path, and a separate `test-integration` job for DB tests.

### M13. `db/00-init-test-db.sql` is used by both CI and docker-compose
**Severity:** 🟠 MEDIUM  
**Location:** `./db/00-init-test-db.sql`  
**Issue:** This script does `CREATE DATABASE citadel_test; GRANT ALL PRIVILEGES...`. In docker-compose, the database is already created by the `POSTGRES_DB` env var, so this script is redundant. In CI, the GitHub Actions postgres service also auto-creates the DB. The script is only needed for manual local setup.  
**Fix:** Remove from docker-compose and CI. Document it in `db/README.md` for local dev only.

### M14. `.env.example` is a stub
**Severity:** 🟠 MEDIUM  
**Location:** `./.env.example`  
**Issue:** Only contains `LOG_LEVEL=DEBUG`. It should show all required environment variables with placeholder values and comments.  
**Fix:** Add `DATABASE_URL`, `API_KEYS`, `CITADEL_JWT_SECRET`, `STRIPE_SECRET_KEY`, etc. with `# CHANGE ME` comments.

---

## 🟢 LOW (Polish)

### L1. `setup.py` is a stub that delegates to `pyproject.toml`
**Severity:** 🟢 LOW  
**Location:** `./setup.py`  
**Issue:** It's fine to have a stub `setup.py` for backward compatibility with `pip install -e .` on old pip versions, but it's unnecessary for pip 21+. If kept, add a comment explaining why it exists.  
**Fix:** Optional. Add `#!/usr/bin/env python` and a docstring.

### L2. `JOURNAL.md` is a personal dev log
**Severity:** 🟢 LOW  
**Location:** `./JOURNAL.md`  
**Issue:** Contains stream-of-consciousness development notes. It's fine for a solo project but should be in `.github/` or `docs/private/` if it contains context that isn't useful to external contributors.  
**Fix:** Move to `docs/private/` or keep but add a header: "Personal development journal — not documentation."

### L3. `SCHEDULER.md` describes a non-existent scheduler
**Severity:** 🟢 LOW  
**Location:** `./SCHEDULER.md`  
**Issue:** Describes a cron-like scheduler for governance tasks, but no scheduler code exists in the repo. This is aspirational documentation that will mislead users.  
**Fix:** Add a "Not yet implemented" banner at the top, or move to `docs/roadmap/`.

### L4. `SECURITY_HARDENING_2026-04-24.md` is a duplicate of audit findings
**Severity:** 🟢 LOW  
**Location:** `./SECURITY_HARDENING_2026-04-24.md`  
**Issue:** This appears to be an earlier version of the hardening findings. It duplicates content now in `ARCHITECTURE_REVIEW.md`.  
**Fix:** Delete or consolidate into `ARCHITECTURE_REVIEW.md`.

### L5. `docs/public/` has no build tooling
**Severity:** 🟢 LOW  
**Location:** `./docs/public/`  
**Issue:** The docs site is referenced in CI for Vercel deployment, but there's no `package.json`, `next.config.js`, or static site generator config in `docs/`. The CI job tries to deploy `docs/public/` but that directory may be empty or manually maintained.  
**Fix:** Add a static site generator (MkDocs, VitePress, or plain HTML) with a build step in CI.

### L6. `vercel.json` references `docs/public` but no build output
**Severity:** 🟢 LOW  
**Location:** `./vercel.json`  
**Issue:** The Vercel config points at `docs/public` as the static root, but there's no build process that populates it from the Markdown docs.  
**Fix:** Either add a build step or remove the Vercel deploy job from CI.

### L7. `apps/dashboard-demo/` duplicates `apps/dashboard/`
**Severity:** 🟢 LOW  
**Location:** `./apps/dashboard-demo/`  
**Issue:** It's a standalone demo app, which is a valid use case. But it shares 99% of the code with `apps/dashboard/`. The demo could be a build flag or environment variable on the main dashboard instead of a full copy.  
**Fix:** Optional. If the duplication is intentional, add a `README.md` explaining the difference.

---

## 📊 Summary Table

| Severity | Count | Issues |
|---|---|---|
| 🔴 CRITICAL | 5 | C1–C5 |
| 🟡 HIGH | 9 | H1–H9 |
| 🟠 MEDIUM | 14 | M1–M14 |
| 🟢 LOW | 7 | L1–L7 |
| **Total** | **35** | |

---

## Top 5 Immediate Actions

1. **Add LICENSE file** (C1) — Legal blocker, 2 minutes.
2. **Purge `__pycache__` and `*.pyc`** (C4) — Repo hygiene, 2 minutes.
3. **Fix `fly.toml` CORS** (C5) — Security, 1 minute.
4. **Remove hardcoded API keys from docker-compose** (C3) — Security, 2 minutes.
5. **Clarify package naming** (C2 + H1 + H2) — User confusion, 30 minutes.

---

## Architecture Verdict

**The hard parts are genuinely well-done.** The schema design, RLS policies, audit chain, token system, and governance kernel are production-grade concepts with solid implementation. The security posture (OWASP middleware, secret validation, kill switches) is better than most early-stage projects.

**But the packaging, repo hygiene, and documentation are not enterprise-ready.** The repo has accumulated artifacts (`__pycache__`, `final_test_count.txt`, `research/`, `experimental/`, `src/`, `templates/`) that create confusion about what is canonical. The lack of a `LICENSE` file and pinned requirements are blockers for any corporate legal or SRE review.

**Recommendation:** Treat this as a "cleaning sprint" before announcing v1.0. The architecture is sound; the repository organization needs to match it.
