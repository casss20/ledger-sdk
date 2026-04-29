"""
Decision Engine — Layer 1: Authorization decisions.

Why: Policy evaluation produces a first-class GovernanceDecision.
Tokens are optional derivations. Every decision is auditable.
Layered enforcement:
  1. Policy engine (this module) → authorization decision
  2. Trust policy engine → trust-derived constraints
  3. Execution middleware → verify decision/token at runtime
  4. RLS → data isolation at database layer
  5. OTel context → cross-service correlation
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Protocol, Dict, Any

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
    Trust-derived constraints are applied AFTER policy evaluation
    (they modify the policy result, never override it).
    All decisions are persisted and auditable.
    """

    def __init__(
        self,
        policy_backend: PolicyBackend,
        audit_logger,
        kill_switch,
        trust_policy_engine=None,  # Optional trust constraint adapter
        default_ttl_seconds: int = 3600,
    ):
        self.policies = policy_backend
        self.audit = audit_logger
        self.kill_switch = kill_switch
        self.trust_engine = trust_policy_engine
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
        1. Check kill switches (FIRST — emergency override)
        2. Evaluate trust policy (produces trust-derived constraints)
        3. Evaluate policy backend (produces base policy result)
        4. Merge trust constraints with policy result
        5. Create GovernanceDecision
        6. Audit the decision
        7. Return decision
        """
        decision_id = self._gen_id()

        # 1. Check kill switches
        ks_check = await self.kill_switch.check(
            actor_id, tenant_id, request_id=decision_id
        )
        if ks_check.active:
            decision = GovernanceDecision(
                decision_id=decision_id,
                decision_type=DecisionType.DENY,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action=action,
                scope=DecisionScope(),
                reason=f"Kill switch active: {ks_check.reason}",
            )
            await self._audit_decision(decision, context)
            return decision

        # 2. Evaluate trust policy (optional, if trust engine configured)
        trust_result = None
        if self.trust_engine:
            trust_result = await self.trust_engine.evaluate(
                action=action,
                actor_id=actor_id,
                tenant_id=tenant_id,
                base_context=context,
            )

        # 3. Evaluate policy backend
        # Merge trust context into policy evaluation context
        policy_context = dict(context)
        if trust_result:
            policy_context["trust"] = trust_result.to_dict()

        policy_result = await self.policies.evaluate(action, policy_context)

        # 4. Merge trust constraints with policy result
        # Trust can only ADD constraints, never REMOVE them
        max_spend = policy_result.get("scope", {}).get("max_spend")
        rate_limit = policy_result.get("scope", {}).get("rate_limit")

        if trust_result:
            # Apply spend multiplier (can only reduce, not increase beyond policy)
            if max_spend is not None and trust_result.max_spend_multiplier < 1.0:
                max_spend = max_spend * trust_result.max_spend_multiplier

            # Apply rate limit multiplier (can only reduce, not increase)
            if rate_limit is not None and trust_result.rate_limit_multiplier < 1.0:
                rate_limit = int(rate_limit * trust_result.rate_limit_multiplier)

        # 5. Build decision
        decision_type = (
            DecisionType.ALLOW if policy_result.get("allowed") else DecisionType.DENY
        )

        # Override decision type if trust requires approval
        if trust_result and trust_result.requires_approval and decision_type == DecisionType.ALLOW:
            decision_type = DecisionType.REQUIRE_APPROVAL

        # Override decision type if trust blocks the action
        if trust_result and trust_result.action_blocked:
            decision_type = DecisionType.DENY

        scope = DecisionScope(
            actions=policy_result.get("scope", {}).get("actions", [action]),
            resources=policy_result.get("scope", {}).get("resources", []),
            max_spend=max_spend,
            rate_limit=rate_limit,
        )
        expiry = None
        if decision_type == DecisionType.ALLOW and self.default_ttl:
            expiry = datetime.now(timezone.utc) + timedelta(seconds=self.default_ttl)

        # Build reason string
        reason = policy_result.get("reason", "")
        if trust_result:
            if trust_result.block_reason:
                reason = f"{reason} | Trust block: {trust_result.block_reason}" if reason else trust_result.block_reason
            elif trust_result.approval_reason:
                reason = f"{reason} | Trust approval required: {trust_result.approval_reason}" if reason else trust_result.approval_reason

        decision = GovernanceDecision(
            decision_id=decision_id,
            decision_type=decision_type,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            scope=scope,
            constraints=policy_result.get("constraints", {}),
            expiry=expiry,
            kill_switch_scope=KillSwitchScope.REQUEST,
            reason=reason,
        )

        # Store trust snapshot reference for reproducibility
        if trust_result and trust_result.trust_snapshot_id:
            decision.trust_snapshot_id = trust_result.trust_snapshot_id

        # 6. Audit
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
        """Lookup decision by ID from the decisions table."""
        import asyncpg
        from citadel.config import settings
        
        conn = await asyncpg.connect(settings.database_dsn)
        try:
            row = await conn.fetchrow(
                """
                SELECT decision_id, action_id, status, winning_rule, reason,
                       capability_token, risk_level, risk_score, path_taken,
                       created_at, executed_at
                FROM decisions
                WHERE decision_id = $1
                """,
                decision_id,
            )
            if row is None:
                return None
            
            # Map database row to GovernanceDecision
            return GovernanceDecision(
                decision_id=row["decision_id"],
                decision_type=DecisionType.ALLOW if row["status"] == "ALLOWED" else DecisionType.DENY,
                tenant_id="",  # Retrieved via joined action if needed
                actor_id="",
                action=row["winning_rule"],
                scope=DecisionScope(),
                reason=row["reason"],
            )
        finally:
            await conn.close()
