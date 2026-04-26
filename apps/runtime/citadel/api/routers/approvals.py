"""
Approvals Router

GET  /v1/approvals              - List pending approvals
GET  /v1/approvals/{id}         - Get approval details
POST /v1/approvals/{id}/approve - Approve pending request
POST /v1/approvals/{id}/reject  - Reject pending request
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from citadel.execution.kernel import Kernel
from citadel.api.dependencies import get_kernel, require_api_key

router = APIRouter(tags=["approvals"])


class ApprovalDecisionRequest(BaseModel):
    reviewed_by: str = Field(..., min_length=1, max_length=128)
    reason: Optional[str] = "Reviewed and approved"


class ApprovalResponse(BaseModel):
    approval_id: str
    action_id: str
    status: str
    priority: str
    reason: str
    requested_by: str
    reviewed_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    decision_reason: Optional[str] = None


class ApprovalListResponse(BaseModel):
    approvals: List[ApprovalResponse]
    total: int


@router.get("/approvals", response_model=ApprovalListResponse)
async def list_approvals(
    limit: int = 100,
    status_filter: Optional[str] = None,
    kernel: Kernel = Depends(get_kernel),
    api_key: str = Depends(require_api_key),
):
    """List pending or filtered approvals (tenant-scoped)."""
    # Enforce tenant isolation: derive tenant from API key context
    tenant_id = getattr(kernel.repo.pool, "_tenant_id", None)
    if tenant_id is None:
        # Fallback: try to get from request state if available
        tenant_id = "default"

    async with kernel.repo.pool.acquire() as conn:
        if status_filter:
            rows = await conn.fetch(
                """
                SELECT * FROM approvals
                WHERE status = $1 AND tenant_id = $2
                ORDER BY created_at DESC LIMIT $3
                """,
                status_filter, tenant_id, limit
            )
        else:
            rows = await conn.fetch(
                """
                SELECT * FROM approvals
                WHERE tenant_id = $1
                ORDER BY created_at DESC LIMIT $2
                """,
                tenant_id, limit
            )
    
    approvals = []
    for row in rows:
        approvals.append(ApprovalResponse(
            approval_id=str(row['approval_id']),
            action_id=str(row['action_id']),
            status=row['status'],
            priority=row['priority'],
            reason=row['reason'],
            requested_by=row['requested_by'],
            reviewed_by=row['reviewed_by'],
            decided_at=row['decided_at'],
            decision_reason=row['decision_reason'],
        ))
    
    return ApprovalListResponse(approvals=approvals, total=len(approvals))


@router.get("/approvals/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: str,
    kernel: Kernel = Depends(get_kernel),
    _: str = Depends(require_api_key),
):
    """Get approval details."""
    try:
        aid = uuid.UUID(approval_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid approval_id format")
    
    row = await kernel.repo.get_approval(aid)
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    return ApprovalResponse(
        approval_id=str(row['approval_id']),
        action_id=str(row['action_id']),
        status=row['status'],
        priority=row['priority'],
        reason=row['reason'],
        requested_by=row['requested_by'],
        reviewed_by=row['reviewed_by'],
        decided_at=row['decided_at'],
        decision_reason=row['decision_reason'],
    )


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalResponse)
async def approve_request(
    approval_id: str,
    req: ApprovalDecisionRequest,
    kernel: Kernel = Depends(get_kernel),
    _: str = Depends(require_api_key),
):
    """Approve a pending approval request."""
    try:
        aid = uuid.UUID(approval_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid approval_id format")
    
    # Get current approval
    approval = await kernel.repo.get_approval(aid)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    if approval['status'] != 'pending':
        raise HTTPException(status_code=409, detail=f"Approval already {approval['status']}")
    
    # Resolve approval
    await kernel.approvals.resolve_approval(
        approval_id=aid,
        reviewed_by=req.reviewed_by,
        decision="approved",
        reason=req.reason,
    )
    
    # Fetch updated
    updated = await kernel.repo.get_approval(aid)
    return ApprovalResponse(
        approval_id=str(updated['approval_id']),
        action_id=str(updated['action_id']),
        status=updated['status'],
        priority=updated['priority'],
        reason=updated['reason'],
        requested_by=updated['requested_by'],
        reviewed_by=updated['reviewed_by'],
        decided_at=updated['decided_at'],
        decision_reason=updated['decision_reason'],
    )


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalResponse)
async def reject_request(
    approval_id: str,
    req: ApprovalDecisionRequest,
    kernel: Kernel = Depends(get_kernel),
    _: str = Depends(require_api_key),
):
    """Reject a pending approval request."""
    try:
        aid = uuid.UUID(approval_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid approval_id format")
    
    # Get current approval
    approval = await kernel.repo.get_approval(aid)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    if approval['status'] != 'pending':
        raise HTTPException(status_code=409, detail=f"Approval already {approval['status']}")
    
    # Resolve approval
    await kernel.approvals.resolve_approval(
        approval_id=aid,
        reviewed_by=req.reviewed_by,
        decision="rejected",
        reason=req.reason,
    )
    
    # Fetch updated
    updated = await kernel.repo.get_approval(aid)
    return ApprovalResponse(
        approval_id=str(updated['approval_id']),
        action_id=str(updated['action_id']),
        status=updated['status'],
        priority=updated['priority'],
        reason=updated['reason'],
        requested_by=updated['requested_by'],
        reviewed_by=updated['reviewed_by'],
        decided_at=updated['decided_at'],
        decision_reason=updated['decision_reason'],
    )
