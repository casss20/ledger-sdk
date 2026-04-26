"""
Citadel API Dependencies

- API key authentication (hashed, scoped)
- Rate limiting
- Kernel factory (singleton per request)
"""

from typing import Optional
from fastapi import HTTPException, Header, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from citadel.config import settings
from citadel.auth.api_key import ApiKeyManager
from citadel.execution.kernel import Kernel
from citadel.core.repository import Repository
from citadel.services.policy_resolver import PolicyResolver, PolicyEvaluator
from citadel.utils.precedence import Precedence
from citadel.services.approval_service import ApprovalService
from citadel.services.capability_service import CapabilityService
from citadel.services.audit_service import AuditService
from citadel.execution.executor import Executor as ActionExecutor
from citadel.tokens import TokenVault, KillSwitch, TokenVerifier

# Global pool reference (set in lifespan)
_pool: Optional = None

# API Key Manager (initialized from settings)
_api_key_manager: Optional[ApiKeyManager] = None

def get_api_key_manager() -> ApiKeyManager:
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = ApiKeyManager.from_settings(settings.api_keys)
    return _api_key_manager

security = HTTPBearer(auto_error=False)


async def require_api_key(
    request: Request,
    api_key: Optional[str] = Header(None, alias=settings.api_key_header),
) -> str:
    """Validate API key from header using hashed, scoped key management."""
    if not settings.require_auth:
        return "anonymous"
    
    manager = get_api_key_manager()
    
    # Check header
    key = api_key
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    validated = manager.validate(key)
    if validated is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired API key",
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
    
    from citadel.middleware.tenant_context import TenantAwarePool
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
