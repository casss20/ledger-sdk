"""Integration: action submission with cost estimation."""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from citadel.actions import Action, KernelStatus
from citadel.api.routers.actions import SubmitActionRequest
from citadel.commercial.cost_controls import BudgetDecision, CostBudget
from citadel.execution.kernel import Kernel


def _make_kernel_with_block_budget():
    """Build a kernel that blocks on budget check."""
    repo = AsyncMock()
    repo.find_decision_by_idempotency = AsyncMock(return_value=None)
    repo.save_action = AsyncMock(return_value=True)
    repo.save_decision = AsyncMock(return_value=None)
    repo.save_execution_result = AsyncMock(return_value=None)

    snapshot = SimpleNamespace(snapshot_id=uuid.uuid4(), policy_version="v1")
    policy_resolver = AsyncMock()
    policy_resolver.resolve = AsyncMock(return_value=snapshot)

    precedence_result = SimpleNamespace(
        blocked=False,
        status=KernelStatus.ALLOWED,
        winning_rule="default_allow",
        reason="ok",
        path_taken="default",
    )
    precedence = AsyncMock()
    precedence.evaluate = AsyncMock(return_value=precedence_result)

    approval_check = SimpleNamespace(required=False, reason="", risk_level=None, risk_score=None)
    approvals = AsyncMock()
    approvals.check_required = AsyncMock(return_value=approval_check)
    approvals.create_pending = AsyncMock(return_value=str(uuid.uuid4()))

    capability_service = AsyncMock()
    audit = AsyncMock()
    executor = AsyncMock()

    now = datetime.now(timezone.utc)
    budget = CostBudget(
        tenant_id="tenant-1",
        name="Monthly cap",
        scope_type="tenant",
        scope_value="tenant-1",
        amount_cents=5_000,
        reset_period="monthly",
        enforcement_action="block",
        budget_id="budget-1",
    )
    blocked_decision = BudgetDecision(
        allowed=False,
        enforcement_action="block",
        reason="Budget would be exceeded",
        projected_cost_cents=100,
        current_spend_cents=4_950,
        budget_amount_cents=5_000,
        period_start=now,
        period_end=now,
        budget=budget,
    )
    cost_service = AsyncMock()
    cost_service.check_budget = AsyncMock(return_value=blocked_decision)

    kernel = Kernel(
        repository=repo,
        policy_resolver=policy_resolver,
        precedence=precedence,
        approval_service=approvals,
        capability_service=capability_service,
        audit_service=audit,
        executor=executor,
        cost_service=cost_service,
    )
    return kernel, executor, audit, cost_service


@pytest.mark.asyncio
async def test_cost_estimation_from_tokens_blocks_on_budget():
    """When user provides provider/model/tokens, kernel estimates cost and
    enforces budgets. If budget would be exceeded, block before execution."""
    kernel, executor, audit, cost_service = _make_kernel_with_block_budget()

    action = Action(
        action_id=uuid.uuid4(),
        actor_id="agent-1",
        actor_type="agent",
        action_name="llm.generate",
        resource="anthropic:claude",
        tenant_id="tenant-1",
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.now(timezone.utc),
    )

    result = await kernel.handle(action)

    assert result.executed is False
    assert result.decision.status == KernelStatus.BLOCKED_POLICY
    assert result.decision.winning_rule == "spend_limit_exceeded"
    executor.run.assert_not_called()
    audit.spend_limit_exceeded.assert_awaited_once()


def test_request_with_explicit_cost():
    """SubmitActionRequest with explicit projected_cost_cents."""
    req = SubmitActionRequest(
        actor_id="agent-1",
        action_name="llm.generate",
        resource="anthropic:claude",
        tenant_id="tenant-1",
        projected_cost_cents=1000,
    )
    assert req.projected_cost_cents == 1000


def test_request_with_provider_and_model():
    """SubmitActionRequest with provider/model/tokens for estimation."""
    req = SubmitActionRequest(
        actor_id="agent-1",
        action_name="llm.generate",
        resource="anthropic:claude",
        tenant_id="tenant-1",
        provider="anthropic",
        model="claude-opus-4-7",
        input_tokens=10_000,
        output_tokens=2_000,
    )
    assert req.provider == "anthropic"
    assert req.model == "claude-opus-4-7"
    assert req.input_tokens == 10_000
    assert req.output_tokens == 2_000


def test_request_cost_fields_optional():
    """Cost fields are all optional."""
    req = SubmitActionRequest(
        actor_id="agent-1",
        action_name="llm.generate",
        resource="anthropic:claude",
        tenant_id="tenant-1",
    )
    assert req.projected_cost_cents is None
    assert req.provider is None
    assert req.model is None
    assert req.input_tokens is None
    assert req.output_tokens is None
