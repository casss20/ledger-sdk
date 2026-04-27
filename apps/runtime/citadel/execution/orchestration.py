"""
Orchestration Runtime — Shared governance primitives for multi-agent coordination.

This module implements the 4 shared orchestration primitives:
- cg.delegate()
- cg.handoff()
- cg.gather()
- cg.introspect()

Design principles:
- One governance kernel: all orchestration flows through the existing kernel.handle()
- Decision-first: every child action gets its own decision
- Shared lineage: parent/child/root decision ancestry preserved
- Runtime enforceability: kill switch, introspection, revocation apply to all branches
- Brownfield compatibility: extends existing Citadel, doesn't replace it
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from citadel.actions import Action, Decision, KernelStatus, KernelResult
from citadel.execution.kernel import Kernel
from citadel.tokens.governance_decision import GovernanceDecision, DecisionType, DecisionScope, KillSwitchScope
from citadel.tokens.governance_token import CapabilityToken
from citadel.tokens.token_vault import TokenVault
from citadel.tokens.token_verifier import TokenVerifier
from citadel.tokens.kill_switch import KillSwitch
from citadel.repository import Repository

logger = logging.getLogger(__name__)


@dataclass
class DelegationResult:
    """Result of cg.delegate()."""
    success: bool
    child_action: Optional[Action] = None
    child_decision: Optional[Decision] = None
    child_grant: Optional[str] = None
    reason: str = ""
    error: Optional[str] = None


@dataclass
class HandoffResult:
    """Result of cg.handoff()."""
    success: bool
    new_decision: Optional[Decision] = None
    new_grant: Optional[str] = None
    previous_authority_superseded: bool = False
    reason: str = ""
    error: Optional[str] = None


@dataclass
class BranchResult:
    """Result of a single gather branch."""
    branch_index: int
    success: bool
    action: Optional[Action] = None
    decision: Optional[Decision] = None
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class GatherResult:
    """Result of cg.gather()."""
    success: bool
    branches: List[BranchResult] = field(default_factory=list)
    completed: int = 0
    failed: int = 0
    reason: str = ""
    error: Optional[str] = None


@dataclass
class IntrospectionStatus:
    """Rich introspection result for orchestration contexts."""
    active: bool
    reason: Optional[str] = None
    kill_switched: bool = False
    expired: bool = False
    revoked: bool = False
    scope_valid: bool = False
    actor_boundary_valid: bool = True
    decision: Optional[GovernanceDecision] = None
    token: Optional[Dict[str, Any]] = None


class OrchestrationRuntime:
    """
    Shared orchestration runtime built on top of the governance kernel.

    All orchestration primitives delegate to the kernel for decision-making
    and to the token vault for grant issuance.
    """

    def __init__(
        self,
        kernel: Kernel,
        token_vault: TokenVault,
        token_verifier: TokenVerifier,
        repository: Repository,
        audit_service,
        kill_switch: Optional[KillSwitch] = None,
    ):
        if audit_service is None:
            raise ValueError("audit_service is required for OrchestrationRuntime")
        self.kernel = kernel
        self.vault = token_vault
        self.verifier = token_verifier
        self.repo = repository
        self.audit = audit_service
        self.kill_switch = kill_switch

    # =====================================================================
    # cg.delegate()
    # =====================================================================

    async def delegate(
        self,
        parent_decision: GovernanceDecision,
        child_actor_id: str,
        action_name: str,
        resource: str,
        scope: DecisionScope,
        payload: Dict[str, Any] = None,
        context: Dict[str, Any] = None,
        tenant_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        dry_run: bool = False,
    ) -> DelegationResult:
        """
        Create a child execution grant under a parent decision lineage.

        Validates:
        - Parent decision is active
        - Parent not kill-switched
        - Child scope is narrower than parent scope
        - Child actor exists

        Issues:
        - Child action with lineage
        - Child decision via kernel
        - Child capability token
        - Audit linkage
        """
        # 1. Introspect parent — resolve ground truth from vault
        parent_status = await self.introspect_decision(
            parent_decision,
            parent_decision.action,
            parent_decision.resource,
        )
        if not parent_status.active:
            await self._audit_delegate_blocked(
                parent_decision, child_actor_id, action_name,
                f"Parent not active: {parent_status.reason}"
            )
            return DelegationResult(
                success=False,
                reason=f"Parent authority not active: {parent_status.reason}",
            )

        # Use vault-resolved parent for all security-critical fields
        resolved_parent = parent_status.decision if (parent_status.decision and parent_status.decision.decision_id == parent_decision.decision_id) else parent_decision

        # 2. Check kill switch on parent
        if self.kill_switch:
            ks = await self.kill_switch.check(
                resolved_parent.actor_id, resolved_parent.tenant_id, request_id=resolved_parent.decision_id
            )
            if ks.active:
                await self._audit_delegate_blocked(
                    resolved_parent, child_actor_id, action_name,
                    f"Kill switch active: {ks.reason}"
                )
                return DelegationResult(
                    success=False,
                    reason=f"Kill switch active: {ks.reason}",
                )

        # 3. Validate scope narrowing against resolved parent scope
        if not self._is_narrower_scope(resolved_parent.scope, scope):
            await self._audit_delegate_blocked(
                resolved_parent, child_actor_id, action_name,
                "Child scope wider than parent scope"
            )
            return DelegationResult(
                success=False,
                reason="Child scope exceeds parent authority",
            )

        # 4. Build child action with lineage from resolved parent
        child_action = Action(
            action_id=uuid.uuid4(),
            actor_id=child_actor_id,
            actor_type="agent",
            action_name=action_name,
            resource=resource,
            tenant_id=tenant_id or resolved_parent.tenant_id,
            payload=payload or {},
            context=context or {},
            session_id=None,
            request_id=None,
            idempotency_key=None,
            root_decision_id=resolved_parent.root_decision_id or resolved_parent.decision_id,
            parent_decision_id=resolved_parent.decision_id,
            trace_id=trace_id or resolved_parent.trace_id or f"trace_{uuid.uuid4().hex}",
            parent_actor_id=resolved_parent.actor_id,
            workflow_id=workflow_id or resolved_parent.workflow_id,
            created_at=datetime.now(timezone.utc),
        )

        # 5. Run through kernel
        governed = await self.kernel.handle(child_action, dry_run=dry_run)

        if governed.decision.status not in (KernelStatus.ALLOWED, KernelStatus.EXECUTED):
            await self._audit_delegate_blocked(
                parent_decision, child_actor_id, action_name,
                f"Kernel blocked: {governed.decision.reason}"
            )
            return DelegationResult(
                success=False,
                child_action=child_action,
                child_decision=governed.decision,
                reason=f"Governance blocked: {governed.decision.reason}",
            )

        # 6. Issue child capability token — FAIL CLOSED
        # If token issuance fails after kernel approved the child, we must
        # not return a usable child grant. Attempt compensating cleanup.
        child_grant = None
        if not dry_run and governed.decision.status == KernelStatus.ALLOWED:
            child_gov_decision = self._kernel_to_governance_decision(
                governed.decision, child_action, scope
            )
            try:
                token = await self.vault.issue_token_for_decision(
                    child_gov_decision,
                    lifetime_seconds=3600,
                )
                child_grant = token.token_id
            except Exception as e:
                logger.error(
                    "Token issuance failed for child decision %s of parent %s: %s",
                    child_gov_decision.decision_id,
                    resolved_parent.decision_id,
                    e,
                )
                # CRITICAL: If token issuance fails after kernel approval, we MUST
                # revoke the child governance decision so it cannot be used as valid
                # authority by any other path. If revoke also fails, we raise to
                # prevent a partial authority state.
                try:
                    await self.vault.revoke_decision(
                        child_gov_decision.decision_id,
                        tenant_id=child_gov_decision.tenant_id,
                        reason="token_issuance_failed",
                    )
                except Exception as revoke_err:
                    logger.error(
                        "CRITICAL: Compensating revoke failed for child decision %s: %s. "
                        "An active child decision without a token may remain.",
                        child_gov_decision.decision_id,
                        revoke_err,
                    )
                    raise RuntimeError(
                        f"Token issuance failed and compensating revoke failed for "
                        f"decision {child_gov_decision.decision_id}. "
                        f"Original error: {e}; Revoke error: {revoke_err}"
                    ) from revoke_err
                await self._audit_delegate_blocked(
                    resolved_parent, child_actor_id, action_name,
                    f"Token issuance failed: {e}"
                )
                return DelegationResult(
                    success=False,
                    child_action=child_action,
                    child_decision=governed.decision,
                    reason=f"Token issuance failed: {e}",
                    error=str(e),
                )

        # 7. Audit
        await self._audit_delegate_created(
            parent_decision, child_action, governed.decision, child_grant
        )

        return DelegationResult(
            success=True,
            child_action=child_action,
            child_decision=governed.decision,
            child_grant=child_grant,
            reason="Delegated successfully",
        )

    # =====================================================================
    # cg.handoff()
    # =====================================================================

    async def handoff(
        self,
        current_decision: GovernanceDecision,
        new_actor_id: str,
        action_name: str,
        resource: str,
        scope: DecisionScope,
        payload: Dict[str, Any] = None,
        context: Dict[str, Any] = None,
        tenant_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        reason: str = "",
        dry_run: bool = False,
    ) -> HandoffResult:
        """
        Transfer active authority from one agent to another.

        1. Validate current decision is active
        2. Record authority transfer event
        3. Mark current authority as superseded
        4. Create new action for new actor with preserved lineage
        5. Run through kernel
        6. Issue new scoped grant
        7. Audit
        """
        # 1. Introspect current — resolve ground truth from vault
        current_status = await self.introspect_decision(
            current_decision,
            current_decision.action,
            current_decision.resource,
        )
        if not current_status.active:
            await self._audit_handoff_blocked(
                current_decision, new_actor_id,
                f"Current authority not active: {current_status.reason}"
            )
            return HandoffResult(
                success=False,
                reason=f"Current authority not active: {current_status.reason}",
            )

        # Use vault-resolved current decision for all security-critical fields
        resolved_current = current_status.decision if (current_status.decision and current_status.decision.decision_id == current_decision.decision_id) else current_decision

        # 2. (Deferred) Supersede current authority — moved to AFTER kernel validation.
        #    If we superseded before kernel approval and the kernel blocked,
        #    the old authority would be permanently lost with no recovery path.

        # 3. Validate scope narrowing — handoff must not widen authority.
        if not self._is_narrower_scope(resolved_current.scope, scope):
            await self._audit_handoff_blocked(
                resolved_current, new_actor_id,
                "Handoff scope wider than current authority"
            )
            return HandoffResult(
                success=False,
                previous_authority_superseded=False,
                reason="Handoff scope exceeds current authority",
            )

        # 4. Build new action with lineage from resolved current decision
        new_action = Action(
            action_id=uuid.uuid4(),
            actor_id=new_actor_id,
            actor_type="agent",
            action_name=action_name,
            resource=resource,
            tenant_id=tenant_id or resolved_current.tenant_id,
            payload=payload or {},
            context=context or {},
            session_id=None,
            request_id=None,
            idempotency_key=None,
            root_decision_id=resolved_current.root_decision_id or resolved_current.decision_id,
            # Handoff: new decision links to the OLD decision's parent,
            # NOT the old decision itself (which will be superseded).
            # This preserves lineage while avoiding ancestry rejection.
            parent_decision_id=resolved_current.parent_decision_id,
            trace_id=trace_id or resolved_current.trace_id or f"trace_{uuid.uuid4().hex}",
            parent_actor_id=resolved_current.actor_id,
            workflow_id=workflow_id or resolved_current.workflow_id,
            created_at=datetime.now(timezone.utc),
        )

        # 5. Run through kernel
        governed = await self.kernel.handle(new_action, dry_run=dry_run)

        if governed.decision.status not in (KernelStatus.ALLOWED, KernelStatus.EXECUTED):
            await self._audit_handoff_blocked(
                resolved_current, new_actor_id,
                f"Kernel blocked: {governed.decision.reason}"
            )
            return HandoffResult(
                success=False,
                previous_authority_superseded=False,
                reason=f"Governance blocked: {governed.decision.reason}",
            )

        # 2. (Actual) Supersede current authority now that kernel has approved the new action.
        # Create a new decision object to avoid mutating the caller's reference
        superseded_decision = GovernanceDecision(
            decision_id=resolved_current.decision_id,
            decision_type=resolved_current.decision_type,
            tenant_id=resolved_current.tenant_id,
            actor_id=resolved_current.actor_id,
            action=resolved_current.action,
            scope=resolved_current.scope,
            request_id=resolved_current.request_id,
            trace_id=resolved_current.trace_id,
            workspace_id=resolved_current.workspace_id,
            agent_id=resolved_current.agent_id,
            subject_type=resolved_current.subject_type,
            subject_id=resolved_current.subject_id,
            resource=resolved_current.resource,
            risk_level=resolved_current.risk_level,
            policy_version=resolved_current.policy_version,
            approval_state=resolved_current.approval_state,
            approved_by=resolved_current.approved_by,
            approved_at=resolved_current.approved_at,
            constraints=resolved_current.constraints,
            expiry=resolved_current.expiry,
            kill_switch_scope=resolved_current.kill_switch_scope,
            created_at=resolved_current.created_at,
            gt_token=resolved_current.gt_token,
            issued_token_id=resolved_current.issued_token_id,
            revoked_at=resolved_current.revoked_at,
            revoked_reason=resolved_current.revoked_reason,
            audit_entry_ids=resolved_current.audit_entry_ids,
            reason=resolved_current.reason,
            root_decision_id=resolved_current.root_decision_id,
            parent_decision_id=resolved_current.parent_decision_id,
            parent_actor_id=resolved_current.parent_actor_id,
            workflow_id=resolved_current.workflow_id,
            superseded_at=datetime.now(timezone.utc),
            superseded_reason=reason or f"Handoff to {new_actor_id}",
        )
        await self.vault.store_decision(superseded_decision)

        # 5. Issue new grant
        new_grant = None
        if not dry_run and governed.decision.status == KernelStatus.ALLOWED:
            new_gov_decision = self._kernel_to_governance_decision(
                governed.decision, new_action, scope
            )
            token = await self.vault.issue_token_for_decision(
                new_gov_decision,
                lifetime_seconds=3600,
            )
            new_grant = token.token_id

        # 6. Audit
        await self._audit_handoff_performed(
            current_decision, new_action, governed.decision, new_grant, reason
        )

        return HandoffResult(
            success=True,
            new_decision=governed.decision,
            new_grant=new_grant,
            previous_authority_superseded=True,
            reason=f"Handoff to {new_actor_id} successful",
        )

    # =====================================================================
    # cg.gather()
    # =====================================================================

    async def gather(
        self,
        parent_decision: GovernanceDecision,
        branches: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        shared_context: Dict[str, Any] = None,
        dry_run: bool = False,
    ) -> GatherResult:
        """
        Run parallel child branches under one parent orchestration scope.

        Each branch gets its own action, decision, and optional grant.
        All branches share root_decision_id and trace_id.
        Kill switch checked on each branch.
        """
        # Validate parent — resolve ground truth from vault
        parent_status = await self.introspect_decision(
            parent_decision,
            parent_decision.action,
            parent_decision.resource,
        )
        if not parent_status.active:
            await self._audit_gather_blocked(
                parent_decision,
                f"Parent not active: {parent_status.reason}"
            )
            return GatherResult(
                success=False,
                reason=f"Parent authority not active: {parent_status.reason}",
            )

        # Use vault-resolved parent for all security-critical fields
        resolved_parent = parent_status.decision if (parent_status.decision and parent_status.decision.decision_id == parent_decision.decision_id) else parent_decision

        # Check kill switch
        if self.kill_switch:
            ks = await self.kill_switch.check(
                resolved_parent.actor_id, resolved_parent.tenant_id, request_id=resolved_parent.decision_id
            )
            if ks.active:
                await self._audit_gather_blocked(
                    resolved_parent,
                    f"Kill switch active: {ks.reason}"
                )
                return GatherResult(
                    success=False,
                    reason=f"Kill switch active: {ks.reason}",
                )

        root_id = resolved_parent.root_decision_id or resolved_parent.decision_id
        tid = trace_id or resolved_parent.trace_id or f"trace_{uuid.uuid4().hex}"

        # Validate each branch scope is narrower than resolved parent scope
        for i, branch in enumerate(branches):
            branch_scope = DecisionScope(
                actions=[branch["action"]],
                resources=[branch["resource"]],
            )
            if not self._is_narrower_scope(resolved_parent.scope, branch_scope):
                await self._audit_gather_blocked(
                    resolved_parent,
                    f"Branch {i} scope wider than parent scope"
                )
                return GatherResult(
                    success=False,
                    reason=f"Branch {i} scope exceeds parent authority",
                )

        # Create branch actions with lineage from resolved parent
        # Use distilled context to avoid passing unnecessary parent history
        branch_actions = []
        for i, branch in enumerate(branches):
            distilled = self._distill_branch_context(
                branch.get("context", {}),
                shared_context=shared_context,
            )
            action = Action(
                action_id=uuid.uuid4(),
                actor_id=branch.get("actor_id", resolved_parent.actor_id),
                actor_type=branch.get("actor_type", "agent"),
                action_name=branch["action"],
                resource=branch["resource"],
                tenant_id=tenant_id or resolved_parent.tenant_id,
                payload=branch.get("payload", {}),
                context=distilled,
                session_id=None,
                request_id=None,
                idempotency_key=None,
                root_decision_id=root_id,
                parent_decision_id=resolved_parent.decision_id,
                trace_id=tid,
                parent_actor_id=resolved_parent.actor_id,
                workflow_id=workflow_id or resolved_parent.workflow_id,
                created_at=datetime.now(timezone.utc),
            )
            branch_actions.append(action)

        # Run branches
        branch_results = []
        if dry_run:
            for i, action in enumerate(branch_actions):
                governed = await self.kernel.handle(action, dry_run=True)
                branch_results.append(BranchResult(
                    branch_index=i,
                    success=governed.decision.status == KernelStatus.ALLOWED,
                    action=action,
                    decision=governed.decision,
                ))
        else:
            coros = [self.kernel.handle(action) for action in branch_actions]
            governed_results = await asyncio.gather(*coros, return_exceptions=True)

            for i, governed in enumerate(governed_results):
                if isinstance(governed, Exception):
                    branch_results.append(BranchResult(
                        branch_index=i,
                        success=False,
                        action=branch_actions[i],
                        error=str(governed),
                    ))
                else:
                    branch_results.append(BranchResult(
                        branch_index=i,
                        success=governed.decision.status in (KernelStatus.ALLOWED, KernelStatus.EXECUTED),
                        action=branch_actions[i],
                        decision=governed.decision,
                        result=governed.result,
                        error=governed.error,
                    ))

        # Audit branches in a single batched call instead of N individual writes
        await self._audit_branches_completed_batch(parent_decision, branch_results)

        completed = sum(1 for br in branch_results if br.success)
        failed = len(branch_results) - completed

        await self._audit_gather_created(parent_decision, branch_results)

        return GatherResult(
            success=failed == 0,
            branches=branch_results,
            completed=completed,
            failed=failed,
            reason=f"Gather complete: {completed}/{len(branches)} succeeded",
        )

    # =====================================================================
    # cg.introspect()
    # =====================================================================

    async def introspect(
        self,
        token_id: Optional[str] = None,
        decision_id: Optional[str] = None,
        required_action: str = "",
        required_resource: Optional[str] = None,
        workspace_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> IntrospectionStatus:
        """
        Central runtime safety check for orchestration.

        Validates:
        - Token/grant validity
        - Expiry
        - Revocation
        - Workspace scope
        - Action scope
        - Resource scope
        - Actor boundary (handoff superseded?)
        - Kill switch state
        """
        decision = None
        token_data = None

        if token_id:
            token_data = await self.vault.resolve_token(token_id, tenant_id=tenant_id)
            if token_data:
                decision_id = token_data.get("decision_id")

        if decision_id:
            decision_data = await self.vault.resolve_decision(decision_id, tenant_id=tenant_id)
            if decision_data:
                decision = self._dict_to_governance_decision(decision_data)

        # Workspace boundary check
        if workspace_id and decision and decision.workspace_id and decision.workspace_id != workspace_id:
            return IntrospectionStatus(
                active=False,
                reason="Workspace mismatch",
                actor_boundary_valid=False,
                decision=decision,
                token=token_data,
            )

        if decision is None:
            return IntrospectionStatus(
                active=False,
                reason="Decision or token not found",
            )

        # Check expiry
        if decision.is_expired:
            return IntrospectionStatus(
                active=False,
                reason="Decision expired",
                expired=True,
                decision=decision,
                token=token_data,
            )

        # Check revocation
        if decision.decision_type == DecisionType.REVOKED or decision.revoked_at is not None:
            return IntrospectionStatus(
                active=False,
                reason="Decision revoked",
                revoked=True,
                decision=decision,
                token=token_data,
            )

        # Check superseded (handoff)
        if decision.superseded_at is not None:
            return IntrospectionStatus(
                active=False,
                reason=f"Authority superseded: {decision.superseded_reason}",
                actor_boundary_valid=False,
                decision=decision,
                token=token_data,
            )

        # Check ancestry: parent and root must still be active
        ancestry_ok, ancestry_reason = await self.vault.check_ancestry(decision)
        if not ancestry_ok:
            return IntrospectionStatus(
                active=False,
                reason=f"Ancestry revoked: {ancestry_reason}",
                revoked=True,
                decision=decision,
                token=token_data,
            )

        # Check scope
        scope_valid = True
        if required_action:
            scope_valid = decision.scope.covers(required_action, required_resource)
            if not scope_valid:
                return IntrospectionStatus(
                    active=False,
                    reason="Scope mismatch",
                    scope_valid=False,
                    decision=decision,
                    token=token_data,
                )

        # Check kill switch
        if self.kill_switch:
            ks = await self.kill_switch.check(
                decision.actor_id, decision.tenant_id, request_id=decision.decision_id
            )
            if ks.active:
                return IntrospectionStatus(
                    active=False,
                    reason=f"Kill switch active: {ks.reason}",
                    kill_switched=True,
                    scope_valid=scope_valid,
                    decision=decision,
                    token=token_data,
                )

        return IntrospectionStatus(
            active=True,
            scope_valid=scope_valid,
            actor_boundary_valid=True,
            decision=decision,
            token=token_data,
        )

    async def introspect_decision(
        self,
        decision: GovernanceDecision,
        required_action: str,
        required_resource: Optional[str] = None,
    ) -> IntrospectionStatus:
        """Convenience: introspect an already-resolved GovernanceDecision object."""
        return await self.introspect(
            decision_id=decision.decision_id,
            required_action=required_action,
            required_resource=required_resource,
            tenant_id=decision.tenant_id,
        )

    # =====================================================================
    # Helpers
    # =====================================================================

    def _distill_branch_context(
        self,
        branch_context: Dict[str, Any],
        shared_context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Build minimal branch context from raw branch + shared inputs.

        Only preserves:
        - Required lineage identifiers (trace_id, workflow_id, parent_decision_id)
        - Governance metadata (risk_level, kill_switch_scope if present)
        - Explicit task-local keys provided by the caller
        - Shared immutable context merged safely

        Drops:
        - Full parent action history
        - Large parent payloads
        - Audit/event logs
        - Ephemeral runtime state
        """
        # Start with shared context (immutable reference, not deep-copied)
        distilled: Dict[str, Any] = {}
        if shared_context:
            # Only copy lightweight keys; drop heavy objects
            for k, v in shared_context.items():
                if isinstance(v, (str, int, float, bool, type(None))):
                    distilled[k] = v
                elif isinstance(v, (list, tuple)) and len(v) <= 16:
                    distilled[k] = list(v)
                elif isinstance(v, dict) and len(v) <= 8:
                    distilled[k] = dict(v)
                # Skip large objects, bytes, custom classes

        # Merge branch-specific context with same filtering
        for k, v in branch_context.items():
            if isinstance(v, (str, int, float, bool, type(None))):
                distilled[k] = v
            elif isinstance(v, (list, tuple)) and len(v) <= 16:
                distilled[k] = list(v)
            elif isinstance(v, dict) and len(v) <= 8:
                distilled[k] = dict(v)
            # Skip large objects, bytes, custom classes

        return distilled

    def _is_narrower_scope(self, parent: DecisionScope, child: DecisionScope) -> bool:
        """Check that child scope is a subset of parent scope.

        Empty child actions or resources are treated as "no additional scope"
        and pass through. If you want empty to mean "deny everything",
        enforce that at the caller.
        """
        # If child declares no actions, it has no action scope to violate.
        if child.actions and parent.actions:
            parent_set = set(parent.actions)
            if '*' not in parent_set:
                for child_action in child.actions:
                    matched = any(
                        pa == '*' or
                        (pa.endswith(':*') and child_action.startswith(pa[:-1])) or
                        pa == child_action
                        for pa in parent.actions
                    )
                    if not matched:
                        return False

        if child.resources and parent.resources:
            for cr in child.resources:
                matched = any(
                    pr == '*' or
                    (pr.endswith('*') and cr.startswith(pr[:-1])) or
                    pr == cr
                    for pr in parent.resources
                )
                if not matched:
                    return False

        if child.max_spend is not None and parent.max_spend is not None:
            if child.max_spend > parent.max_spend:
                return False

        if child.rate_limit is not None and parent.rate_limit is not None:
            if child.rate_limit > parent.rate_limit:
                return False

        return True

    def _kernel_to_governance_decision(
        self,
        decision: Decision,
        action: Action,
        scope: DecisionScope,
    ) -> GovernanceDecision:
        """Convert a kernel Decision + Action into a GovernanceDecision for token vault."""
        return GovernanceDecision(
            decision_id=str(decision.decision_id),
            decision_type=DecisionType.ALLOW if decision.status in (KernelStatus.ALLOWED, KernelStatus.EXECUTED) else DecisionType.DENY,
            tenant_id=action.tenant_id or "default",
            actor_id=action.actor_id,
            action=action.action_name,
            scope=scope,
            resource=action.resource,
            request_id=action.request_id,
            trace_id=action.trace_id,
            workspace_id=action.tenant_id,
            agent_id=action.actor_id,
            risk_level=decision.risk_level or "low",
            policy_version="unknown",
            expiry=None,
            root_decision_id=action.root_decision_id,
            parent_decision_id=action.parent_decision_id,
            parent_actor_id=action.parent_actor_id,
            workflow_id=action.workflow_id,
        )

    def _dict_to_governance_decision(self, data: Dict[str, Any]) -> GovernanceDecision:
        """Reconstruct GovernanceDecision from vault dict."""
        return GovernanceDecision(
            decision_id=data["decision_id"],
            decision_type=DecisionType(data["decision_type"]),
            tenant_id=data["tenant_id"],
            actor_id=data["actor_id"],
            action=data["action"],
            scope=DecisionScope(
                actions=data.get("scope_actions", []),
                resources=data.get("scope_resources", []),
                max_spend=data.get("scope_max_spend"),
                rate_limit=data.get("scope_rate_limit"),
            ),
            request_id=data.get("request_id"),
            trace_id=data.get("trace_id"),
            workspace_id=data.get("workspace_id") or data["tenant_id"],
            agent_id=data.get("agent_id") or data["actor_id"],
            subject_type=data.get("subject_type", "agent"),
            subject_id=data.get("subject_id") or data["actor_id"],
            resource=data.get("resource"),
            risk_level=data.get("risk_level", "low"),
            policy_version=data.get("policy_version", "unknown"),
            approval_state=data.get("approval_state", "auto_approved"),
            approved_by=data.get("approved_by"),
            approved_at=self._parse_dt(data.get("approved_at")),
            constraints=data.get("constraints", {}),
            expiry=self._parse_dt(data.get("expiry") or data.get("expires_at")),
            kill_switch_scope=KillSwitchScope(data.get("kill_switch_scope", "request")),
            created_at=self._parse_dt(data.get("created_at")),
            gt_token=data.get("gt_token"),
            issued_token_id=data.get("issued_token_id"),
            revoked_at=self._parse_dt(data.get("revoked_at")),
            revoked_reason=data.get("revoked_reason"),
            reason=data.get("reason", ""),
            root_decision_id=data.get("root_decision_id"),
            parent_decision_id=data.get("parent_decision_id"),
            parent_actor_id=data.get("parent_actor_id"),
            workflow_id=data.get("workflow_id"),
            superseded_at=self._parse_dt(data.get("superseded_at")),
            superseded_reason=data.get("superseded_reason"),
        )

    def _parse_dt(self, value):
        if value is None or isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    # =====================================================================
    # Audit helpers
    # =====================================================================

    async def _audit_delegate_created(
        self,
        parent: GovernanceDecision,
        child_action: Action,
        child_decision: Decision,
        child_grant: Optional[str],
    ):
        payload = {
            "parent_decision_id": parent.decision_id,
            "child_decision_id": str(child_decision.decision_id),
            "child_action_id": str(child_action.action_id),
            "child_actor_id": child_action.actor_id,
            "child_grant": child_grant,
            "trace_id": child_action.trace_id,
        }
        if hasattr(self.audit, 'delegate_created'):
            await self.audit.delegate_created(child_action, payload)
        elif hasattr(self.audit, 'record'):
            await self.audit.record(
                event_type="delegate_created",
                tenant_id=parent.tenant_id,
                actor_id=parent.actor_id,
                payload=payload,
            )
        else:
            await self.audit._log(
                action=child_action,
                event_type="delegate_created",
                payload=payload,
            )

    async def _audit_delegate_blocked(
        self,
        parent: GovernanceDecision,
        child_actor_id: str,
        action_name: str,
        reason: str,
    ):
        payload = {
            "parent_decision_id": parent.decision_id,
            "child_actor_id": child_actor_id,
            "action_name": action_name,
            "reason": reason,
        }
        if hasattr(self.audit, 'record'):
            await self.audit.record(
                event_type="delegate_created",
                tenant_id=parent.tenant_id,
                actor_id=parent.actor_id,
                payload={**payload, "blocked": True},
            )
        else:
            # Fallback: can't _log without an Action, skip
            pass

    async def _audit_handoff_performed(
        self,
        old: GovernanceDecision,
        new_action: Action,
        new_decision: Decision,
        new_grant: Optional[str],
        reason: str,
    ):
        payload = {
            "old_decision_id": old.decision_id,
            "old_actor_id": old.actor_id,
            "new_decision_id": str(new_decision.decision_id),
            "new_actor_id": new_action.actor_id,
            "new_grant": new_grant,
            "reason": reason,
            "trace_id": new_action.trace_id,
        }
        if hasattr(self.audit, 'handoff_performed'):
            await self.audit.handoff_performed(new_action, payload)
        elif hasattr(self.audit, 'record'):
            await self.audit.record(
                event_type="handoff_performed",
                tenant_id=old.tenant_id,
                actor_id=old.actor_id,
                payload=payload,
            )
        else:
            await self.audit._log(
                action=new_action,
                event_type="handoff_performed",
                payload=payload,
            )

    async def _audit_handoff_blocked(
        self,
        old: GovernanceDecision,
        new_actor_id: str,
        reason: str,
    ):
        payload = {
            "old_decision_id": old.decision_id,
            "new_actor_id": new_actor_id,
            "reason": reason,
        }
        if hasattr(self.audit, 'record'):
            await self.audit.record(
                event_type="handoff_performed",
                tenant_id=old.tenant_id,
                actor_id=old.actor_id,
                payload={**payload, "blocked": True},
            )

    async def _audit_gather_created(
        self,
        parent: GovernanceDecision,
        branch_results: List[BranchResult],
    ):
        payload = {
            "parent_decision_id": parent.decision_id,
            "branch_count": len(branch_results),
            "branches": [
                {
                    "index": br.branch_index,
                    "action_id": str(br.action.action_id) if br.action else None,
                    "decision_id": str(br.decision.decision_id) if br.decision else None,
                    "success": br.success,
                }
                for br in branch_results
            ],
            "trace_id": parent.trace_id,
        }
        if hasattr(self.audit, 'gather_created'):
            await self.audit.gather_created(parent, payload)
        elif hasattr(self.audit, 'record'):
            await self.audit.record(
                event_type="gather_created",
                tenant_id=parent.tenant_id,
                actor_id=parent.actor_id,
                payload=payload,
            )
        else:
            # Can't _log without Action for all branches; skip
            pass

    async def _audit_gather_blocked(
        self,
        parent: GovernanceDecision,
        reason: str,
    ):
        payload = {
            "parent_decision_id": parent.decision_id,
            "reason": reason,
        }
        if hasattr(self.audit, 'record'):
            await self.audit.record(
                event_type="gather_created",
                tenant_id=parent.tenant_id,
                actor_id=parent.actor_id,
                payload={**payload, "blocked": True},
            )

    async def _audit_branches_completed_batch(
        self,
        parent: GovernanceDecision,
        branch_results: List[BranchResult],
    ):
        """Batch audit all branch completions into a single record.

        Reduces DB round-trips from N individual writes to 1 summary write.
        Each branch still gets its own entry in the payload for traceability.
        """
        payload = {
            "parent_decision_id": parent.decision_id,
            "branches": [
                {
                    "index": br.branch_index,
                    "action_id": str(br.action.action_id) if br.action else None,
                    "decision_id": str(br.decision.decision_id) if br.decision else None,
                    "success": br.success,
                    "error": br.error,
                }
                for br in branch_results
            ],
            "trace_id": parent.trace_id,
        }
        if hasattr(self.audit, 'branches_completed'):
            await self.audit.branches_completed(parent, payload)
        elif hasattr(self.audit, 'record'):
            await self.audit.record(
                event_type="branches_completed",
                tenant_id=parent.tenant_id,
                actor_id=parent.actor_id,
                payload=payload,
            )
        else:
            # Fallback: log each branch individually if no batch support
            for br in branch_results:
                if br.action:
                    await self.audit._log(
                        action=br.action,
                        event_type="branch_completed",
                        payload={
                            "parent_decision_id": parent.decision_id,
                            "branch_index": br.branch_index,
                            "success": br.success,
                            "error": br.error,
                        },
                    )

    async def _audit_branch_completed(
        self,
        parent: GovernanceDecision,
        branch: BranchResult,
    ):
        payload = {
            "parent_decision_id": parent.decision_id,
            "branch_index": branch.branch_index,
            "action_id": str(branch.action.action_id) if branch.action else None,
            "decision_id": str(branch.decision.decision_id) if branch.decision else None,
            "success": branch.success,
            "error": branch.error,
        }
        if hasattr(self.audit, 'branch_completed'):
            await self.audit.branch_completed(branch.action, payload)
        elif hasattr(self.audit, 'record'):
            await self.audit.record(
                event_type="branch_completed",
                tenant_id=parent.tenant_id,
                actor_id=parent.actor_id,
                payload=payload,
            )
        else:
            if branch.action:
                await self.audit._log(
                    action=branch.action,
                    event_type="branch_completed",
                    payload=payload,
                )
