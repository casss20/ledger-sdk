"""
Public API — Ledger SDK entry point.
Decorator handles: capability check → risk classify → rate limit → audit write → execute → audit close.
"""

import functools
import uuid
from typing import Any, Callable, Awaitable

from ledger.loader import build_system_prompt
from ledger.classifier import classify as classify_path
from ledger.governor import Governor, ActionState, get_governor
from ledger.governance.capability import CapabilityIssuer
from ledger.governance.risk import classify as classify_risk, Approval
from ledger.governance.audit import AuditService
from ledger.governance.killswitch import KillSwitch


class Denied(Exception):
    pass


class Ledger:
    def __init__(self, *, audit_dsn: str, agent: str = "default", governor: Governor | None = None) -> None:
        self.agent = agent
        self.caps = CapabilityIssuer()
        self.audit = AuditService(audit_dsn)
        self.killsw = KillSwitch()
        self.governor = governor or get_governor()
        self._approval_hook: Callable[[dict], Awaitable[bool]] | None = None

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

    def governed(self, *, action: str, resource: str, flag: str | None = None):
        def wrap(fn):
            @functools.wraps(fn)
            async def inner(*args, **kwargs):
                action_id = str(uuid.uuid4())
                risk, approval = classify_risk(action)
                
                # Create record in GOVERNOR
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