"""Commercial HTTP routes — generic endpoints + Stripe-specific wiring."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from citadel.config import settings

from .cost_controls import CostAttribution, CostBudget, CostControlService
from .entitlement_service import EntitlementService
from .events import CommercialEventProcessor
from .usage_service import UsageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/billing", tags=["billing"])


class BudgetCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    scope_type: str = Field(..., pattern=r"^(tenant|project|agent|api_key)$")
    scope_value: str | None = Field(None, max_length=256)
    amount_cents: int = Field(..., gt=0)
    currency: str = Field("usd", min_length=3, max_length=3)
    reset_period: str = Field(..., pattern=r"^(daily|weekly|monthly)$")
    enforcement_action: str = Field(..., pattern=r"^(block|require_approval|throttle)$")
    warning_threshold_percent: int = Field(80, ge=1, le=100)


class BudgetCheckRequest(BaseModel):
    projected_cost_cents: int = Field(..., ge=0)
    actor_id: str | None = Field(None, max_length=256)
    project_id: str | None = Field(None, max_length=256)
    api_key_id: str | None = Field(None, max_length=256)
    provider: str | None = Field(None, max_length=64)
    model: str | None = Field(None, max_length=256)
    request_id: str | None = Field(None, max_length=256)
    decision_id: str | None = Field(None, max_length=256)
    metadata: dict[str, Any] | None = None


class SpendRecordRequest(BaseModel):
    cost_cents: int = Field(..., ge=0)
    actor_id: str | None = Field(None, max_length=256)
    project_id: str | None = Field(None, max_length=256)
    api_key_id: str | None = Field(None, max_length=256)
    provider: str | None = Field(None, max_length=64)
    model: str | None = Field(None, max_length=256)
    input_tokens: int = Field(0, ge=0)
    output_tokens: int = Field(0, ge=0)
    request_id: str | None = Field(None, max_length=256)
    decision_id: str | None = Field(None, max_length=256)
    metadata: dict[str, Any] | None = None


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


def _get_cost_control_service(request: Request) -> CostControlService:
    """Lazy-load cost control service from app state."""
    if not hasattr(request.app.state, "_cost_control_service"):
        request.app.state._cost_control_service = CostControlService(
            request.app.state.db_pool
        )
    return request.app.state._cost_control_service


def _tenant_id(request: Request) -> str:
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not identified")
    return tenant_id


def _budget_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "budget_id": row.get("budget_id"),
        "tenant_id": row.get("tenant_id"),
        "name": row.get("name"),
        "scope_type": row.get("scope_type"),
        "scope_value": row.get("scope_value"),
        "amount_cents": row.get("amount_cents"),
        "currency": row.get("currency"),
        "reset_period": row.get("reset_period"),
        "enforcement_action": row.get("enforcement_action"),
        "warning_threshold_percent": row.get("warning_threshold_percent"),
        "is_active": row.get("is_active"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


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
    tenant_id = _tenant_id(request)

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


@router.get("/summary")
async def get_billing_summary(request: Request):
    """Get subscription, quota, and budget summary for the authenticated tenant."""
    tenant_id = _tenant_id(request)
    usage_service = _get_usage_service(request)
    entitlement_service = _get_entitlement_service(request)
    cost_service = _get_cost_control_service(request)

    snapshot = await usage_service.get_snapshot(tenant_id)
    entitlements = await entitlement_service.resolve(tenant_id)
    cost_summary = await cost_service.get_summary(tenant_id)

    return {
        "tenant_id": tenant_id,
        "plan": entitlements.plan_code,
        "status": entitlements.billing_status.value,
        "limits": {
            "api_calls": entitlements.api_calls_limit,
            "agents": entitlements.active_agents_limit,
            "approvals": entitlements.approval_requests_limit,
        },
        "usage": {
            "api_calls": snapshot.api_calls,
            "active_agents": snapshot.active_agents,
            "approval_requests": snapshot.approval_requests,
            "governed_actions": snapshot.governed_actions,
        },
        "features": entitlements.features,
        "current_period_end": None,
        "cost_controls": cost_summary,
    }


@router.get("/budgets")
async def list_budgets(request: Request):
    """List configured cost budgets for the authenticated tenant."""
    tenant_id = _tenant_id(request)
    service = _get_cost_control_service(request)
    budgets = await service.list_budgets(tenant_id)
    return {"budgets": [_budget_response(budget) for budget in budgets]}


@router.post("/budgets")
async def create_budget(body: BudgetCreateRequest, request: Request):
    """Create a deterministic cost budget."""
    tenant_id = _tenant_id(request)
    scope_value = body.scope_value or (tenant_id if body.scope_type == "tenant" else None)
    if not scope_value:
        raise HTTPException(status_code=400, detail="scope_value is required for this scope")

    budget = CostBudget(
        tenant_id=tenant_id,
        name=body.name,
        scope_type=body.scope_type,
        scope_value=scope_value,
        amount_cents=body.amount_cents,
        currency=body.currency.lower(),
        reset_period=body.reset_period,
        enforcement_action=body.enforcement_action,
        warning_threshold_percent=body.warning_threshold_percent,
    )
    service = _get_cost_control_service(request)
    try:
        row = await service.create_budget(
            budget,
            created_by=getattr(request.state, "user_id", None) or "api",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"budget": _budget_response(row)}


@router.post("/cost/check")
async def check_cost_budget(body: BudgetCheckRequest, request: Request):
    """Pre-request LLM cost budget check."""
    tenant_id = _tenant_id(request)
    service = _get_cost_control_service(request)
    decision = await service.check_budget(
        CostAttribution(
            tenant_id=tenant_id,
            projected_cost_cents=body.projected_cost_cents,
            actor_id=body.actor_id,
            project_id=body.project_id,
            api_key_id=body.api_key_id,
            provider=body.provider,
            model=body.model,
            request_id=body.request_id,
            decision_id=body.decision_id,
            metadata=body.metadata,
        )
    )
    budget = decision.budget
    return {
        "allowed": decision.allowed,
        "enforcement_action": decision.enforcement_action,
        "requires_approval": decision.requires_approval,
        "throttled": decision.throttled,
        "reason": decision.reason,
        "projected_cost_cents": decision.projected_cost_cents,
        "current_spend_cents": decision.current_spend_cents,
        "budget_amount_cents": decision.budget_amount_cents,
        "warning": decision.warning,
        "period_start": decision.period_start.isoformat(),
        "period_end": decision.period_end.isoformat(),
        "budget": {
            "budget_id": budget.budget_id,
            "name": budget.name,
            "scope_type": budget.scope_type,
            "scope_value": budget.scope_value,
            "enforcement_action": budget.enforcement_action,
        } if budget else None,
    }


@router.post("/cost/spend")
async def record_spend(body: SpendRecordRequest, request: Request):
    """Record actual LLM spend after execution."""
    tenant_id = _tenant_id(request)
    service = _get_cost_control_service(request)
    try:
        event = await service.record_spend(
            CostAttribution(
                tenant_id=tenant_id,
                actual_cost_cents=body.cost_cents,
                actor_id=body.actor_id,
                project_id=body.project_id,
                api_key_id=body.api_key_id,
                provider=body.provider,
                model=body.model,
                input_tokens=body.input_tokens,
                output_tokens=body.output_tokens,
                request_id=body.request_id,
                decision_id=body.decision_id,
                metadata=body.metadata,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"spend_event": event}


@router.get("/entitlements")
async def get_entitlements(request: Request):
    """Get resolved entitlements for the authenticated tenant."""
    tenant_id = _tenant_id(request)

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
    tenant_id = _tenant_id(request)

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
