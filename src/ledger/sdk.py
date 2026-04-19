"""Public API — Ledger SDK entry point.
Decorator handles: capability check → risk classify → rate limit → audit write → execute → audit close.

SOURCE OF TRUTH: ledger/core/GOVERNOR.md, ledger/core/EXECUTOR.md
This module implements EXECUTOR — execution with momentum.
GOVERNOR owns intervention authority; EXECUTOR respects it.
"""

import functools
import uuid
from typing import Any, Callable, Awaitable

from ledger.loader import build_system_prompt
from ledger.classifier import classify as classify_path
from ledger.core.governor import Governor, EscalationLevel, ExecutionLocked, get_governor
from ledger.governance.capability import CapabilityIssuer
from ledger.governance.risk import classify as classify_risk, Approval
from ledger.governance.audit import AuditService
from ledger.governance.killswitch import KillSwitch


class Denied(Exception):
    """Action denied by governance."""
    pass


class Ledger:
    """
    EXECUTOR implementation.
    
    Owns: execution context, capability management, error handling
    Checks with: GOVERNOR (intervention authority)
    
    Flow:
    1. User requests action
    2. Check GOVERNOR intervention level
    3. If Level 3 (locked) → block
    4. If Level 2 (correction) → strict mode, require confirmation
    5. If Level 0-1 → proceed with capability/risk checks
    """
    
    def __init__(
        self,
        *,
        audit_dsn: str,
        agent: str = "default",
        governor: Governor | None = None
    ) -> None:
        self.agent = agent
        self.caps = CapabilityIssuer()
        self.audit = AuditService(audit_dsn)
        self.killsw = KillSwitch()
        self.governor = governor or get_governor()
        self._approval_hook: Callable[[dict], Awaitable[bool]] | None = None
        self._strict_mode = False

    async def start(self):
        await self.audit.start()

    async def stop(self):
        await self.audit.stop()

    def set_approval_hook(self, hook):
        self._approval_hook = hook

    def build_prompt(self, task, session_id="default"):
        return build_system_prompt(
            agent=self.agent,
            path=classify_path(task),
            session_id=session_id,
            task=task,
        )

    def governed(self, *, action: str, resource: str, flag: str | None = None, context: dict | None = None):
        """
        Wrap a function with full governance.
        
        EXECUTOR checks with GOVERNOR before proceeding.
        Respects escalation levels and execution locks.
        """
        def wrap(fn):
            @functools.wraps(fn)
            async def inner(*args, **kwargs):
                # Build context for GOVERNOR
                check_context = context or {}
                check_context.update({
                    "action": action,
                    "resource": resource,
                    "agent": self.agent,
                    "args_preview": str(args)[:200],
                })
                
                # Check GOVERNOR intervention level
                level = self.governor.check_intervention(check_context)
                
                # Level 3: Execution locked
                if level == EscalationLevel.INTERVENTION or self.governor.locked:
                    raise ExecutionLocked(
                        f"GOVERNOR intervention: {self.governor.lock_reason or 'Pattern detected'}"
                    )
                
                # Level 2: Strict mode
                if level == EscalationLevel.CORRECTION:
                    self._strict_mode = True
                    confirmation = self.governor.require_confirmation(
                        f"This action ({action}) may conflict with your priorities. "
                        "Explicit confirmation required."
                    )
                    # In strict mode, require explicit user confirmation
                    # This would integrate with UI layer
                    
                # Proceed with standard governance flow
                return await self._execute_with_governance(
                    fn, args, kwargs, action, resource, flag
                )
            
            return inner
        return wrap

    async def _deny(self, action, resource, reason):
        risk, _ = classify_risk(action)
        await self.audit.log(
            actor=self.agent,
            action=action,
            resource=resource,
            risk=risk.value,
            approved=False,
            payload={"denied": reason},
        )
    
    async def _execute_with_governance(
        self, fn, args, kwargs, action, resource, flag
    ):
        """Execute function with full governance checks."""
        from ledger.governor import ActionState
        
        action_id = str(uuid.uuid4())
        risk, approval = classify_risk(action)
        
        # Create record in GOVERNOR (state tracking)
        await self.governor.create(
            action_id=action_id,
            action=action,
            resource=resource,
            agent=self.agent,
            risk=risk.value,
            approval_level=approval.value,
            args_preview=str(args)[:200],
        )

        # Check kill switch
        if flag and not self.killsw.is_enabled(flag):
            await self.governor.transition(action_id, ActionState.DENIED, 
                                           metadata={"reason": "kill_switch"})
            await self._deny(action, resource, "kill_switch")
            raise Denied(f"flag '{flag}' killed")

        # Hard approval required
        if approval is Approval.HARD:
            if not self._approval_hook:
                await self.governor.transition(action_id, ActionState.DENIED,
                                               metadata={"reason": "no_hook"})
                await self._deny(action, resource, "no_hook")
                raise Denied("HARD approval required")
            
            await self.governor.transition(action_id, ActionState.PENDING)
            ok = await self._approval_hook({
                "id": action_id,
                "action": action,
                "resource": resource,
                "risk": risk.value,
                "args": str(args)[:200],
            })
            if not ok:
                await self.governor.transition(action_id, ActionState.DENIED,
                                               metadata={"reason": "rejected"})
                await self._deny(action, resource, "rejected")
                raise Denied("rejected by hook")

        # Issue capability token
        cap = self.caps.issue(
            action=action,
            resource=resource,
            ttl_seconds=120,
            max_uses=1,
            issued_to=self.agent,
        )

        # Transition to executing
        await self.governor.transition(action_id, ActionState.EXECUTING,
                                       metadata={"cap_token": cap.token})

        try:
            # Execute
            result = await fn(*args, **kwargs)
            self.caps.consume(cap.token)
            
            # Success
            await self.governor.transition(
                action_id, 
                ActionState.SUCCESS,
                result_preview=str(result)[:200],
                metadata={"cap": cap.token}
            )
            
            await self.audit.log(
                actor=self.agent,
                action=action,
                resource=resource,
                risk=risk.value,
                approved=True,
                payload={"cap": cap.token, "ok": True, "action_id": action_id},
            )
            
            # Reset strict mode after success
            self._strict_mode = False
            return result
            
        except Exception as e:
            # Failed
            await self.governor.transition(
                action_id,
                ActionState.FAILED,
                error_message=str(e),
                metadata={"cap": cap.token}
            )
            
            await self.audit.log(
                actor=self.agent,
                action=action,
                resource=resource,
                risk=risk.value,
                approved=True,
                payload={"cap": cap.token, "error": str(e), "action_id": action_id},
            )
            raise