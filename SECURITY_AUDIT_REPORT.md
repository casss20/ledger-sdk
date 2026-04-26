# Citadel Security Audit Report

**Date:** 2026-04-26  
**Scope:** `/root/.openclaw/workspace/ledger-sdk` — Full runtime, API, auth, middleware, CI/CD, dependencies  
**Methodology:** Static code review, architecture analysis, defensive-only findings (no exploit payloads)  

---

## 1. Executive Summary

This audit identified **6 critical**, **6 high**, **5 medium**, and **3 low** severity findings. The codebase has a solid security foundation with OWASP middleware, parameterized SQL, JWT with algorithm whitelisting, and rate limiting. However, several endpoints are missing authentication or tenant isolation, creating data leakage and privilege escalation paths. The auth middleware contains a dangerous dev-mode bypass, and error handling can leak internal details in debug mode.

**Risk Score:** HIGH — Multiple paths to cross-tenant data access and unauthenticated billing/metrics exposure.

---

## 2. Critical Findings

### C1: Billing Routes Missing Authentication
- **Severity:** Critical  
- **File:** `apps/runtime/citadel/billing/routes.py`  
- **Issue:** `/v1/billing/summary` and `/v1/billing/checkout` have **no `require_api_key` dependency**. Anyone can access billing data and trigger checkout sessions.  
- **Risk:** Financial data leakage, unauthorized subscription manipulation, tenant enumeration.  
- **Fix:** Add `_: str = Depends(require_api_key)` to both endpoints. Add `tenant_id` filtering to the summary query.  
- **Test:** `test_billing_requires_auth` — assert 401 without API key, assert 403 with invalid key.

### C2: Metrics Router Missing Tenant Isolation
- **Severity:** Critical  
- **File:** `apps/runtime/citadel/api/routers/metrics.py`  
- **Issue:** All metrics queries (`COUNT(*) FROM actions`, `COUNT(*) FROM decisions`, etc.) lack `WHERE tenant_id = $1`. Any authenticated user sees **global** statistics across all tenants.  
- **Risk:** Cross-tenant data leakage, competitive intelligence exposure, tenant enumeration.  
- **Fix:** Add `tenant_id` parameter and filter every query with `WHERE tenant_id = $1`.  
- **Test:** `test_metrics_tenant_isolation` — create data in tenant A, verify tenant B sees only zeros.

### C3: Auth Middleware Dev-Mode Bypass
- **Severity:** Critical  
- **File:** `apps/runtime/citadel/middleware/auth_middleware.py` (lines 45-50)  
- **Issue:** If `CITADEL_DEV_MODE=true` (or `LEDGER_DEV_MODE=true`) **AND** `settings.debug=True`, **all authentication is bypassed** and `tenant_id` is set to `"dev_tenant"`. If debug is accidentally enabled in production, anyone can access any endpoint.  
- **Risk:** Complete authentication bypass, unauthorized access to all endpoints.  
- **Fix:** Remove the environment-variable bypass entirely, or gate it behind an additional `CITADEL_TESTING=true` check. Never allow a single env var to disable auth.  
- **Test:** `test_dev_mode_does_not_bypass_auth_in_production` — assert 401 when hitting protected endpoint with `CITADEL_DEV_MODE=true` but `debug=False`.

### C4: API Key Demo Bypass (Secret Not Required)
- **Severity:** Critical  
- **File:** `apps/runtime/citadel/middleware/auth_middleware.py` (lines 80-84)  
- **Issue:** If `api_key_id` is in `settings.valid_api_keys`, the request is accepted **without verifying the secret**, and tenant is hardcoded to `"demo-tenant"`.  
- **Risk:** Stolen/leaked API key IDs allow full access without the secret. All requests land in the demo tenant, bypassing real tenant isolation.  
- **Fix:** Remove the demo bypass. Always require both key ID and secret, validate against `APIKeyService`, and use the actual tenant from the key record.  
- **Test:** `test_api_key_id_only_is_rejected` — assert 401 when only `X-API-Key` is provided without `X-API-Secret`.

### C5: Health Readiness Endpoint Leaks Database Error Details
- **Severity:** Critical  
- **File:** `apps/runtime/citadel/api/routers/health.py` (lines 38-42)  
- **Issue:** When DB connection fails, `db_startup_error` (which may contain connection strings, credentials, or hostnames) is returned in the HTTP response.  
- **Risk:** Exposure of database credentials, internal network topology, or cloud provider details.  
- **Fix:** Return a generic "Database unavailable" message. Log the detailed error server-side only.  
- **Test:** `test_health_readiness_no_error_leak` — mock DB failure with sensitive string, assert 503 response does not contain the string.

### C6: ErrorHandlingMiddleware Leaks Stack Traces in Debug Mode
- **Severity:** Critical  
- **File:** `apps/runtime/citadel/api/middleware.py` (line 199)  
- **Issue:** `ErrorHandlingMiddleware` returns `str(exc)` in the JSON response when `settings.debug=True`. This can leak file paths, SQL queries, internal variable names, and library versions.  
- **Risk:** Information disclosure aiding reconnaissance and targeted attacks.  
- **Fix:** Always return a generic "Internal server error" message to the client, regardless of debug mode. Use structured server-side logging for diagnostics.  
- **Test:** `test_error_handler_no_info_leak_in_debug` — trigger exception with debug=True, assert response body does not contain file paths or exception messages.

---

## 3. High Findings

### H1: Audit Router Missing Tenant Isolation
- **Severity:** High  
- **File:** `apps/runtime/citadel/api/routers/audit.py`  
- **Issue:** `/v1/audit/verify` calls `kernel.repo.verify_audit_chain()` **without passing `tenant_id`**. The underlying implementation may not filter by tenant.  
- **Risk:** Cross-tenant audit data access.  
- **Fix:** Pass `tenant_id` to `verify_audit_chain()` and ensure the repository filters by tenant.  
- **Test:** `test_audit_verify_tenant_isolation`.

### H2: Dashboard Kill-Switch No Role Check
- **Severity:** High  
- **File:** `apps/runtime/citadel/api/routers/dashboard.py` — `trigger_kill_switch`  
- **Issue:** Any authenticated user (not just admin/operator) can trigger kill switches. The endpoint only checks `tenant_id` and `user_id` from request state, not role.  
- **Risk:** Privilege escalation — a viewer or compromised API key can disable tenant operations.  
- **Fix:** Add role check: `if request.state.role not in ("admin", "operator"): raise HTTPException(403)`.  
- **Test:** `test_kill_switch_requires_admin_role`.

### H3: No Rate Limiting / Account Lockout on Login
- **Severity:** High  
- **File:** `apps/runtime/citadel/middleware/auth_middleware.py` — `login` endpoint  
- **Issue:** `/auth/login` has no per-username rate limiting or account lockout. Brute-force attacks against operator passwords are possible.  
- **Risk:** Credential stuffing, brute-force password attacks.  
- **Fix:** Add per-IP and per-username rate limiting (e.g., 5 attempts per 15 minutes). Increment a failed-login counter in cache. Lock account after N failures.  
- **Test:** `test_login_rate_limit` — assert 429 after 5 failed attempts.

### H4: Step-Up Auth Fallback Vulnerability
- **Severity:** High  
- **File:** `apps/runtime/citadel/middleware/auth_middleware.py` (lines 140-148)  
- **Issue:** `/auth/step-up` falls back to `operator_service.authenticate(user_id, password)` if `authenticate_by_id` fails. Since `user_id` may be guessable (e.g., `op_bootstrap_...`), this effectively allows authentication by user ID instead of username.  
- **Risk:** Bypass of step-up authentication if attacker knows or guesses operator IDs.  
- **Fix:** Remove the fallback. If `authenticate_by_id` is unavailable, return 501. Never treat user_id as a username.  
- **Test:** `test_step_up_no_fallback_to_user_id`.

### H5: Prometheus Metrics Exposed Without Authentication
- **Severity:** High  
- **File:** `apps/runtime/citadel/api/__init__.py` (metrics mount)  
- **Issue:** The Prometheus `/metrics` endpoint is mounted as a raw ASGI app **outside** the auth middleware stack. It is accessible without any authentication.  
- **Risk:** Exposure of runtime metrics, request counts, memory usage, and potentially tenant-scoped data if custom metrics include it.  
- **Fix:** Mount metrics behind an authenticated router, or add a simple API key check middleware before the metrics app.  
- **Test:** `test_metrics_requires_auth`.

### H6: API Key in Query Parameters
- **Severity:** High  
- **File:** `apps/runtime/citadel/api/dependencies.py` (line 54)  
- **Issue:** `require_api_key` falls back to `request.query_params.get("api_key")`. API keys in URLs are logged by proxies, servers, and browsers.  
- **Risk:** API key leakage in access logs, browser history, and referrer headers.  
- **Fix:** Remove the query-parameter fallback. Only accept API keys in headers.  
- **Test:** `test_api_key_in_query_param_rejected`.

---

## 4. Medium Findings

### M1: Stripe Webhook Secret Optional in Development
- **Severity:** Medium  
- **File:** `apps/runtime/citadel/billing/stripe_webhooks.py` (lines 25-32)  
- **Issue:** If `webhook_secret` is not set, signature verification is **skipped** with only a log warning. A misconfigured production deployment would accept forged webhooks.  
- **Risk:** Fake Stripe events causing unauthorized subscription changes or data corruption.  
- **Fix:** Refuse to start the billing module if `stripe_webhook_secret` is missing and `debug=False`.  
- **Test:** `test_stripe_webhook_requires_secret_in_production`.

### M2: CORS Credentials with Dynamic Origins
- **Severity:** Medium  
- **File:** `apps/runtime/citadel/api/middleware.py` (CORS setup)  
- **Issue:** `allow_credentials=True` is set for all configured origins. If an attacker can influence `CORS_ORIGINS` (e.g., via SSRF or config injection), they could receive authenticated requests.  
- **Risk:** Cross-origin credential leakage if origin allowlist is compromised.  
- **Fix:** Validate `cors_origins` at startup (ensure no wildcards, no attacker-controlled domains). Add a strict domain validation regex.  
- **Test:** `test_cors_rejects_wildcard_origin`.

### M3: Request Body Size Limit Bypass
- **Severity:** Medium  
- **File:** `apps/runtime/citadel/api/middleware.py` (RequestSizeLimitMiddleware)  
- **Issue:** The middleware checks `Content-Length` but does not protect against chunked transfer encoding (no Content-Length header) or body consumption before the check.  
- **Risk:** Memory exhaustion from very large request bodies.  
- **Fix:** Add a streaming body limit using Starlette's `request.stream()` with a max-read counter.  
- **Test:** `test_chunked_request_body_limited`.

### M4: Health Endpoint Version Disclosure
- **Severity:** Medium  
- **File:** `apps/runtime/citadel/api/routers/health.py` (line 24)  
- **Issue:** `/v1/health` returns `app_version` in the response.  
- **Risk:** Attackers can use the version to identify known CVEs in dependencies.  
- **Fix:** Remove `version` from the public health response, or return a static/generic version string.  
- **Test:** `test_health_no_version_leak`.

### M5: JWT Secret Auto-Generated on Missing Config
- **Severity:** Medium  
- **File:** `apps/runtime/citadel/api/__init__.py` (lines 95-110)  
- **Issue:** If `citadel_jwt_secret` is not set, a random one-time secret is generated. JWTs issued before restart become invalid after restart. More importantly, if two instances start without the secret, they each have different secrets and cannot validate each other's tokens.  
- **Risk:** Session invalidation, inconsistent auth state across replicas, potential for secret reuse if RNG is weak.  
- **Fix:** Refuse to start if `citadel_jwt_secret` is missing in production. Do not auto-generate.  
- **Test:** `test_startup_fails_without_jwt_secret`.

---

## 5. Low Findings

### L1: Debug Docs Endpoints Exposed When Debug Enabled
- **Severity:** Low  
- **File:** `apps/runtime/citadel/api/__init__.py` (FastAPI constructor)  
- **Issue:** `/docs` and `/redoc` are enabled when `debug=True`. If debug is enabled in staging/pre-prod, API schemas are exposed.  
- **Risk:** Attackers can learn endpoint structures, parameter types, and internal models.  
- **Fix:** Disable docs entirely in non-local environments, or require auth to access them.  
- **Test:** `test_docs_disabled_in_production`.

### L2: CI/CD Permissive Lint/Typecheck Steps
- **Severity:** Low  
- **File:** `.github/workflows/ci-cd.yml`  
- **Issue:** `ruff check ... || true` and `mypy ... || true` mean lint/type errors do not fail the build.  
- **Risk:** Type safety and code quality regressions slip into production.  
- **Fix:** Remove `|| true` from lint and typecheck steps (already done for Bandit and integration tests in previous commits; apply same to ruff and mypy).  
- **Test:** N/A (CI configuration).

### L3: No Signed Releases or Artifact Verification
- **Severity:** Low  
- **File:** `.github/workflows/ci-cd.yml` (deploy jobs)  
- **Issue:** PyPI uploads and Docker/Vercel deploys have no artifact signing, SBOM generation, or supply-chain verification.  
- **Risk:** Supply-chain attacks if build artifacts are tampered with.  
- **Fix:** Generate SBOMs with `cyclonedx-bom`, sign PyPI packages with Sigstore, pin GitHub Actions to commit SHAs instead of `@v4`.  
- **Test:** N/A (CI configuration).

---

## 6. Remediation Plan

### Phase 1 — Immediate (Critical Fixes)
| # | Fix | Files |
|---|-----|-------|
| C1 | Add `require_api_key` to billing routes | `billing/routes.py` |
| C2 | Add `tenant_id` filter to all metrics queries | `api/routers/metrics.py` |
| C3 | Remove or harden dev-mode auth bypass | `middleware/auth_middleware.py` |
| C4 | Remove API key ID-only bypass | `middleware/auth_middleware.py` |
| C5 | Sanitize health readiness error response | `api/routers/health.py` |
| C6 | Always return generic error to client | `api/middleware.py` |

### Phase 2 — High Priority
| # | Fix | Files |
|---|-----|-------|
| H1 | Add tenant isolation to audit verify | `api/routers/audit.py`, `core/repository.py` |
| H2 | Add role check to kill-switch | `api/routers/dashboard.py` |
| H3 | Add login rate limiting | `middleware/auth_middleware.py` |
| H4 | Remove step-up fallback | `middleware/auth_middleware.py` |
| H5 | Auth-protect metrics endpoint | `api/__init__.py` |
| H6 | Remove query-param API key fallback | `api/dependencies.py` |

### Phase 3 — Medium/Low
| # | Fix | Files |
|---|-----|-------|
| M1 | Enforce Stripe webhook secret in prod | `billing/stripe_webhooks.py` |
| M2 | Validate CORS origins at startup | `api/middleware.py` |
| M3 | Add streaming body size limit | `api/middleware.py` |
| M4 | Remove version from health response | `api/routers/health.py` |
| M5 | Fail startup on missing JWT secret | `api/__init__.py`, `config.py` |
| L1 | Disable docs in non-local envs | `api/__init__.py` |
| L2 | Remove `|| true` from lint/typecheck | `.github/workflows/ci-cd.yml` |
| L3 | Add SBOM + signed releases | `.github/workflows/ci-cd.yml` |

---

## 7. Tests to Add

### Security Regression Tests

```python
# tests/security/test_audit_report_regression.py

class TestBillingAuth:
    def test_billing_summary_requires_api_key(self, client):
        response = client.get("/v1/billing/summary")
        assert response.status_code == 401

    def test_billing_checkout_requires_api_key(self, client):
        response = client.post("/v1/billing/checkout")
        assert response.status_code == 401

class TestMetricsTenantIsolation:
    def test_metrics_only_shows_own_tenant(self, client, api_key_a, api_key_b):
        # Create action in tenant A
        client.post("/v1/actions", headers={"X-API-Key": api_key_a}, json={...})
        # Tenant B metrics should not include tenant A data
        resp = client.get("/v1/metrics/summary", headers={"X-API-Key": api_key_b})
        assert resp.json()["actions_total"] == 0

class TestAuthBypass:
    def test_dev_mode_does_not_bypass_auth(self, client):
        # With debug=False, CITADEL_DEV_MODE should not matter
        response = client.get("/api/agents", headers={"X-LEDGER-DEV-MODE": "true"})
        assert response.status_code == 401

    def test_api_key_id_only_is_rejected(self, client):
        response = client.get("/api/agents", headers={"X-API-Key": "some-key-id"})
        assert response.status_code == 401

class TestInfoLeakage:
    def test_health_ready_no_db_error_details(self, client):
        # Mock DB failure with sensitive string
        response = client.get("/v1/health/ready")
        assert "postgresql://" not in response.text
        assert "password" not in response.text.lower()

    def test_error_handler_no_debug_leak(self, client):
        # Trigger an error endpoint with debug=True
        response = client.get("/trigger-error")
        assert "Traceback" not in response.text
        assert "File \"" not in response.text

class TestKillSwitchRBAC:
    def test_kill_switch_requires_admin(self, client, viewer_token):
        response = client.post("/api/dashboard/kill-switch", 
                               headers={"Authorization": f"Bearer {viewer_token}"},
                               json={"scope": "tenant", "reason": "test"})
        assert response.status_code == 403

class TestLoginRateLimit:
    def test_login_brute_force_protection(self, client):
        for _ in range(6):
            response = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
        assert response.status_code == 429

class TestMetricsAuth:
    def test_prometheus_metrics_require_auth(self, client):
        response = client.get("/metrics")
        assert response.status_code == 401

class TestStripeWebhookSecurity:
    def test_webhook_rejected_without_secret_in_prod(self, client):
        # In production mode, webhook without configured secret should 500 or refuse
        response = client.post("/v1/billing/webhooks/stripe", data=b"{}")
        assert response.status_code in (401, 500)
```

---

## 8. Remaining Risks (After Remediation)

Even after fixing all findings above, the following residual risks remain:

1. **Insider Threat:** Anyone with a valid admin API key or JWT can access all tenant data. No row-level security policies are enforced at the database level.
2. **Dependency Supply Chain:** `requirements.txt` uses SHA-256 hashes, but new dependencies added without `pip-compile --generate-hashes` could bypass this. Quarterly `safety check` is recommended.
3. **Social Engineering:** The bootstrap admin account is created automatically. If the bootstrap password is weak or leaked, full admin access is granted.
4. **DDoS:** While rate limiting exists, no distributed rate limiting (e.g., per-tenant API call budgets) is enforced at the edge.
5. **Data Retention:** Audit logs have a 90-day retention. Beyond that, forensic investigation capability is lost.
6. **Multi-Region Consistency:** The in-memory `AppCache` (dict-based) does not synchronize across replicas. Token revocation and rate-limit counters may be inconsistent in a multi-instance deployment.

---

## 9. Secure-by-Default Recommendations

1. **Fail Closed:** Every new endpoint should default to `require_api_key` unless explicitly exempted.
2. **Tenant Everywhere:** Every database query should include `tenant_id` by default. Use a query builder or repository pattern that enforces this.
3. **No Debug in Prod:** Make `debug=True` impossible to set via environment variables in production builds. Require a config file change.
4. **Secret Rotation:** Implement automatic JWT secret rotation with grace periods for old tokens.
5. **Zero-Trust Metrics:** All observability endpoints (`/metrics`, `/health/ready`) should require mTLS or API keys.
6. **Schema Validation:** Add `zod` or `pydantic` strict mode to all request models to prevent extra field injection.
7. **Signed Commits:** Require GPG-signed commits for the repository and signed tags for releases.
8. **Penetration Testing:** Schedule an annual third-party penetration test focused on tenant isolation and auth bypass.

---

*End of Report*
