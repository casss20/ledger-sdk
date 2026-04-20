"""
Ledger SDK — Public API (Kernel-Integrated)

Wraps the governance kernel for developer convenience.
"""

from typing import Any, Callable, Optional, Awaitable, TypeVar
import functools
import uuid
from datetime import datetime

# New kernel imports
from ledger.kernel import Kernel, Action, KernelResult, KernelStatus
from ledger.repository import Repository
from ledger.policy_resolver import PolicyResolver, PolicyEvaluator
from ledger.precedence import Precedence
from ledger.approval_service import ApprovalService
from ledger.capability_service import CapabilityService
from ledger.audit_service import AuditService
from ledger.executor import Executor as KernelExecutor
from ledger.status import ActorType

# Legacy imports for backwards compatibility
from ledger.core import Executor, ExecutionMode, Governor, Constitution, DEFAULT_CONSTITUTION
from ledger.governance.alignment import Alignment, get_alignment

T = TypeVar('T')


class Denied(Exception):
    """Action denied by governance."""
    pass


class Ledger:
    """
    Public API for Ledger SDK.
    
    Uses the new governance kernel for all enforcement.
    """
    
    def __init__(
        self,
        *,
        audit_dsn: str,
        agent: str = "default",
        governor: Optional[Governor] = None,
        constitution: Optional[Constitution] = None,
        world_goals: Optional[dict] = None,
        db_pool: Optional[Any] = None,
    ):
        self.agent = agent
        self.constitution = constitution or DEFAULT_CONSTITUTION
        self.audit_dsn = audit_dsn
        self._db_pool = db_pool
        
        # Legacy components
        self._executor = Executor(
            audit_dsn=audit_dsn,
            agent=agent,
            governor=governor or get_governor()
        )
        self._alignment = get_alignment(world_goals=world_goals)
        self._governor = governor or get_governor()
        
        # New kernel (initialized on first use if db_pool not provided)
        self._kernel: Optional[Kernel] = None
        self._repository: Optional[Repository] = None
    
    async def initialize(self):
        """Initialize database pool and kernel."""
        if self._db_pool is None:
            import asyncpg
            self._db_pool = await asyncpg.create_pool(self.audit_dsn)
        
        self._repository = Repository(self._db_pool)
        
        # Build kernel with all services
        policy_resolver = PolicyResolver(self._repository)
        policy_evaluator = PolicyEvaluator()
        precedence = Precedence(self._repository, policy_evaluator)
        approval_service = ApprovalService(self._repository)
        capability_service = CapabilityService(self._repository)
        audit_service = AuditService(self._repository)
        executor = KernelExecutor()
        
        self._kernel = Kernel(
            repository=self._repository,
            policy_resolver=policy_resolver,
            precedence=precedence,
            approval_service=approval_service,
            capability_service=capability_service,
            audit_service=audit_service,
            executor=executor,
        )
        
        # Ensure agent actor exists
        await self._repository.ensure_actor(
            actor_id=self.agent,
            actor_type=ActorType.AGENT.value
        )
    
    async def shutdown(self):
        """Cleanup resources."""
        if self._db_pool:
            await self._db_pool.close()
    
    def governed(
        self,
        *,
        action: str,
        resource: str,
        flag: Optional[str] = None,
        context: Optional[dict] = None,
        capability_required: bool = False,
        idempotent: bool = False,
        risk: Optional[str] = None,
    ) -> Callable:
        """
        Decorator for governed actions.
        
        Uses the kernel for full governance lifecycle.
        """
        def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
            @functools.wraps(fn)
            async def wrapper(*args, **kwargs):
                if self._kernel is None:
                    await self.initialize()
                
                # Build action from decorator params
                action_obj = Action(
                    action_id=uuid.uuid4(),
                    actor_id=self.agent,
                    actor_type=ActorType.AGENT.value,
                    action_name=action,
                    resource=resource,
                    tenant_id=None,
                    payload={
                        "args": str(args),
                        "kwargs": str(kwargs),
                        "flag": flag,
                    },
                    context={
                        "risk": risk,
                        **(context or {})
                    },
                    session_id=None,
                    request_id=str(uuid.uuid4()),
                    idempotency_key=f"{self.agent}:{action}:{resource}:{hash(str(args))}" if idempotent else None,
                    created_at=datetime.utcnow(),
                )
                
                # Run through kernel
                result: KernelResult = await self._kernel.handle(
                    action=action_obj,
                    capability_token=None,  # Could be extracted from kwargs
                )
                
                # Handle outcomes
                if result.decision.status == KernelStatus.BLOCKED_EMERGENCY:
                    raise Denied(f"Blocked by kill switch: {result.decision.reason}")
                
                if result.decision.status == KernelStatus.BLOCKED_POLICY:
                    raise Denied(f"Blocked by policy: {result.decision.reason}")
                
                if result.decision.status == KernelStatus.BLOCKED_CAPABILITY:
                    raise Denied(f"Blocked: {result.decision.reason}")
                
                if result.decision.status == KernelStatus.PENDING_APPROVAL:
                    raise Denied(f"Pending approval: {result.decision.reason}")
                
                if result.decision.status == KernelStatus.REJECTED_APPROVAL:
                    raise Denied(f"Approval rejected: {result.decision.reason}")
                
                if result.decision.status == KernelStatus.EXPIRED_APPROVAL:
                    raise Denied(f"Approval expired: {result.decision.reason}")
                
                if result.decision.status == KernelStatus.ALLOWED:
                    # Execute the actual function
                    exec_result = await fn(*args, **kwargs)
                    
                    # Record execution
                    await self._repository.save_execution_result(
                        action_id=action_obj.action_id,
                        success=True,
                        result={"result": str(exec_result)[:1000]}
                    )
                    
                    # Update decision to EXECUTED
                    # (In real implementation, kernel would do this)
                    
                    return exec_result
                
                if result.decision.status == KernelStatus.EXECUTED:
                    return result.result
                
                if result.decision.status == KernelStatus.FAILED_EXECUTION:
                    raise RuntimeError(f"Execution failed: {result.error}")
                
                # Fallback for unknown states
                raise Denied(f"Unexpected status: {result.decision.status}")
            
            return wrapper
        return decorator
    
    # Legacy API compatibility
    def set_approval_hook(self, hook):
        """Register hook for HARD approval decisions."""
        self._executor.set_approval_hook(hook)
    
    @property
    def executor(self) -> Executor:
        """Access EXECUTOR component."""
        return self._executor
    
    @property
    def governor(self) -> Governor:
        """Access GOVERNOR component."""
        return self._governor
    
    @property
    def alignment(self) -> Alignment:
        """Access ALIGNMENT component."""
        return self._alignment
    
    def set_mode(self, mode: ExecutionMode):
        """Set execution mode (FLOW, CONTROLLED, STRICT)."""
        self._executor.set_mode(mode)
    
    def enter_autonomy(self, goal: str, constraints: list, allowed_actions: list, 
                       disallowed_actions: list, timeout_minutes: int = 60):
        """Enter guided autonomy mode."""
        return self._executor.enter_autonomy(
            goal=goal, constraints=constraints,
            allowed_actions=allowed_actions, disallowed_actions=disallowed_actions,
            timeout_minutes=timeout_minutes
        )
    
    def exit_autonomy(self, reason: str):
        """Exit autonomy mode."""
        return self._executor.exit_autonomy(reason)
    
    # New kernel API
    @property
    def kernel(self) -> Optional[Kernel]:
        """Access governance kernel."""
        return self._kernel
    
    async def verify_audit_chain(self) -> dict:
        """Verify audit chain integrity."""
        if self._kernel is None:
            await self.initialize()
        return await self._kernel.audit.verify_chain()


# Backwards compatibility
GovernedLedger = Ledger
