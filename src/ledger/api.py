"""
Ledger API - Thin HTTP surface over the governance kernel.

Not full productization. Just enough to prove the kernel externally.

Run: uvicorn ledger.api:app --reload
"""

from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field

import asyncpg

from ledger.kernel import Kernel, Action, KernelStatus
from ledger.repository import Repository
from ledger.policy_resolver import PolicyResolver, PolicyEvaluator
from ledger.precedence import Precedence
from ledger.approval_service import ApprovalService
from ledger.capability_service import CapabilityService
from ledger.audit_service import AuditService
from ledger.executor import Executor as ActionExecutor


# ============================================================================
# Pydantic Models
# ============================================================================

class SubmitActionRequest(BaseModel):
    actor_id: str
    actor_type: str = "agent"
    action_name: str = Field(..., pattern=r"^\w+\.\w+$")
    resource: str
    tenant_id: Optional[str] = None
    payload: Dict[str, Any] = {}
    context: Dict[str, Any] = {}
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    capability_token: Optional[str] = None


class ActionResponse(BaseModel):
    action_id: str
    status: str
    winning_rule: str
    reason: str
    executed: bool
    result: Optional[Any] = None
    error: Optional[str] = None


class ApprovalResponse(BaseModel):
    approval_id: str
    status: str
    action_id: str
    reason: str
    requested_by: str
    reviewed_by: Optional[str] = None
    decided_at: Optional[datetime] = None


class AuditVerifyResponse(BaseModel):
    valid: bool
    checked_count: int
    broken_at_event_id: Optional[int] = None


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="Ledger Governance API",
    description="Thin HTTP surface over the Ledger governance kernel",
    version="0.1.0",
)

# Database pool (initialized on startup)
_pool: Optional[asyncpg.Pool] = None


async def get_kernel() -> Kernel:
    """Dependency: Get kernel instance with fresh DB pool."""
    global _pool
    if _pool is None:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    repo = Repository(_pool)
    policy_resolver = PolicyResolver(repo)
    policy_evaluator = PolicyEvaluator()
    precedence = Precedence(repo, policy_evaluator)
    approval_service = ApprovalService(repo)
    capability_service = CapabilityService(repo)
    audit_service = AuditService(repo)
    executor = ActionExecutor()
    
    return Kernel(
        repository=repo,
        policy_resolver=policy_resolver,
        precedence=precedence,
        approval_service=approval_service,
        capability_service=capability_service,
        audit_service=audit_service,
        executor=executor,
    )


@app.on_event("startup")
async def startup():
    """Initialize database pool."""
    global _pool
    _pool = await asyncpg.create_pool(
        "postgresql://ledger:ledger@127.0.0.1:5432/ledger",
        min_size=2,
        max_size=10,
    )


@app.on_event("shutdown")
async def shutdown():
    """Close database pool."""
    global _pool
    if _pool:
        await _pool.close()


# ============================================================================
# Endpoints
# ============================================================================

@app.post("/actions", response_model=ActionResponse)
async def submit_action(req: SubmitActionRequest, kernel: Kernel = Depends(get_kernel)):
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
    
    result = await kernel.handle(action, capability_token=req.capability_token)
    
    return ActionResponse(
        action_id=str(result.action.action_id),
        status=result.decision.status.value,
        winning_rule=result.decision.winning_rule,
        reason=result.decision.reason,
        executed=result.executed,
        result=result.result,
        error=result.error,
    )


@app.post("/approvals/{approval_id}/approve")
async def approve_request(approval_id: str, kernel: Kernel = Depends(get_kernel)):
    """Approve a pending approval request."""
    # TODO: Implement approval resolution in approval_service
    raise HTTPException(status_code=501, detail="Approval resolution not yet implemented")


@app.post("/approvals/{approval_id}/reject")
async def reject_request(approval_id: str, kernel: Kernel = Depends(get_kernel)):
    """Reject a pending approval request."""
    # TODO: Implement approval resolution in approval_service
    raise HTTPException(status_code=501, detail="Approval resolution not yet implemented")


@app.get("/actions/{action_id}")
async def get_action(action_id: str, kernel: Kernel = Depends(get_kernel)):
    """Get action details and decision."""
    # TODO: Implement action lookup in repository
    raise HTTPException(status_code=501, detail="Action lookup not yet implemented")


@app.get("/audit/verify", response_model=AuditVerifyResponse)
async def verify_audit(kernel: Kernel = Depends(get_kernel)):
    """Verify the audit chain integrity."""
    async with kernel.repo.pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM verify_audit_chain()")
    
    return AuditVerifyResponse(
        valid=result['valid'],
        checked_count=result['checked_count'],
        broken_at_event_id=result['broken_at_event_id'],
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    global _pool
    if _pool is None:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    try:
        async with _pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {e}")
