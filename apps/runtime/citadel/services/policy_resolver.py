"""
Policy Resolver - Returns immutable policy snapshots.

Single job: Resolve which policy applies and return an immutable snapshot.
No decision logic here - just policy lookup and snapshot creation.
"""

import uuid
import hashlib
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass

from citadel.actions import Action
from citadel.repository import Repository


@dataclass
class PolicySnapshot:
    """Immutable resolved policy at decision time."""
    snapshot_id: uuid.UUID
    policy_id: uuid.UUID
    policy_version: str
    snapshot_hash: str
    snapshot_json: Dict[str, Any]

    def get_rules(self) -> list:
        """Extract rules from snapshot."""
        return self.snapshot_json.get('rules', [])

    def get_rule(self, name: str) -> Optional[Dict]:
        """Get specific rule by name."""
        for rule in self.get_rules():
            if rule.get('name') == name:
                return rule
        return None


class PolicyResolver:
    """
    Resolves the active policy for an action and creates immutable snapshot.

    Resolution order (most specific to least):
    1. action:{action_name}
    2. resource:{resource}
    3. actor:{actor_id}
    4. tenant:{tenant_id}
    5. global
    """

    def __init__(self, repository: Repository):
        self.repo = repository

    async def resolve(self, action: Action) -> Optional[PolicySnapshot]:
        """
        Resolve policy for action and return immutable snapshot.

        Returns None if no policy found (default allow).
        """
        # Try resolution order
        policy = await self._resolve_specific(action)

        if not policy:
            return None

        # Create immutable snapshot
        snapshot = await self._create_snapshot(policy)
        return snapshot

    async def _resolve_specific(self, action: Action) -> Optional[Dict]:
        """Try policy resolution in precedence order."""
        tenant_id = action.tenant_id

        # 1. Action-specific policy
        policy = await self.repo.get_active_policy(
            'action', action.action_name, tenant_id
        )
        if policy:
            return policy

        # 2. Resource-specific policy
        policy = await self.repo.get_active_policy(
            'resource', action.resource, tenant_id
        )
        if policy:
            return policy

        # 3. Actor-specific policy
        policy = await self.repo.get_active_policy(
            'actor', action.actor_id, tenant_id
        )
        if policy:
            return policy

        # 4. Tenant-specific policy
        if tenant_id:
            policy = await self.repo.get_active_policy(
                'tenant', tenant_id, tenant_id
            )
            if policy:
                return policy

        # 5. Global policy
        policy = await self.repo.get_active_policy(
            'global', '*', None
        )
        return policy

    async def _create_snapshot(self, policy: Dict) -> PolicySnapshot:
        """Create immutable snapshot of resolved policy."""
        policy_id = policy['policy_id']
        version = f"{policy['name']}:{policy['version']}"

        # Build snapshot JSON
        rules_json = policy['rules_json']
        if isinstance(rules_json, str):
            rules_json = json.loads(rules_json)

        snapshot_json = {
            'policy_id': str(policy_id),
            'name': policy['name'],
            'version': policy['version'],
            'scope_type': policy['scope_type'],
            'scope_value': policy['scope_value'],
            'rules': rules_json.get('rules', []),
            'resolved_at': str(uuid.uuid1()),  # Unique resolution marker
        }

        # Calculate hash
        snapshot_hash = self._calculate_hash(snapshot_json)

        # Persist snapshot
        snapshot_id = await self.repo.save_policy_snapshot(
            policy_id=policy_id,
            version=version,
            snapshot_hash=snapshot_hash,
            snapshot_json=snapshot_json,
        )

        return PolicySnapshot(
            snapshot_id=snapshot_id,
            policy_id=policy_id,
            policy_version=version,
            snapshot_hash=snapshot_hash,
            snapshot_json=snapshot_json,
        )

    def _calculate_hash(self, snapshot_json: Dict) -> str:
        """Calculate deterministic hash of policy snapshot."""
        # Normalize JSON for consistent hashing
        canonical = json.dumps(snapshot_json, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()


class PolicyEvaluator:
    """
    Evaluates policy rules against an action.

    Called by Precedence module, not directly by Kernel.
    """

    def evaluate(
        self,
        snapshot: PolicySnapshot,
        action: Action,
        context: Dict[str, Any],
    ) -> 'PolicyEvaluationResult':
        """
        Evaluate all rules in order, return first matching.
        """
        rules = snapshot.get_rules()

        for rule in rules:
            result = self._evaluate_rule(rule, action, context)
            if result.matched:
                return result

        # No rules matched - default allow
        return PolicyEvaluationResult(
            matched=True,
            effect="ALLOW",
            rule_name="default_allow",
            reason="No blocking rules matched",
            risk_level="none",
            risk_score=0,
        )

    def _evaluate_rule(
        self,
        rule: Dict,
        action: Action,
        context: Dict[str, Any],
    ) -> 'PolicyEvaluationResult':
        """Evaluate single rule against action."""
        condition = rule.get('condition', 'false')

        # Simple condition evaluation (can be expanded)
        matched = self._eval_condition(condition, action, context)

        if not matched:
            return PolicyEvaluationResult(matched=False)

        return PolicyEvaluationResult(
            matched=True,
            effect=rule.get('effect', 'ALLOW'),
            rule_name=rule.get('name', 'unnamed'),
            reason=rule.get('reason', 'Rule matched'),
            risk_level=rule.get('risk_level', 'none'),
            risk_score=rule.get('risk_score', 0),
            requires_approval=rule.get('requires_approval', False),
        )

    def _eval_condition(self, condition: str, action: Action, context: Dict) -> bool:
        """
        Evaluate condition against action context.

        Supports both string conditions (legacy) and dict conditions
        from JSON-parsed policy snapshots.
        """
        # Handle dict conditions first (from JSONB / parsed rules_json)
        if isinstance(condition, dict):
            if condition.get("always") is True:
                return True
            if condition.get("always") is False:
                return False
            # Unknown dict shape: fail closed for safety
            return False

        # Handle common string patterns
        if condition == 'true':
            return True
        if condition == 'false':
            return False

        # Risk score conditions
        if 'risk_score >' in condition:
            threshold = int(condition.split('>')[1].strip())
            return context.get('risk_score', 0) > threshold

        if 'risk_score <' in condition:
            threshold = int(condition.split('<')[1].strip())
            return context.get('risk_score', 0) < threshold

        # Action name patterns
        if condition.startswith('action_name =='):
            expected = condition.split('==')[1].strip().strip('"\'')
            return action.action_name == expected

        # Resource patterns
        if condition.startswith('resource =='):
            expected = condition.split('==')[1].strip().strip('"\'')
            return action.resource == expected

        # Default: fail closed if can't evaluate
        return False


@dataclass
class PolicyEvaluationResult:
    """Result of evaluating a policy rule."""
    matched: bool
    effect: Optional[str] = None  # "ALLOW", "BLOCK", "PENDING_APPROVAL"
    rule_name: Optional[str] = None
    reason: Optional[str] = None
    risk_level: Optional[str] = None
    risk_score: Optional[int] = None
    requires_approval: bool = False
