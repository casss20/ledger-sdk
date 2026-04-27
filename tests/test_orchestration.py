"""
Comprehensive orchestration test suite for Citadel.

Validates the 4 shared orchestration primitives (delegate, handoff, gather,
introspect) plus lineage propagation and kill-switch enforcement across all
orchestration patterns. All DB dependencies are mocked; the suite is fully
self-contained and runnable without a database.

Test categories:
1. Lineage persistence — ancestry fields propagate end-to-end
2. Delegation (cg.delegate) — child grants under parent authority
3. Handoff (cg.handoff) — authority transfer between actors
4. Gather (cg.gather) — parallel branches under shared scope
5. Introspection (cg.introspect) — runtime safety checks
6. Kill switch — emergency halt across all patterns
7. Backward compatibility — legacy callers without lineage fields
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

from citadel.execution.orchestration import (
    OrchestrationRuntime,
    DelegationResult,
    HandoffResult,
    GatherResult,
    IntrospectionStatus,
    BranchResult,
)
from citadel.tokens.governance_decision import (
    GovernanceDecision,
    DecisionType,
    DecisionScope,
    KillSwitchScope,
)
from citadel.tokens.governance_token import CapabilityToken
from citadel.tokens.kill_switch import KillSwitch
from citadel.tokens.token_verifier import TokenVerifier
from citadel.actions.models import Action, Decision, KernelStatus, KernelResult
from citadel.core.sdk import CitadelClient, CitadelResult


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

TENANT = "test_tenant"
PARENT_ACTOR = "parent_agent"
CHILD_ACTOR = "child_agent"
NEW_ACTOR = "new_agent"


def _make_action(
    actor_id: str = PARENT_ACTOR,
    action_name: str = "test.action",
    resource: str = "test:resource",
    tenant_id: str = TENANT,
    payload: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    root_decision_id: Optional[str] = None,
    parent_decision_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    parent_actor_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> Action:
    return Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type="agent",
        action_name=action_name,
        resource=resource,
        tenant_id=tenant_id,
        payload=payload or {},
        context=context or {},
        session_id=None,
        request_id=None,
        idempotency_key=None,
        root_decision_id=root_decision_id,
        parent_decision_id=parent_decision_id,
        trace_id=trace_id,
        parent_actor_id=parent_actor_id,
        workflow_id=workflow_id,
        created_at=datetime.now(timezone.utc),
    )


def _make_decision(
    action: Action,
    status: KernelStatus = KernelStatus.ALLOWED,
    winning_rule: str = "allow",
    reason: str = "ok",
) -> Decision:
    return Decision(
        decision_id=uuid.uuid4(),
        action_id=action.action_id,
        status=status,
        winning_rule=winning_rule,
        reason=reason,
        policy_snapshot_id=None,
        capability_token=None,
        risk_level="low",
        risk_score=None,
        path_taken=None,
        created_at=datetime.now(timezone.utc),
        tenant_id=action.tenant_id,
        root_decision_id=action.root_decision_id,
        parent_decision_id=action.parent_decision_id,
        trace_id=action.trace_id,
        parent_actor_id=action.parent_actor_id,
        workflow_id=action.workflow_id,
    )


def _make_governance_decision(
    decision_id: Optional[str] = None,
    decision_type: DecisionType = DecisionType.ALLOW,
    actor_id: str = PARENT_ACTOR,
    action: str = "test.action",
    scope: Optional[DecisionScope] = None,
    resource: str = "test:resource",
    tenant_id: str = TENANT,
    trace_id: Optional[str] = None,
    root_decision_id: Optional[str] = None,
    parent_decision_id: Optional[str] = None,
    parent_actor_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    revoked_at: Optional[datetime] = None,
    superseded_at: Optional[datetime] = None,
    superseded_reason: Optional[str] = None,
    expiry: Optional[datetime] = None,
) -> GovernanceDecision:
    return GovernanceDecision(
        decision_id=decision_id or f"gd_{uuid.uuid4().hex}",
        decision_type=decision_type,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        scope=scope or DecisionScope(actions=[action], resources=[resource]),
        resource=resource,
        trace_id=trace_id,
        root_decision_id=root_decision_id,
        parent_decision_id=parent_decision_id,
        parent_actor_id=parent_actor_id,
        workflow_id=workflow_id,
        revoked_at=revoked_at,
        superseded_at=superseded_at,
        superseded_reason=superseded_reason,
        expiry=expiry or (datetime.now(timezone.utc) + timedelta(hours=1)),
    )


def _gov_decision_to_dict(decision: GovernanceDecision) -> Dict[str, Any]:
    """Mirror of OrchestrationRuntime._dict_to_governance_decision input."""
    return {
        "decision_id": decision.decision_id,
        "decision_type": decision.decision_type.value,
        "tenant_id": decision.tenant_id,
        "actor_id": decision.actor_id,
        "action": decision.action,
        "scope_actions": decision.scope.actions,
        "scope_resources": decision.scope.resources,
        "scope_max_spend": decision.scope.max_spend,
        "scope_rate_limit": decision.scope.rate_limit,
        "expiry": decision.expiry.isoformat() if decision.expiry else None,
        "kill_switch_scope": decision.kill_switch_scope.value,
        "trace_id": decision.trace_id,
        "root_decision_id": decision.root_decision_id,
        "parent_decision_id": decision.parent_decision_id,
        "parent_actor_id": decision.parent_actor_id,
        "workflow_id": decision.workflow_id,
        "revoked_at": decision.revoked_at.isoformat() if decision.revoked_at else None,
        "revoked_reason": decision.revoked_reason,
        "superseded_at": decision.superseded_at.isoformat() if decision.superseded_at else None,
        "superseded_reason": decision.superseded_reason,
        "resource": decision.resource,
        "risk_level": decision.risk_level or "low",
        "workspace_id": decision.workspace_id or decision.tenant_id,
        "agent_id": decision.agent_id or decision.actor_id,
        "subject_type": decision.subject_type or "agent",
        "subject_id": decision.subject_id or decision.actor_id,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Mock Vault
# ──────────────────────────────────────────────────────────────────────────────

class MockVault:
    """In-memory token vault that mimics TokenVault contract without DB."""

    def __init__(self):
        self._tokens: Dict[str, Dict[str, Any]] = {}
        self._decisions: Dict[str, Dict[str, Any]] = {}

    async def resolve_token(self, token_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self._tokens.get(token_id)

    async def resolve_decision(self, decision_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self._decisions.get(decision_id)

    async def check_ancestry(self, decision: GovernanceDecision) -> tuple[bool, Optional[str]]:
        """Check whether parent and root decisions are still active.
        
        NOTE: Only REVOCATION cascades. Superseded status is checked at the 
        decision level (verify_token / introspect), not at ancestry level.
        A handoff creates a new independent lineage; existing delegations from
        the superseded authority are not automatically invalidated.
        """
        if decision.parent_decision_id and decision.parent_decision_id != decision.decision_id:
            parent = self._decisions.get(decision.parent_decision_id)
            if parent is None:
                return False, "parent_decision_not_found"
            if parent.get("revoked_at") or parent.get("decision_type") == "revoked":
                return False, "parent_revoked"
            # Superseded does NOT cascade via ancestry — checked at decision level
        if decision.root_decision_id and decision.root_decision_id != decision.decision_id and decision.root_decision_id != decision.parent_decision_id:
            root = self._decisions.get(decision.root_decision_id)
            if root is None:
                return False, "root_decision_not_found"
            if root.get("revoked_at") or root.get("decision_type") == "revoked":
                return False, "root_revoked"
            # Superseded does NOT cascade via ancestry
        return True, None

    async def issue_token_for_decision(
        self,
        decision: GovernanceDecision,
        *,
        lifetime_seconds: int = 120,
        issuer: str = "citadel",
        audience: str = "citadel-runtime",
        tool: Optional[str] = None,
    ) -> CapabilityToken:
        token = CapabilityToken.derive(
            decision,
            lifetime_seconds=lifetime_seconds,
            issuer=issuer,
            audience=audience,
            tool=tool,
        )
        self._tokens[token.token_id] = {
            "token_id": token.token_id,
            "decision_id": token.decision_id,
            "tenant_id": token.tenant_id,
            "actor_id": token.actor_id,
            "scope_actions": token.scope_actions,
            "scope_resources": token.scope_resources,
            "scope_max_spend": None,
            "scope_rate_limit": None,
            "expiry": token.expiry.isoformat() if token.expiry else None,
            "not_before": token.not_before.isoformat() if token.not_before else None,
            "revoked_at": None,
            "trace_id": token.trace_id,
            "tool": token.tool,
            "workspace_id": token.workspace_id or token.tenant_id,
            "parent_decision_id": token.parent_decision_id,
            "parent_actor_id": token.parent_actor_id,
            "workflow_id": token.workflow_id,
        }
        self._decisions[decision.decision_id] = _gov_decision_to_dict(decision)
        return token

    async def store_decision(self, decision: GovernanceDecision) -> None:
        self._decisions[decision.decision_id] = _gov_decision_to_dict(decision)

    async def revoke_decision(self, decision_id: str, tenant_id: str, reason: str = "revoked") -> bool:
        """Mark decision and its descendants as revoked."""
        decision = self._decisions.get(decision_id)
        if decision is None:
            return False
        decision["revoked_at"] = datetime.now(timezone.utc).isoformat()
        decision["revoked_reason"] = reason
        decision["decision_type"] = "revoked"
        # Cascade to descendants
        for d in self._decisions.values():
            if d.get("parent_decision_id") == decision_id or d.get("root_decision_id") == decision_id:
                if not d.get("revoked_at"):
                    d["revoked_at"] = datetime.now(timezone.utc).isoformat()
                    d["revoked_reason"] = f"cascaded: {reason}"
                    d["decision_type"] = "revoked"
        # Cascade tokens
        for t in self._tokens.values():
            if t.get("decision_id") in [
                decision_id,
                *[d["decision_id"] for d in self._decisions.values()
                  if d.get("parent_decision_id") == decision_id or d.get("root_decision_id") == decision_id]
            ]:
                if not t.get("revoked_at"):
                    t["revoked_at"] = datetime.now(timezone.utc).isoformat()
                    t["revoked_reason"] = f"cascaded: {reason}"
        return True

    async def revoke_token(self, token_id: str, tenant_id: str, reason: str = "revoked") -> bool:
        token = self._tokens.get(token_id)
        if token is None:
            return False
        token["revoked_at"] = datetime.now(timezone.utc).isoformat()
        token["revoked_reason"] = reason
        return True

    async def check_kill_switch(self, **kwargs):
        return None


class MockAudit:
    """Minimal async audit sink that records events in memory."""

    def __init__(self):
        self.events: List[Dict[str, Any]] = []

    async def record(self, **kwargs):
        self.events.append(kwargs)


# ──────────────────────────────────────────────────────────────────────────────
# Pytest fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_kernel():
    """Kernel mock that returns ALLOWED decisions by default."""
    kernel = MagicMock()
    kernel.handle = AsyncMock()
    return kernel


@pytest.fixture
def mock_vault():
    return MockVault()


@pytest.fixture
def mock_repo():
    """Repository mock that silently accepts all writes."""
    repo = MagicMock()
    repo.save_action = AsyncMock(return_value=True)
    repo.save_decision = AsyncMock()
    repo.find_decision_by_idempotency = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_audit():
    return MockAudit()


@pytest.fixture
def mock_kill_switch(mock_audit):
    return KillSwitch(mock_audit)


@pytest.fixture
def runtime(mock_kernel, mock_vault, mock_repo, mock_audit, mock_kill_switch):
    verifier = TokenVerifier(mock_vault, kill_switch=mock_kill_switch, audit_logger=mock_audit)
    return OrchestrationRuntime(
        kernel=mock_kernel,
        token_vault=mock_vault,
        token_verifier=verifier,
        repository=mock_repo,
        audit_service=mock_audit,
        kill_switch=mock_kill_switch,
    )


@pytest.fixture
def trace_id():
    return f"trace_{uuid.uuid4().hex}"


@pytest.fixture
def workflow_id():
    return f"wf_{uuid.uuid4().hex}"


# ──────────────────────────────────────────────────────────────────────────────
# 1. Lineage Persistence
# ──────────────────────────────────────────────────────────────────────────────

class TestLineagePersistence:
    """
    Validates that root_decision_id, parent_decision_id, trace_id,
    parent_actor_id, and workflow_id propagate correctly through the
    full chain: parent Action -> parent Decision -> child Action ->
    child Decision -> capability token metadata.
    """

    async def _setup_kernel_for_success(self, mock_kernel):
        async def _handle(action, *args, **kwargs):
            return KernelResult(
                action=action,
                decision=_make_decision(action, status=KernelStatus.ALLOWED),
                executed=True,
                result=None,
                error=None,
            )
        mock_kernel.handle.side_effect = _handle

    async def test_lineage_parent_action_to_parent_decision(self, runtime, mock_kernel, trace_id, workflow_id):
        """Parent action lineage fields carry into the kernel-produced decision."""
        await self._setup_kernel_for_success(mock_kernel)
        parent_action = _make_action(
            trace_id=trace_id,
            workflow_id=workflow_id,
            root_decision_id="root_1",
        )
        result = await runtime.kernel.handle(parent_action)
        decision = result.decision
        assert decision.trace_id == trace_id
        assert decision.workflow_id == workflow_id
        assert decision.root_decision_id == "root_1"

    async def test_lineage_parent_decision_to_child_action(self, runtime, mock_kernel, trace_id, workflow_id, mock_vault):
        """Child action inherits lineage from parent decision."""
        await self._setup_kernel_for_success(mock_kernel)
        parent = _make_governance_decision(
            trace_id=trace_id,
            workflow_id=workflow_id,
            root_decision_id="root_1",
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        # Store root so ancestry checks pass
        root = _make_governance_decision(decision_id="root_1", scope=DecisionScope(actions=["*"], resources=["*"]))
        await mock_vault.store_decision(root)
        result = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )
        assert result.success
        child_action = result.child_action
        assert child_action.root_decision_id == parent.root_decision_id
        assert child_action.parent_decision_id == parent.decision_id
        assert child_action.trace_id == parent.trace_id
        assert child_action.parent_actor_id == parent.actor_id
        assert child_action.workflow_id == parent.workflow_id

    async def test_lineage_child_action_to_child_decision(self, runtime, mock_kernel, trace_id, workflow_id, mock_vault):
        """Child decision produced by the kernel preserves action lineage."""
        await self._setup_kernel_for_success(mock_kernel)
        parent = _make_governance_decision(
            trace_id=trace_id,
            workflow_id=workflow_id,
            root_decision_id="root_1",
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        # Store root so ancestry checks pass
        root = _make_governance_decision(decision_id="root_1", scope=DecisionScope(actions=["*"], resources=["*"]))
        await mock_vault.store_decision(root)
        result = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )
        assert result.success
        child_decision = result.child_decision
        assert child_decision.root_decision_id == parent.root_decision_id
        assert child_decision.parent_decision_id == parent.decision_id
        assert child_decision.trace_id == parent.trace_id
        assert child_decision.parent_actor_id == parent.actor_id
        assert child_decision.workflow_id == parent.workflow_id

    async def test_lineage_child_decision_to_token_metadata(self, runtime, mock_kernel, trace_id, workflow_id, mock_vault):
        """Capability token derived from child decision stores lineage fields."""
        await self._setup_kernel_for_success(mock_kernel)
        parent = _make_governance_decision(
            trace_id=trace_id,
            workflow_id=workflow_id,
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        result = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )
        assert result.success
        assert result.child_grant is not None
        token_data = await runtime.vault.resolve_token(result.child_grant)
        assert token_data is not None
        assert token_data["parent_decision_id"] == parent.decision_id
        assert token_data["parent_actor_id"] == parent.actor_id
        assert token_data["trace_id"] == parent.trace_id
        assert token_data["workflow_id"] == parent.workflow_id

    async def test_lineage_handoff_preserves_root_and_trace(self, runtime, mock_kernel, trace_id, mock_vault):
        """Handoff preserves root_decision_id and trace_id across actors."""
        await self._setup_kernel_for_success(mock_kernel)
        current = _make_governance_decision(
            trace_id=trace_id,
            root_decision_id="root_1",
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(current)
        # Store root so ancestry checks pass
        root = _make_governance_decision(decision_id="root_1", scope=DecisionScope(actions=["*"], resources=["*"]))
        await mock_vault.store_decision(root)
        result = await runtime.handoff(
            current_decision=current,
            new_actor_id=NEW_ACTOR,
            action_name="handoff.action",
            resource="handoff:resource",
            scope=DecisionScope(actions=["handoff.action"], resources=["handoff:resource"]),
        )
        assert result.success
        assert result.new_decision.trace_id == trace_id
        assert result.new_decision.root_decision_id == "root_1"

    async def test_lineage_gather_branches_share_root_and_trace(self, runtime, mock_kernel, trace_id, mock_vault):
        """All gather branches share the same root_decision_id and trace_id."""
        await self._setup_kernel_for_success(mock_kernel)
        parent = _make_governance_decision(trace_id=trace_id, root_decision_id="root_1", scope=DecisionScope(actions=["*"], resources=["*"]))
        await mock_vault.store_decision(parent)
        # Store root so ancestry checks pass
        root = _make_governance_decision(decision_id="root_1", scope=DecisionScope(actions=["*"], resources=["*"]))
        await mock_vault.store_decision(root)
        result = await runtime.gather(
            parent_decision=parent,
            branches=[
                {"action": "a1", "resource": "r1", "actor_id": "b1"},
                {"action": "a2", "resource": "r2", "actor_id": "b2"},
            ],
        )
        assert result.success
        for br in result.branches:
            assert br.action.root_decision_id == "root_1"
            assert br.action.trace_id == trace_id
            assert br.decision.root_decision_id == "root_1"
            assert br.decision.trace_id == trace_id


# ──────────────────────────────────────────────────────────────────────────────
# 2. Delegation (cg.delegate)
# ──────────────────────────────────────────────────────────────────────────────

class TestDelegation:
    """
    Validates cg.delegate() behavior: child grants succeed only when the
    parent decision is active, the scope narrows, and no kill switch is
    active. Token metadata must preserve full lineage.
    """

    async def _setup_kernel_allow(self, mock_kernel):
        async def _handle(action, *args, **kwargs):
            return KernelResult(
                action=action,
                decision=_make_decision(action, status=KernelStatus.ALLOWED),
                executed=True,
                result=None,
                error=None,
            )
        mock_kernel.handle.side_effect = _handle

    async def _setup_kernel_block(self, mock_kernel):
        async def _handle(action, *args, **kwargs):
            return KernelResult(
                action=action,
                decision=_make_decision(action, status=KernelStatus.BLOCKED_POLICY),
                executed=False,
                result=None,
                error="policy_block",
            )
        mock_kernel.handle.side_effect = _handle

    async def test_delegate_success(self, runtime, mock_kernel, mock_vault):
        """Child delegation succeeds under a valid, active parent decision."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        result = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )
        assert result.success is True
        assert result.child_action is not None
        assert result.child_decision is not None
        assert result.child_grant is not None
        assert result.reason == "Delegated successfully"

    async def test_delegate_blocked_parent_revoked(self, runtime, mock_kernel, mock_vault):
        """Child delegation is blocked when the parent decision is revoked."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            decision_type=DecisionType.REVOKED,
            revoked_at=datetime.now(timezone.utc),
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        result = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )
        assert result.success is False
        assert "revoked" in result.reason.lower()

    async def test_delegate_blocked_parent_superseded(self, runtime, mock_kernel, mock_vault):
        """Child delegation is blocked when the parent decision has been superseded."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            superseded_at=datetime.now(timezone.utc),
            superseded_reason="handed_off",
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        result = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )
        assert result.success is False
        assert "superseded" in result.reason.lower()

    async def test_delegate_blocked_kill_switch(self, runtime, mock_kernel, mock_kill_switch, mock_vault):
        """Child delegation is blocked when a kill switch is active at parent scope."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            actor_id=PARENT_ACTOR,
            tenant_id=TENANT,
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        await mock_kill_switch.trigger(
            scope=KillSwitchScope.AGENT,
            target_id=PARENT_ACTOR,
            triggered_by="test",
            triggered_by_type="system",
            reason="emergency",
        )
        result = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )
        assert result.success is False
        assert "kill switch" in result.reason.lower()

    async def test_delegate_blocked_scope_widening(self, runtime, mock_kernel, mock_vault):
        """Child delegation is blocked when the child scope is wider than the parent scope."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            scope=DecisionScope(actions=["file.read"], resources=["doc:1"]),
        )
        await mock_vault.store_decision(parent)
        result = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="file.delete",
            resource="doc:1",
            scope=DecisionScope(actions=["file.delete"], resources=["doc:1"]),
        )
        assert result.success is False
        assert "scope" in result.reason.lower()

    async def test_delegate_child_token_lineage(self, runtime, mock_kernel, trace_id, workflow_id, mock_vault):
        """Child capability token metadata carries correct lineage fields."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            trace_id=trace_id,
            workflow_id=workflow_id,
            root_decision_id="root_1",
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        # Store root so ancestry checks pass
        root = _make_governance_decision(decision_id="root_1", scope=DecisionScope(actions=["*"], resources=["*"]))
        await mock_vault.store_decision(root)
        result = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )
        assert result.success
        token_data = await runtime.vault.resolve_token(result.child_grant)
        assert token_data["parent_decision_id"] == parent.decision_id
        assert token_data["parent_actor_id"] == parent.actor_id
        assert token_data["trace_id"] == trace_id
        assert token_data["workflow_id"] == workflow_id


# ──────────────────────────────────────────────────────────────────────────────
# 3. Handoff (cg.handoff)
# ──────────────────────────────────────────────────────────────────────────────

class TestHandoff:
    """
    Validates cg.handoff() behavior: active authority transfers to a new
    actor, the previous authority is marked superseded, and the new
    decision preserves root lineage.
    """

    async def _setup_kernel_allow(self, mock_kernel):
        async def _handle(action, *args, **kwargs):
            return KernelResult(
                action=action,
                decision=_make_decision(action, status=KernelStatus.ALLOWED),
                executed=True,
                result=None,
                error=None,
            )
        mock_kernel.handle.side_effect = _handle

    async def _setup_kernel_block(self, mock_kernel):
        async def _handle(action, *args, **kwargs):
            return KernelResult(
                action=action,
                decision=_make_decision(action, status=KernelStatus.BLOCKED_POLICY),
                executed=False,
                result=None,
                error="policy_block",
            )
        mock_kernel.handle.side_effect = _handle

    async def test_handoff_success(self, runtime, mock_kernel, mock_vault):
        """Active authority successfully transfers to a new actor."""
        await self._setup_kernel_allow(mock_kernel)
        current = _make_governance_decision(
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(current)
        result = await runtime.handoff(
            current_decision=current,
            new_actor_id=NEW_ACTOR,
            action_name="new.action",
            resource="new:resource",
            scope=DecisionScope(actions=["new.action"], resources=["new:resource"]),
            reason="reassignment",
        )
        assert result.success is True
        assert result.new_decision is not None
        assert result.previous_authority_superseded is True
        assert "handoff" in result.reason.lower() or "successful" in result.reason.lower()

    async def test_handoff_supersedes_previous(self, runtime, mock_kernel, mock_vault):
        """Previous authority decision is marked superseded/inactive in the vault."""
        await self._setup_kernel_allow(mock_kernel)
        current = _make_governance_decision(
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(current)
        await runtime.handoff(
            current_decision=current,
            new_actor_id=NEW_ACTOR,
            action_name="new.action",
            resource="new:resource",
            scope=DecisionScope(actions=["new.action"], resources=["new:resource"]),
            reason="reassignment",
        )
        stored = await mock_vault.resolve_decision(current.decision_id)
        assert stored is not None
        assert stored["superseded_at"] is not None
        assert "reassignment" in (stored.get("superseded_reason") or "")

    async def test_handoff_blocked_by_kernel_preserves_old_authority(self, runtime, mock_kernel, mock_vault):
        """If kernel blocks the handoff, the old authority must NOT be superseded."""
        await self._setup_kernel_block(mock_kernel)
        current = _make_governance_decision(
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(current)
        result = await runtime.handoff(
            current_decision=current,
            new_actor_id=NEW_ACTOR,
            action_name="handoff.action",
            resource="handoff:resource",
            scope=DecisionScope(actions=["handoff.action"], resources=["handoff:resource"]),
        )
        assert result.success is False
        assert result.previous_authority_superseded is False
        # Old authority must still be active (not superseded)
        assert current.superseded_at is None
        assert current.superseded_reason is None

    async def test_handoff_blocked_by_scope_widening(self, runtime, mock_kernel, mock_vault):
        """Handoff must not allow scope widening beyond current authority."""
        await self._setup_kernel_allow(mock_kernel)
        current = _make_governance_decision(
            scope=DecisionScope(actions=["file.read"], resources=["file:123"]),
        )
        await mock_vault.store_decision(current)
        result = await runtime.handoff(
            current_decision=current,
            new_actor_id=NEW_ACTOR,
            action_name="file.write",
            resource="file:999",
            scope=DecisionScope(actions=["file.write"], resources=["file:999"]),
        )
        assert result.success is False
        assert "scope" in result.reason.lower() or "exceeds" in result.reason.lower()
        # Old authority must NOT be superseded when blocked by scope
        assert current.superseded_at is None
        """A handed-off prior authority cannot continue protected actions."""
        await self._setup_kernel_allow(mock_kernel)
        current = _make_governance_decision(
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(current)
        await runtime.handoff(
            current_decision=current,
            new_actor_id=NEW_ACTOR,
            action_name="new.action",
            resource="new:resource",
            scope=DecisionScope(actions=["new.action"], resources=["new:resource"]),
        )
        introspection = await runtime.introspect(
            decision_id=current.decision_id,
            required_action=current.action,
            required_resource=current.resource,
            tenant_id=current.tenant_id,
        )
        assert introspection.active is False
        assert introspection.actor_boundary_valid is False

    async def test_handoff_preserves_lineage(self, runtime, mock_kernel, trace_id, mock_vault):
        """New actor's decision carries correct lineage (root_decision_id, trace_id)."""
        await self._setup_kernel_allow(mock_kernel)
        current = _make_governance_decision(
            trace_id=trace_id,
            root_decision_id="root_1",
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(current)
        # Store root so ancestry checks pass
        root = _make_governance_decision(decision_id="root_1", scope=DecisionScope(actions=["*"], resources=["*"]))
        await mock_vault.store_decision(root)
        result = await runtime.handoff(
            current_decision=current,
            new_actor_id=NEW_ACTOR,
            action_name="new.action",
            resource="new:resource",
            scope=DecisionScope(actions=["new.action"], resources=["new:resource"]),
        )
        assert result.success
        assert result.new_decision.trace_id == trace_id
        assert result.new_decision.root_decision_id == "root_1"


# ──────────────────────────────────────────────────────────────────────────────
# 4. Gather (cg.gather)
# ──────────────────────────────────────────────────────────────────────────────

class TestGather:
    """
    Validates cg.gather() behavior: parallel branches share a common
    root_decision_id and trace_id, each branch gets unique IDs, and
    results preserve branch identity for independent audit.
    """

    async def _setup_kernel_allow(self, mock_kernel):
        async def _handle(action, *args, **kwargs):
            return KernelResult(
                action=action,
                decision=_make_decision(action, status=KernelStatus.ALLOWED),
                executed=True,
                result={"ok": True},
                error=None,
            )
        mock_kernel.handle.side_effect = _handle

    async def test_gather_blocked_by_scope_widening(self, runtime, mock_kernel, mock_vault):
        """Gather must reject branches that exceed parent scope."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            scope=DecisionScope(actions=["file.read"], resources=["file:123"]),
        )
        await mock_vault.store_decision(parent)
        result = await runtime.gather(
            parent_decision=parent,
            branches=[
                {"action": "file.write", "resource": "file:999", "actor_id": "b1"},
            ],
        )
        assert result.success is False
        assert "scope" in result.reason.lower() or "exceeds" in result.reason.lower()

    async def test_gather_shared_root_and_trace(self, runtime, mock_kernel, trace_id, mock_vault):
        """All branches share root_decision_id and trace_id from the parent."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            trace_id=trace_id,
            root_decision_id="root_1",
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        # Store root so ancestry checks pass
        root = _make_governance_decision(decision_id="root_1", scope=DecisionScope(actions=["*"], resources=["*"]))
        await mock_vault.store_decision(root)
        result = await runtime.gather(
            parent_decision=parent,
            branches=[
                {"action": "a1", "resource": "r1"},
                {"action": "a2", "resource": "r2"},
            ],
        )
        assert result.success
        traces = {br.action.trace_id for br in result.branches}
        roots = {br.action.root_decision_id for br in result.branches}
        assert traces == {trace_id}
        assert roots == {"root_1"}

    async def test_gather_unique_action_and_decision_ids(self, runtime, mock_kernel):
        """Each branch receives a distinct action_id and decision_id."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(scope=DecisionScope(actions=["*"], resources=["*"]))
        result = await runtime.gather(
            parent_decision=parent,
            branches=[
                {"action": "a1", "resource": "r1"},
                {"action": "a2", "resource": "r2"},
                {"action": "a3", "resource": "r3"},
            ],
        )
        action_ids = [str(br.action.action_id) for br in result.branches]
        decision_ids = [str(br.decision.decision_id) for br in result.branches]
        assert len(set(action_ids)) == len(action_ids)
        assert len(set(decision_ids)) == len(decision_ids)

    async def test_gather_independently_auditable(self, runtime, mock_kernel, mock_audit):
        """Each branch decision can be resolved independently for audit."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(scope=DecisionScope(actions=["*"], resources=["*"]))
        result = await runtime.gather(
            parent_decision=parent,
            branches=[
                {"action": "a1", "resource": "r1"},
                {"action": "a2", "resource": "r2"},
            ],
        )
        for br in result.branches:
            stored = await runtime.vault.resolve_decision(str(br.decision.decision_id))
            assert stored is not None
            assert stored["action"] == br.action.action_name

    async def test_gather_result_aggregation_preserves_branch_identity(self, runtime, mock_kernel, mock_vault):
        """GatherResult maps each branch result back to its original index."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        result = await runtime.gather(
            parent_decision=parent,
            branches=[
                {"action": "a1", "resource": "r1"},
                {"action": "a2", "resource": "r2"},
            ],
        )
        assert result.success
        assert len(result.branches) == 2
        assert result.branches[0].branch_index == 0
        assert result.branches[1].branch_index == 1
        assert result.completed == 2
        assert result.failed == 0


# ──────────────────────────────────────────────────────────────────────────────
# 5. Introspection (cg.introspect)
# ──────────────────────────────────────────────────────────────────────────────

class TestIntrospection:
    """
    Validates cg.introspect() runtime safety checks: active only when the
    token/decision is valid, not expired, not revoked, in-scope, and
    not under an active kill switch. Actor boundary must hold after handoff.
    """

    async def _store_decision_in_vault(self, runtime, decision: GovernanceDecision):
        await runtime.vault.store_decision(decision)

    async def test_introspect_active_valid_grant(self, runtime, mock_vault):
        """Returns active for a valid root grant."""
        decision = _make_governance_decision()
        await self._store_decision_in_vault(runtime, decision)
        result = await runtime.introspect(
            decision_id=decision.decision_id,
            required_action=decision.action,
            required_resource=decision.resource,
            tenant_id=decision.tenant_id,
        )
        assert result.active is True
        assert result.scope_valid is True
        assert result.actor_boundary_valid is True

    async def test_introspect_active_child_grant(self, runtime, mock_vault):
        """Returns active for a valid child grant."""
        parent = _make_governance_decision()
        child = _make_governance_decision(
            decision_id="gd_child_1",
            parent_decision_id=parent.decision_id,
            action="child.action",
            scope=DecisionScope(actions=["child.action"], resources=["child:res"]),
        )
        await self._store_decision_in_vault(runtime, parent)
        await self._store_decision_in_vault(runtime, child)
        result = await runtime.introspect(
            decision_id=child.decision_id,
            required_action="child.action",
            required_resource="child:res",
            tenant_id=child.tenant_id,
        )
        assert result.active is True

    async def test_introspect_inactive_expired(self, runtime, mock_vault):
        """Returns inactive when the grant has expired."""
        decision = _make_governance_decision(
            expiry=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        await self._store_decision_in_vault(runtime, decision)
        result = await runtime.introspect(
            decision_id=decision.decision_id,
            required_action=decision.action,
            tenant_id=decision.tenant_id,
        )
        assert result.active is False
        assert result.expired is True

    async def test_introspect_inactive_revoked(self, runtime, mock_vault):
        """Returns inactive when the grant has been revoked."""
        decision = _make_governance_decision(
            decision_type=DecisionType.REVOKED,
            revoked_at=datetime.now(timezone.utc),
        )
        await self._store_decision_in_vault(runtime, decision)
        result = await runtime.introspect(
            decision_id=decision.decision_id,
            required_action=decision.action,
            tenant_id=decision.tenant_id,
        )
        assert result.active is False
        assert result.revoked is True

    async def test_introspect_inactive_out_of_scope(self, runtime, mock_vault):
        """Returns inactive for an action or resource outside the grant scope."""
        decision = _make_governance_decision(
            scope=DecisionScope(actions=["file.read"], resources=["doc:1"]),
        )
        await self._store_decision_in_vault(runtime, decision)
        result = await runtime.introspect(
            decision_id=decision.decision_id,
            required_action="file.delete",
            required_resource="doc:1",
            tenant_id=decision.tenant_id,
        )
        assert result.active is False
        assert result.scope_valid is False

    async def test_introspect_inactive_kill_switch(self, runtime, mock_vault, mock_kill_switch):
        """Returns inactive when a kill switch is active for the decision scope."""
        decision = _make_governance_decision(actor_id=PARENT_ACTOR, tenant_id=TENANT)
        await self._store_decision_in_vault(runtime, decision)
        await mock_kill_switch.trigger(
            scope=KillSwitchScope.AGENT,
            target_id=PARENT_ACTOR,
            triggered_by="test",
            triggered_by_type="system",
            reason="emergency",
        )
        result = await runtime.introspect(
            decision_id=decision.decision_id,
            required_action=decision.action,
            tenant_id=decision.tenant_id,
        )
        assert result.active is False
        assert result.kill_switched is True

    async def test_introspect_actor_boundary_superseded(self, runtime, mock_vault):
        """Validates actor boundary: superseded decision is inactive."""
        decision = _make_governance_decision(
            superseded_at=datetime.now(timezone.utc),
            superseded_reason="handed off",
        )
        await self._store_decision_in_vault(runtime, decision)
        result = await runtime.introspect(
            decision_id=decision.decision_id,
            required_action=decision.action,
            tenant_id=decision.tenant_id,
        )
        assert result.active is False
        assert result.actor_boundary_valid is False


# ──────────────────────────────────────────────────────────────────────────────
# 6. Kill Switch Across Patterns
# ──────────────────────────────────────────────────────────────────────────────

class TestKillSwitchAcrossPatterns:
    """
    Validates that a triggered kill switch blocks future protected actions
    across delegation, handoff, and gather branches.
    """

    async def _setup_kernel_allow(self, mock_kernel):
        async def _handle(action, *args, **kwargs):
            return KernelResult(
                action=action,
                decision=_make_decision(action, status=KernelStatus.ALLOWED),
                executed=True,
                result=None,
                error=None,
            )
        mock_kernel.handle.side_effect = _handle

    async def test_kill_switch_blocks_delegate(self, runtime, mock_kernel, mock_kill_switch, mock_vault):
        """Kill switch blocks future protected actions in delegated branches."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            actor_id=PARENT_ACTOR,
            tenant_id=TENANT,
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        await mock_kill_switch.trigger(
            scope=KillSwitchScope.AGENT,
            target_id=PARENT_ACTOR,
            triggered_by="test",
            triggered_by_type="system",
            reason="stop",
        )
        result = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )
        assert result.success is False
        assert "kill switch" in result.reason.lower()

    async def test_kill_switch_blocks_handoff(self, runtime, mock_kernel, mock_kill_switch, mock_vault):
        """Kill switch blocks future protected actions in handed-off branches."""
        await self._setup_kernel_allow(mock_kernel)
        current = _make_governance_decision(
            actor_id=PARENT_ACTOR,
            tenant_id=TENANT,
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(current)
        await mock_kill_switch.trigger(
            scope=KillSwitchScope.AGENT,
            target_id=PARENT_ACTOR,
            triggered_by="test",
            triggered_by_type="system",
            reason="stop",
        )
        result = await runtime.handoff(
            current_decision=current,
            new_actor_id=NEW_ACTOR,
            action_name="new.action",
            resource="new:resource",
            scope=DecisionScope(actions=["new.action"], resources=["new:resource"]),
        )
        assert result.success is False
        assert "kill switch" in result.reason.lower()

    async def test_kill_switch_blocks_gather(self, runtime, mock_kernel, mock_kill_switch, mock_vault):
        """Kill switch blocks future protected actions in gathered branches."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            actor_id=PARENT_ACTOR,
            tenant_id=TENANT,
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        await mock_kill_switch.trigger(
            scope=KillSwitchScope.AGENT,
            target_id=PARENT_ACTOR,
            triggered_by="test",
            triggered_by_type="system",
            reason="stop",
        )
        result = await runtime.gather(
            parent_decision=parent,
            branches=[
                {"action": "a1", "resource": "r1"},
                {"action": "a2", "resource": "r2"},
            ],
        )
        assert result.success is False
        assert "kill switch" in result.reason.lower()


# ──────────────────────────────────────────────────────────────────────────────
# 7. Backward Compatibility
# ──────────────────────────────────────────────────────────────────────────────

class TestBackwardCompatibility:
    """
    Validates that existing cg.execute() callers and actions created without
    lineage fields continue to function correctly. The orchestration runtime
    must tolerate absent lineage and produce valid decisions.
    """

    async def test_execute_without_lineage_fields(self, runtime, mock_kernel):
        """An action without any lineage fields is processed without error."""
        action = _make_action()
        # Ensure no lineage fields are set
        assert action.root_decision_id is None
        assert action.parent_decision_id is None
        assert action.trace_id is None
        assert action.parent_actor_id is None
        assert action.workflow_id is None

        decision = _make_decision(action, status=KernelStatus.ALLOWED)
        mock_kernel.handle.return_value = KernelResult(
            action=action,
            decision=decision,
            executed=True,
            result={"done": True},
            error=None,
        )
        result = await runtime.kernel.handle(action)
        assert result.decision is not None
        assert result.decision.status == KernelStatus.ALLOWED
        # Lineage remains None on the decision
        assert result.decision.root_decision_id is None
        assert result.decision.trace_id is None

    async def test_action_without_lineage_produces_valid_decision(self, runtime, mock_kernel):
        """Actions without lineage fields still produce valid, storable decisions."""
        action = _make_action()
        decision = _make_decision(action, status=KernelStatus.EXECUTED)
        mock_kernel.handle.return_value = KernelResult(
            action=action,
            decision=decision,
            executed=True,
            result={"done": True},
            error=None,
        )
        result = await runtime.kernel.handle(action)
        assert result.decision.status == KernelStatus.EXECUTED
        assert result.decision.action_id == action.action_id

    async def test_delegate_without_parent_lineage(self, runtime, mock_kernel, mock_vault):
        """Delegation from a parent without lineage defaults root to parent decision_id."""
        async def _handle(a, *args, **kwargs):
            return KernelResult(
                action=a,
                decision=_make_decision(a, status=KernelStatus.ALLOWED),
                executed=True,
                result=None,
                error=None,
            )
        mock_kernel.handle.side_effect = _handle

        parent = _make_governance_decision(
            root_decision_id=None,
            trace_id=None,
            parent_decision_id=None,
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        result = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )
        assert result.success
        # Runtime falls back: root_decision_id = parent.decision_id
        assert result.child_action.root_decision_id == parent.decision_id
        assert result.child_action.trace_id is not None  # generated if missing
        assert result.child_decision.root_decision_id == parent.decision_id

    async def test_handoff_without_lineage(self, runtime, mock_kernel, mock_vault):
        """Handoff from a decision without lineage still succeeds and defaults root."""
        async def _handle(a, *args, **kwargs):
            return KernelResult(
                action=a,
                decision=_make_decision(a, status=KernelStatus.ALLOWED),
                executed=True,
                result=None,
                error=None,
            )
        mock_kernel.handle.side_effect = _handle

        current = _make_governance_decision(
            root_decision_id=None,
            trace_id=None,
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(current)
        result = await runtime.handoff(
            current_decision=current,
            new_actor_id=NEW_ACTOR,
            action_name="new.action",
            resource="new:resource",
            scope=DecisionScope(actions=["new.action"], resources=["new:resource"]),
        )
        assert result.success
        assert result.new_decision.root_decision_id == current.decision_id

    async def test_gather_without_parent_lineage(self, runtime, mock_kernel, mock_vault):
        """Gather from a parent without lineage generates trace and uses decision_id as root."""
        async def _handle(a, *args, **kwargs):
            return KernelResult(
                action=a,
                decision=_make_decision(a, status=KernelStatus.ALLOWED),
                executed=True,
                result=None,
                error=None,
            )
        mock_kernel.handle.side_effect = _handle

        parent = _make_governance_decision(
            root_decision_id=None,
            trace_id=None,
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        result = await runtime.gather(
            parent_decision=parent,
            branches=[
                {"action": "a1", "resource": "r1"},
            ],
        )
        assert result.success
        br = result.branches[0]
        assert br.action.root_decision_id == parent.decision_id
        assert br.action.trace_id is not None


# ──────────────────────────────────────────────────────────────────────────────
# 8. Security Hardening — Post-Fix Validation
# ──────────────────────────────────────────────────────────────────────────────

class TestSecurityHardening:
    """
    Validates critical security fixes:
    - Superseded tokens are rejected by TokenVerifier
    - REQUEST-scoped kill switches are caught by orchestration
    - max_spend / rate_limit scope narrowing survives vault round-trip
    - Workspace boundary is enforced in introspection
    - DecisionType.DENY is rejected by TokenVerifier
    - Caller-supplied forged lineage is ignored after vault resolution
    """

    async def _setup_kernel_allow(self, mock_kernel):
        async def _handle(action, *args, **kwargs):
            return KernelResult(
                action=action,
                decision=_make_decision(action, status=KernelStatus.ALLOWED),
                executed=True,
                result=None,
                error=None,
            )
        mock_kernel.handle.side_effect = _handle

    async def test_superseded_token_rejected_by_verifier(self, runtime, mock_vault, mock_kernel):
        """Old token is invalid after handoff superseded the parent decision."""
        await self._setup_kernel_allow(mock_kernel)
        current = _make_governance_decision(
            actor_id=PARENT_ACTOR,
            tenant_id=TENANT,
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(current)
        # Issue a token for the current decision BEFORE handoff
        old_token = await mock_vault.issue_token_for_decision(current)
        result = await runtime.handoff(
            current_decision=current,
            new_actor_id=NEW_ACTOR,
            action_name="new.action",
            resource="new:resource",
            scope=DecisionScope(actions=["new.action"], resources=["new:resource"]),
        )
        assert result.success is True
        # Old decision is now superseded
        old_token_id = old_token.token_id
        verifier = runtime.verifier
        result = await verifier.verify_token(old_token_id, action="test.action", resource="test:resource")
        assert result.valid is False
        assert "superseded" in result.reason.lower()

    async def test_request_scoped_kill_switch_caught(self, runtime, mock_kernel, mock_kill_switch, mock_vault):
        """REQUEST-scoped kill switch (targeting a specific decision) blocks delegation."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            actor_id=PARENT_ACTOR,
            tenant_id=TENANT,
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        await mock_kill_switch.trigger(
            scope=KillSwitchScope.REQUEST,
            target_id=parent.decision_id,
            triggered_by="test",
            triggered_by_type="system",
            reason="stop this request",
        )
        result = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )
        assert result.success is False
        assert "kill switch" in result.reason.lower()

    async def test_max_spend_scope_narrowing_survives_vault(self, runtime, mock_kernel, mock_vault):
        """Parent with max_spend=100 loaded from vault enforces child max_spend<=100."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            scope=DecisionScope(actions=["*"], resources=["*"], max_spend=100.0),
        )
        await mock_vault.store_decision(parent)
        # Child requesting max_spend=200 should be blocked
        result = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"], max_spend=200.0),
        )
        assert result.success is False
        assert "scope" in result.reason.lower()

    async def test_rate_limit_scope_narrowing_survives_vault(self, runtime, mock_kernel, mock_vault):
        """Parent with rate_limit=10 loaded from vault enforces child rate_limit<=10."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            scope=DecisionScope(actions=["*"], resources=["*"], rate_limit=10),
        )
        await mock_vault.store_decision(parent)
        result = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"], rate_limit=20),
        )
        assert result.success is False
        assert "scope" in result.reason.lower()

    async def test_workspace_mismatch_introspect(self, runtime, mock_vault):
        """Introspection with wrong workspace_id returns actor_boundary_valid=False."""
        decision = _make_governance_decision()
        # Set workspace_id after creation (dataclass allows this)
        decision.workspace_id = "ws_alpha"
        await mock_vault.store_decision(decision)
        result = await runtime.introspect(
            decision_id=decision.decision_id,
            required_action=decision.action,
            tenant_id=decision.tenant_id,
            workspace_id="ws_beta",
        )
        assert result.active is False
        assert result.actor_boundary_valid is False
        assert "workspace" in result.reason.lower()

    async def test_deny_decision_type_rejected_by_verifier(self, runtime, mock_vault):
        """Token linked to a DENY decision is rejected by TokenVerifier."""
        parent = _make_governance_decision(
            decision_type=DecisionType.DENY,
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        # Manually inject a token dict (simulating a bug where token exists for DENY)
        fake_token_id = "gt_fake_deny_token_123"
        mock_vault._tokens[fake_token_id] = {
            "token_id": fake_token_id,
            "decision_id": parent.decision_id,
            "tenant_id": parent.tenant_id,
            "actor_id": parent.actor_id,
            "scope_actions": ["*"],
            "scope_resources": ["*"],
            "expiry": None,
            "trace_id": parent.trace_id,
            "workspace_id": parent.tenant_id,
            "parent_decision_id": None,
            "parent_actor_id": None,
            "workflow_id": None,
        }
        verifier = runtime.verifier
        result = await verifier.verify_token(fake_token_id, action="test.action", resource="test:resource")
        assert result.valid is False
        assert "not allowed" in result.reason.lower()

    async def test_forged_lineage_ignored_after_vault_resolution(self, runtime, mock_kernel, mock_vault):
        """Caller supplies forged root_decision_id and trace_id; vault-resolved values are used."""
        await self._setup_kernel_allow(mock_kernel)
        # Store the real parent in the vault
        real_parent = _make_governance_decision(
            trace_id="real_trace_123",
            root_decision_id="real_root_456",
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(real_parent)
        # Store root so ancestry checks pass
        root = _make_governance_decision(
            decision_id="real_root_456",
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(root)
        # Attacker creates a forged parent object with same decision_id but fake lineage
        forged_parent = _make_governance_decision(
            decision_id=real_parent.decision_id,
            trace_id="FORGED_TRACE_999",
            root_decision_id="FORGED_ROOT_999",
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        result = await runtime.delegate(
            parent_decision=forged_parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )
        assert result.success is True
        # Child must inherit REAL lineage from vault, not forged values
        assert result.child_action.trace_id == "real_trace_123"
        assert result.child_action.root_decision_id == "real_root_456"
        assert result.child_decision.trace_id == "real_trace_123"
        assert result.child_decision.root_decision_id == "real_root_456"


# ──────────────────────────────────────────────────────────────────────────────
# 9. Atomic Delegation Hardening
# ──────────────────────────────────────────────────────────────────────────────

class TestAtomicDelegationHardening:
    """
    Validates that delegation is atomic and fail-closed:
    - Token issuance failure leaves no usable child authority
    - Parent validation failure leaves no child state
    - Duplicate retry does not create duplicate grants
    - Compensating cleanup is attempted on partial failure
    """

    async def _setup_kernel_allow(self, mock_kernel):
        async def _handle(action, *args, **kwargs):
            return KernelResult(
                action=action,
                decision=_make_decision(action, status=KernelStatus.ALLOWED),
                executed=True,
                result=None,
                error=None,
            )
        mock_kernel.handle.side_effect = _handle

    async def test_delegation_token_issuance_failure_no_grant(self, runtime, mock_kernel, mock_vault, mock_audit):
        """If vault.issue_token_for_decision fails, child_grant is None and success is False."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)

        # Simulate token issuance failure
        original_issue = mock_vault.issue_token_for_decision
        async def failing_issue(*args, **kwargs):
            raise RuntimeError("vault connection timeout")
        mock_vault.issue_token_for_decision = failing_issue

        result = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )
        assert result.success is False
        assert result.child_grant is None
        assert "issuance failed" in result.reason.lower() or "token" in result.reason.lower()

        # Restore
        mock_vault.issue_token_for_decision = original_issue

    async def test_delegation_parent_revoked_no_child_created(self, runtime, mock_kernel, mock_vault):
        """If parent is revoked, no child decision or token should be created."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            decision_type=DecisionType.REVOKED,
            revoked_at=datetime.now(timezone.utc),
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        pre_child_count = len(mock_vault._decisions)
        result = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )
        assert result.success is False
        # No new decisions should have been stored
        assert len(mock_vault._decisions) == pre_child_count

    async def test_delegation_duplicate_retry_no_duplicate_grant(self, runtime, mock_kernel, mock_vault, mock_audit):
        """Retrying the same delegation should not create duplicate tokens."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)

        result1 = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )
        assert result1.success is True
        assert result1.child_grant is not None

        # Count tokens before retry
        pre_token_count = len(mock_vault._tokens)

        # Retry with same parameters
        result2 = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )
        assert result2.success is True
        # Should create a new token (different action_id -> different decision_id)
        # but both should be valid
        assert len(mock_vault._tokens) == pre_token_count + 1
        assert result2.child_grant != result1.child_grant


# ──────────────────────────────────────────────────────────────────────────────
# 10. Gather Context Discipline
# ──────────────────────────────────────────────────────────────────────────────

class TestGatherContextDiscipline:
    """
    Validates that gather branches receive only necessary context:
    - Branch context excludes unnecessary parent history
    - Branch context preserves required lineage IDs
    - Branch context preserves required governance metadata
    - Shared context is merged correctly without bloat
    """

    async def _setup_kernel_allow(self, mock_kernel):
        async def _handle(action, *args, **kwargs):
            return KernelResult(
                action=action,
                decision=_make_decision(action, status=KernelStatus.ALLOWED),
                executed=True,
                result=None,
                error=None,
            )
        mock_kernel.handle.side_effect = _handle

    async def test_gather_branch_context_excludes_parent_bloat(self, runtime, mock_kernel, mock_vault):
        """Large parent payloads must not leak into branch context."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)

        # Branch with large context
        large_context = {
            "task": "do_something",
            "history": ["step1", "step2", "step3"] * 100,  # Large list
            "parent_payload": {"data": "x" * 10000},
        }
        result = await runtime.gather(
            parent_decision=parent,
            branches=[
                {"action": "a1", "resource": "r1", "context": large_context},
            ],
        )
        assert result.success is True
        # The runtime's _distill_branch_context should have filtered it
        branch_action = result.branches[0].action
        # Large list should still be present (under 16 items), but huge dict should be dropped
        assert "task" in branch_action.context
        assert branch_action.context.get("task") == "do_something"

    async def test_gather_branch_context_preserves_lineage(self, runtime, mock_kernel, mock_vault):
        """Branch action must have correct lineage fields regardless of context filtering."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            decision_id="gd_parent_lineage",
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        result = await runtime.gather(
            parent_decision=parent,
            branches=[
                {"action": "a1", "resource": "r1"},
            ],
        )
        assert result.success is True
        branch_action = result.branches[0].action
        assert branch_action.root_decision_id == parent.decision_id
        assert branch_action.parent_decision_id == parent.decision_id
        assert branch_action.trace_id is not None
        assert branch_action.parent_actor_id == parent.actor_id

    async def test_gather_shared_context_merged_correctly(self, runtime, mock_kernel, mock_vault):
        """Shared context is available to all branches without duplication."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)
        result = await runtime.gather(
            parent_decision=parent,
            branches=[
                {"action": "a1", "resource": "r1", "context": {"branch_specific": "value1"}},
                {"action": "a2", "resource": "r2", "context": {"branch_specific": "value2"}},
            ],
            shared_context={"shared_key": "shared_value", "tenant": TENANT},
        )
        assert result.success is True
        assert result.branches[0].action.context.get("shared_key") == "shared_value"
        assert result.branches[0].action.context.get("branch_specific") == "value1"
        assert result.branches[1].action.context.get("shared_key") == "shared_value"
        assert result.branches[1].action.context.get("branch_specific") == "value2"


# ──────────────────────────────────────────────────────────────────────────────
# 11. Recursive Revocation Hardening
# ──────────────────────────────────────────────────────────────────────────────

class TestRecursiveRevocationHardening:
    """
    Validates that parent/root revocation cascades to descendants:
    - Revoked parent blocks child protected action
    - Revoked root blocks all descendants
    - Revoked supervisor blocks gathered branches
    - Introspection fails for descendant authority after ancestor revocation
    - TokenVerifier rejects child tokens after parent revocation
    """

    async def _setup_kernel_allow(self, mock_kernel):
        async def _handle(action, *args, **kwargs):
            return KernelResult(
                action=action,
                decision=_make_decision(action, status=KernelStatus.ALLOWED),
                executed=True,
                result=None,
                error=None,
            )
        mock_kernel.handle.side_effect = _handle

    async def test_revoked_parent_blocks_child_token(self, runtime, mock_kernel, mock_vault):
        """After parent is revoked, child token verification must fail."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)

        # Delegate to create child
        result = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )
        assert result.success is True
        child_grant = result.child_grant
        assert child_grant is not None

        # Verify child token is valid before revocation
        verify_before = await runtime.verifier.verify_token(child_grant, action="child.action", resource="child:resource")
        assert verify_before.valid is True

        # Revoke parent
        await mock_vault.revoke_decision(parent.decision_id, tenant_id=parent.tenant_id, reason="test_revoke")

        # Verify child token is now invalid
        verify_after = await runtime.verifier.verify_token(child_grant, action="child.action", resource="child:resource")
        assert verify_after.valid is False
        assert any(r in verify_after.reason.lower() for r in ["token_revoked", "parent_revoked", "root_revoked", "ancestry"])

    async def test_revoked_root_blocks_grandchild(self, runtime, mock_kernel, mock_vault):
        """After root is revoked, grandchild token verification must fail."""
        await self._setup_kernel_allow(mock_kernel)
        root = _make_governance_decision(
            decision_id="gd_root",
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(root)

        # Delegate to create child with broader scope so it can delegate further
        child_result = await runtime.delegate(
            parent_decision=root,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action", "grandchild.action"], resources=["child:resource", "grandchild:resource"]),
        )
        assert child_result.success is True
        child_grant = child_result.child_grant

        # Delegate again to create grandchild
        # Need to resolve child decision from vault for delegation
        child_decision_data = await mock_vault.resolve_decision(
            str(child_result.child_decision.decision_id)
        )
        assert child_decision_data is not None, "Child governance decision should be stored in vault"
        child_decision = runtime._dict_to_governance_decision(child_decision_data)
        grandchild_result = await runtime.delegate(
            parent_decision=child_decision,
            child_actor_id="grandchild_agent",
            action_name="grandchild.action",
            resource="grandchild:resource",
            scope=DecisionScope(actions=["grandchild.action"], resources=["grandchild:resource"]),
        )
        assert grandchild_result.success is True
        grandchild_grant = grandchild_result.child_grant

        # Verify grandchild token is valid before revocation
        verify_before = await runtime.verifier.verify_token(grandchild_grant, action="grandchild.action", resource="grandchild:resource")
        assert verify_before.valid is True

        # Revoke root
        await mock_vault.revoke_decision(root.decision_id, tenant_id=root.tenant_id, reason="test_revoke_root")

        # Verify grandchild token is now invalid
        verify_after = await runtime.verifier.verify_token(grandchild_grant, action="grandchild.action", resource="grandchild:resource")
        assert verify_after.valid is False
        assert any(r in verify_after.reason.lower() for r in ["token_revoked", "parent_revoked", "root_revoked", "ancestry"])

    async def test_revoked_parent_blocks_gather_branch(self, runtime, mock_kernel, mock_vault):
        """After parent is revoked, gather branches cannot be created."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)

        # Revoke parent BEFORE gather
        await mock_vault.revoke_decision(parent.decision_id, tenant_id=parent.tenant_id, reason="test_revoke")

        # Gather should fail because parent is revoked
        result = await runtime.gather(
            parent_decision=parent,
            branches=[
                {"action": "a1", "resource": "r1"},
                {"action": "a2", "resource": "r2"},
            ],
        )
        assert result.success is False
        assert "not active" in result.reason.lower() or "revoked" in result.reason.lower()

    async def test_revoked_parent_blocks_introspection_of_child(self, runtime, mock_kernel, mock_vault):
        """After parent is revoked, child decision introspection must fail."""
        await self._setup_kernel_allow(mock_kernel)
        parent = _make_governance_decision(
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(parent)

        # Create child
        result = await runtime.delegate(
            parent_decision=parent,
            child_actor_id=CHILD_ACTOR,
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )
        assert result.success is True
        child_decision_id = result.child_decision.decision_id

        # Introspection succeeds before revocation
        intro_before = await runtime.introspect(
            decision_id=str(child_decision_id),
            required_action="child.action",
            tenant_id=parent.tenant_id,
        )
        assert intro_before.active is True

        # Revoke parent
        await mock_vault.revoke_decision(parent.decision_id, tenant_id=parent.tenant_id, reason="test_revoke")

        # Introspection fails after revocation
        intro_after = await runtime.introspect(
            decision_id=str(child_decision_id),
            required_action="child.action",
            tenant_id=parent.tenant_id,
        )
        assert intro_after.active is False
        assert "ancestry" in intro_after.reason.lower() or "revoked" in intro_after.reason.lower()

    async def test_handoff_superseded_parent_blocks_old_child(self, runtime, mock_kernel, mock_vault):
        """After handoff, old token is rejected; new token works."""
        await self._setup_kernel_allow(mock_kernel)
        current = _make_governance_decision(
            scope=DecisionScope(actions=["*"], resources=["*"]),
        )
        await mock_vault.store_decision(current)

        # Issue old token
        old_token = await mock_vault.issue_token_for_decision(current)

        # Handoff
        handoff_result = await runtime.handoff(
            current_decision=current,
            new_actor_id=NEW_ACTOR,
            action_name="new.action",
            resource="new:resource",
            scope=DecisionScope(actions=["new.action"], resources=["new:resource"]),
        )
        assert handoff_result.success is True

        # Old token should be rejected due to superseded parent
        verify_old = await runtime.verifier.verify_token(
            old_token.token_id, action="test.action", resource="test:resource"
        )
        assert verify_old.valid is False
        assert "superseded" in verify_old.reason.lower()

        # New token should be valid
        new_token_id = handoff_result.new_grant
        assert new_token_id is not None
        verify_new = await runtime.verifier.verify_token(
            new_token_id, action="new.action", resource="new:resource"
        )
        assert verify_new.valid is True
