"""
Execution Middleware — Layer 2: Runtime execution checks.

Why: Before an action executes, verify the decision/token is still valid.
This is the enforcement boundary between authorization and execution.

Layered enforcement:
  1. Policy engine (DecisionEngine) → authorization decision
  2. ExecutionMiddleware (this module) → verify at runtime
  3. RLS → data isolation
  4. OTel context → cross-service correlation
"""

from typing import Optional, Union

from .governance_decision import GovernanceDecision
from .token_verifier import TokenVerifier, VerificationResult


class ExecutionMiddleware:
    """
    Verifies decisions or tokens before allowing action execution.

    Usage:
        middleware = ExecutionMiddleware(verifier, audit)
        result = await middleware.check(token_id, action, context)
        if result.allowed:
            await execute_action()
    """

    def __init__(self, verifier: TokenVerifier, audit_logger, rate_limiter=None):
        self.verifier = verifier
        self.audit = audit_logger
        self.rate_limiter = rate_limiter

    async def check(
        self,
        credential: Union[str, GovernanceDecision],
        action: str,
        resource: Optional[str] = None,
        context: dict = None,
    ) -> VerificationResult:
        """
        Verify credential before execution.

        credential: gt_ token ID or GovernanceDecision object
        """
        context = context or {}

        if isinstance(credential, str):
            # Token verification (resolves linked decision)
            result = await self.verifier.verify_token(
                credential, action, resource, context
            )
        elif isinstance(credential, GovernanceDecision):
            # Direct decision verification
            result = await self.verifier.verify_decision(
                credential, action, resource, context
            )
        else:
            raise ValueError("credential must be token ID or GovernanceDecision")

        if not result.valid:
            if hasattr(self.audit, "record_execution_blocked"):
                await self.audit.record_execution_blocked(
                    tenant_id=context.get("tenant_id", "unknown"),
                    actor_id=context.get("actor_id", "unknown"),
                    decision_id=result.decision.decision_id if result.decision else None,
                    action=action,
                    resource=resource,
                    reason=result.reason,
                    credential_type=type(credential).__name__,
                )
            else:
                await self.audit.record(
                    event_type="execution.blocked",
                    tenant_id=context.get("tenant_id", "unknown"),
                    actor_id=context.get("actor_id", "unknown"),
                    data={
                        "action": action,
                        "resource": resource,
                        "reason": result.reason,
                        "credential_type": type(credential).__name__,
                    },
                )
            return result

        # Rate limit check
        if self.rate_limiter and result.decision:
            allowed = await self.rate_limiter.check(result.decision, context)
            if not allowed:
                if hasattr(self.audit, "record_execution_rate_limited"):
                    await self.audit.record_execution_rate_limited(
                        tenant_id=result.decision.tenant_id,
                        actor_id=result.decision.actor_id,
                        decision_id=result.decision.decision_id,
                        action=action,
                    )
                else:
                    await self.audit.record(
                        event_type="execution.rate_limited",
                        tenant_id=result.decision.tenant_id,
                        actor_id=result.decision.actor_id,
                        data={
                            "action": action,
                            "decision_id": result.decision.decision_id,
                        },
                    )
                return VerificationResult(valid=False, reason="rate_limited")

        # All checks passed
        if hasattr(self.audit, "record_execution_allowed"):
            await self.audit.record_execution_allowed(
                tenant_id=result.decision.tenant_id,
                actor_id=result.decision.actor_id,
                decision_id=result.decision.decision_id,
                action=action,
                resource=resource,
            )
        else:
            await self.audit.record(
                event_type="execution.allowed",
                tenant_id=result.decision.tenant_id if result.decision else "unknown",
                actor_id=result.decision.actor_id if result.decision else "unknown",
                data={
                    "action": action,
                    "resource": resource,
                    "decision_id": result.decision.decision_id if result.decision else None,
                },
            )
        return result
