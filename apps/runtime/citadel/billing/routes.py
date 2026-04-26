from fastapi import APIRouter, Depends, Request, HTTPException
from citadel.api.dependencies import require_api_key
from .repository import BillingRepository
from .stripe_client import StripeClient
from .stripe_webhooks import StripeWebhookHandler
from .entitlement_service import EntitlementService
from .usage_service import UsageService

router = APIRouter(prefix="/v1/billing", tags=["billing"])

def get_repo(request: Request):
    return BillingRepository(request.app.state.db_pool)

@router.get("/summary")
async def get_billing_summary(request: Request, repo: BillingRepository = Depends(get_repo), _: str = Depends(require_api_key)):
    tenant_id = request.state.tenant_id
    entitlement_service = EntitlementService(repo)
    usage_service = UsageService(repo)
    
    entitlements = await entitlement_service.resolve(tenant_id)
    usage = await usage_service.get_snapshot(tenant_id)
    
    return {
        "tenant_id": tenant_id,
        "plan": entitlements.plan_code,
        "status": entitlements.billing_status,
        "limits": {
            "api_calls": entitlements.api_calls_limit,
            "agents": entitlements.active_agents_limit,
            "approvals": entitlements.approval_requests_limit
        },
        "usage": usage,
        "features": entitlements.features,
        "current_period_end": entitlements.current_period_end
    }

@router.post("/checkout")
async def create_checkout(request: Request, repo: BillingRepository = Depends(get_repo), _: str = Depends(require_api_key)):
    tenant_id = request.state.tenant_id
    customer = await repo.get_customer(tenant_id)
    
    # Normally we'd take a plan code from body
    stripe = StripeClient()
    
    if not customer or not customer['stripe_customer_id']:
        # Create customer on the fly if needed
        # (Usually done during onboarding or first checkout)
        pass

    session = stripe.create_checkout_session(
        customer['stripe_customer_id'], 
        "price_pro_id_here", # This should be dynamic
        tenant_id
    )
    return {"url": session.url}

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, repo: BillingRepository = Depends(get_repo)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    from citadel.config import settings
    
    # Use our own HMAC verification (more control than Stripe library)
    handler = StripeWebhookHandler(repo, webhook_secret=settings.stripe_webhook_secret)
    
    if not handler.verify_signature(payload, sig_header):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    # Parse the payload after verification
    import json
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    await repo.log_event("stripe", event["id"], event["type"], event)
    
    try:
        await handler.handle(event)
        await repo.mark_event_processed(event["id"])
    except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError) as webhook_err:
        await repo.mark_event_processed(event["id"], error=f"{type(webhook_err).__name__}: {webhook_err}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {type(webhook_err).__name__}")

    return {"status": "ok"}
