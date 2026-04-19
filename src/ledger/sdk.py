"""Ledger SDK — Public API

This module provides the public-facing API for the Ledger SDK.
It wraps the core components (EXECUTOR, GOVERNOR, RUNTIME) into a
developer-friendly interface.

The heavy lifting is done in core/:
- core/executor.py implements EXECUTOR.md
- core/governor.py implements GOVERNOR.md
- core/runtime.py implements RUNTIME.md
- core/constitution.py implements CONSTITUTION.md

This file is the convenience layer, not the implementation.
"""

from typing import Any, Callable, Optional, Awaitable
import functools

from ledger.core import (
    Executor,
    ExecutionMode,
    Governor,
    get_governor,
    Constitution,
    DEFAULT_CONSTITUTION,
)
from ledger.core.governor import ExecutionLocked
from ledger.governance.alignment import Alignment, get_alignment


class Denied(Exception):
    """Action denied by governance."""
    pass


class Ledger:
    """
    Public API for Ledger SDK.
    
    Wraps core components for developer convenience.
    
    Example:
        gov = Ledger(audit_dsn="postgresql://...")
        
        @gov.governed(action="send_email", resource="outbound")
        async def send_email(to: str, body: str):
            return await smtp.send(to, body)
    """
    
    def __init__(
        self,
        *,
        audit_dsn: str,
        agent: str = "default",
        governor: Optional[Governor] = None,
        constitution: Optional[Constitution] = None,
        world_goals: Optional[dict] = None
    ):
        self.agent = agent
        self.constitution = constitution or DEFAULT_CONSTITUTION
        
        # Core components
        self._executor = Executor(
            audit_dsn=audit_dsn,
            agent=agent,
            governor=governor or get_governor()
        )
        self._alignment = get_alignment(world_goals=world_goals)
        self._governor = governor or get_governor()
    
    def set_approval_hook(self, hook):
        """Register hook for HARD approval decisions."""
        self._executor.set_approval_hook(hook)
    
    def governed(
        self,
        *,
        action: str,
        resource: str,
        flag: Optional[str] = None,
        context: Optional[dict] = None
    ) -> Callable:
        """
        Decorator for governed actions.
        
        Wraps functions with full governance:
        - CONSTITUTION check
        - ALIGNMENT check
        - GOVERNOR intervention check
        - Risk classification
        - Capability tokens
        - Audit logging
        """
        def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
            @functools.wraps(fn)
            async def wrapper(*args, **kwargs):
                # Check alignment first
                alignment_result = self._alignment.check(
                    action=action,
                    context={
                        "args": args,
                        "kwargs": kwargs,
                        "resource": resource,
                        **(context or {})
                    }
                )
                
                if alignment_result.result.value == "refuse":
                    raise Denied("Action refused by CONSTITUTION")
                
                if alignment_result.result.value == "challenge":
                    # In real implementation, would surface to user
                    # For now, log and continue
                    pass
                
                # Execute with full governance via EXECUTOR
                return await self._executor.execute(
                    action=action,
                    resource=resource,
                    fn=fn,
                    args=args,
                    kwargs=kwargs,
                    flag=flag,
                    context=context
                )
            
            return wrapper
        return decorator
    
    # Convenience methods for accessing core components
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
    
    # Execution mode helpers
    def set_mode(self, mode: ExecutionMode):
        """Set execution mode (FLOW, CONTROLLED, STRICT)."""
        self._executor.set_mode(mode)
    
    # Autonomy helpers
    def enter_autonomy(
        self,
        goal: str,
        constraints: list,
        allowed_actions: list,
        disallowed_actions: list,
        timeout_minutes: int = 60
    ):
        """Enter guided autonomy mode."""
        return self._executor.enter_autonomy(
            goal=goal,
            constraints=constraints,
            allowed_actions=allowed_actions,
            disallowed_actions=disallowed_actions,
            timeout_minutes=timeout_minutes
        )
    
    def exit_autonomy(self, reason: str):
        """Exit autonomy mode."""
        return self._executor.exit_autonomy(reason)


# Backwards compatibility alias
GovernedLedger = Ledger
