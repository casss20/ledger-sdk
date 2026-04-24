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
from typing import Optional, Dict, Any, Callable, Awaitable
from dataclasses import dataclass

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
        repository: 'Repository',
        policy_resolver: 'PolicyResolver',
        precedence: 'Precedence',
        approval_service: 'ApprovalService',
        capability_service: 'CapabilityService',
        audit_service: 'AuditService',
        executor: 'Executor',
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
        except Exception as e:
            decision = await self._terminal_decision(
                action, KernelStatus.BLOCKED_SCHEMA, "policy_resolution_failed", str(e)
            )
            return KernelResult(action=action, decision=decision, executed=False, result=None, error=str(e))

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

        # 6. Execute (if we get here, action is allowed)
        try:
            result = await self.executor.run(action)
            executed = True
            exec_status = KernelStatus.EXECUTED
            exec_error = None
        except Exception as e:
            result = None
            executed = False
            exec_status = KernelStatus.FAILED_EXECUTION
            exec_error = str(e)

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


@dataclass
class PrecedenceResult:
    """Result of precedence evaluation."""
    blocked: bool
    status: Optional[KernelStatus]
    winning_rule: Optional[str]
    reason: Optional[str]
    path_taken: Optional[str]


class Precedence:
    """
    Evaluates governance precedence: kill switch -> capability -> policy.

    No decision logic leaks outside this module.
    """

    async def evaluate(
        self,
        action: Action,
        snapshot: Optional[Any],  # PolicySnapshot
        capability_token: Optional[str],
        caps: 'CapabilityService',
        audit: 'AuditService',
    ) -> PrecedenceResult:
        """
        Evaluate precedence chain.

        Order: Kill Switch -> Capability -> Policy
        """
        # 1. Kill switch check (highest precedence)
        kill_switch = await self._check_kill_switch(action)
        if kill_switch.active:
            await audit.kill_switch_checked(action, kill_switch)
            return PrecedenceResult(
                blocked=True,
                status=KernelStatus.BLOCKED_EMERGENCY,
                winning_rule="kill_switch_active",
                reason=kill_switch.reason,
                path_taken="blocked"
            )

        # 2. Capability check (if token provided)
        if capability_token:
            cap_check = await caps.validate(capability_token, action)
            await audit.capability_checked(action, cap_check)

            if not cap_check.valid:
                return PrecedenceResult(
                    blocked=True,
                    status=KernelStatus.BLOCKED_CAPABILITY,
                    winning_rule="capability_invalid",
                    reason=cap_check.reason,
                    path_taken="blocked"
                )

        # 3. Policy evaluation
        if snapshot:
            policy_result = self._evaluate_policy(snapshot, action)

            if policy_result.effect == "BLOCK":
                return PrecedenceResult(
                    blocked=True,
                    status=KernelStatus.BLOCKED_POLICY,
                    winning_rule=policy_result.rule_name,
                    reason=policy_result.reason,
                    path_taken="blocked"
                )
            elif policy_result.effect == "PENDING_APPROVAL":
                # Don't block here - let approval_service handle
                return PrecedenceResult(
                    blocked=False,
                    status=None,
                    winning_rule=policy_result.rule_name,
                    reason=policy_result.reason,
                    path_taken="approval_required"
                )

        # 4. Path selection (from RUNTIME.md)
        path = self._select_path(action, snapshot)

        return PrecedenceResult(
            blocked=False,
            status=None,
            winning_rule="allowed",
            reason="All checks passed",
            path_taken=path
        )

    async def _check_kill_switch(self, action: Action) -> Any:
        """Check if kill switch is active for action scope."""
        # Delegates to repository
        pass

    def _evaluate_policy(self, snapshot: Any, action: Action) -> Any:
        """Evaluate policy rules against action."""
        # Returns PolicyEvaluationResult with effect
        pass

    def _select_path(self, action: Action, snapshot: Any) -> str:
        """Select execution path: fast, standard, structured, high_risk."""
        # From RUNTIME.md path selection
        if self._is_fast_path(action):
            return "fast"
        elif self._is_high_risk(action):
            return "high_risk"
        elif self._is_structured(action):
            return "structured"
        return "standard"

    def _is_fast_path(self, action: Action) -> bool:
        """Trusted actor + known action + no risk flags."""
        pass

    def _is_high_risk(self, action: Action) -> bool:
        """Irreversible + high stakes + production."""
        pass

    def _is_structured(self, action: Action) -> bool:
        """Multi-step + needs planning."""
        pass


# Placeholder classes for type hints
class Repository:
    async def save_action(self, action: Action): pass
    async def save_decision(self, decision: Decision): pass
    async def find_decision_by_idempotency(self, actor_id: str, key: str) -> Optional[Decision]: pass
    async def save_execution_result(self, action_id: uuid.UUID, success: bool, result: Any, error: Optional[str] = None): pass


class PolicyResolver:
    async def resolve(self, action: Action) -> Any: pass  # Returns PolicySnapshot


class ApprovalService:
    async def check_required(self, action: Action, snapshot: Any) -> Any: pass  # Returns ApprovalCheck
    async def create_pending(self, action: Action, check: Any) -> uuid.UUID: pass  # Returns approval_id


class CapabilityService:
    async def validate(self, token: str, action: Action) -> Any: pass  # Returns CapabilityCheck


class AuditService:
    async def action_received(self, action: Action): pass
    async def policy_evaluated(self, action: Action, snapshot: Any): pass
    async def kill_switch_checked(self, action: Action, kill_switch: Any): pass
    async def capability_checked(self, action: Action, check: Any): pass
    async def approval_requested(self, action: Action, approval_id: uuid.UUID): pass
    async def decision_made(self, action: Action, decision: Decision): pass
    async def action_executed(self, action: Action, result: Any): pass
    async def action_failed(self, action: Action, error: str): pass
    async def idempotent_return(self, action: Action, cached: Decision): pass


class Executor:
    async def run(self, action: Action) -> Any: pass
