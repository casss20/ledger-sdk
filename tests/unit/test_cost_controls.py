from datetime import datetime, timezone
from pathlib import Path

import pytest
from citadel.commercial.cost_controls import (
    BudgetTopUp,
    CostAttribution,
    CostBudget,
    can_top_up_budget,
    current_period_window,
    evaluate_budget,
    evaluate_budget_set,
    matching_scope_values,
    validate_budget,
    validate_top_up,
)


def test_tenant_budget_blocks_projected_overspend():
    budget = CostBudget(
        tenant_id="tenant-1",
        name="Monthly LLM cap",
        scope_type="tenant",
        scope_value="tenant-1",
        amount_cents=10_000,
        reset_period="monthly",
        enforcement_action="block",
    )

    decision = evaluate_budget(
        budget,
        current_spend_cents=9_500,
        projected_cost_cents=600,
        now=datetime(2026, 4, 28, tzinfo=timezone.utc),
    )

    assert decision.allowed is False
    assert decision.enforcement_action == "block"
    assert decision.budget == budget
    assert "would be exceeded" in decision.reason


def test_require_approval_budget_surfaces_approval_action():
    budget = CostBudget(
        tenant_id="tenant-1",
        name="Agent approval cap",
        scope_type="agent",
        scope_value="agent-7",
        amount_cents=1_000,
        reset_period="daily",
        enforcement_action="require_approval",
    )

    decision = evaluate_budget(
        budget,
        current_spend_cents=990,
        projected_cost_cents=20,
    )

    assert decision.allowed is False
    assert decision.requires_approval is True
    assert decision.enforcement_action == "require_approval"


def test_throttle_budget_surfaces_throttled_action():
    budget = CostBudget(
        tenant_id="tenant-1",
        name="Project throttle cap",
        scope_type="project",
        scope_value="search",
        amount_cents=2_000,
        reset_period="weekly",
        enforcement_action="throttle",
    )

    decision = evaluate_budget(
        budget,
        current_spend_cents=2_000,
        projected_cost_cents=1,
    )

    assert decision.allowed is False
    assert decision.throttled is True
    assert decision.enforcement_action == "throttle"


def test_hierarchical_budget_checks_more_specific_scope_first():
    tenant_budget = CostBudget(
        budget_id="budget-tenant",
        tenant_id="tenant-1",
        name="Tenant cap",
        scope_type="tenant",
        scope_value="tenant-1",
        amount_cents=100_000,
        reset_period="monthly",
        enforcement_action="block",
    )
    agent_budget = CostBudget(
        budget_id="budget-agent",
        tenant_id="tenant-1",
        name="Agent cap",
        scope_type="agent",
        scope_value="agent-7",
        amount_cents=500,
        reset_period="monthly",
        enforcement_action="require_approval",
    )

    decision = evaluate_budget_set(
        [tenant_budget, agent_budget],
        spend_by_budget_id={"budget-tenant": 100, "budget-agent": 490},
        projected_cost_cents=20,
    )

    assert decision.allowed is False
    assert decision.budget == agent_budget
    assert decision.enforcement_action == "require_approval"


def test_matching_scope_values_supports_spend_attribution():
    attribution = CostAttribution(
        tenant_id="tenant-1",
        actor_id="agent-7",
        project_id="search",
        api_key_id="key-1",
    )

    assert matching_scope_values(attribution) == {
        "tenant": "tenant-1",
        "project": "search",
        "agent": "agent-7",
        "api_key": "key-1",
    }


def test_period_windows_are_deterministic():
    now = datetime(2026, 4, 28, 15, 30, tzinfo=timezone.utc)

    day_start, day_end = current_period_window("daily", now)
    week_start, week_end = current_period_window("weekly", now)
    month_start, month_end = current_period_window("monthly", now)

    assert day_start.isoformat() == "2026-04-28T00:00:00+00:00"
    assert day_end.isoformat() == "2026-04-29T00:00:00+00:00"
    assert week_start.isoformat() == "2026-04-27T00:00:00+00:00"
    assert week_end.isoformat() == "2026-05-04T00:00:00+00:00"
    assert month_start.isoformat() == "2026-04-01T00:00:00+00:00"
    assert month_end.isoformat() == "2026-05-01T00:00:00+00:00"


def test_tenant_scope_budget_must_use_tenant_id_as_scope_value():
    budget = CostBudget(
        tenant_id="tenant-1",
        name="Bad tenant cap",
        scope_type="tenant",
        scope_value="other",
        amount_cents=1_000,
        reset_period="monthly",
        enforcement_action="block",
    )

    with pytest.raises(ValueError, match="tenant_id as scope_value"):
        validate_budget(budget)


def test_executive_top_up_validation_accepts_positive_amount_and_reason():
    validate_top_up(
        BudgetTopUp(
            budget_id="budget-tenant",
            tenant_id="tenant-1",
            amount_cents=50_000,
            reason="Temporary capacity for Q2 evaluation workload",
            actor_id="exec-1",
            actor_role="executive",
        )
    )


def test_top_up_rejects_non_positive_amounts():
    with pytest.raises(ValueError, match="greater than 0"):
        validate_top_up(
            BudgetTopUp(
                budget_id="budget-tenant",
                tenant_id="tenant-1",
                amount_cents=0,
                reason="Capacity request",
                actor_id="exec-1",
                actor_role="executive",
            )
        )


def test_top_up_requires_audit_reason():
    with pytest.raises(ValueError, match="reason is required"):
        validate_top_up(
            BudgetTopUp(
                budget_id="budget-tenant",
                tenant_id="tenant-1",
                amount_cents=10_000,
                reason=" ",
                actor_id="exec-1",
                actor_role="executive",
            )
        )


def test_top_up_rejects_unauthorized_roles():
    assert can_top_up_budget("executive") is True
    assert can_top_up_budget("admin") is False
    assert can_top_up_budget("operator") is False
    assert can_top_up_budget("auditor") is False

    with pytest.raises(PermissionError, match="executive role"):
        validate_top_up(
            BudgetTopUp(
                budget_id="budget-tenant",
                tenant_id="tenant-1",
                amount_cents=10_000,
                reason="Capacity request",
                actor_id="admin-1",
                actor_role="admin",
            )
        )


def test_top_up_migration_preserves_adjustment_and_governance_audit():
    migration = Path("db/migrations/019_cost_budget_topups.sql").read_text()

    assert "CREATE TABLE IF NOT EXISTS cost_budget_adjustments" in migration
    assert "cost.budget_top_up" in migration
    assert "governance_audit_log" in migration
    assert "append-only" in migration
