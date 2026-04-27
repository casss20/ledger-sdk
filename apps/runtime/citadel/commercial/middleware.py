"""Commercial middleware — attaches entitlements/usage to requests and enforces quotas.

This is the provider-agnostic enforcement layer. It uses the CommercialRepository
port (satisfied at runtime by the Stripe adapter) to resolve entitlements.
"""

import logging
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .entitlement_service import EntitlementService
from .usage_service import UsageService
from .models import BillingStatus

logger = logging.getLogger(__name__)


class CommercialMiddleware(BaseHTTPMiddleware):
    """Attaches commercial state to every request and enforces hard blocks.

    Order: Must run AFTER auth/tenant context middleware so that
    request.state.tenant_id is already set.
    """

    async def dispatch(self, request: Request, call_next):
        # 1. Skip exempt paths
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

        # 2. Get tenant context
        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            return await call_next(request)

        # 3. Resolve entitlements and usage
        pool = getattr(request.app.state, "db_pool", None)
        if pool is None:
            return await call_next(request)

        # Use the adapter composition root to wire the concrete repository
        # TODO: In a future refactor, inject the repository via app.state
        from .adapters.stripe.repository import StripeCommercialRepository
        repo = StripeCommercialRepository(pool)
        entitlement_service = EntitlementService(repo)
        usage_service = UsageService(repo)

        try:
            entitlements = await entitlement_service.resolve(tenant_id)
            usage = await usage_service.get_snapshot(tenant_id)
        except Exception as exc:
            logger.warning("Commercial resolution failed for %s: %s", tenant_id, exc)
            return await call_next(request)

        request.state.entitlements = entitlements
        request.state.usage = usage

        # 4. Hard block: subscription canceled / unpaid / past_due (outside grace)
        if not entitlements.can_access_api:
            return JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                content={
                    "error": "payment_required",
                    "plan": entitlements.plan_code,
                    "status": entitlements.billing_status.value,
                    "message": "Subscription is not active. Please update payment method.",
                },
            )

        # 5. Hard block: quota exceeded
        if entitlements.api_calls_limit is not None and usage.api_calls >= entitlements.api_calls_limit:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "quota_exceeded",
                    "plan": entitlements.plan_code,
                    "quota_key": "api_calls",
                    "current_usage": usage.api_calls,
                    "limit": entitlements.api_calls_limit,
                    "message": "Monthly API quota exceeded. Please upgrade your plan.",
                },
            )

        # 6. Track usage
        await usage_service.increment(tenant_id, "api_calls")

        return await call_next(request)


# Backward-compatible alias
BillingMiddleware = CommercialMiddleware
