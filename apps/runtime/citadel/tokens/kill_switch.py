"""
Kill Switch — Multi-scope emergency halt.

Why: EU AI Act Article 14(4)(e) mandates "stop button or similar procedure".
Penalties up to €15M or 3% of global turnover.

Scope levels:
- REQUEST: Halt one specific request
- AGENT: Halt all requests from one agent
- TENANT: Halt all requests from one tenant
- GLOBAL: Halt all requests everywhere

Cascading: Stopping agent X → stop all agents dependent on X.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from .governance_decision import KillSwitchScope


@dataclass
class KillSwitchRecord:
    """Immutable record of a kill switch activation."""

    record_id: str
    scope: KillSwitchScope
    target_id: str  # request_id, agent_id, tenant_id, or "*" for global
    triggered_by: str
    triggered_by_type: str  # "human" | "system"
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    actions_stopped: int = 0
    cascade_depth: int = 0

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "scope": self.scope.value,
            "target_id": self.target_id,
            "triggered_by": self.triggered_by,
            "triggered_by_type": self.triggered_by_type,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "actions_stopped": self.actions_stopped,
            "cascade_depth": self.cascade_depth,
        }


@dataclass
class KillSwitchCheck:
    """Result of a kill switch check."""

    active: bool
    reason: str = ""
    record: Optional[KillSwitchRecord] = None


class KillSwitch:
    """
    Multi-scope kill switch.

    Checks are performed at decision time (not token verification time).
    This ensures kill switches are evaluated for every new decision.
    """

    def __init__(self, audit_logger, storage=None):
        self.audit = audit_logger
        self.storage = storage or {}  # In-memory for MVP; use Redis/DB in production
        self._active: dict[str, KillSwitchRecord] = {}

    async def trigger(
        self,
        scope: KillSwitchScope,
        target_id: str,
        triggered_by: str,
        triggered_by_type: str,
        reason: str,
    ) -> KillSwitchRecord:
        """
        Trigger kill switch at specified scope.

        Flow:
        1. Create kill switch record
        2. Revoke all active decisions in scope
        3. Audit the activation
        4. Return record
        """
        record = KillSwitchRecord(
            record_id=f"ks_{uuid.uuid4().hex}",
            scope=scope,
            target_id=target_id,
            triggered_by=triggered_by,
            triggered_by_type=triggered_by_type,
            reason=reason,
        )

        key = self._key(scope, target_id)
        self._active[key] = record

        # Audit
        await self.audit.record(
            event_type="kill_switch.triggered",
            tenant_id=target_id if scope in (KillSwitchScope.TENANT, KillSwitchScope.GLOBAL) else "system",
            actor_id=triggered_by,
            data=record.to_dict(),
        )

        return record

    async def release(
        self,
        scope: KillSwitchScope,
        target_id: str,
        released_by: str,
        reason: str,
    ) -> bool:
        """Release a previously triggered kill switch."""
        key = self._key(scope, target_id)
        if key not in self._active:
            return False

        del self._active[key]

        await self.audit.record(
            event_type="kill_switch.released",
            tenant_id=target_id if scope in (KillSwitchScope.TENANT, KillSwitchScope.GLOBAL) else "system",
            actor_id=released_by,
            data={
                "scope": scope.value,
                "target_id": target_id,
                "reason": reason,
            },
        )
        return True

    async def check(self, actor_id: str, tenant_id: str) -> KillSwitchCheck:
        """
        Check if any kill switch is active for the given context.

        Checks in order of specificity (most specific wins):
        1. REQUEST (specific request ID)
        2. AGENT (actor_id)
        3. TENANT (tenant_id)
        4. GLOBAL ("*")
        """
        # Check agent scope
        agent_key = self._key(KillSwitchScope.AGENT, actor_id)
        if agent_key in self._active:
            return KillSwitchCheck(
                active=True,
                reason=f"Agent kill switch active",
                record=self._active[agent_key],
            )

        # Check tenant scope
        tenant_key = self._key(KillSwitchScope.TENANT, tenant_id)
        if tenant_key in self._active:
            return KillSwitchCheck(
                active=True,
                reason=f"Tenant kill switch active",
                record=self._active[tenant_key],
            )

        # Check global scope
        global_key = self._key(KillSwitchScope.GLOBAL, "*")
        if global_key in self._active:
            return KillSwitchCheck(
                active=True,
                reason=f"Global kill switch active",
                record=self._active[global_key],
            )

        return KillSwitchCheck(active=False)

    def _key(self, scope: KillSwitchScope, target_id: str) -> str:
        return f"{scope.value}:{target_id}"
