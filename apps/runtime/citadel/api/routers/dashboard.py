import uuid
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from citadel.execution.kernel import Kernel
from citadel.api.dependencies import get_kernel, require_api_key

router = APIRouter(tags=["dashboard"])

class ApprovalDecisionRequest(BaseModel):
    reviewed_by: str = Field(..., min_length=1, max_length=128)
    reason: Optional[str] = Field(default="Reviewed and approved", max_length=500)

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    request: Request,
    kernel: Kernel = Depends(get_kernel),
    _: str = Depends(require_api_key),
) -> Dict[str, Any]:
    """Get consolidated statistics for the dashboard."""
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    
    async with kernel.repo.pool.acquire() as conn:
        pending_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM approvals a
            JOIN actions act ON a.action_id = act.action_id
            WHERE act.tenant_id = $1 AND a.status = 'pending'
            """,
            tenant_id
        ) or 0

        # Total actions
        total_actions = await conn.fetchval(
            "SELECT COUNT(*) FROM actions WHERE tenant_id = $1",
            tenant_id
        ) or 0
        
        # Approved this month (using decisions table status or audit_events)
        approved_month = await conn.fetchval(
            """
            SELECT COUNT(*) FROM audit_events 
            WHERE tenant_id = $1 
            AND event_type = 'approval_granted'
            AND event_ts > NOW() - INTERVAL '30 days'
            """,
            tenant_id
        ) or 0
        
        # Blocked this month (using audit_events kill_switch or action_failed/policy_evaluated)
        # Using a simplified check for demo
        blocked_month = await conn.fetchval(
            """
            SELECT COUNT(*) FROM audit_events 
            WHERE tenant_id = $1 
            AND event_type IN ('action_failed', 'kill_switch_activated')
            AND event_ts > NOW() - INTERVAL '30 days'
            """,
            tenant_id
        ) or 0
        
        # Active agents (from actions table — agents that performed actions)
        active_agents = await conn.fetchval(
            """
            SELECT COUNT(DISTINCT actor_id) FROM actions 
            WHERE tenant_id = $1
            AND created_at > NOW() - INTERVAL '24 hours'
            """,
            tenant_id
        ) or 0

        # ---- Agent Identity Stats ----
        registered_identities = await conn.fetchval(
            "SELECT COUNT(*) FROM agent_identities WHERE tenant_id = $1",
            tenant_id
        ) or 0

        verified_identities = await conn.fetchval(
            """
            SELECT COUNT(*) FROM agent_identities
            WHERE tenant_id = $1 AND verified = TRUE AND revoked = FALSE
            """,
            tenant_id
        ) or 0

        revoked_identities = await conn.fetchval(
            """
            SELECT COUNT(*) FROM agent_identities
            WHERE tenant_id = $1 AND revoked = TRUE
            """,
            tenant_id
        ) or 0

        avg_trust_score = await conn.fetchval(
            """
            SELECT COALESCE(AVG(trust_score), 0.0)
            FROM agent_identities
            WHERE tenant_id = $1 AND revoked = FALSE
            """,
            tenant_id
        ) or 0.0

        trust_breakdown = await conn.fetch(
            """
            SELECT trust_level, COUNT(*) as cnt
            FROM agent_identities
            WHERE tenant_id = $1 AND revoked = FALSE
            GROUP BY trust_level
            """,
            tenant_id
        )
        trust_levels = {row["trust_level"]: row["cnt"] for row in trust_breakdown}

        kill_switches_active = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM kill_switches
            WHERE tenant_id = $1 AND enabled = TRUE
            """,
            tenant_id
        ) or 0

        recent_events_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM audit_events
            WHERE tenant_id = $1
            AND event_ts > NOW() - INTERVAL '24 hours'
            """,
            tenant_id
        ) or 0
        
        return {
            "pending_approvals": pending_count,
            "active_agents": active_agents,
            "risk_level": "HIGH" if blocked_month else "LOW",
            "kill_switches_active": kill_switches_active,
            "killswitches": {
                "email_send": kill_switches_active > 0,
                "stripe_charge": kill_switches_active > 0,
                "db_write": kill_switches_active > 0,
            },
            "recent_events_count": recent_events_count,
            "total_actions": total_actions,
            "approved_this_month": approved_month,
            "blocked_this_month": blocked_month,
            "active_agents_24h": active_agents,
            "agent_identities": {
                "registered": registered_identities,
                "verified": verified_identities,
                "revoked": revoked_identities,
                "avg_trust_score": round(float(avg_trust_score), 3),
                "trust_level_breakdown": trust_levels,
            },
        }

@router.get("/dashboard/approvals")
async def list_dashboard_approvals(
    request: Request,
    kernel: Kernel = Depends(get_kernel),
    _: str = Depends(require_api_key),
):
    """List pending approvals for the dashboard operator."""
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    
    async with kernel.repo.pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT a.approval_id, a.action_id, a.status, a.priority, a.reason, a.requested_by, a.created_at, a.expires_at, act.action_name, act.resource
            FROM approvals a
            JOIN actions act ON a.action_id = act.action_id
            WHERE act.tenant_id = $1 AND a.status = 'pending'
            ORDER BY a.created_at DESC
            """,
            tenant_id
        )
    
    return {
        "approvals": [
            {
                "id": str(row['approval_id']),
                "action": row['action_name'],
                "resource": row['resource'],
                "risk": row['priority'],
                "requested_at": row['created_at'].isoformat() if row['created_at'] else None,
                "expires_at": row['expires_at'].isoformat() if row['expires_at'] else None,
                "assigned_to": row['requested_by'],
                "reason": row['reason'],
            } for row in rows
        ]
    }

@router.post("/dashboard/approvals/{approval_id}/approve")
async def approve_dashboard_request(
    approval_id: str,
    req: ApprovalDecisionRequest,
    kernel: Kernel = Depends(get_kernel),
    _: str = Depends(require_api_key),
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
    _: str = Depends(require_api_key),
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
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0, le=10000),
    kernel: Kernel = Depends(get_kernel),
    _: str = Depends(require_api_key),
):
    """List recent audit logs for the dashboard operator."""
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    
    async with kernel.repo.pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT 
                e.event_id, e.event_type, e.actor_id, e.event_ts,
                a.action_name, a.resource, d.status as decision_status
            FROM audit_events e
            LEFT JOIN actions a ON e.action_id = a.action_id
            LEFT JOIN decisions d ON e.action_id = d.action_id
            WHERE e.tenant_id = $1
            ORDER BY e.event_ts DESC
            LIMIT $2 OFFSET $3
            """,
            tenant_id, limit, offset
        )
    
    return {
        "events": [
            {
                "id": str(row['event_id']),
                "type": row['event_type'],
                "actor": row['actor_id'] or "system",
                "resource": f"{row['action_name']}:{row['resource']}" if row['action_name'] else "system",
                "status": row['decision_status'] or "pending",
                "timestamp": row['event_ts'].isoformat() if row['event_ts'] else None,
                "severity": "high" if row['event_type'] in ('action_failed', 'kill_switch_activated') else "medium",
            } for row in rows
        ]
    }

class KillSwitchBody(BaseModel):
    scope: Literal["agent", "tenant", "global"]
    target_id: Optional[str] = Field(None, max_length=128)
    reason: str = Field(..., min_length=1, max_length=500)


@router.post("/dashboard/kill-switch")
async def trigger_kill_switch(
    body: KillSwitchBody,
    request: Request,
    kernel: Kernel = Depends(get_kernel),
    _: str = Depends(require_api_key),
):
    tenant_id = getattr(request.state, "tenant_id", None)
    user_id = getattr(request.state, "user_id", None)
    if not tenant_id or not user_id:
        raise HTTPException(status_code=401, detail="unauthenticated")

    # Role check: only admin can trigger kill switches
    role = getattr(request.state, "role", None)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")

    # Validate target_id belongs to this tenant when scoped to an agent
    if body.scope == "agent":
        if not body.target_id:
            raise HTTPException(status_code=400, detail="target_id required for agent scope")
        async with kernel.repo.pool.acquire() as conn:
            owned = await conn.fetchval(
                "SELECT 1 FROM agents WHERE tenant_id = $1 AND agent_id = $2",
                tenant_id, body.target_id,
            )
        if not owned:
            raise HTTPException(status_code=404, detail="agent not found in tenant scope")

    scope_value = body.target_id or tenant_id
    async with kernel.repo.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO kill_switches (tenant_id, scope_type, scope_value, enabled, reason, created_by)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (tenant_id, scope_type, scope_value)
            DO UPDATE SET enabled = EXCLUDED.enabled, reason = EXCLUDED.reason, updated_at = NOW()
            """,
            tenant_id, body.scope, scope_value, True, body.reason, user_id,
        )

    return {
        "status": "success",
        "kill_switch_id": str(uuid.uuid4()),
        "scope": body.scope,
        "target_id": scope_value,
    }
