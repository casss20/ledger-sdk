"""
Decision Engine — Layer 1: Authorization decisions.

Why: Policy evaluation produces a first-class GovernanceDecision.
Tokens are optional derivations. Every decision is auditable.
Layered enforcement:
  1. Policy engine (this module) → authorization decision
  2. Execution middleware → verify decision/token at runtime
  3. RLS → data isolation at database layer
  4. OTel context → cross-service correlation
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Protocol

from .governance_decision import (
    GovernanceDecision,
    DecisionType,
    DecisionScope,
    KillSwitchScope,
)


class PolicyBackend(Protocol):
    """Pluggable policy backend (OPA, Cedar, or Citadel native)."""

    async def evaluate(self, action: str, context: dict) -> dict:
        """
        Evaluate action against policies.

        Returns dict with keys:
        - allowed: bool
        - reason: str
        - scope: dict (actions, resources, max_spend, rate_limit)
        - constraints: dict
        """
        ...


class DecisionEngine:
    """
    Produces GovernanceDecisions from policy evaluation.

    Checks kill switches BEFORE policy evaluation.
    All decisions are persisted and auditable.
    """

    def __init__(
        self,
        policy_backend: PolicyBackend,
        audit_logger,
        kill_switch,
        default_ttl_seconds: int = 3600,
    ):
        self.policies = policy_backend
        self.audit = audit_logger
        self.kill_switch = kill_switch
        self.default_ttl = default_ttl_seconds

    async def decide(
        self,
        action: str,
        context: dict,
        tenant_id: str,
        actor_id: str,
    ) -> GovernanceDecision:
        """
        Make a governance decision.

        Flow:
        1. Check kill switches
        2. Evaluate policy backend
        3. Create GovernanceDecision
        4. Audit the decision
        5. Return decision
        """
        # 1. Check kill switches
        ks_check = await self.kill_switch.check(actor_id, tenant_id)
        if ks_check.active:
            decision = GovernanceDecision(
                decision_id=self._gen_id(),
                decision_type=DecisionType.DENY,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action=action,
                scope=DecisionScope(),
                reason=f"Kill switch active: {ks_check.reason}",
            )
            await self._audit_decision(decision, context)
            return decision

        # 2. Evaluate policy
        policy_result = await self.policies.evaluate(action, context)

        # 3. Build decision
        decision_type = (
            DecisionType.ALLOW if policy_result.get("allowed") else DecisionType.DENY
        )
        scope = DecisionScope(
            actions=policy_result.get("scope", {}).get("actions", [action]),
            resources=policy_result.get("scope", {}).get("resources", []),
            max_spend=policy_result.get("scope", {}).get("max_spend"),
            rate_limit=policy_result.get("scope", {}).get("rate_limit"),
        )
        expiry = None
        if decision_type == DecisionType.ALLOW and self.default_ttl:
            expiry = datetime.now(timezone.utc) + timedelta(seconds=self.default_ttl)

        decision = GovernanceDecision(
            decision_id=self._gen_id(),
            decision_type=decision_type,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            scope=scope,
            constraints=policy_result.get("constraints", {}),
            expiry=expiry,
            kill_switch_scope=KillSwitchScope.REQUEST,
            reason=policy_result.get("reason", ""),
        )

        # 4. Audit
        await self._audit_decision(decision, context)

        return decision

    async def revoke(self, decision_id: str, reason: str) -> GovernanceDecision:
        """Revoke an existing decision."""
        # Lookup existing decision
        existing = await self._get_decision(decision_id)
        if existing is None:
            raise ValueError(f"Decision {decision_id} not found")

        existing.decision_type = DecisionType.REVOKED
        existing.reason = f"Revoked: {reason}"
        await self._audit_revocation(existing, reason)
        return existing

    def _gen_id(self) -> str:
        return f"gd_{uuid.uuid4().hex}"

    async def _audit_decision(self, decision: GovernanceDecision, context: dict):
        await self.audit.record(
            event_type="governance.decision",
            tenant_id=decision.tenant_id,
            actor_id=decision.actor_id,
            data={
                "decision_id": decision.decision_id,
                "decision_type": decision.decision_type.value,
                "action": decision.action,
                "reason": decision.reason,
                "context": context,
            },
        )

    async def _audit_revocation(self, decision: GovernanceDecision, reason: str):
        await self.audit.record(
            event_type="governance.decision.revoked",
            tenant_id=decision.tenant_id,
            actor_id=decision.actor_id,
            data={
                "decision_id": decision.decision_id,
                "revocation_reason": reason,
            },
        )

    async def _get_decision(self, decision_id: str) -> Optional[GovernanceDecision]:
        """Lookup decision by ID."""
        # TODO: implement persistence lookup
        return None
