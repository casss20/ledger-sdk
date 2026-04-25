"""
Actions Router

POST /v1/actions        - Submit action for governance
GET  /v1/actions/{id}   - Lookup action + decision
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from citadel.actions import Action, KernelStatus
from citadel.execution.kernel import Kernel
from citadel.api.dependencies import get_kernel, require_api_key

router = APIRouter(tags=["actions"])


class SubmitActionRequest(BaseModel):
    actor_id: str = Field(..., min_length=1, max_length=128)
    actor_type: str = "agent"
    action_name: str = Field(..., pattern=r"^\w+\.\w+$")
    resource: str = Field(..., min_length=1, max_length=256)
    tenant_id: Optional[str] = None
    payload: Dict[str, Any] = {}
    context: Dict[str, Any] = {}
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    idempotency_key: Optional[str] = Field(None, max_length=256)
    capability_token: Optional[str] = None
    dry_run: bool = False  # If True, evaluate policies but don't execute


class ActionResponse(BaseModel):
    action_id: str
    status: str  # lowercase: executed, blocked, pending_approval, etc.
    winning_rule: str
    reason: str
    executed: bool
    result: Optional[Any] = None
    error: Optional[str] = None

    model_config = {"json_schema_extra": {
        "example": {
            "action_id": "uuid",
            "status": "blocked",
            "winning_rule": "policy_hard_deny",
            "reason": "amount exceeds policy",
            "executed": False,
            "result": None,
            "error": None,
        }
    }}


class ActionDetailResponse(BaseModel):
    action_id: str
    actor_id: str
    action_name: str
    resource: str
    status: str
    winning_rule: str
    reason: str
    executed: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None


@router.post("/actions", response_model=ActionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_action(
    req: SubmitActionRequest,
    kernel: Kernel = Depends(get_kernel),
    _: str = Depends(require_api_key),
):
    """Submit an action for governance evaluation."""
    action = Action(
        action_id=uuid.uuid4(),
        actor_id=req.actor_id,
        actor_type=req.actor_type,
        action_name=req.action_name,
        resource=req.resource,
        tenant_id=req.tenant_id,
        payload=req.payload,
        context=req.context,
        session_id=req.session_id,
        request_id=req.request_id or str(uuid.uuid4()),
        idempotency_key=req.idempotency_key,
        created_at=datetime.utcnow(),
    )
    
    result = await kernel.handle(action, capability_token=req.capability_token, dry_run=req.dry_run)
    
    # Convert status to lowercase for API consistency
    status_value = result.decision.status.value.lower()
    
    return ActionResponse(
        action_id=str(result.action.action_id),
        status=status_value,
        winning_rule=result.decision.winning_rule,
        reason=result.decision.reason,
        executed=result.executed,
        result=result.result,
        error=result.error,
    )


@router.post("/actions/execute", response_model=ActionResponse, status_code=status.HTTP_202_ACCEPTED)
async def execute_action(
    req: SubmitActionRequest,
    kernel: Kernel = Depends(get_kernel),
    _: str = Depends(require_api_key),
):
    """
    Execute an action under governance control.
    
    Universal entry point — the single primitive Citadel exposes.
    Same as POST /actions, named explicitly for clarity.
    """
    return await submit_action(req, kernel, _)


@router.get("/actions/{action_id}", response_model=ActionDetailResponse)
async def get_action(
    action_id: str,
    kernel: Kernel = Depends(get_kernel),
    _: str = Depends(require_api_key),
):
    """Get action details and its decision."""
    try:
        aid = uuid.UUID(action_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid action_id format")
    
    action_row = await kernel.repo.get_action(aid)
    if not action_row:
        raise HTTPException(status_code=404, detail="Action not found")
    
    decision = await kernel.repo.get_decision(aid)
    
    return ActionDetailResponse(
        action_id=str(action_row['action_id']),
        actor_id=action_row['actor_id'],
        action_name=action_row['action_name'],
        resource=action_row['resource'],
        status=decision.status.value if decision else "unknown",
        winning_rule=decision.winning_rule if decision else "none",
        reason=decision.reason if decision else "No decision recorded",
        executed=decision.status == KernelStatus.EXECUTED if decision else False,
        created_at=action_row['created_at'],
    )
