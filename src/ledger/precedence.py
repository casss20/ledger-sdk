"""
Precedence - Evaluates governance precedence chain.

Order: Kill Switch -> Capability -> Policy

This module contains the decision logic for which control wins.
No other module makes these decisions.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any

from ledger.actions import Action, KernelStatus
from ledger.repository import Repository
from ledger.policy_resolver import PolicySnapshot, PolicyEvaluator, PolicyEvaluationResult


@dataclass
class PrecedenceResult:
    """Result of precedence evaluation."""
    blocked: bool
    status: Optional[KernelStatus]
    winning_rule: Optional[str]
    reason: Optional[str]
    path_taken: Optional[str]
    risk_level: Optional[str] = None
    risk_score: Optional[int] = None


class KillSwitchStatus:
    """Kill switch check result."""
    def __init__(self, active: bool, reason: Optional[str] = None):
        self.active = active
        self.reason = reason


class CapabilityStatus:
    """Capability validation result."""
    def __init__(
        self,
        valid: bool,
        reason: Optional[str] = None,
        remaining_uses: int = 0,
    ):
        self.valid = valid
        self.reason = reason
        self.remaining_uses = remaining_uses


class Precedence:
    """
    Evaluates governance precedence: kill switch -> capability -> policy.
    
    This is where the decision logic lives. Kernel calls this, gets result,
    acts on it without additional decision-making.
    """
    
    def __init__(
        self,
        repository: Repository,
        policy_evaluator: PolicyEvaluator,
    ):
        self.repo = repository
        self.policy_eval = policy_evaluator
    
    async def evaluate(
        self,
        action: Action,
        snapshot: Optional[PolicySnapshot],
        capability_token: Optional[str],
        context: Dict[str, Any],
    ) -> PrecedenceResult:
        """
        Evaluate full precedence chain.
        
        Returns PrecedenceResult telling kernel what to do.
        """
        # 1. Kill switch check (highest precedence)
        kill = await self._check_kill_switch(action)
        if kill.active:
            return PrecedenceResult(
                blocked=True,
                status=KernelStatus.BLOCKED_EMERGENCY,
                winning_rule="kill_switch_active",
                reason=kill.reason or "Emergency kill switch active",
                path_taken="blocked"
            )
        
        # 2. Capability check (if provided)
        if capability_token:
            cap = await self._check_capability(action, capability_token)
            if not cap.valid:
                return PrecedenceResult(
                    blocked=True,
                    status=KernelStatus.BLOCKED_CAPABILITY,
                    winning_rule="capability_invalid",
                    reason=cap.reason or "Invalid or expired capability",
                    path_taken="blocked"
                )
        
        # 3. Policy evaluation
        if snapshot:
            policy_result = self.policy_eval.evaluate(snapshot, action, context)
            
            if policy_result.effect == "BLOCK":
                return PrecedenceResult(
                    blocked=True,
                    status=KernelStatus.BLOCKED_POLICY,
                    winning_rule=policy_result.rule_name or "policy_block",
                    reason=policy_result.reason or "Blocked by policy",
                    path_taken="blocked",
                    risk_level=policy_result.risk_level,
                    risk_score=policy_result.risk_score,
                )
            
            if policy_result.effect == "PENDING_APPROVAL" or policy_result.requires_approval:
                # Don't block - signal approval required
                return PrecedenceResult(
                    blocked=False,  # Not blocked, just needs approval
                    status=None,
                    winning_rule=policy_result.rule_name or "approval_required",
                    reason=policy_result.reason or "Approval required",
                    path_taken="approval_required",
                    risk_level=policy_result.risk_level or "high",
                    risk_score=policy_result.risk_score or 75,
                )
        
        # 4. Path selection
        path = self._select_path(action, snapshot, context)
        
        return PrecedenceResult(
            blocked=False,
            status=None,
            winning_rule="allowed",
            reason="All checks passed",
            path_taken=path,
            risk_level="none",
            risk_score=0,
        )
    
    async def _check_kill_switch(self, action: Action) -> KillSwitchStatus:
        """Check kill switches at all relevant scopes."""
        # Check global
        ks = await self.repo.check_kill_switch('global', '*', action.tenant_id)
        if ks:
            return KillSwitchStatus(active=True, reason=ks.get('reason'))
        
        # Check action-specific
        ks = await self.repo.check_kill_switch('action', action.action_name, action.tenant_id)
        if ks:
            return KillSwitchStatus(active=True, reason=ks.get('reason'))
        
        # Check resource-specific
        ks = await self.repo.check_kill_switch('resource', action.resource, action.tenant_id)
        if ks:
            return KillSwitchStatus(active=True, reason=ks.get('reason'))
        
        # Check actor-specific
        ks = await self.repo.check_kill_switch('actor', action.actor_id, action.tenant_id)
        if ks:
            return KillSwitchStatus(active=True, reason=ks.get('reason'))
        
        return KillSwitchStatus(active=False)
    
    async def _check_capability(
        self,
        action: Action,
        token: str,
    ) -> CapabilityStatus:
        """Validate capability token for action."""
        cap = await self.repo.get_capability(token)
        
        if not cap:
            return CapabilityStatus(valid=False, reason="Capability not found")
        
        if cap['actor_id'] != action.actor_id:
            return CapabilityStatus(valid=False, reason="Capability not issued to this actor")
        
        if cap['revoked']:
            return CapabilityStatus(valid=False, reason="Capability revoked")
        
        # Check expiry
        from datetime import datetime, timezone
        if cap['expires_at'] < datetime.now(timezone.utc):
            return CapabilityStatus(valid=False, reason="Capability expired")
        
        # Check uses
        if cap['uses'] >= cap['max_uses']:
            return CapabilityStatus(valid=False, reason="Capability exhausted")
        
        # Check scope match
        if not self._capability_matches_scope(cap, action):
            return CapabilityStatus(
                valid=False,
                reason=f"Capability scope {cap['action_scope']} doesn't match action {action.action_name}"
            )
        
        return CapabilityStatus(
            valid=True,
            remaining_uses=cap['max_uses'] - cap['uses']
        )
    
    def _capability_matches_scope(self, cap: Dict, action: Action) -> bool:
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
    
    def _select_path(
        self,
        action: Action,
        snapshot: Optional[PolicySnapshot],
        context: Dict[str, Any],
    ) -> str:
        """
        Select execution path from RUNTIME.md.
        
        - fast: Trusted actor, low risk, known pattern
        - standard: Normal governance flow
        - structured: Multi-step, needs planning
        - high_risk: Irreversible, high stakes
        """
        risk_score = context.get('risk_score', 0)
        
        # High risk -> high_risk path
        if risk_score > 70:
            return "high_risk"
        
        # Check if irreversible
        if self._is_irreversible(action):
            return "high_risk"
        
        # Check if structured/multi-step
        if self._is_structured(action):
            return "structured"
        
        # Check if fast path eligible
        if self._is_fast_path(action, context):
            return "fast"
        
        return "standard"
    
    def _is_irreversible(self, action: Action) -> bool:
        """Check if action is irreversible."""
        irreversible_actions = [
            'stripe.charge', 'stripe.refund',
            'db.delete', 'db.drop',
            'email.send', 'email.bulk',
            'github.commit', 'github.merge',
        ]
        return action.action_name in irreversible_actions
    
    def _is_structured(self, action: Action) -> bool:
        """Check if action needs structured planning."""
        # Multi-step actions or those with milestones
        structured_prefixes = ['plan.', 'deploy.', 'migrate.']
        return any(action.action_name.startswith(p) for p in structured_prefixes)
    
    def _is_fast_path(self, action: Action, context: Dict[str, Any]) -> bool:
        """
        Check if action qualifies for fast path.
        
        From RUNTIME.md:
        - Trusted actor
        - Low risk
        - Known action pattern
        - No approval flags
        """
        risk_score = context.get('risk_score', 0)
        if risk_score > 30:
            return False
        
        # Could add trusted actor list, action whitelist, etc.
        return True
