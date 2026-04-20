"""
Metrics Router

GET /v1/metrics/summary - Human-readable metrics summary
"""

from typing import Dict, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ledger.kernel import Kernel
from ledger.api.dependencies import get_kernel, require_api_key

router = APIRouter(tags=["metrics"])


class MetricsSummaryResponse(BaseModel):
    actions_total: int
    decisions_by_status: Dict[str, int]
    pending_approvals: int
    audit_events: int
    kill_switches_active: int
    capabilities_active: int


@router.get("/metrics/summary", response_model=MetricsSummaryResponse)
async def metrics_summary(
    kernel: Kernel = Depends(get_kernel),
    _: str = Depends(require_api_key),
):
    """Human-readable governance metrics."""
    async with kernel.repo.pool.acquire() as conn:
        actions_total = await conn.fetchval("SELECT COUNT(*) FROM actions")
        
        decision_rows = await conn.fetch(
            "SELECT status, COUNT(*) as count FROM decisions GROUP BY status"
        )
        decisions_by_status = {r['status']: r['count'] for r in decision_rows}
        
        pending_approvals = await conn.fetchval(
            "SELECT COUNT(*) FROM approvals WHERE status = 'pending'"
        )
        
        audit_events = await conn.fetchval("SELECT COUNT(*) FROM audit_events")
        
        kill_switches_active = await conn.fetchval(
            "SELECT COUNT(*) FROM kill_switches WHERE enabled = TRUE"
        )
        
        capabilities_active = await conn.fetchval(
            "SELECT COUNT(*) FROM capabilities WHERE revoked = FALSE AND uses < max_uses"
        )
    
    return MetricsSummaryResponse(
        actions_total=actions_total or 0,
        decisions_by_status=decisions_by_status,
        pending_approvals=pending_approvals or 0,
        audit_events=audit_events or 0,
        kill_switches_active=kill_switches_active or 0,
        capabilities_active=capabilities_active or 0,
    )
