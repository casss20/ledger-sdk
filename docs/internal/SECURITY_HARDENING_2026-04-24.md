# Security Hardening Pass — 2026-04-24

> **Note:** This document captures the initial hardening pass. For a comprehensive production-readiness review with severity rankings, see `PRODUCTION_AUDIT.md`.

## Issues Fixed

### 1. Rate Limiting (NEW)
**Before:** No rate limiting. API could be hammered, auth endpoints vulnerable to brute force.
**After:** Two-tier rate limiting:
- `RateLimitMiddleware` — Per-tenant (or per-IP) limits for all API calls
  - Auth endpoints: 5 req / 5 min (brute force protection)
  - API endpoints: 100 req / min
  - Webhooks: 1000 req / min
- `AuthRateLimitMiddleware` — Stricter pre-auth limits on login/refresh/key-creation
  - Login: 5 per 5 minutes per IP
  - Refresh: 10 per minute
  - Key creation: 3 per hour

**Algorithm:** Token bucket with Redis sliding window fallback.
**Headers:** `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`.

### 2. CORS Lockdown
**Before:** `allow_origins=["*"]` in debug mode.
**After:** 
- Debug: Only localhost origins (`:3000`, `:5173`, `:8080`)
- Production: No origins unless explicitly configured via `CORS_ORIGINS` env var
- Methods restricted to `GET, POST, PUT, DELETE, PATCH, OPTIONS`
- Headers explicitly enumerated (no wildcard)
- `max_age=600` for preflight caching

### 3. Request Body Size Limits
**Before:** No body size limits. Could receive multi-GB payloads, causing memory exhaustion.
**After:** `RequestSizeLimitMiddleware` with 10MB default limit. Returns `413 Payload Too Large`.

### 4. Auth Endpoint Hardening
**Before:** Login endpoints had no special protection beyond general auth.
**After:** Dedicated `AuthRateLimitMiddleware` that runs **before** auth, limiting unauthenticated requests by IP.

### 5. Stripe Webhook HMAC Verification
**Before:** Webhook handler parsed events without signature verification. Anyone could POST fake events.
**After:**
- HMAC-SHA256 signature verification with `stripe-signature` header
- 5-minute timestamp tolerance (replay attack protection)
- Constant-time comparison (`hmac.compare_digest`) to prevent timing attacks
- Fails closed: invalid signature → `401 Unauthorized`

### 6. Health Check Enhancement
**Before:** `/health` returned static response, didn't actually verify DB.
**After:**
- `/v1/health/ready` — Attempts `SELECT 1` on DB pool, returns `503` if unreachable
- `/v1/health/live` — Always `200` (liveness probe)
- `/v1/health` — Includes actual DB connection status

## Production Checklist

Before deploying to production, verify:

- [ ] `CORS_ORIGINS` env var set to your actual frontend domains
- [ ] `STRIPE_WEBHOOK_SECRET` configured (never skip in prod)
- [ ] Redis available for distributed rate limiting (or single-instance only)
- [ ] `debug=false` in production
- [ ] Request body limit tuned for your use case (default 10MB)
- [ ] Rate limit windows adjusted for expected traffic patterns
- [ ] Load tested with `locust` or `k6`

## Architecture

```
Request → RateLimitMiddleware → AuthRateLimitMiddleware → TenantContextMiddleware → AuthMiddleware → BillingMiddleware → App
            (all paths)           (auth only)              (tenant isolation)         (JWT/API key)    (payment/quota)
```

Each middleware rejects at its layer:
- Rate limit → `429 Too Many Requests`
- Auth failure → `401 Unauthorized`
- Tenant missing → `400 Bad Request`
- Billing suspended → `402 Payment Required`
- Quota exceeded → `429 Too Many Requests`

## Files Changed

| File | Change |
|------|--------|
| `middleware/rate_limit.py` | NEW — Token bucket rate limiting |
| `api/middleware.py` | CORS lockdown + body size limit |
| `middleware/auth_middleware.py` | Removed webhook from exempt paths |
| `billing/stripe_webhooks.py` | HMAC signature verification |
| `billing/routes.py` | Uses new webhook verification |
| `middleware/__init__.py` | Exports new middleware |
| `tests/security/test_security_hardening.py` | NEW — 24 security tests |

## Test Results

```
24 passed, 0 failed
- Token bucket algorithm
- Rate limit integration
- Auth endpoint brute force
- Body size enforcement
- CORS origin restrictions
- Stripe HMAC verification (valid, invalid, replay, tampered)
```
