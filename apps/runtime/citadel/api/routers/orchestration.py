"""
Orchestration Router

POST /v1/orchestrate/delegate - Delegate authority to a child agent
POST /v1/orchestrate/handoff  - Transfer active authority to another agent
POST /v1/orchestrate/gather   - Run parallel branches under one root
POST /v1/orchestrate/introspect - Runtime safety check for any grant
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from citadel.actions import Action
from citadel.execution.orchestration import (
    OrchestrationRuntime,
    DelegationResult,
    HandoffResult,
    GatherResult,
    IntrospectionStatus,
)
from citadel.tokens.governance_decision import GovernanceDecision, DecisionScope, DecisionType, KillSwitchScope
from citadel.api.dependencies import get_orchestration_runtime, require_api_key

router = APIRouter(tags=["orchestration"], prefix="/orchestrate")


# =========================================================================
# Request / Response Models
# =========================================================================

class DecisionScopeModel(BaseModel):
    actions: List[str] = []
    resources: List[str] = []
    max_spend: Optional[float] = None
    rate_limit: Optional[int] = None


class DelegateRequest(BaseModel):
    parent_decision_id: str
    child_actor_id: str
    action_name: str = Field(..., pattern=r"^\w+\.\w+$")
    resource: str
    scope: DecisionScopeModel
    payload: Dict[str, Any] = {}
    context: Dict[str, Any] = {}
    tenant_id: Optional[str] = None
    trace_id: Optional[str] = None
    workflow_id: Optional[str] = None
    dry_run: bool = False


class DelegateResponse(BaseModel):
    success: bool
    child_action_id: Optional[str] = None
    child_decision_id: Optional[str] = None
    child_grant: Optional[str] = None
    reason: str
    error: Optional[str] = None


class HandoffRequest(BaseModel):
    current_decision_id: str
    new_actor_id: str
    action_name: str = Field(..., pattern=r"^\w+\.\w+$")
    resource: str
    scope: DecisionScopeModel
    payload: Dict[str, Any] = {}
    context: Dict[str, Any] = {}
    tenant_id: Optional[str] = None
    trace_id: Optional[str] = None
    workflow_id: Optional[str] = None
    reason: str = ""
    dry_run: bool = False


class HandoffResponse(BaseModel):
    success: bool
    new_decision_id: Optional[str] = None
    new_grant: Optional[str] = None
    previous_authority_superseded: bool
    reason: str
    error: Optional[str] = None


class GatherBranchRequest(BaseModel):
    actor_id: Optional[str] = None
    actor_type: str = "agent"
    action: str = Field(..., pattern=r"^\w+\.\w+$")
    resource: str
    payload: Dict[str, Any] = {}
    context: Dict[str, Any] = {}


class GatherRequest(BaseModel):
    parent_decision_id: str
    branches: List[GatherBranchRequest]
    tenant_id: Optional[str] = None
    trace_id: Optional[str] = None
    workflow_id: Optional[str] = None
    dry_run: bool = False


class GatherBranchResponse(BaseModel):
    branch_index: int
    success: bool
    action_id: Optional[str] = None
    decision_id: Optional[str] = None
    error: Optional[str] = None


class GatherResponse(BaseModel):
    success: bool
    branches: List[GatherBranchResponse]
    completed: int
    failed: int
    reason: str
    error: Optional[str] = None


class IntrospectRequest(BaseModel):
    token_id: Optional[str] = None
    decision_id: Optional[str] = None
    required_action: str = ""
    required_resource: Optional[str] = None
    workspace_id: Optional[str] = None
    tenant_id: Optional[str] = None


class IntrospectResponse(BaseModel):
    active: bool
    reason: Optional[str] = None
    kill_switched: bool = False
    expired: bool = False
    revoked: bool = False
    scope_valid: bool = False
    actor_boundary_valid: bool = True


# =========================================================================
# Helpers
# =========================================================================

def _scope_model_to_domain(scope: DecisionScopeModel) -> DecisionScope:
    return DecisionScope(
        actions=scope.actions,
        resources=scope.resources,
        max_spend=scope.max_spend,
        rate_limit=scope.rate_limit,
    )


async def _resolve_parent_decision(runtime: OrchestrationRuntime, decision_id: str, tenant_id: Optional[str]) -> GovernanceDecision:
    """Resolve a governance decision by ID via the token vault."""
    data = await runtime.vault.resolve_decision(decision_id, tenant_id=tenant_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Decision {decision_id} not found")

    # Reconstruct GovernanceDecision (lightweight; full logic is in verifier)
    from datetime import timezone
    expiry = data.get("expiry") or data.get("expires_at")
    if isinstance(expiry, str):
        from datetime import datetime as dt
        expiry = dt.fromisoformat(expiry.replace("Z", "+00:00"))

    return GovernanceDecision(
        decision_id=data["decision_id"],
        decision_type=DecisionType(data["decision_type"]),
        tenant_id=data["tenant_id"],
        actor_id=data["actor_id"],
        action=data["action"],
        scope=DecisionScope(
            actions=data.get("scope_actions", []),
            resources=data.get("scope_resources", []),
        ),
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
        constraints=data.get("constraints", {}),
        expiry=expiry,
        kill_switch_scope=KillSwitchScope(data.get("kill_switch_scope", "request")),
        created_at=data.get("created_at"),
        issued_token_id=data.get("issued_token_id"),
        revoked_at=data.get("revoked_at"),
        revoked_reason=data.get("revoked_reason"),
        reason=data.get("reason", ""),
        root_decision_id=data.get("root_decision_id"),
        parent_decision_id=data.get("parent_decision_id"),
        parent_actor_id=data.get("parent_actor_id"),
        workflow_id=data.get("workflow_id"),
        superseded_at=data.get("superseded_at"),
        superseded_reason=data.get("superseded_reason"),
    )


# =========================================================================
# Endpoints
# =========================================================================

@router.post("/delegate", response_model=DelegateResponse)
async def delegate(
    req: DelegateRequest,
    runtime: OrchestrationRuntime = Depends(get_orchestration_runtime),
    _: str = Depends(require_api_key),
):
    """
    Delegate authority from a parent decision to a child agent.
    """
    parent = await _resolve_parent_decision(runtime, req.parent_decision_id, req.tenant_id)
    result: DelegationResult = await runtime.delegate(
        parent_decision=parent,
        child_actor_id=req.child_actor_id,
        action_name=req.action_name,
        resource=req.resource,
        scope=_scope_model_to_domain(req.scope),
        payload=req.payload,
        context=req.context,
        tenant_id=req.tenant_id,
        trace_id=req.trace_id,
        workflow_id=req.workflow_id,
        dry_run=req.dry_run,
    )
    return DelegateResponse(
        success=result.success,
        child_action_id=str(result.child_action.action_id) if result.child_action else None,
        child_decision_id=str(result.child_decision.decision_id) if result.child_decision else None,
        child_grant=result.child_grant,
        reason=result.reason,
        error=result.error,
    )


@router.post("/handoff", response_model=HandoffResponse)
async def handoff(
    req: HandoffRequest,
    runtime: OrchestrationRuntime = Depends(get_orchestration_runtime),
    _: str = Depends(require_api_key),
):
    """
    Transfer active authority from one agent to another.
    """
    current = await _resolve_parent_decision(runtime, req.current_decision_id, req.tenant_id)
    result: HandoffResult = await runtime.handoff(
        current_decision=current,
        new_actor_id=req.new_actor_id,
        action_name=req.action_name,
        resource=req.resource,
        scope=_scope_model_to_domain(req.scope),
        payload=req.payload,
        context=req.context,
        tenant_id=req.tenant_id,
        trace_id=req.trace_id,
        workflow_id=req.workflow_id,
        reason=req.reason,
        dry_run=req.dry_run,
    )
    return HandoffResponse(
        success=result.success,
        new_decision_id=str(result.new_decision.decision_id) if result.new_decision else None,
        new_grant=result.new_grant,
        previous_authority_superseded=result.previous_authority_superseded,
        reason=result.reason,
        error=result.error,
    )


@router.post("/gather", response_model=GatherResponse)
async def gather(
    req: GatherRequest,
    runtime: OrchestrationRuntime = Depends(get_orchestration_runtime),
    _: str = Depends(require_api_key),
):
    """
    Run parallel child branches under one parent orchestration scope.
    """
    parent = await _resolve_parent_decision(runtime, req.parent_decision_id, req.tenant_id)
    branches = [
        {
            "actor_id": b.actor_id,
            "actor_type": b.actor_type,
            "action": b.action,
            "resource": b.resource,
            "payload": b.payload,
            "context": b.context,
        }
        for b in req.branches
    ]
    result: GatherResult = await runtime.gather(
        parent_decision=parent,
        branches=branches,
        tenant_id=req.tenant_id,
        trace_id=req.trace_id,
        workflow_id=req.workflow_id,
        dry_run=req.dry_run,
    )
    return GatherResponse(
        success=result.success,
        branches=[
            GatherBranchResponse(
                branch_index=br.branch_index,
                success=br.success,
                action_id=str(br.action.action_id) if br.action else None,
                decision_id=str(br.decision.decision_id) if br.decision else None,
                error=br.error,
            )
            for br in result.branches
        ],
        completed=result.completed,
        failed=result.failed,
        reason=result.reason,
        error=result.error,
    )


@router.post("/introspect", response_model=IntrospectResponse)
async def introspect(
    req: IntrospectRequest,
    runtime: OrchestrationRuntime = Depends(get_orchestration_runtime),
    _: str = Depends(require_api_key),
):
    """
    Runtime safety check for any grant or decision.
    """
    status: IntrospectionStatus = await runtime.introspect(
        token_id=req.token_id,
        decision_id=req.decision_id,
        required_action=req.required_action,
        required_resource=req.required_resource,
        workspace_id=req.workspace_id,
        tenant_id=req.tenant_id,
    )
    return IntrospectResponse(
        active=status.active,
        reason=status.reason,
        kill_switched=status.kill_switched,
        expired=status.expired,
        revoked=status.revoked,
        scope_valid=status.scope_valid,
        actor_boundary_valid=status.actor_boundary_valid,
    )
