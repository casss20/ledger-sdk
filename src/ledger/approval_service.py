"""
Approval Service - Human-in-the-loop queue management.

Handles:
- Approval requirement checking
- Pending approval creation
- Approval resolution (approve/reject)
- Expiry handling
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass

from ledger.actions import Action, KernelStatus
from ledger.repository import Repository


@dataclass
class ApprovalCheck:
    """Result of checking if approval is required."""
    required: bool
    priority: str  # 'low', 'medium', 'high', 'critical'
    reason: str
    expires_hours: int = 24
    risk_level: Optional[str] = None


@dataclass
class ApprovalResult:
    """Result of approval resolution."""
    approval_id: uuid.UUID
    status: str  # 'approved', 'rejected', 'expired'
    reviewed_by: Optional[str]
    reason: Optional[str]


class ApprovalService:
    """
    Manages human-in-the-loop approvals.
    
    Single responsibility: Queue and resolve human decisions.
    """
    
    def __init__(self, repository: Repository):
        self.repo = repository
    
    async def check_required(
        self,
        action: Action,
        snapshot: Any,  # PolicySnapshot
        risk_level: Optional[str] = None,
        risk_score: Optional[int] = None,
    ) -> ApprovalCheck:
        """
        Determine if human approval is required.
        
        Based on:
        - Policy rules
        - Risk level
        - Action type
        - Historical patterns
        """
        # Check policy for explicit approval requirement
        if snapshot:
            for rule in snapshot.get_rules():
                if rule.get('requires_approval', False):
                    return ApprovalCheck(
                        required=True,
                        priority=rule.get('approval_priority', 'high'),
                        reason=rule.get('reason', 'Approval required by policy'),
                        expires_hours=rule.get('approval_expiry_hours', 24)
                    )
        
        # Risk-based approval
        if risk_score and risk_score > 70:
            return ApprovalCheck(
                required=True,
                priority='high',
                reason=f'High risk action (score: {risk_score})',
                expires_hours=12
            )
        
        if risk_level == 'critical':
            return ApprovalCheck(
                required=True,
                priority='critical',
                reason='Critical risk action',
                expires_hours=4
            )
        
        # Default: no approval required
        return ApprovalCheck(
            required=False,
            priority='low',
            reason='No approval required'
        )
    
    async def create_pending(
        self,
        action: Action,
        check: ApprovalCheck,
    ) -> uuid.UUID:
        """Create pending approval entry."""
        expires_at = datetime.utcnow() + timedelta(hours=check.expires_hours)
        
        approval_id = await self.repo.create_approval(
            action_id=action.action_id,
            priority=check.priority,
            reason=check.reason,
            requested_by=action.actor_id,
            expires_at=expires_at,
        )
        
        return approval_id
    
    async def resolve_approval(
        self,
        approval_id: uuid.UUID,
        reviewed_by: str,
        decision: str,  # 'approved' or 'rejected'
        reason: Optional[str] = None,
    ) -> ApprovalResult:
        """
        Resolve a pending approval to approved or rejected.
        
        Updates DB and returns the result.
        """
        approval = await self.repo.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        if approval['status'] != 'pending':
            raise ValueError(f"Approval already {approval['status']}")
        
        # Update in database
        async with self.repo.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE approvals
                SET status = $1,
                    reviewed_by = $2,
                    decided_at = NOW(),
                    decision_reason = $3
                WHERE approval_id = $4
                """,
                decision,
                reviewed_by,
                reason or f"Decision: {decision}",
                approval_id,
            )
        
        return ApprovalResult(
            approval_id=approval_id,
            status=decision,
            reviewed_by=reviewed_by,
            reason=reason or f"Decision: {decision}",
        )

    async def approve(
        self,
        approval_id: uuid.UUID,
        reviewed_by: str,
        reason: Optional[str] = None,
    ) -> ApprovalResult:
        """Approve a pending approval."""
        approval = await self.repo.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        if approval['status'] != 'pending':
            raise ValueError(f"Approval already {approval['status']}")
        
        # Update approval status
        # Note: In real implementation, this would be a DB update
        # For now, returning the intended result
        
        return ApprovalResult(
            approval_id=approval_id,
            status='approved',
            reviewed_by=reviewed_by,
            reason=reason or "Approved"
        )
    
    async def reject(
        self,
        approval_id: uuid.UUID,
        reviewed_by: str,
        reason: str,
    ) -> ApprovalResult:
        """Reject a pending approval."""
        approval = await self.repo.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        if approval['status'] != 'pending':
            raise ValueError(f"Approval already {approval['status']}")
        
        return ApprovalResult(
            approval_id=approval_id,
            status='rejected',
            reviewed_by=reviewed_by,
            reason=reason
        )
    
    async def check_expired(self, approval_id: uuid.UUID) -> bool:
        """Check if approval has expired."""
        approval = await self.repo.get_approval(approval_id)
        if not approval:
            return False
        
        if approval['status'] != 'pending':
            return False
        
        if approval['expires_at'] < datetime.utcnow():
            return True
        
        return False
    
    async def process_expirations(self) -> int:
        """
        Process all expired approvals.
        
        Returns count of approvals expired.
        """
        # In real implementation, this would:
        # 1. Find all pending approvals where expires_at < NOW()
        # 2. Update status to 'expired'
        # 3. Update corresponding decisions to EXPIRED_APPROVAL
        
        # Placeholder
        return 0
    
    async def get_pending_queue(
        self,
        limit: int = 100,
    ) -> list:
        """Get pending approvals queue (for dashboards)."""
        return await self.repo.get_pending_approvals(limit)
    
    async def resolve_approval_to_decision(
        self,
        approval_result: ApprovalResult,
        action_id: uuid.UUID,
    ) -> KernelStatus:
        """
        Convert approval result to terminal decision status.
        
        Called by kernel after approval is resolved.
        """
        if approval_result.status == 'approved':
            return KernelStatus.ALLOWED
        elif approval_result.status == 'rejected':
            return KernelStatus.REJECTED_APPROVAL
        elif approval_result.status == 'expired':
            return KernelStatus.EXPIRED_APPROVAL
        else:
            raise ValueError(f"Unknown approval status: {approval_result.status}")
