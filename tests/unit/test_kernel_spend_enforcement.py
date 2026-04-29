"""Kernel-level pre-execution spend enforcement.

These tests exercise the wedge claim: BLOCK before any LLM/API call when a
budget is exceeded, and emit a `spend_limit_exceeded` audit event.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from citadel.actions import Action, KernelStatus
from citadel.commercial.cost_controls import BudgetDecision, CostBudget
from citadel.execution.kernel import Kernel


def _make_action(tenant_id: str = "tenant-1", projected_cost_cents: int = 600) -> Action:
    return Action(
        action_id=uuid.uuid4(),
        actor_id="agent-1",
        actor_type="agent",
        action_name="llm.generate",
        resource="anthropic:claude",
        tenant_id=tenant_id,
        payload={},
        context={"projected_cost_cents": projected_cost_cents, "project_id": "proj-1"},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.now(timezone.utc),
    )


def _allowed_decision() -> BudgetDecision:
    now = datetime.now(timezone.utc)
    return BudgetDecision(
        allowed=True,
        enforcement_action="allow",
        reason="Budget check passed",
        projected_cost_cents=600,
        current_spend_cents=100,
        budget_amount_cents=10_000,
        period_start=now,
        period_end=now,
    )


def _blocked_decision() -> BudgetDecision:
    now = datetime.now(timezone.utc)
    budget = CostBudget(
        tenant_id="tenant-1",
        name="Monthly LLM cap",
        scope_type="tenant",
        scope_value="tenant-1",
        amount_cents=10_000,
        reset_period="monthly",
        enforcement_action="block",
        budget_id="budget-1",
    )
    return BudgetDecision(
        allowed=False,
        enforcement_action="block",
        reason="tenant budget 'Monthly LLM cap' would be exceeded: 10100/10000 cents",
        projected_cost_cents=600,
        current_spend_cents=9_500,
        budget_amount_cents=10_000,
        period_start=now,
        period_end=now,
        budget=budget,
    )


def _build_kernel(cost_service):
    """Wire a Kernel with stub collaborators that always permit the action,
    so the only thing exercised is the budget gate."""
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
    executor.run = AsyncMock(return_value={"ok": True})

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
    return kernel, executor, audit


@pytest.mark.asyncio
async def test_kernel_blocks_before_execution_when_budget_exceeded():
    cost_service = AsyncMock()
    cost_service.check_budget = AsyncMock(return_value=_blocked_decision())
    kernel, executor, audit = _build_kernel(cost_service)

    result = await kernel.handle(_make_action())

    assert result.executed is False
    assert result.decision is not None
    assert result.decision.status == KernelStatus.BLOCKED_POLICY
    assert result.decision.winning_rule == "spend_limit_exceeded"
    assert "would be exceeded" in result.decision.reason

    executor.run.assert_not_called()
    audit.spend_limit_exceeded.assert_awaited_once()
    audit.action_executed.assert_not_called()


@pytest.mark.asyncio
async def test_kernel_executes_when_budget_allows():
    cost_service = AsyncMock()
    cost_service.check_budget = AsyncMock(return_value=_allowed_decision())
    kernel, executor, audit = _build_kernel(cost_service)

    result = await kernel.handle(_make_action(projected_cost_cents=100))

    assert result.executed is True
    assert result.decision.status == KernelStatus.EXECUTED
    executor.run.assert_awaited_once()
    audit.spend_limit_exceeded.assert_not_called()


@pytest.mark.asyncio
async def test_kernel_skips_budget_check_when_no_cost_service_configured():
    kernel, executor, audit = _build_kernel(cost_service=None)

    result = await kernel.handle(_make_action())

    assert result.executed is True
    executor.run.assert_awaited_once()
    audit.spend_limit_exceeded.assert_not_called()


@pytest.mark.asyncio
async def test_kernel_does_not_block_for_non_block_enforcement_actions():
    """`require_approval` and `throttle` go through their own paths — the
    budget gate only enforces the hard `block` action."""
    now = datetime.now(timezone.utc)
    cost_service = AsyncMock()
    cost_service.check_budget = AsyncMock(
        return_value=BudgetDecision(
            allowed=False,
            enforcement_action="require_approval",
            reason="approval required",
            projected_cost_cents=600,
            current_spend_cents=9_500,
            budget_amount_cents=10_000,
            period_start=now,
            period_end=now,
        )
    )
    kernel, executor, audit = _build_kernel(cost_service)

    result = await kernel.handle(_make_action())

    audit.spend_limit_exceeded.assert_not_called()
    assert result.decision.winning_rule != "spend_limit_exceeded"
