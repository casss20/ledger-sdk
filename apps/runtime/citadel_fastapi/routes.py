"""
Citadel FastAPI Routes — Core API endpoints (trimmed to 5).

Endpoints:
    GET  /health          → Health check
    GET  /status          → Citadel status
    POST /classify        → Classify task risk
    POST /execute         → Execute governed action
    POST /killswitch      → Trigger/reset kill switches
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

from citadel.sdk import Citadel
from citadel.schema import AgentOutput, OutputType
from citadel.router import CitadelRouter, RoutingDecision
from citadel.governance.risk import classify as classify_risk, Approval
from citadel.governance.killswitch import KillSwitch
from .middleware import get_current_user, TokenPayload


router = APIRouter(prefix="/citadel", tags=["citadel"])


# ============================================================================
# MODELS
# ============================================================================

class HealthResponse(BaseModel):
    status: str
    version: str


class StatusResponse(BaseModel):
    agent: str
    capabilities: int
    kill_switches: List[str]


class ClassifyRequest(BaseModel):
    task: str
    agent: Optional[str] = None


class ClassifyResponse(BaseModel):
    risk: str
    approval: str
    path: str


class ExecuteRequest(BaseModel):
    action: str
    resource: str
    flag: Optional[str] = None
    payload: Dict[str, Any] = {}


class ExecuteResponse(BaseModel):
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None


class KillswitchRequest(BaseModel):
    name: str
    reason: str


class KillswitchResponse(BaseModel):
    name: str
    enabled: bool
    reason: Optional[str] = None


# ============================================================================
# DEPENDENCIES
# ============================================================================

# Global instances (in production, use proper dependency injection)
_ledger: Optional[Citadel] = None
_router: Optional[CitadelRouter] = None


def get_ledger() -> Citadel:
    """Get or create Citadel instance."""
    global _ledger
    if _ledger is None:
        # Requires AUDIT_DSN env var
        import os
        dsn = os.getenv("AUDIT_DSN", "postgres://postgres:password@localhost/postgres")
        _ledger = Citadel(audit_dsn=dsn, agent="api")
    return _ledger


def get_router() -> CitadelRouter:
    """Get or create CitadelRouter instance."""
    global _router
    if _router is None:
        _router = CitadelRouter()
    return _router


# ============================================================================
# ROUTES (5 endpoints)
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint — public, no auth."""
    return HealthResponse(status="healthy", version="0.1.0")


@router.get("/status", response_model=StatusResponse)
async def ledger_status(user: TokenPayload = Depends(get_current_user)):
    """Get Citadel governance status."""
    citadel = get_ledger()
    return StatusResponse(
        agent=citadel.agent,
        capabilities=len(citadel.caps._tokens) if hasattr(citadel.caps, '_tokens') else 0,
        kill_switches=list(citadel.killsw._switches.keys()) if hasattr(citadel.killsw, '_switches') else []
    )


@router.post("/classify", response_model=ClassifyResponse)
async def classify_task(
    request: ClassifyRequest,
    user: TokenPayload = Depends(get_current_user)
):
    """Classify a task's risk level."""
    citadel = get_ledger()
    
    # Use citadel's internal classifier
    path = citadel.build_prompt(request.task).split("\n")[0] if hasattr(citadel, 'build_prompt') else "standard"
    
    # Classify risk
    risk, approval = classify_risk(request.task)
    
    return ClassifyResponse(
        risk=risk.name.lower(),
        approval=approval.name.lower(),
        path=path
    )


@router.post("/execute", response_model=ExecuteResponse)
async def execute_action(
    request: ExecuteRequest,
    user: TokenPayload = Depends(get_current_user)
):
    """
    Execute a governed action.
    
    This is a simulation endpoint — in practice, actions are decorated
    with @citadel.governed() and called directly.
    """
    citadel = get_ledger()
    
    # Check kill switch
    if request.flag and citadel.killsw.is_killed(request.flag):
        return ExecuteResponse(
            success=False,
            error=f"Action blocked: kill switch '{request.flag}' is active"
        )
    
    # Log to audit
    if citadel.audit:
        await citadel.audit.log(
            actor=user.sub,
            action=request.action,
            resource=request.resource,
            risk=classify_risk(request.action)[0].name.lower(),
            approved=True,
            payload=request.payload
        )
    
    return ExecuteResponse(success=True, result={"executed": True})


@router.post("/killswitch", response_model=KillswitchResponse)
async def trigger_killswitch(
    request: KillswitchRequest,
    user: TokenPayload = Depends(get_current_user)
):
    """Trigger a kill switch to disable a feature."""
    citadel = get_ledger()
    
    # Only admins can trigger killswitches
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    
    citadel.killsw.kill(request.name, reason=request.reason)
    
    return KillswitchResponse(
        name=request.name,
        enabled=True,
        reason=request.reason
    )


@router.delete("/killswitch/{name}", response_model=KillswitchResponse)
async def reset_killswitch(
    name: str,
    user: TokenPayload = Depends(get_current_user)
):
    """Reset (disable) a kill switch."""
    citadel = get_ledger()
    
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    
    citadel.killsw.reset(name)
    
    return KillswitchResponse(
        name=name,
        enabled=False
    )
