from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from .repository import BillingRepository
from .entitlement_service import EntitlementService
from .usage_service import UsageService

class BillingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Skip paths that don't require billing checks
        exempt_paths = [
            "/health",
            "/v1/health",
            "/auth/login",
            "/auth/refresh",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/metrics",
            "/v1/billing/webhooks",
        ]
        if any(request.url.path.startswith(path) for path in exempt_paths):
            return await call_next(request)

        # 2. Get tenant context (must be set by Auth middleware earlier)
        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            return await call_next(request)

        # 3. Resolve Entitlements and Usage
        # We use the app state pool for efficiency
        pool = getattr(request.app.state, "db_pool", None)
        if pool is None:
            return await call_next(request)

        repo = BillingRepository(pool)
        entitlement_service = EntitlementService(repo)
        usage_service = UsageService(repo)

        entitlements = await entitlement_service.resolve(tenant_id)
        usage = await usage_service.get_snapshot(tenant_id)
        
        request.state.entitlements = entitlements
        request.state.usage = usage

        # 4. Hard Enforcement: Block if access is suspended
        if not entitlements.can_access_api:
            return JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                content={
                    "error": "Billing access suspended",
                    "plan": entitlements.plan_code,
                    "billing_status": entitlements.billing_status,
                    "upgrade_required": True,
                }
            )

        # 5. Quota Enforcement: Block if API limit is hit
        if entitlements.api_calls_limit is not None and usage.api_calls >= entitlements.api_calls_limit:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Monthly API quota exceeded",
                    "plan": entitlements.plan_code,
                    "quota_key": "api_calls",
                    "current_usage": usage.api_calls,
                    "limit": entitlements.api_calls_limit,
                    "upgrade_required": True,
                }
            )

        # 6. Track Usage (Auto-increment API call for successful request)
        # Note: We might want to increment ONLY if request succeeds, but for now we do it here.
        await usage_service.increment(tenant_id, "api_calls")

        return await call_next(request)
