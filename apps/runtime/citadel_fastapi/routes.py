"""
CITADEL FastAPI Routes â€” Core API endpoints (trimmed to 5).

Endpoints:
    GET  /health          â†’ Health check
    GET  /status          â†’ CITADEL status
    POST /classify        â†’ Classify task risk
    POST /execute         â†’ Execute governed action
    POST /killswitch      â†’ Trigger/reset kill switches
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

from CITADEL.sdk import CITADEL
from CITADEL.schema import AgentOutput, OutputType
from CITADEL.router import CITADELRouter, RoutingDecision
from citadel.governance.risk import classify as classify_risk, Approval
from citadel.governance.killswitch import KillSwitch
from .middleware import get_current_user, TokenPayload


router = APIRouter(prefix="/CITADEL", tags=["CITADEL"])


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
_CITADEL: Optional[CITADEL] = None
_router: Optional[CITADELRouter] = None


def get_CITADEL() -> CITADEL:
    """Get or create CITADEL instance."""
    global _CITADEL
    if _CITADEL is None:
        # Requires AUDIT_DSN env var
        import os
        dsn = os.getenv("AUDIT_DSN", "postgres://postgres:password@localhost/postgres")
        _CITADEL = CITADEL(audit_dsn=dsn, agent="api")
    return _CITADEL


def get_router() -> CITADELRouter:
    """Get or create CITADELRouter instance."""
    global _router
    if _router is None:
        _router = CITADELRouter()
    return _router


# ============================================================================
# ROUTES (5 endpoints)
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint â€” public, no auth."""
    return HealthResponse(status="healthy", version="0.1.0")


@router.get("/status", response_model=StatusResponse)
async def CITADEL_status(user: TokenPayload = Depends(get_current_user)):
    """Get CITADEL governance status."""
    CITADEL = get_CITADEL()
    return StatusResponse(
        agent=CITADEL.agent,
        capabilities=len(CITADEL.caps._tokens) if hasattr(CITADEL.caps, '_tokens') else 0,
        kill_switches=list(CITADEL.killsw._switches.keys()) if hasattr(CITADEL.killsw, '_switches') else []
    )


@router.post("/classify", response_model=ClassifyResponse)
async def classify_task(
    request: ClassifyRequest,
    user: TokenPayload = Depends(get_current_user)
):
    """Classify a task's risk level."""
    CITADEL = get_CITADEL()
    
    # Use CITADEL's internal classifier
    path = CITADEL.build_prompt(request.task).split("\n")[0] if hasattr(CITADEL, 'build_prompt') else "standard"
    
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
    
    This is a simulation endpoint â€” in practice, actions are decorated
    with @citadel.governed() and called directly.
    """
    CITADEL = get_CITADEL()
    
    # Check kill switch
    if request.flag and CITADEL.killsw.is_killed(request.flag):
        return ExecuteResponse(
            success=False,
            error=f"Action blocked: kill switch '{request.flag}' is active"
        )
    
    # Log to audit
    if CITADEL.audit:
        await CITADEL.audit.log(
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
    CITADEL = get_CITADEL()
    
    # Only admins can trigger killswitches
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    
    CITADEL.killsw.kill(request.name, reason=request.reason)
    
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
    CITADEL = get_CITADEL()
    
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    
    CITADEL.killsw.reset(name)
    
    return KillswitchResponse(
        name=name,
        enabled=False
    )
