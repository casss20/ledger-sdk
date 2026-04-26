"""
Citadel Kernel - Core Execution Lifecycle

The kernel is the governance enforcement engine. It orchestrates:
1. Action normalization
2. Policy resolution
3. Precedence evaluation
4. Approval handling
5. Execution
6. Audit logging

Rule: No decision logic leaks across modules. Each module has one job.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from citadel.actions import Action, Decision, KernelStatus, KernelResult


class Kernel:
    """
    Governance kernel - orchestrates the action lifecycle.

    Single entry point: handle(action) -> KernelResult

    Lifecycle:
    1. Normalize action -> write to actions table
    2. Check idempotency -> return cached if duplicate
    3. Resolve policy -> get immutable snapshot
    4. Precedence check -> kill switch, capability, policy
    5. Risk assessment -> approval required?
    6. Execute or block
    7. Write terminal decision
    8. Audit log
    """

    def __init__(
        self,
        repository,
        policy_resolver,
        precedence,
        approval_service,
        capability_service,
        audit_service,
        executor,
    ):
        self.repo = repository
        self.policy = policy_resolver
        self.precedence = precedence
        self.approvals = approval_service
        self.caps = capability_service
        self.audit = audit_service
        self.executor = executor

    async def handle(
        self,
        action: Action,
        capability_token: Optional[str] = None,
        dry_run: bool = False,
    ) -> KernelResult:
        """
        Handle a single action through the governance lifecycle.

        This is the ONLY entry point. All paths go through here.
        """
        # 1. Check idempotency FIRST (before persisting duplicate action)
        if action.idempotency_key:
            cached = await self.repo.find_decision_by_idempotency(
                action.actor_id, action.idempotency_key, tenant_id=action.tenant_id
            )
            if cached:
                await self.audit.idempotent_return(action, cached)
                return KernelResult(
                    action=action,
                    decision=cached,
                    executed=False,
                    result=None,
                    error=None
                )

        # 2. Persist action (idempotent: ON CONFLICT returns False)
        inserted = await self.repo.save_action(action)
        if not inserted and action.idempotency_key:
            # Another concurrent request with the same idempotency key won the race.
            # Poll briefly for the winning request's decision (max ~500ms).
            for _ in range(50):
                cached = await self.repo.find_decision_by_idempotency(
                    action.actor_id, action.idempotency_key, tenant_id=action.tenant_id
                )
                if cached:
                    await self.audit.idempotent_return(action, cached)
                    return KernelResult(
                        action=action,
                        decision=cached,
                        executed=False,
                        result=None,
                        error=None
                    )
                await asyncio.sleep(0.01)
            # If decision still not found, the winning request may have failed.
            # Return a graceful error instead of crashing.
            return KernelResult(
                action=action,
                decision=None,
                executed=False,
                result=None,
                error="Idempotency conflict: duplicate action in flight, decision not yet available"
            )

        await self.audit.action_received(action)

        # 3. Resolve policy snapshot
        try:
            snapshot = await self.policy.resolve(action)
            await self.audit.policy_evaluated(action, snapshot)
        except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, TimeoutError) as policy_err:
            logger.error(f"Policy resolution failed ({type(policy_err).__name__}): {policy_err}", exc_info=True)
            decision = await self._terminal_decision(
                action, KernelStatus.BLOCKED_SCHEMA, "policy_resolution_failed", str(policy_err)
            )
            return KernelResult(action=action, decision=decision, executed=False, result=None, error=str(policy_err))

        # 4. Precedence evaluation (kill switch -> capability -> policy)
        precedence_result = await self.precedence.evaluate(
            action=action,
            snapshot=snapshot,
            capability_token=capability_token,
            context=action.context,
        )

        if precedence_result.blocked:
            decision = await self._terminal_decision(
                action,
                precedence_result.status,
                precedence_result.winning_rule,
                precedence_result.reason,
                policy_snapshot_id=snapshot.snapshot_id if snapshot else None,
                capability_token=capability_token,
            )
            return KernelResult(action=action, decision=decision, executed=False, result=None, error=precedence_result.reason)

        # 5. Risk assessment / approval check
        approval_check = await self.approvals.check_required(action, snapshot)

        if approval_check.required:
            # Create pending approval
            approval_id = await self.approvals.create_pending(action, approval_check)
            await self.audit.approval_requested(action, approval_id)

            decision = await self._terminal_decision(
                action,
                KernelStatus.PENDING_APPROVAL,
                "approval_required",
                approval_check.reason,
                policy_snapshot_id=snapshot.snapshot_id if snapshot else None,
                risk_level=approval_check.risk_level,
            )
            return KernelResult(action=action, decision=decision, executed=False, result=None, error=None)

        # 5.5 Dry run: evaluate but don't execute
        if dry_run:
            decision = await self._terminal_decision(
                action,
                KernelStatus.DRY_RUN,
                "dry_run",
                "Dry run — policies evaluated but action not executed",
                policy_snapshot_id=snapshot.snapshot_id if snapshot else None,
                capability_token=capability_token,
                path_taken=precedence_result.path_taken,
            )
            return KernelResult(action=action, decision=decision, executed=False, result=None, error=None)

        # 6. Execute (if we get here, action is allowed)
        try:
            result = await self.executor.run(action)
            executed = True
            exec_status = KernelStatus.EXECUTED
            exec_error = None
        except (ValueError, TypeError, RuntimeError, ConnectionError, TimeoutError) as exec_err:
            result = None
            executed = False
            exec_status = KernelStatus.FAILED_EXECUTION
            exec_error = str(exec_err)
            logger.error(f"Action execution failed ({type(exec_err).__name__}): {exec_err}", exc_info=True)

        # 7. Write terminal decision
        decision = await self._terminal_decision(
            action,
            exec_status,
            "execution_complete" if executed else "execution_failed",
            exec_error or "Action executed successfully",
            policy_snapshot_id=snapshot.snapshot_id if snapshot else None,
            capability_token=capability_token,
            path_taken=precedence_result.path_taken,
        )

        # 8. Log execution result
        if executed:
            await self.repo.save_execution_result(action.action_id, True, result, tenant_id=action.tenant_id)
            await self.audit.action_executed(action, result)
        else:
            await self.repo.save_execution_result(action.action_id, False, None, exec_error, tenant_id=action.tenant_id)
            await self.audit.action_failed(action, exec_error)

        return KernelResult(
            action=action,
            decision=decision,
            executed=executed,
            result=result,
            error=exec_error
        )

    async def _terminal_decision(
        self,
        action: Action,
        status: KernelStatus,
        winning_rule: str,
        reason: str,
        policy_snapshot_id: Optional[uuid.UUID] = None,
        capability_token: Optional[str] = None,
        risk_level: Optional[str] = None,
        risk_score: Optional[int] = None,
        path_taken: Optional[str] = None,
    ) -> Decision:
        """Create and persist a terminal decision."""
        decision = Decision(
            decision_id=uuid.uuid4(),
            action_id=action.action_id,
            status=status,
            winning_rule=winning_rule,
            reason=reason,
            policy_snapshot_id=policy_snapshot_id,
            capability_token=capability_token,
            risk_level=risk_level,
            risk_score=risk_score,
            path_taken=path_taken,
            created_at=datetime.utcnow(),
            tenant_id=action.tenant_id,
        )
        await self.repo.save_decision(decision)
        await self.audit.decision_made(action, decision)
        return decision
