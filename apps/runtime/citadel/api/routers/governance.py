"""
Governance Router — REST API for the decision-centric governance system.

Endpoints:
  POST /v1/governance/decisions              — Create a governance decision
  GET  /v1/governance/decisions/{id}         — Get decision by ID
  POST /v1/governance/decisions/{id}/tokens  — Derive a capability token
  GET  /v1/governance/tokens/{token_id}      — Get token by ID
  POST /v1/governance/verify                 — Verify a token or decision
  GET  /v1/governance/audit/verify           — Verify governance audit chain
  GET  /v1/governance/decisions/{id}/audit   — Get audit events for a decision
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from pydantic import BaseModel, Field

from citadel.api.dependencies import require_api_key
from citadel.tokens import (
    CapabilityToken,
    DecisionScope,
    DecisionType,
    GovernanceAuditTrail,
    GovernanceDecision,
    KillSwitch,
    KillSwitchScope,
    TokenVerifier,
    TokenVault,
)

router = APIRouter(tags=["governance"])


# ============================================================================
# Request / Response Models
# ============================================================================

class CreateDecisionRequest(BaseModel):
    decision_type: str = Field(..., pattern=r"^(allow|deny|revoked)$")
    actor_id: str = Field(..., min_length=1, max_length=128)
    action: str = Field(..., min_length=1, max_length=256)
    scope_actions: List[str] = Field(default_factory=list)
    scope_resources: List[str] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    expiry_minutes: Optional[int] = Field(None, ge=1, le=525600)  # max 1 year
    kill_switch_scope: str = Field("request", pattern=r"^(request|agent|tenant|global)$")
    reason: str = Field("", max_length=1024)


class DecisionResponse(BaseModel):
    decision_id: str
    decision_type: str
    tenant_id: str
    actor_id: str
    action: str
    scope_actions: List[str]
    scope_resources: List[str]
    expiry: Optional[datetime] = None
    kill_switch_scope: str
    reason: str
    created_at: Optional[datetime] = None


class DeriveTokenRequest(BaseModel):
    pass  # No body needed; token derived from decision


class TokenResponse(BaseModel):
    token_id: str
    decision_id: str
    tenant_id: str
    actor_id: str
    scope_actions: List[str]
    scope_resources: List[str]
    expiry: Optional[datetime] = None
    created_at: Optional[datetime] = None
    chain_hash: str


class VerifyRequest(BaseModel):
    credential: str = Field(..., description="gt_ token ID or gd_ decision ID")
    action: str = Field(..., min_length=1)
    resource: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class VerifyResponse(BaseModel):
    valid: bool
    reason: str
    decision_id: Optional[str] = None
    decision_type: Optional[str] = None
    actor_id: Optional[str] = None
    action: Optional[str] = None


class AuditEventResponse(BaseModel):
    event_id: int
    event_ts: datetime
    event_type: str
    tenant_id: str
    actor_id: str
    decision_id: Optional[str] = None
    token_id: Optional[str] = None
    payload: Dict[str, Any]
    event_hash: str


class ChainVerifyResponse(BaseModel):
    valid: bool
    checked_count: int
    first_event_id: Optional[int] = None
    last_event_id: Optional[int] = None
    broken_at_event_id: Optional[int] = None


# ============================================================================
# Helpers
# ============================================================================

def _parse_expiry(data: Dict[str, Any]) -> Optional[datetime]:
    """Parse expiry from vault row data."""
    expiry = data.get("expiry")
    if isinstance(expiry, str):
        return datetime.fromisoformat(expiry.replace("Z", "+00:00"))
    return expiry


async def _get_pool(request):
    """Get database pool from app state."""
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not connected",
        )
    return pool


def _to_decision_response(decision: GovernanceDecision) -> DecisionResponse:
    return DecisionResponse(
        decision_id=decision.decision_id,
        decision_type=decision.decision_type.value,
        tenant_id=decision.tenant_id,
        actor_id=decision.actor_id,
        action=decision.action,
        scope_actions=decision.scope.actions,
        scope_resources=decision.scope.resources,
        expiry=decision.expiry,
        kill_switch_scope=decision.kill_switch_scope.value,
        reason=decision.reason,
        created_at=decision.created_at,
    )


def _build_decision_from_row(data: Dict[str, Any]) -> GovernanceDecision:
    """Reconstruct a GovernanceDecision from a vault row."""
    return GovernanceDecision(
        decision_id=data["decision_id"],
        decision_type=DecisionType(data["decision_type"]),
        tenant_id=data["tenant_id"],
        actor_id=data["actor_id"],
        action=data["action"],
        scope=DecisionScope(
            actions=data["scope_actions"],
            resources=data.get("scope_resources", []),
        ),
        constraints=data.get("constraints", {}),
        expiry=_parse_expiry(data),
        kill_switch_scope=KillSwitchScope(data.get("kill_switch_scope", "request")),
        created_at=data.get("created_at"),
        reason=data.get("reason", ""),
    )


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/governance/decisions",
    response_model=DecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_decision(
    request: Request,
    req: CreateDecisionRequest,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    _: str = Depends(require_api_key),
):
    """
    Create a governance decision.

    This is the first-class artifact. Tokens are derived from decisions.
    """
    pool = await _get_pool(request)

    # Build decision
    expiry = None
    if req.expiry_minutes:
        expiry = datetime.now(timezone.utc) + timedelta(minutes=req.expiry_minutes)

    decision = GovernanceDecision(
        decision_id=GovernanceDecision.generate_id(),
        decision_type=DecisionType(req.decision_type),
        tenant_id=tenant_id,
        actor_id=req.actor_id,
        action=req.action,
        scope=DecisionScope(
            actions=req.scope_actions or [req.action],
            resources=req.scope_resources,
        ),
        constraints=req.constraints,
        expiry=expiry,
        kill_switch_scope=KillSwitchScope(req.kill_switch_scope),
        reason=req.reason,
    )

    # Persist
    vault = TokenVault(pool)
    await vault.store_decision(decision)

    # Audit
    audit = GovernanceAuditTrail(pool)
    await audit.record_decision_created(
        tenant_id=tenant_id,
        actor_id=req.actor_id,
        decision_id=decision.decision_id,
        decision_type=req.decision_type,
        action=req.action,
        reason=req.reason,
    )

    return _to_decision_response(decision)


@router.get("/governance/decisions/{decision_id}", response_model=DecisionResponse)
async def get_decision(
    request: Request,
    decision_id: str,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    _: str = Depends(require_api_key),
):
    """Get a governance decision by ID."""
    pool = await _get_pool(request)
    vault = TokenVault(pool)

    data = await vault.resolve_decision(decision_id, tenant_id=tenant_id)
    if not data:
        raise HTTPException(status_code=404, detail="Decision not found")

    # Verify tenant isolation
    if data.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=404, detail="Decision not found")

    return _to_decision_response(_build_decision_from_row(data))


@router.post(
    "/governance/decisions/{decision_id}/tokens",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def derive_token(
    request: Request,
    decision_id: str,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    _: str = Depends(require_api_key),
):
    """
    Derive a capability token from a governance decision.

    Tokens are portable proofs — they carry the decision's authority.
    """
    pool = await _get_pool(request)
    vault = TokenVault(pool)

    # Fetch decision
    data = await vault.resolve_decision(decision_id, tenant_id=tenant_id)
    if not data:
        raise HTTPException(status_code=404, detail="Decision not found")

    if data.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=404, detail="Decision not found")

    decision = _build_decision_from_row(data)

    # Only ALLOW decisions can produce tokens
    if decision.decision_type != DecisionType.ALLOW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot derive token from {decision.decision_type.value} decision",
        )

    token = CapabilityToken.derive(decision)
    await vault.store_token(token)

    # Audit
    audit = GovernanceAuditTrail(pool)
    await audit.record_token_derived(
        tenant_id=tenant_id,
        actor_id=decision.actor_id,
        token_id=token.token_id,
        decision_id=decision.decision_id,
    )

    return TokenResponse(
        token_id=token.token_id,
        decision_id=token.decision_id,
        tenant_id=token.tenant_id,
        actor_id=token.actor_id,
        scope_actions=token.scope_actions,
        scope_resources=token.scope_resources,
        expiry=token.expiry,
        created_at=token.created_at,
        chain_hash=token.chain_hash,
    )


@router.get("/governance/tokens/{token_id}", response_model=TokenResponse)
async def get_token(
    request: Request,
    token_id: str,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    _: str = Depends(require_api_key),
):
    """Get a capability token by ID."""
    pool = await _get_pool(request)
    vault = TokenVault(pool)

    data = await vault.resolve_token(token_id, tenant_id=tenant_id)
    if not data:
        raise HTTPException(status_code=404, detail="Token not found")

    if data.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=404, detail="Token not found")

    return TokenResponse(
        token_id=data["token_id"],
        decision_id=data["decision_id"],
        tenant_id=data["tenant_id"],
        actor_id=data["actor_id"],
        scope_actions=data["scope_actions"],
        scope_resources=data.get("scope_resources", []),
        expiry=data.get("expiry"),
        created_at=data.get("created_at"),
        chain_hash=data.get("chain_hash", ""),
    )


@router.post("/governance/verify", response_model=VerifyResponse)
async def verify_credential(
    request: Request,
    req: VerifyRequest,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    _: str = Depends(require_api_key),
):
    """
    Verify a token or decision at runtime.

    Checks expiry, revocation, scope, and kill-switch state.
    """
    pool = await _get_pool(request)
    vault = TokenVault(pool)
    audit = GovernanceAuditTrail(pool)
    kill_switch = KillSwitch(audit)
    verifier = TokenVerifier(vault, kill_switch, audit)

    # Determine if token or decision
    if req.credential.startswith("gt_cap_"):
        # Inject tenant_id into context so verifier can resolve via RLS
        context = {**(req.context or {}), "tenant_id": tenant_id}
        result = await verifier.verify_token(
            req.credential, req.action, req.resource, context
        )
    elif req.credential.startswith("gd_"):
        # Fetch decision from vault
        data = await vault.resolve_decision(req.credential, tenant_id=tenant_id)
        if not data:
            return VerifyResponse(valid=False, reason="decision_not_found")

        decision = _build_decision_from_row(data)
        # Inject tenant_id into context for RLS in verifier
        context = {**(req.context or {}), "tenant_id": tenant_id}
        result = await verifier.verify_decision(
            decision, req.action, req.resource, context
        )
    else:
        return VerifyResponse(valid=False, reason="invalid_credential_format")

    return VerifyResponse(
        valid=result.valid,
        reason=result.reason,
        decision_id=result.decision.decision_id if result.decision else None,
        decision_type=result.decision.decision_type.value if result.decision else None,
        actor_id=result.decision.actor_id if result.decision else None,
        action=result.decision.action if result.decision else None,
    )


@router.get("/governance/audit/verify", response_model=ChainVerifyResponse)
async def verify_governance_audit(
    request: Request,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    _: str = Depends(require_api_key),
):
    """Verify the governance audit chain integrity."""
    pool = await _get_pool(request)
    audit = GovernanceAuditTrail(pool)
    result = await audit.verify_chain(tenant_id=tenant_id)

    return ChainVerifyResponse(
        valid=result["valid"],
        checked_count=result["checked_count"],
        first_event_id=result.get("first_event_id"),
        last_event_id=result.get("last_event_id"),
        broken_at_event_id=result.get("broken_at_event_id"),
    )


@router.get("/governance/decisions/{decision_id}/audit", response_model=List[AuditEventResponse])
async def get_decision_audit(
    request: Request,
    decision_id: str,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    limit: int = 100,
    _: str = Depends(require_api_key),
):
    """Get governance audit events for a specific decision."""
    pool = await _get_pool(request)
    audit = GovernanceAuditTrail(pool)
    events = await audit.query_by_decision(decision_id, tenant_id=tenant_id, limit=limit)

    return [
        AuditEventResponse(
            event_id=e["event_id"],
            event_ts=e["event_ts"],
            event_type=e["event_type"],
            tenant_id=e["tenant_id"],
            actor_id=e["actor_id"],
            decision_id=e.get("decision_id"),
            token_id=e.get("token_id"),
            payload=e["payload_json"] if isinstance(e["payload_json"], dict) else {},
            event_hash=e["event_hash"],
        )
        for e in events
    ]
