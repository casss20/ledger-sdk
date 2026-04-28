# Citadel Cross-System Wiring Audit

> **Historical Document** — This audit was performed during the repo rename from `ledger-sdk` to `citadel-sdk`. All URLs listed as "OLD branding" or "404" have been fixed in subsequent commits. See `PRODUCTION_AUDIT.md` for the current state.

Audit date: 2026-04-25

## URL Inventory

| System | What it points to | Current Value | Status |
|--------|------------------|---------------|--------|
| **SDK README** `base_url` | Backend API | `https://api.citadelsdk.com` | ✅ Fixed |
| **Dashboard API client** | Backend API | `https://api.citadelsdk.com/v1` | ✅ NEW branding |
| **Dashboard vite config** | Backend API | `http://127.0.0.1:8000` (dev proxy) | ✅ Fixed |
| **Landing page code** | Backend API | `https://api.citadelsdk.com` | ✅ NEW branding |
| **SDK README** Dashboard | Dashboard app | `https://dashboard.citadelsdk.com` | ✅ Fixed |
| **Landing page** Dashboard | Dashboard app | `/demo/` (relative) | ⚠️ Assumes same domain |
| **Landing page** Docs | Docs site | `https://citadelsdk.com/docs` | ✅ NEW branding |
| **PyPI package** | Source repo | `https://github.com/casss20/citadel-sdk` | ✅ NEW branding |
| **GitHub repo** | Source repo | `https://github.com/casss20/citadel-sdk` | ✅ NEW branding |

## Findings (Historical)

**Problem:** The backend was referenced by both the old `ledger-sdk.fly.dev` and new `api.citadelsdk.com` domains.
- SDK README + client default: `https://ledger-sdk.fly.dev` → **Fixed to `https://api.citadelsdk.com`**
- Dashboard vite config: `https://ledger-sdk.fly.dev` → **Fixed to dev proxy**

**Problem:** `https://casss20-ledger-sdk-6nlu.vercel.app` returned 404.
- Fixed to `https://dashboard.citadelsdk.com`

## Verification Commands

```bash
# Backend health
curl https://api.citadelsdk.com/v1/health/live

# Dashboard
curl -I https://dashboard.citadelsdk.com

# Landing
curl -I https://citadelsdk.com
```

## Related Documents

- `PRODUCTION_AUDIT.md` — Current production-readiness review
- `ARCHITECTURE_REVIEW.md` — Full architecture assessment
