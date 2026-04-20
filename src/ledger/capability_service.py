"""
Capability Service - Token-based capability validation and consumption.

Atomic operations only. All capability state changes go through here.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from ledger.actions import Action
from ledger.repository import Repository


@dataclass
class CapabilityCheck:
    """Result of capability validation."""
    valid: bool
    reason: Optional[str]
    remaining_uses: int = 0
    scope: Optional[str] = None


class CapabilityService:
    """
    Validates and consumes capability tokens.
    
    All capability operations are atomic (via repository.consume_capability).
    """
    
    def __init__(self, repository: Repository):
        self.repo = repository
    
    async def validate(
        self,
        token: str,
        action: Action,
    ) -> CapabilityCheck:
        """
        Validate capability without consuming.
        
        Use for pre-checks. Use consume() for actual execution.
        """
        cap = await self.repo.get_capability(token)
        
        if not cap:
            return CapabilityCheck(valid=False, reason="Capability not found")
        
        if cap['actor_id'] != action.actor_id:
            return CapabilityCheck(
                valid=False,
                reason="Capability not issued to this actor"
            )
        
        if cap['revoked']:
            return CapabilityCheck(valid=False, reason="Capability revoked")
        
        # Check expiry
        from datetime import datetime
        if cap['expires_at'] < datetime.utcnow():
            return CapabilityCheck(valid=False, reason="Capability expired")
        
        # Check uses
        if cap['uses'] >= cap['max_uses']:
            return CapabilityCheck(valid=False, reason="Capability exhausted")
        
        # Check scope
        if not self._matches_scope(cap, action):
            return CapabilityCheck(
                valid=False,
                reason=f"Capability scope doesn't match action"
            )
        
        remaining = cap['max_uses'] - cap['uses']
        return CapabilityCheck(
            valid=True,
            reason="Valid",
            remaining_uses=remaining,
            scope=f"{cap['action_scope']}:{cap['resource_scope']}"
        )
    
    async def consume(
        self,
        token: str,
        action: Action,
    ) -> CapabilityCheck:
        """
        Validate and consume capability use.
        
        This is atomic - either consumes or fails entirely.
        """
        result = await self.repo.consume_capability(token, action.actor_id)
        
        if result['success']:
            return CapabilityCheck(
                valid=True,
                reason="Consumed successfully",
                remaining_uses=result['remaining_uses'],
            )
        else:
            return CapabilityCheck(
                valid=False,
                reason=result['error'],
                remaining_uses=0,
            )
    
    def _matches_scope(self, cap: Dict, action: Action) -> bool:
        """Check if capability scope covers the action."""
        action_scope = cap['action_scope']
        resource_scope = cap['resource_scope']
        
        # Action scope matching (supports wildcards)
        if action_scope == '*':
            action_match = True
        elif action_scope.endswith(':*'):
            prefix = action_scope[:-2]
            action_match = action.action_name.startswith(prefix + '.')
        else:
            action_match = action.action_name == action_scope
        
        # Resource scope matching
        if resource_scope == '*':
            resource_match = True
        elif resource_scope == action.resource:
            resource_match = True
        else:
            resource_match = False
        
        return action_match and resource_match
    
    async def get_remaining_uses(self, token: str) -> int:
        """Get remaining uses without consuming."""
        cap = await self.repo.get_capability(token)
        if not cap:
            return 0
        return cap['max_uses'] - cap['uses']
    
    async def is_valid_for_action(
        self,
        token: str,
        action_name: str,
        resource: str,
    ) -> bool:
        """Check if capability valid for specific action/resource."""
        cap = await self.repo.get_capability(token)
        if not cap:
            return False
        
        # Build mock action for scope check
        from ledger.actions import Action
        mock_action = Action(
            action_id=uuid.uuid4(),
            actor_id=cap['actor_id'],
            actor_type='agent',
            action_name=action_name,
            resource=resource,
            tenant_id=None,
            payload={},
            context={},
            session_id=None,
            request_id=None,
            idempotency_key=None,
            created_at=datetime.utcnow(),
        )
        
        return self._matches_scope(cap, mock_action)
