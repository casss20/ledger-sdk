"""Commercial HTTP routes — generic endpoints + Stripe-specific wiring."""

import logging
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse

from citadel.config import settings

from .models import BillingStatus
from .entitlement_service import EntitlementService
from .usage_service import UsageService
from .events import CommercialEventProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/billing", tags=["billing"])


def _get_pool(request: Request):
    return request.app.state.db_pool


def _get_entitlement_service(request: Request) -> EntitlementService:
    """Lazy-load entitlement service from app state."""
    if not hasattr(request.app.state, "_entitlement_service"):
        from .adapters.stripe.repository import StripeCommercialRepository
        repo = StripeCommercialRepository(request.app.state.db_pool)
        request.app.state._entitlement_service = EntitlementService(repo)
    return request.app.state._entitlement_service


def _get_usage_service(request: Request) -> UsageService:
    """Lazy-load usage service from app state."""
    if not hasattr(request.app.state, "_usage_service"):
        from .adapters.stripe.repository import StripeCommercialRepository
        repo = StripeCommercialRepository(request.app.state.db_pool)
        request.app.state._usage_service = UsageService(repo)
    return request.app.state._usage_service


@router.get("/plans")
async def list_plans(request: Request):
    """List available billing plans."""
    pool = _get_pool(request)
    rows = await pool.fetch("SELECT code, name, api_calls_limit, active_agents_limit, features_json FROM billing_plans ORDER BY api_calls_limit")
    return {
        "plans": [
            {
                "code": r["code"],
                "name": r["name"],
                "limits": {
                    "api_calls": r["api_calls_limit"],
                    "active_agents": r["active_agents_limit"],
                },
                "features": r["features_json"] or {},
            }
            for r in rows
        ]
    }


@router.get("/usage")
async def get_usage(request: Request):
    """Get current-period usage for the authenticated tenant."""
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not identified")

    usage_service = _get_usage_service(request)
    snapshot = await usage_service.get_snapshot(tenant_id)
    entitlement_service = _get_entitlement_service(request)
    entitlements = await entitlement_service.resolve(tenant_id)

    return {
        "tenant_id": tenant_id,
        "period": usage_service._current_period(),
        "usage": {
            "api_calls": snapshot.api_calls,
            "active_agents": snapshot.active_agents,
            "approval_requests": snapshot.approval_requests,
            "governed_actions": snapshot.governed_actions,
        },
        "limits": {
            "api_calls": entitlements.api_calls_limit,
            "active_agents": entitlements.active_agents_limit,
            "approval_requests": entitlements.approval_requests_limit,
        },
        "status": entitlements.billing_status.value,
        "in_grace_period": entitlements.in_grace_period,
    }


@router.get("/entitlements")
async def get_entitlements(request: Request):
    """Get resolved entitlements for the authenticated tenant."""
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not identified")

    entitlement_service = _get_entitlement_service(request)
    entitlements = await entitlement_service.resolve(tenant_id)

    return {
        "tenant_id": entitlements.tenant_id,
        "plan_code": entitlements.plan_code,
        "status": entitlements.billing_status.value,
        "can_access_api": entitlements.can_access_api,
        "can_manage_billing": entitlements.can_manage_billing,
        "in_grace_period": entitlements.in_grace_period,
        "limits": {
            "api_calls": entitlements.api_calls_limit,
            "active_agents": entitlements.active_agents_limit,
            "approval_requests": entitlements.approval_requests_limit,
            "audit_retention_days": entitlements.audit_retention_days,
        },
        "features": entitlements.features,
    }


# ── Stripe-specific endpoints ────────────────────────────────────────────

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Receive Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Lazy-load Stripe handler
    if not hasattr(request.app.state, "_stripe_webhook_handler"):
        from .adapters.stripe.repository import StripeCommercialRepository
        from .adapters.stripe.webhooks import StripeWebhookHandler
        repo = StripeCommercialRepository(request.app.state.db_pool)
        event_processor = CommercialEventProcessor(repo)
        request.app.state._stripe_webhook_handler = StripeWebhookHandler(
            repo=repo,
            event_processor=event_processor,
            webhook_secret=settings.stripe_webhook_secret,
        )

    handler = request.app.state._stripe_webhook_handler
    try:
        result = await handler.handle(request)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Stripe webhook processing failed: %s", exc)
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.post("/portal")
async def create_billing_portal(request: Request):
    """Create a Stripe Billing Portal session for the tenant."""
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not identified")

    from .adapters.stripe.client import StripeClient
    client = StripeClient()

    pool = _get_pool(request)
    row = await pool.fetchrow(
        "SELECT stripe_customer_id FROM billing_customers WHERE tenant_id = $1", tenant_id
    )
    if not row or not row.get("stripe_customer_id"):
        raise HTTPException(status_code=404, detail="No Stripe customer found for tenant")

    session_url = await client.create_portal_session(row["stripe_customer_id"])
    return {"portal_url": session_url}
