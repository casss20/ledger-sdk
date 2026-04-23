"""
Ledger API Dependencies

- API key authentication
- Rate limiting
- Kernel factory (singleton per request)
"""

from typing import Optional
from fastapi import HTTPException, Header, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ledger.config import settings
from ledger.execution.kernel import Kernel
from ledger.repository import Repository
from ledger.policy_resolver import PolicyResolver, PolicyEvaluator
from ledger.precedence import Precedence
from ledger.approval_service import ApprovalService
from ledger.capability_service import CapabilityService
from ledger.audit_service import AuditService
from ledger.execution.executor import Executor as ActionExecutor
from ledger.tokens import TokenVault, KillSwitch, TokenVerifier

# Global pool reference (set in lifespan)
_pool: Optional = None

security = HTTPBearer(auto_error=False)


async def require_api_key(
    request: Request,
    api_key: Optional[str] = Header(None, alias=settings.api_key_header),
) -> str:
    """Validate API key from header."""
    if not settings.require_auth:
        return "anonymous"
    
    # Check header
    key = api_key
    if not key:
        # Try query param fallback
        key = request.query_params.get("api_key")
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if key not in settings.valid_api_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    
    return key


async def get_kernel(request: Request) -> Kernel:
    """Dependency: Get kernel instance with DB pool from app state."""
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not connected",
        )
    
    from ledger.middleware.tenant_context import TenantAwarePool
    repo = Repository(TenantAwarePool(pool))
    policy_resolver = PolicyResolver(repo)
    policy_evaluator = PolicyEvaluator()
    
    # Governance components (Phase 4 integration)
    vault = TokenVault(pool)
    kill_switch = KillSwitch(pool)
    verifier = TokenVerifier(vault, kill_switch)
    
    precedence = Precedence(
        repo,
        policy_evaluator,
        token_verifier=verifier,
        governance_kill_switch=kill_switch,
    )
    
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
