# Citadel Cross-System Wiring Audit

Audit date: 2026-04-25

## URL Inventory

| System | What it points to | Current Value | Status |
|--------|------------------|---------------|--------|
| **SDK README** `base_url` | Backend API | `https://ledger-sdk.fly.dev` | ⚠️ OLD branding |
| **Dashboard API client** | Backend API | `https://api.citadelsdk.com/v1` | ✅ NEW branding |
| **Dashboard vite config** | Backend API | `https://ledger-sdk.fly.dev` | ⚠️ OLD branding |
| **Landing page code** | Backend API | `https://api.citadelsdk.com` | ✅ NEW branding |
| **SDK README** Dashboard | Dashboard app | `https://casss20-ledger-sdk-6nlu.vercel.app` | ❌ 404 |
| **Landing page** Dashboard | Dashboard app | `/demo/` (relative) | ⚠️ Assumes same domain |
| **Landing page** Docs | Docs site | `https://citadelsdk.com/docs` | ⚠️ Unverified |
| **Landing page** GitHub | Repo | `https://github.com/casss20/ledger-sdk` | ❌ Repo renamed |
| **Landing page** PyPI | Package | `https://pypi.org/project/citadel-governance/` | ✅ Correct |
| **SDK README** PyPI | Package | Not linked | ⚠️ Missing |
| **Backend CORS** | Allowed origins | `*.vercel.app`, `citadelsdk.com` | ✅ Correct |

## Mismatches Found

### 1. API Base URL: Two brands in production

**Problem:** The backend is referenced by both the old `ledger-sdk.fly.dev` and new `api.citadelsdk.com` domains.

- SDK README + client default: `https://ledger-sdk.fly.dev`
- Dashboard vite config: `https://ledger-sdk.fly.dev`
- Dashboard API client: `https://api.citadelsdk.com/v1`
- Landing page example: `https://api.citadelsdk.com`

**Impact:** Users copying from SDK README hit a different domain than the dashboard.

### 2. Dashboard URL: 404

**Problem:** `https://casss20-ledger-sdk-6nlu.vercel.app` returns 404.

**Impact:** SDK README links to a dead dashboard. Landing page links to `/demo/` which only works if landing + dashboard are co-deployed.

### 3. GitHub Repo URL: Stale

**Problem:** Landing page footer links to `https://github.com/casss20/ledger-sdk` but repo was renamed to `citadel-sdk`.

**Impact:** Link redirect works but should use canonical URL.

### 4. Landing Page Code Example: Deprecated Import

**Problem:** The "See it in action" code window uses `import citadel` which is deprecated.

**Impact:** New users copy-paste deprecated code.

### 5. SDK README: Missing Links

**Problem:** SDK README doesn't link to GitHub repo or PyPI page.

## Recommended Fixes

| Priority | Fix | Where |
|----------|-----|-------|
| P0 | Standardize API URL to `https://api.citadelsdk.com` | SDK README, SDK client default, dashboard vite config |
| P0 | Fix dashboard URL in SDK README | SDK README |
| P1 | Update GitHub repo link | Landing page footer |
| P1 | Update landing code example | `apps/landing/src/App.tsx` code window |
| P1 | Add GitHub + PyPI links to SDK README | `packages/sdk-python/README.md` |
| P2 | Verify docs deployment at `citadelsdk.com/docs` | Vercel / hosting config |

## Verification Commands

```bash
# Check API health
curl https://ledger-sdk.fly.dev/health/live
curl https://api.citadelsdk.com/health/live

# Check dashboard
curl -I https://casss20-ledger-sdk-6nlu.vercel.app

# Check GitHub redirect
curl -I https://github.com/casss20/ledger-sdk

# Check PyPI
curl https://pypi.org/pypi/citadel-governance/json
```
