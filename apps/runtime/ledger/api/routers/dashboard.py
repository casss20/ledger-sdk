import uuid
from fastapi import APIRouter, Depends, Request, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from ledger.execution.kernel import Kernel
from ledger.api.dependencies import get_kernel

router = APIRouter(tags=["dashboard"])

class ApprovalDecisionRequest(BaseModel):
    reviewed_by: str = Field(..., min_length=1, max_length=128)
    reason: Optional[str] = "Reviewed and approved"

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    request: Request,
    kernel: Kernel = Depends(get_kernel),
) -> Dict[str, Any]:
    """Get consolidated statistics for the dashboard."""
    async with kernel.repo.pool.acquire() as conn:
        pending_count = await conn.fetchval("SELECT count(*) FROM approvals WHERE status = 'pending'")
        active_agents = await conn.fetchval(
            "SELECT count(distinct user_id) FROM audit_log WHERE created_at > now() - interval '1 hour'"
        ) or 0
        
        return {
            "pending_approvals": pending_count,
            "active_agents": active_agents,
            "risk_level": "MEDIUM",
            "killswitches": {
                "email_send": False,
                "stripe_charge": True,
                "db_write": False,
            },
            "recent_events_count": 142
        }

@router.get("/dashboard/approvals")
async def list_dashboard_approvals(
    kernel: Kernel = Depends(get_kernel),
):
    """List pending approvals for the dashboard operator."""
    async with kernel.repo.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM approvals WHERE status = 'pending' ORDER BY created_at DESC"
        )
    
    return {
        "approvals": [
            {
                "approval_id": str(row['approval_id']),
                "action_id": str(row['action_id']),
                "status": row['status'],
                "priority": row['priority'],
                "reason": row['reason'],
                "requested_by": row['requested_by'],
            } for row in rows
        ]
    }

@router.post("/dashboard/approvals/{approval_id}/approve")
async def approve_dashboard_request(
    approval_id: str,
    req: ApprovalDecisionRequest,
    kernel: Kernel = Depends(get_kernel),
):
    """Approve a request via the dashboard."""
    try:
        aid = uuid.UUID(approval_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID")
    
    await kernel.approval_service.resolve_approval(
        approval_id=aid,
        reviewed_by=req.reviewed_by,
        decision="approved",
        reason=req.reason,
    )
    return {"status": "approved"}

@router.post("/dashboard/approvals/{approval_id}/reject")
async def reject_dashboard_request(
    approval_id: str,
    req: ApprovalDecisionRequest,
    kernel: Kernel = Depends(get_kernel),
):
    """Reject a request via the dashboard."""
    try:
        aid = uuid.UUID(approval_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID")
    
    await kernel.approval_service.resolve_approval(
        approval_id=aid,
        reviewed_by=req.reviewed_by,
        decision="rejected",
        reason=req.reason,
    )
    return {"status": "rejected"}

@router.get("/dashboard/audit")
async def list_dashboard_audit(
    limit: int = 100,
    kernel: Kernel = Depends(get_kernel),
):
    """List recent audit logs for the dashboard operator."""
    async with kernel.repo.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT $1",
            limit
        )
    
    return {
        "events": [
            {
                "event_id": str(row['event_id']),
                "action_id": str(row['action_id']),
                "user_id": row['user_id'],
                "action_type": row['action_type'],
                "status": row['status'],
                "risk_score": row['risk_score'],
                "created_at": row['created_at'].isoformat(),
            } for row in rows
        ]
    }
