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
    decision_type: str = Field("allow", pattern=r"^(allow|deny|escalate|require_approval|pending|revoked)$")
    decision: Optional[str] = Field(None, pattern=r"^(allow|deny|escalate|require_approval|pending|revoked)$")
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    workspace_id: Optional[str] = None
    agent_id: Optional[str] = None
    subject_type: str = "agent"
    subject_id: Optional[str] = None
    actor_id: str = Field(..., min_length=1, max_length=128)
    action: str = Field(..., min_length=1, max_length=256)
    resource: Optional[str] = None
    risk_level: str = Field("low", pattern=r"^(none|low|medium|high|critical)$")
    policy_version: str = "unknown"
    approval_state: str = Field("auto_approved", pattern=r"^(pending|approved|rejected|auto_approved|expired)$")
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
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
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    workspace_id: str
    agent_id: str
    subject_type: str
    subject_id: str
    actor_id: str
    action: str
    resource: Optional[str] = None
    risk_level: str
    policy_version: str
    approval_state: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    scope_actions: List[str]
    scope_resources: List[str]
    issued_token_id: Optional[str] = None
    expiry: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None
    kill_switch_scope: str
    reason: str
    created_at: Optional[datetime] = None


class DeriveTokenRequest(BaseModel):
    pass  # No body needed; token derived from decision


class TokenResponse(BaseModel):
    token_id: str
    decision_id: str
    iss: str
    subject: str
    audience: str
    tenant_id: str
    workspace_id: str
    actor_id: str
    tool: Optional[str] = None
    action: Optional[str] = None
    resource_scope: Optional[str] = None
    risk_level: str
    scope_actions: List[str]
    scope_resources: List[str]
    expiry: Optional[datetime] = None
    not_before: Optional[datetime] = None
    trace_id: Optional[str] = None
    approval_ref: Optional[str] = None
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None
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


class IntrospectionRequest(BaseModel):
    token: str = Field(..., min_length=1)
    required_action: str = Field(..., min_length=1)
    required_resource: Optional[str] = None
    workspace_id: str = Field(..., min_length=1)
    tool: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class IntrospectionResponse(BaseModel):
    active: bool
    decision_id: Optional[str] = None
    subject: Optional[str] = None
    workspace_id: Optional[str] = None
    tool: Optional[str] = None
    action: Optional[str] = None
    resource_scope: Optional[str] = None
    risk_level: Optional[str] = None
    policy_version: Optional[str] = None
    approval_state: Optional[str] = None
    exp: Optional[int] = None
    kill_switch: bool = False
    reason: Optional[str] = None


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


class TraceabilityGraphNode(BaseModel):
    id: str
    type: str
    title: str
    subtitle: Optional[str] = None
    detail: str = ""
    meta: Dict[str, Any] = Field(default_factory=dict)
    status: str = "evidence"


class TraceabilityGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str
    status: str = "active"


class TraceabilityGraphResponse(BaseModel):
    decision_id: Optional[str] = None
    trace_id: Optional[str] = None
    nodes: List[TraceabilityGraphNode]
    edges: List[TraceabilityGraphEdge]
    source: str = "live"


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
        request_id=decision.request_id,
        trace_id=decision.trace_id,
        workspace_id=decision.workspace_id or decision.tenant_id,
        agent_id=decision.agent_id or decision.actor_id,
        subject_type=decision.subject_type,
        subject_id=decision.subject_id or decision.actor_id,
        actor_id=decision.actor_id,
        action=decision.action,
        resource=decision.resource,
        risk_level=decision.risk_level,
        policy_version=decision.policy_version,
        approval_state=decision.approval_state,
        approved_by=decision.approved_by,
        approved_at=decision.approved_at,
        scope_actions=decision.scope.actions,
        scope_resources=decision.scope.resources,
        issued_token_id=decision.issued_token_id or decision.gt_token,
        expiry=decision.expiry,
        revoked_at=decision.revoked_at,
        revoked_reason=decision.revoked_reason,
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
        request_id=data.get("request_id"),
        trace_id=data.get("trace_id"),
        workspace_id=data.get("workspace_id") or data["tenant_id"],
        agent_id=data.get("agent_id") or data["actor_id"],
        subject_type=data.get("subject_type", "agent"),
        subject_id=data.get("subject_id") or data["actor_id"],
        resource=data.get("resource"),
        risk_level=data.get("risk_level", "low"),
        policy_version=data.get("policy_version", "unknown"),
        approval_state=data.get("approval_state", "auto_approved"),
        approved_by=data.get("approved_by"),
        approved_at=data.get("approved_at"),
        scope=DecisionScope(
            actions=data["scope_actions"],
            resources=data.get("scope_resources", []),
        ),
        constraints=data.get("constraints", {}),
        expiry=_parse_expiry(data),
        kill_switch_scope=KillSwitchScope(data.get("kill_switch_scope", "request")),
        created_at=data.get("created_at"),
        issued_token_id=data.get("issued_token_id"),
        revoked_at=data.get("revoked_at"),
        revoked_reason=data.get("revoked_reason"),
        reason=data.get("reason", ""),
    )


def _to_token_response(data: Dict[str, Any]) -> TokenResponse:
    return TokenResponse(
        token_id=data["token_id"],
        decision_id=data["decision_id"],
        iss=data.get("iss", "citadel"),
        subject=data.get("subject") or data["actor_id"],
        audience=data.get("audience") or data.get("aud", "citadel-runtime"),
        tenant_id=data["tenant_id"],
        workspace_id=data.get("workspace_id") or data["tenant_id"],
        actor_id=data["actor_id"],
        tool=data.get("tool"),
        action=data.get("action"),
        resource_scope=data.get("resource_scope"),
        risk_level=data.get("risk_level", "low"),
        scope_actions=data["scope_actions"],
        scope_resources=data.get("scope_resources", []),
        expiry=data.get("expiry"),
        not_before=data.get("not_before") or data.get("nbf"),
        trace_id=data.get("trace_id"),
        approval_ref=data.get("approval_ref"),
        revoked_at=data.get("revoked_at"),
        revoked_reason=data.get("revoked_reason"),
        created_at=data.get("created_at"),
        chain_hash=data.get("chain_hash", ""),
    )


def _iso(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _short(value: Optional[str], length: int = 18) -> str:
    if not value:
        return "none"
    if len(value) <= length:
        return value
    return f"{value[: length - 6]}...{value[-3:]}"


def _lineage_status(decision_type: Optional[str], revoked_at: Any = None) -> str:
    if revoked_at:
        return "revoked"
    if decision_type in {"deny", "revoked"}:
        return "blocked"
    if decision_type in {"escalate", "require_approval", "pending"}:
        return "pending"
    if decision_type == "allow":
        return "active"
    return "evidence"


def _is_expired(value: Any) -> bool:
    if not value:
        return False

    expiry = value
    if isinstance(expiry, str):
        expiry = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
    if isinstance(expiry, datetime) and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    return isinstance(expiry, datetime) and expiry < datetime.now(timezone.utc)


def _trace_node(
    node_id: str,
    node_type: str,
    title: str,
    detail: str,
    meta: Dict[str, Any],
    status_value: str,
    subtitle: Optional[str] = None,
) -> TraceabilityGraphNode:
    return TraceabilityGraphNode(
        id=node_id,
        type=node_type,
        title=title,
        subtitle=subtitle,
        detail=detail,
        meta={key: _iso(value) for key, value in meta.items() if value is not None},
        status=status_value,
    )


def _trace_edge(
    edge_id: str,
    source: str,
    target: str,
    label: str,
    status_value: str = "active",
) -> TraceabilityGraphEdge:
    return TraceabilityGraphEdge(
        id=edge_id,
        source=source,
        target=target,
        label=label,
        status=status_value,
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

    decision_type = req.decision or req.decision_type
    decision = GovernanceDecision(
        decision_id=GovernanceDecision.generate_id(),
        decision_type=DecisionType(decision_type),
        tenant_id=tenant_id,
        actor_id=req.actor_id,
        action=req.action,
        request_id=req.request_id,
        trace_id=req.trace_id,
        workspace_id=req.workspace_id or tenant_id,
        agent_id=req.agent_id or req.actor_id,
        subject_type=req.subject_type,
        subject_id=req.subject_id or req.actor_id,
        resource=req.resource,
        risk_level=req.risk_level,
        policy_version=req.policy_version,
        approval_state=req.approval_state,
        approved_by=req.approved_by,
        approved_at=req.approved_at,
        scope=DecisionScope(
            actions=req.scope_actions or [req.action],
            resources=req.scope_resources or ([req.resource] if req.resource else []),
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
        decision_type=decision_type,
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

    if decision.issued_token_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Decision already has an issued capability token",
        )

    # Only ALLOW decisions can produce tokens
    if decision.decision_type != DecisionType.ALLOW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot derive token from {decision.decision_type.value} decision",
        )

    token = await vault.issue_token_for_decision(
        decision,
        lifetime_seconds=120 if decision.risk_level in {"high", "critical"} else 300,
        tool=decision.constraints.get("tool"),
    )

    # Audit
    audit = GovernanceAuditTrail(pool)
    await audit.record_token_derived(
        tenant_id=tenant_id,
        actor_id=decision.actor_id,
        token_id=token.token_id,
        decision_id=decision.decision_id,
    )

    return _to_token_response(token.to_public_dict())


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

    return _to_token_response(data)


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


@router.post("/introspect", response_model=IntrospectionResponse)
@router.post("/governance/introspect", response_model=IntrospectionResponse)
async def introspect_token(
    request: Request,
    req: IntrospectionRequest,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    _: str = Depends(require_api_key),
):
    """
    RFC 7662-style runtime introspection for high-risk actions.

    The token is only execution proof. This endpoint resolves the linked
    decision record and checks expiry, revocation, scope, and central
    kill-switch state before a runtime gateway executes the protected action.
    """
    pool = await _get_pool(request)
    vault = TokenVault(pool)
    audit = GovernanceAuditTrail(pool)
    verifier = TokenVerifier(vault, audit_logger=audit)

    context = {
        **(req.context or {}),
        "tenant_id": tenant_id,
        "workspace_id": req.workspace_id,
        "tool": req.tool,
    }
    result = await verifier.introspect_token(
        req.token,
        req.required_action,
        req.required_resource,
        req.workspace_id,
        context,
    )

    decision = result.decision
    token = result.token or {}
    expiry = token.get("expiry")
    if isinstance(expiry, datetime):
        exp = int(expiry.timestamp())
    elif expiry:
        exp = int(datetime.fromisoformat(str(expiry).replace("Z", "+00:00")).timestamp())
    else:
        exp = None

    return IntrospectionResponse(
        active=result.active,
        decision_id=decision.decision_id if decision else token.get("decision_id"),
        subject=token.get("subject") or (decision.subject_id if decision else None),
        workspace_id=token.get("workspace_id") or (decision.workspace_id if decision else req.workspace_id),
        tool=token.get("tool") or req.tool,
        action=token.get("action") or (decision.action if decision else None),
        resource_scope=token.get("resource_scope") or (decision.resource if decision else None),
        risk_level=(decision.risk_level if decision else token.get("risk_level")),
        policy_version=decision.policy_version if decision else None,
        approval_state=decision.approval_state if decision else None,
        exp=exp,
        kill_switch=result.kill_switch,
        reason=result.reason,
    )


@router.get("/governance/traceability", response_model=TraceabilityGraphResponse)
async def get_traceability_graph(
    request: Request,
    decision_id: Optional[str] = None,
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    _: str = Depends(require_api_key),
):
    """
    Return a dashboard-ready lineage graph for a governance decision.

    The graph makes the audit spine explicit: policy version -> decision ->
    capability token -> approval state -> runtime execution -> audit evidence.
    """
    pool = await _get_pool(request)

    async with pool.acquire() as conn:
        await conn.execute("SELECT set_tenant_context($1)", tenant_id)

        if decision_id:
            decision_row = await conn.fetchrow(
                """
                SELECT
                    decision_id, decision_type, tenant_id, actor_id, request_id,
                    trace_id, workspace_id, agent_id, subject_type, subject_id,
                    action, resource, risk_level, policy_version, approval_state,
                    approved_by, approved_at, issued_token_id, expiry,
                    revoked_at, revoked_reason, scope_actions, scope_resources,
                    created_at, reason
                FROM governance_decisions
                WHERE tenant_id = $1 AND decision_id = $2
                LIMIT 1
                """,
                tenant_id,
                decision_id,
            )
        else:
            decision_row = await conn.fetchrow(
                """
                SELECT
                    decision_id, decision_type, tenant_id, actor_id, request_id,
                    trace_id, workspace_id, agent_id, subject_type, subject_id,
                    action, resource, risk_level, policy_version, approval_state,
                    approved_by, approved_at, issued_token_id, expiry,
                    revoked_at, revoked_reason, scope_actions, scope_resources,
                    created_at, reason
                FROM governance_decisions
                WHERE tenant_id = $1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                tenant_id,
            )

        if not decision_row:
            return TraceabilityGraphResponse(nodes=[], edges=[], source="live")

        decision = dict(decision_row)
        active_decision_id = decision["decision_id"]

        token_row = await conn.fetchrow(
            """
            SELECT
                token_id, decision_id, subject, audience, workspace_id, tool,
                action, resource_scope, risk_level, not_before, trace_id,
                approval_ref, revoked_at, revoked_reason, expiry, created_at
            FROM governance_tokens
            WHERE tenant_id = $1 AND decision_id = $2
            ORDER BY created_at DESC
            LIMIT 1
            """,
            tenant_id,
            active_decision_id,
        )

        audit_row = await conn.fetchrow(
            """
            SELECT
                event_id, event_ts, event_type, actor_id, token_id,
                payload_json, event_hash
            FROM governance_audit_log
            WHERE tenant_id = $1 AND decision_id = $2
            ORDER BY event_id DESC
            LIMIT 1
            """,
            tenant_id,
            active_decision_id,
        )

    token = dict(token_row) if token_row else None
    audit_event = dict(audit_row) if audit_row else None
    policy_version = decision.get("policy_version") or "unknown"
    trace_id = decision.get("trace_id") or (token or {}).get("trace_id")

    policy_node_id = f"policy:{policy_version}"
    decision_node_id = f"decision:{active_decision_id}"
    approval_node_id = f"approval:{active_decision_id}"
    execution_node_id = f"execution:{active_decision_id}"

    nodes: List[TraceabilityGraphNode] = [
        _trace_node(
            policy_node_id,
            "policy",
            policy_version,
            "Exact policy version captured when Citadel evaluated the action.",
            {"policy_version": policy_version},
            "verified",
        ),
        _trace_node(
            decision_node_id,
            "decision",
            str(decision.get("decision_type", "decision")).replace("_", " ").title(),
            decision.get("reason") or f"{decision.get('action')} on {decision.get('resource') or 'resource'}",
            {
                "decision_id": active_decision_id,
                "request_id": decision.get("request_id"),
                "trace_id": trace_id,
                "workspace_id": decision.get("workspace_id"),
                "actor_id": decision.get("actor_id"),
                "risk_level": decision.get("risk_level"),
                "created_at": decision.get("created_at"),
            },
            _lineage_status(decision.get("decision_type"), decision.get("revoked_at")),
            subtitle=decision.get("action"),
        ),
        _trace_node(
            approval_node_id,
            "approval",
            str(decision.get("approval_state", "unknown")).replace("_", " ").title(),
            "Approval state is preserved on the durable decision record.",
            {
                "approval_state": decision.get("approval_state"),
                "approved_by": decision.get("approved_by"),
                "approved_at": decision.get("approved_at"),
            },
            str(decision.get("approval_state") or "evidence"),
        ),
        _trace_node(
            execution_node_id,
            "execution",
            decision.get("action") or "runtime action",
            f"Protected runtime operation scoped to {decision.get('resource') or 'any resource'}.",
            {
                "resource": decision.get("resource"),
                "workspace_id": decision.get("workspace_id"),
                "risk_level": decision.get("risk_level"),
            },
            "executed" if audit_event else _lineage_status(decision.get("decision_type")),
        ),
    ]

    edges: List[TraceabilityGraphEdge] = [
        _trace_edge("policy-decision", policy_node_id, decision_node_id, "evaluates"),
        _trace_edge("decision-approval", decision_node_id, approval_node_id, "preserves state"),
        _trace_edge("approval-execution", approval_node_id, execution_node_id, "authorizes"),
    ]

    if token:
        token_node_id = f"token:{token['token_id']}"
        token_status = "revoked" if token.get("revoked_at") else "active"
        if _is_expired(token.get("expiry")):
            token_status = "expired"

        nodes.append(
            _trace_node(
                token_node_id,
                "token",
                _short(token["token_id"], 24),
                "Short-lived gt_cap_ execution proof bound to exactly one decision.",
                {
                    "token_id": token.get("token_id"),
                    "decision_id": token.get("decision_id"),
                    "tool": token.get("tool"),
                    "action": token.get("action"),
                    "resource_scope": token.get("resource_scope"),
                    "expiry": token.get("expiry"),
                },
                token_status,
            )
        )
        edges.extend(
            [
                _trace_edge("decision-token", decision_node_id, token_node_id, "issues"),
                _trace_edge("token-execution", token_node_id, execution_node_id, "introspected"),
            ]
        )

    if audit_event:
        audit_node_id = f"audit:{audit_event['event_id']}"
        nodes.append(
            _trace_node(
                audit_node_id,
                "audit",
                str(audit_event.get("event_type", "audit event")).replace("_", " ").title(),
                "Latest hash-chained governance event for this decision.",
                {
                    "event_id": audit_event.get("event_id"),
                    "event_hash": audit_event.get("event_hash"),
                    "event_ts": audit_event.get("event_ts"),
                    "token_id": audit_event.get("token_id"),
                },
                "evidence",
            )
        )
        edges.append(_trace_edge("execution-audit", execution_node_id, audit_node_id, "records outcome"))

    return TraceabilityGraphResponse(
        decision_id=active_decision_id,
        trace_id=trace_id,
        nodes=nodes,
        edges=edges,
        source="live",
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
