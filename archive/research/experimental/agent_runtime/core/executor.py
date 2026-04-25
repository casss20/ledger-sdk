"""EXECUTOR — Continuous Execution

Implementation of EXECUTOR.md.

Purpose: Execute tasks with flow, adapting in real time without unnecessary stops.
- Maintains momentum
- Applies low-risk corrections inline
- Minimizes unnecessary pauses
- Shifts modes when required

OWNERSHIP:
- OWNS: action execution, momentum, artifact production, speed modes
- DOES NOT OWN: safety rules, escalation, relationship philosophy, strategic direction

EXECUTOR must always defer to CONSTITUTION and GOVERNOR.
If flow conflicts with safety or priorities, stop and escalate.

SOURCE OF TRUTH: citadel/core/EXECUTOR.md
If this code contradicts the MD file, the MD file is correct.
"""

import functools
import uuid
from typing import Any, Callable, Awaitable, Optional, Dict, TypeVar
from enum import Enum

T = TypeVar('T')

from citadel.core.governor import Governor, EscalationLevel, ExecutionLocked, get_governor
from citadel.governance.capability import CapabilityIssuer
from citadel.governance.risk import classify as classify_risk, Approval
from citadel.governance.audit import AuditService
from citadel.governance.killswitch import KillSwitch


class ExecutionMode(Enum):
    """Execution modes per EXECUTOR.md."""
    FLOW = "flow"           # Default: continuous execution
    CONTROLLED = "controlled"  # Moderate risk, multiple paths
    STRICT = "strict"       # High risk, requires approval
    RED_TEAM = "red_team"   # Explicit trigger, attacks vulnerabilities


class AutonomyMode:
    """Autonomous execution within boundaries."""
    
    def __init__(
        self,
        goal: str,
        constraints: list,
        allowed_actions: list,
        disallowed_actions: list,
        timeout_minutes: int = 60
    ):
        self.goal = goal
        self.constraints = constraints
        self.allowed_actions = allowed_actions
        self.disallowed_actions = disallowed_actions
        self.timeout_minutes = timeout_minutes
        self.start_time = None
        self.consecutive_failures = 0
        self.active = False
    
    def enter(self):
        """Enter autonomy mode."""
        from datetime import datetime
        self.start_time = datetime.utcnow()
        self.active = True
        self.consecutive_failures = 0
    
    def exit(self, reason: str):
        """Exit autonomy mode with reason."""
        self.active = False
        return {"exited": True, "reason": reason, "summary": self._generate_summary()}
    
    def check_timeout(self) -> bool:
        """Check if autonomy has timed out."""
        if not self.start_time:
            return False
        from datetime import datetime
        elapsed = (datetime.utcnow() - self.start_time).total_seconds() / 60
        return elapsed >= self.timeout_minutes
    
    def record_failure(self) -> bool:
        """Record a failure. Returns True if 3 consecutive failures (hard stop)."""
        self.consecutive_failures += 1
        return self.consecutive_failures >= 3
    
    def reset_failures(self):
        """Reset failure count after success."""
        self.consecutive_failures = 0
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary of autonomy session."""
        return {
            "goal": self.goal,
            "constraints_followed": self.constraints,
            "exited_at": datetime.utcnow().isoformat() if not self.active else None
        }


class Executor:
    """
    EXECUTOR implementation.
    
    Owns: execution context, momentum, artifact production
    Checks with: GOVERNOR (intervention authority), PLANNER (plan), CRITIC (quality)
    
    Flow:
    1. Select execution mode (FLOW, CONTROLLED, STRICT)
    2. Check GOVERNOR periodically during sustained execution
    3. Apply inline corrections for low-risk issues
    4. Escalate to FAILURE after 2 correction attempts
    """
    
    def __init__(
        self,
        audit_dsn: str,
        agent: str = "default",
        governor: Optional[Governor] = None
    ):
        self.agent = agent
        self.caps = CapabilityIssuer()
        self.audit = AuditService(audit_dsn)
        self.killsw = KillSwitch()
        self.governor = governor or get_governor()
        self._approval_hook: Optional[Callable[[dict], Awaitable[bool]]] = None
        self._mode = ExecutionMode.FLOW
        self._autonomy: Optional[AutonomyMode] = None
        self._steps_since_governor_check = 0
    
    def set_approval_hook(self, hook: Callable[[dict], Awaitable[bool]]):
        """Register hook for HARD approval decisions."""
        self._approval_hook = hook
    
    def set_mode(self, mode: ExecutionMode):
        """Set execution mode."""
        self._mode = mode
    
    def enter_autonomy(
        self,
        goal: str,
        constraints: list,
        allowed_actions: list,
        disallowed_actions: list,
        timeout_minutes: int = 60
    ) -> AutonomyMode:
        """Enter guided autonomy mode."""
        self._autonomy = AutonomyMode(
            goal=goal,
            constraints=constraints,
            allowed_actions=allowed_actions,
            disallowed_actions=disallowed_actions,
            timeout_minutes=timeout_minutes
        )
        self._autonomy.enter()
        return self._autonomy
    
    def exit_autonomy(self, reason: str) -> Dict[str, Any]:
        """Exit autonomy mode."""
        if self._autonomy:
            return self._autonomy.exit(reason)
        return {"exited": False, "reason": "no_autonomy_active"}
    
    def execute(
        self,
        action: str,
        resource: str,
        fn: Callable[..., Awaitable[T]],
        args: tuple,
        kwargs: dict,
        flag: Optional[str] = None,
        context: Optional[dict] = None
    ) -> Awaitable[T]:
        """
        Execute a governed action.
        
        This is the main entry point for EXECUTOR.
        """
        # Wrap the function with full governance
        wrapped = self._wrap_with_governance(fn, action, resource, flag)
        return wrapped(*args, **kwargs)
    
    def _wrap_with_governance(
        self,
        fn: Callable[..., Awaitable[T]],
        action: str,
        resource: str,
        flag: Optional[str] = None
    ) -> Callable[..., Awaitable[T]]:
        """Wrap function with governance checks."""
        @functools.wraps(fn)
        async def inner(*args, **kwargs):
            # Build context for GOVERNOR
            check_context = {
                "action": action,
                "resource": resource,
                "agent": self.agent,
                "args_preview": str(args)[:200],
            }
            
            # Check GOVERNOR intervention level
            level = self.governor.check_intervention(check_context)
            
            # Level 3: Execution locked
            if level == EscalationLevel.INTERVENTION or self.governor.locked:
                raise ExecutionLocked(
                    f"GOVERNOR intervention: {self.governor.lock_reason or 'Pattern detected'}"
                )
            
            # Level 2: Strict mode
            if level == EscalationLevel.CORRECTION:
                self._mode = ExecutionMode.STRICT
                # In strict mode, require explicit confirmation
                # This would integrate with UI layer
            
            # Check autonomy mode
            if self._autonomy and self._autonomy.active:
                if self._autonomy.check_timeout():
                    summary = self.exit_autonomy("timeout")
                    raise ExecutionLocked(f"Autonomy timeout: {summary}")
                
                if action in self._autonomy.disallowed_actions:
                    self.exit_autonomy("disallowed_action")
                    raise ExecutionLocked(f"Action '{action}' not allowed in autonomy")
            
            # Execute with full governance
            return await self._execute_with_governance(fn, args, kwargs, action, resource, flag)
        
        return inner
    
    async def _execute_with_governance(
        self,
        fn: Callable[..., Awaitable[T]],
        args: tuple,
        kwargs: dict,
        action: str,
        resource: str,
        flag: Optional[str]
    ) -> T:
        """Execute function with full governance checks."""
        from citadel.governor import ActionState
        
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
            raise ExecutionLocked(f"flag '{flag}' killed")

        # Hard approval required
        if approval is Approval.HARD:
            if not self._approval_hook:
                await self.governor.transition(action_id, ActionState.DENIED,
                                               metadata={"reason": "no_hook"})
                await self._deny(action, resource, "no_hook")
                raise ExecutionLocked("HARD approval required")
            
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
                raise ExecutionLocked("rejected by hook")

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
            
            # Reset autonomy failures on success
            if self._autonomy:
                self._autonomy.reset_failures()
            
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
            
            # Reset mode after success
            self._mode = ExecutionMode.FLOW
            return result
            
        except Exception as e:
            # Check autonomy failures
            if self._autonomy:
                hard_stop = self._autonomy.record_failure()
                if hard_stop:
                    summary = self.exit_autonomy("3_consecutive_failures")
                    raise ExecutionLocked(f"Autonomy hard stop after 3 failures: {summary}")
            
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
    
    async def _deny(self, action, resource, reason):
        """Log denied action to audit."""
        risk, _ = classify_risk(action)
        await self.audit.log(
            actor=self.agent,
            action=action,
            resource=resource,
            risk=risk.value,
            approved=False,
            payload={"denied": reason},
        )
    
    def periodic_governor_check(self, context: dict) -> EscalationLevel:
        """
        Re-check GOVERNOR conditions during sustained execution.
        
        EXECUTOR must call this:
        - After 3 meaningful steps
        - When scope changes
        - When new risk appears
        - When user behavior suggests drift
        """
        self._steps_since_governor_check = 0
        return self.governor.check_intervention(context)
    
    def record_step(self):
        """Record step completion for periodic checks."""
        self._steps_since_governor_check += 1
        return self._steps_since_governor_check
    
    def should_check_governor(self) -> bool:
        """Check if 3 steps passed since last GOVERNOR check."""
        return self._steps_since_governor_check >= 3
    
    def apply_inline_correction(self, issue: str, fix: Callable) -> bool:
        """
        Apply low-risk correction inline without escalating.
        
        Returns True if correction applied successfully.
        """
        try:
            fix()
            return True
        except Exception:
            # Correction failed, will escalate on retry
            return False
    
    def escalate_to_failure(self, issue: str, attempts: int) -> bool:
        """
        Determine if execution should escalate to FAILURE.
        
        Returns True if should escalate (2+ correction attempts failed).
        """
        return attempts >= 2

    async def run(self, action) -> Any:
        """
        Run action through executor with a no-op function.
        This is used when the kernel just needs to mark an action as allowed
        without executing a specific user function.
        """
        async def noop():
            return {"status": "allowed", "action": action.action_name}
        
        return await self.execute(
            action=action.action_name,
            resource=action.resource,
            fn=noop,
            args=(),
            kwargs={},
        )


# Convenience decorator
def executor(gov: Governor = None, audit_dsn: str = None, agent: str = "default"):
    """Create an executor decorator."""
    exec_instance = Executor(audit_dsn=audit_dsn or "postgresql://localhost/citadel", 
                            agent=agent, governor=gov)
    
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            # Extract action/resource from function metadata or use defaults
            action = getattr(fn, '_action', fn.__name__)
            resource = getattr(fn, '_resource', action)
            flag = getattr(fn, '_flag', None)
            
            return await exec_instance.execute(
                action=action,
                resource=resource,
                fn=fn,
                args=args,
                kwargs=kwargs,
                flag=flag
            )
        return wrapper
    return decorator
