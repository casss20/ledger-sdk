"""
Token Verifier — Verify gt_ token by resolving its linked decision.

Why: Token verification is a READ operation on the decision.
It checks expiry, revocation, scope, and kill-switch state.
It does NOT create a new decision.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .governance_decision import GovernanceDecision, DecisionType, DecisionScope, KillSwitchScope
from .kill_switch import KillSwitch, KillSwitchCheck


@dataclass
class VerificationResult:
    """Result of token/decision verification."""

    valid: bool
    reason: str = ""
    decision: Optional[GovernanceDecision] = None


@dataclass
class IntrospectionResult:
    """RFC 7662-style token introspection result."""

    active: bool
    reason: Optional[str] = None
    kill_switch: bool = False
    decision: Optional[GovernanceDecision] = None
    token: Optional[dict] = None


class TokenVerifier:
    """
    Verify a capability token by resolving its linked GovernanceDecision.

    Checks (in order):
    1. Token exists and is valid
    2. Linked decision exists
    3. Decision not expired
    4. Decision not revoked
    5. Decision scope covers requested action/resource
    6. Kill switch not active for decision scope
    """

    def __init__(self, vault, kill_switch=None, audit_logger=None):
        self.vault = vault
        self.kill_switch = kill_switch
        self.audit = audit_logger

    async def verify_token(
        self,
        token_id: str,
        action: str,
        resource: Optional[str] = None,
        context: dict = None,
    ) -> VerificationResult:
        """Verify a gt_ token for the given action."""
        context = context or {}

        # 0. Fast-path: reject malformed or empty token IDs without DB lookup
        if not token_id or not isinstance(token_id, str):
            return VerificationResult(valid=False, reason="token_id_invalid")

        # 1. Resolve token (pass tenant_id from context if vault supports it)
        tenant_id = context.get("tenant_id")
        token_data = await self.vault.resolve_token(token_id, tenant_id=tenant_id)
        if token_data is None:
            await self._audit_token_verification(token_id, False, "token_not_found", context)
            return VerificationResult(valid=False, reason="token_not_found")

        # 2. Token-level fast checks (no decision lookup needed)
        token_nbf = self._parse_datetime(token_data.get("not_before"))
        if token_nbf and datetime.now(timezone.utc) < token_nbf:
            await self._audit_token_verification(token_id, False, "token_not_yet_valid", context)
            return VerificationResult(valid=False, reason="token_not_yet_valid")

        token_expiry = self._parse_datetime(token_data.get("expiry"))
        if token_expiry and datetime.now(timezone.utc) > token_expiry:
            await self._audit_token_verification(token_id, False, "token_expired", context)
            return VerificationResult(valid=False, reason="token_expired")

        if token_data.get("revoked_at"):
            await self._audit_token_verification(token_id, False, "token_revoked", context)
            return VerificationResult(valid=False, reason="token_revoked")

        # 3. Resolve linked decision
        decision_id = token_data.get("decision_id")
        if not decision_id:
            await self._audit_token_verification(token_id, False, "no_linked_decision", context)
            return VerificationResult(valid=False, reason="no_linked_decision")

        decision_data = await self.vault.resolve_decision(decision_id, tenant_id=tenant_id)
        if decision_data is None:
            await self._audit_token_verification(token_id, False, "decision_not_found", context, decision_id=decision_id)
            return VerificationResult(valid=False, reason="decision_not_found")

        # Reconstruct GovernanceDecision from dict
        expiry = self._parse_datetime(decision_data.get("expiry") or decision_data.get("expires_at"))

        decision = GovernanceDecision(
            decision_id=decision_data["decision_id"],
            decision_type=DecisionType(decision_data["decision_type"]),
            tenant_id=decision_data["tenant_id"],
            actor_id=decision_data["actor_id"],
            action=decision_data["action"],
            request_id=decision_data.get("request_id"),
            trace_id=decision_data.get("trace_id") or token_data.get("trace_id"),
            workspace_id=decision_data.get("workspace_id") or decision_data["tenant_id"],
            agent_id=decision_data.get("agent_id") or decision_data["actor_id"],
            subject_type=decision_data.get("subject_type", "agent"),
            subject_id=decision_data.get("subject_id") or decision_data["actor_id"],
            resource=decision_data.get("resource"),
            risk_level=decision_data.get("risk_level", token_data.get("risk_level", "low")),
            policy_version=decision_data.get("policy_version", "unknown"),
            approval_state=decision_data.get("approval_state", "auto_approved"),
            approved_by=decision_data.get("approved_by"),
            approved_at=self._parse_datetime(decision_data.get("approved_at")),
            scope=DecisionScope(
                actions=decision_data["scope_actions"],
                resources=decision_data["scope_resources"],
            ),
            constraints=decision_data.get("constraints", {}),
            expiry=expiry,
            kill_switch_scope=KillSwitchScope(decision_data.get("kill_switch_scope", "request")),
            created_at=decision_data.get("created_at"),
            issued_token_id=decision_data.get("issued_token_id"),
            revoked_at=self._parse_datetime(decision_data.get("revoked_at")),
            revoked_reason=decision_data.get("revoked_reason"),
            reason=decision_data.get("reason", ""),
            root_decision_id=decision_data.get("root_decision_id"),
            parent_decision_id=decision_data.get("parent_decision_id"),
            parent_actor_id=decision_data.get("parent_actor_id"),
            workflow_id=decision_data.get("workflow_id"),
            superseded_at=self._parse_datetime(decision_data.get("superseded_at")),
            superseded_reason=decision_data.get("superseded_reason"),
        )

        workspace_id = context.get("workspace_id")
        token_workspace = token_data.get("workspace_id") or token_data.get("tenant_id")
        if workspace_id and workspace_id not in {decision.workspace_id, decision.tenant_id, token_workspace}:
            await self._audit_token_verification(token_id, False, "workspace_mismatch", context, decision)
            return VerificationResult(valid=False, reason="workspace_mismatch", decision=decision)

        # 4. Decision-level checks (after reconstructing the decision)
        if decision.is_expired:
            await self._audit_token_verification(token_id, False, "decision_expired", context, decision)
            return VerificationResult(valid=False, reason="decision_expired", decision=decision)

        if decision.decision_type == DecisionType.REVOKED or decision.revoked_at is not None:
            await self._audit_token_verification(token_id, False, "decision_revoked", context, decision)
            return VerificationResult(valid=False, reason="decision_revoked", decision=decision)

        if decision.superseded_at is not None:
            await self._audit_token_verification(token_id, False, "decision_superseded", context, decision)
            return VerificationResult(
                valid=False,
                reason=f"Decision superseded at {decision.superseded_at} — authority transferred",
                decision=decision,
            )

        if decision.decision_type != DecisionType.ALLOW:
            await self._audit_token_verification(token_id, False, "decision_not_allowed", context, decision)
            return VerificationResult(
                valid=False,
                reason=f"Decision type is {decision.decision_type.value} — not allowed",
                decision=decision,
            )

        # 4b. Ancestry check: ensure parent and root are still active
        if hasattr(self.vault, "check_ancestry"):
            ancestry_ok, ancestry_reason = await self.vault.check_ancestry(decision)
            if not ancestry_ok:
                await self._audit_token_verification(token_id, False, ancestry_reason, context, decision)
                return VerificationResult(valid=False, reason=ancestry_reason, decision=decision)

        # 5. Check scope
        if not decision.scope.covers(action, resource):
            await self._audit_token_verification(token_id, False, "scope_mismatch", context, decision)
            return VerificationResult(valid=False, reason="scope_mismatch", decision=decision)

        # 6. Check kill switch
        if self.kill_switch is not None:
            ks_check = await self.kill_switch.check(
                decision.actor_id, decision.tenant_id, request_id=decision.decision_id
            )
            if ks_check.active:
                await self._audit_token_verification(token_id, False, "kill_switch_active", context, decision)
                return VerificationResult(valid=False, reason="kill_switch_active", decision=decision)

        if hasattr(self.vault, "check_kill_switch"):
            switch = await self.vault.check_kill_switch(
                tenant_id=decision.tenant_id,
                actor_id=decision.actor_id,
                action=action,
                resource=resource,
                tool=context.get("tool") or token_data.get("tool"),
                decision_id=decision.decision_id,
            )
            if switch:
                await self._audit_token_verification(token_id, False, "kill_switch_active", context, decision)
                return VerificationResult(valid=False, reason="kill_switch_active", decision=decision)

        # All checks passed
        await self._audit_token_verification(token_id, True, "verified", context, decision)
        return VerificationResult(valid=True, decision=decision)

    async def introspect_token(
        self,
        token_id: str,
        required_action: str,
        required_resource: Optional[str] = None,
        workspace_id: Optional[str] = None,
        context: dict = None,
    ) -> IntrospectionResult:
        """Centralized high-risk runtime introspection."""
        context = {
            **(context or {}),
            "workspace_id": workspace_id or (context or {}).get("workspace_id"),
        }
        result = await self.verify_token(
            token_id,
            required_action,
            required_resource,
            context,
        )
        return IntrospectionResult(
            active=result.valid,
            reason=None if result.valid else result.reason,
            kill_switch=result.reason == "kill_switch_active",
            decision=result.decision,
            token=await self.vault.resolve_token(token_id, tenant_id=context.get("tenant_id")),
        )

    def _parse_datetime(self, value):
        if value is None or isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    async def verify_decision(
        self,
        decision: GovernanceDecision,
        action: str,
        resource: Optional[str] = None,
        context: dict = None,
    ) -> VerificationResult:
        """Verify a decision directly (no token)."""
        context = context or {}

        # 1. Check expiry
        if decision.is_expired:
            await self._audit_decision_verification(decision, False, "expired", context)
            return VerificationResult(valid=False, reason="decision_expired", decision=decision)

        # 2. Check revocation
        if decision.decision_type == DecisionType.REVOKED:
            await self._audit_decision_verification(decision, False, "revoked", context)
            return VerificationResult(valid=False, reason="decision_revoked", decision=decision)

        # 3. Check scope
        if not decision.scope.covers(action, resource):
            await self._audit_decision_verification(decision, False, "scope_mismatch", context)
            return VerificationResult(valid=False, reason="scope_mismatch", decision=decision)

        # 4. Check kill switch
        if self.kill_switch is not None:
            ks_check = await self.kill_switch.check(
                decision.actor_id, decision.tenant_id, request_id=decision.decision_id
            )
            if ks_check.active:
                await self._audit_decision_verification(decision, False, "kill_switch", context)
                return VerificationResult(valid=False, reason="kill_switch", decision=decision)

        # 4b. Ancestry check: ensure parent and root are still active
        if hasattr(self.vault, "check_ancestry"):
            ancestry_ok, ancestry_reason = await self.vault.check_ancestry(decision)
            if not ancestry_ok:
                await self._audit_decision_verification(decision, False, ancestry_reason, context)
                return VerificationResult(valid=False, reason=ancestry_reason, decision=decision)

        await self._audit_decision_verification(decision, True, "verified", context)
        return VerificationResult(valid=True, decision=decision)

    async def _audit_token_verification(
        self,
        token_id: str,
        valid: bool,
        reason: str,
        context: dict,
        decision: Optional[GovernanceDecision] = None,
        decision_id: Optional[str] = None,
    ):
        """Audit token verification event."""
        tid = decision.tenant_id if decision else context.get("tenant_id", "unknown")
        aid = decision.actor_id if decision else context.get("actor_id", "unknown")
        did = decision.decision_id if decision else (decision_id or None)

        if self.audit is not None:
            if hasattr(self.audit, "record_token_verification"):
                await self.audit.record_token_verification(
                    tenant_id=tid,
                    actor_id=aid,
                    token_id=token_id,
                    decision_id=did,
                    valid=valid,
                    reason=reason,
                    context=context,
                )
            else:
                # Fallback for legacy/generic audit loggers (e.g. mocks)
                await self.audit.record(
                    event_type="token.verification",
                    tenant_id=tid,
                    actor_id=aid,
                    data={
                        "token_id": token_id,
                        "valid": valid,
                        "reason": reason,
                        "decision_id": did,
                        "context": context,
                    },
                )

    async def _audit_decision_verification(
        self,
        decision: GovernanceDecision,
        valid: bool,
        reason: str,
        context: dict,
    ):
        """Audit decision verification event."""
        if self.audit is not None:
            if hasattr(self.audit, "record_decision_verification"):
                await self.audit.record_decision_verification(
                    tenant_id=decision.tenant_id,
                    actor_id=decision.actor_id,
                    decision_id=decision.decision_id,
                    valid=valid,
                    reason=reason,
                    context=context,
                )
            else:
                await self.audit.record(
                    event_type="decision.verification",
                    tenant_id=decision.tenant_id,
                    actor_id=decision.actor_id,
                    data={
                        "decision_id": decision.decision_id,
                        "valid": valid,
                        "reason": reason,
                        "context": context,
                    },
                )
