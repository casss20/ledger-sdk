"""
Audit Service - Append-only event logging with hash chain.

All governance events flow through here.
No decisions, just logging.
"""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from ledger.kernel import Action, Decision
from ledger.repository import Repository


class AuditService:
    """
    Writes all governance events to the append-only audit log.
    
    Events:
    - action_received
    - policy_evaluated
    - kill_switch_checked
    - capability_checked
    - risk_assessed
    - approval_requested
    - approval_granted
    - approval_denied
    - decision_made
    - action_executed
    - action_failed
    - escalation_triggered
    - idempotent_return
    """
    
    def __init__(self, repository: Repository):
        self.repo = repository
    
    async def action_received(self, action: Action) -> int:
        """Log action entering the system."""
        return await self._log(
            action=action,
            event_type='action_received',
            payload={
                'action_name': action.action_name,
                'resource': action.resource,
                'payload_keys': list(action.payload.keys()),
            }
        )
    
    async def policy_evaluated(
        self,
        action: Action,
        snapshot: Any,  # PolicySnapshot
    ) -> int:
        """Log policy resolution."""
        return await self._log(
            action=action,
            event_type='policy_evaluated',
            payload={
                'snapshot_id': str(snapshot.snapshot_id) if snapshot else None,
                'policy_version': snapshot.policy_version if snapshot else None,
            }
        )
    
    async def kill_switch_checked(
        self,
        action: Action,
        kill_switch: Any,  # KillSwitchStatus
    ) -> int:
        """Log kill switch check."""
        return await self._log(
            action=action,
            event_type='kill_switch_checked',
            payload={
                'active': kill_switch.active,
                'reason': kill_switch.reason,
            }
        )
    
    async def capability_checked(
        self,
        action: Action,
        cap_check: Any,  # CapabilityStatus
    ) -> int:
        """Log capability validation."""
        return await self._log(
            action=action,
            event_type='capability_checked',
            payload={
                'valid': cap_check.valid,
                'reason': cap_check.reason,
                'remaining_uses': cap_check.remaining_uses,
            }
        )
    
    async def risk_assessed(
        self,
        action: Action,
        risk_level: str,
        risk_score: int,
    ) -> int:
        """Log risk assessment."""
        return await self._log(
            action=action,
            event_type='risk_assessed',
            payload={
                'risk_level': risk_level,
                'risk_score': risk_score,
            }
        )
    
    async def approval_requested(
        self,
        action: Action,
        approval_id: uuid.UUID,
    ) -> int:
        """Log approval queue entry."""
        return await self._log(
            action=action,
            event_type='approval_requested',
            payload={
                'approval_id': str(approval_id),
            }
        )
    
    async def approval_granted(
        self,
        action: Action,
        approval_id: uuid.UUID,
        reviewed_by: str,
    ) -> int:
        """Log human approval."""
        return await self._log(
            action=action,
            event_type='approval_granted',
            payload={
                'approval_id': str(approval_id),
                'reviewed_by': reviewed_by,
            }
        )
    
    async def approval_denied(
        self,
        action: Action,
        approval_id: uuid.UUID,
        reviewed_by: str,
        reason: str,
    ) -> int:
        """Log human rejection."""
        return await self._log(
            action=action,
            event_type='approval_denied',
            payload={
                'approval_id': str(approval_id),
                'reviewed_by': reviewed_by,
                'reason': reason,
            }
        )
    
    async def decision_made(
        self,
        action: Action,
        decision: Decision,
    ) -> int:
        """Log terminal decision."""
        return await self._log(
            action=action,
            event_type='decision_made',
            payload={
                'decision_id': str(decision.decision_id),
                'status': decision.status.value,
                'winning_rule': decision.winning_rule,
                'reason': decision.reason,
                'path_taken': decision.path_taken,
            }
        )
    
    async def action_executed(
        self,
        action: Action,
        result: Any,
    ) -> int:
        """Log successful execution."""
        return await self._log(
            action=action,
            event_type='action_executed',
            payload={
                'success': True,
                'result_type': type(result).__name__,
            }
        )
    
    async def action_failed(
        self,
        action: Action,
        error: str,
    ) -> int:
        """Log execution failure."""
        return await self._log(
            action=action,
            event_type='action_failed',
            payload={
                'error': error[:500],  # Truncate long errors
            }
        )
    
    async def idempotent_return(
        self,
        action: Action,
        cached_decision: Decision,
    ) -> int:
        """Log idempotent cache hit."""
        return await self._log(
            action=action,
            event_type='action_received',
            payload={
                'idempotent': True,
                'cached_decision_id': str(cached_decision.decision_id),
                'cached_status': cached_decision.status.value,
            },
            override_action_id=cached_decision.action_id,
        )
    
    async def escalation_triggered(
        self,
        action: Action,
        level: int,
        reason: str,
    ) -> int:
        """Log escalation to higher level."""
        return await self._log(
            action=action,
            event_type='escalation_triggered',
            payload={
                'escalation_level': level,
                'reason': reason,
            }
        )
    
    async def _log(
        self,
        action: Action,
        event_type: str,
        payload: Dict[str, Any],
        override_action_id: Optional[uuid.UUID] = None,
    ) -> int:
        """Write event to audit log."""
        return await self.repo.save_audit_event(
            action_id=override_action_id or action.action_id,
            event_type=event_type,
            payload=payload,
            actor_id=action.actor_id,
            tenant_id=action.tenant_id,
        )
    
    async def verify_chain(self) -> Dict[str, Any]:
        """Verify audit chain integrity."""
        return await self.repo.verify_audit_chain()
