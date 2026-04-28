"""Cost controls and budget enforcement for LLM usage.

This module extends the existing commercial control plane. It does not replace
Stripe quota enforcement, governance audit, or policy evaluation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

BudgetScope = str
ResetPeriod = str
EnforcementAction = str

VALID_SCOPES = {"tenant", "project", "agent", "api_key"}
VALID_PERIODS = {"daily", "weekly", "monthly"}
VALID_ENFORCEMENT_ACTIONS = {"block", "require_approval", "throttle"}
TOP_UP_ALLOWED_ROLES = {"executive"}

SCOPE_PRIORITY = {
    "api_key": 4,
    "agent": 3,
    "project": 2,
    "tenant": 1,
}


@dataclass(frozen=True)
class CostBudget:
    """Operator-configured cost budget."""

    tenant_id: str
    name: str
    scope_type: BudgetScope
    scope_value: str
    amount_cents: int
    reset_period: ResetPeriod
    enforcement_action: EnforcementAction
    currency: str = "usd"
    warning_threshold_percent: int = 80
    is_active: bool = True
    budget_id: str | None = None


@dataclass(frozen=True)
class CostAttribution:
    """Attribution labels for an LLM cost event or pre-request check."""

    tenant_id: str
    projected_cost_cents: int = 0
    actual_cost_cents: int = 0
    actor_id: str | None = None
    project_id: str | None = None
    api_key_id: str | None = None
    provider: str | None = None
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    request_id: str | None = None
    decision_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class BudgetDecision:
    """Pre-request budget enforcement result."""

    allowed: bool
    enforcement_action: str
    reason: str
    projected_cost_cents: int
    current_spend_cents: int
    budget_amount_cents: int | None
    period_start: datetime
    period_end: datetime
    budget: CostBudget | None = None
    warning: bool = False

    @property
    def requires_approval(self) -> bool:
        return self.enforcement_action == "require_approval"

    @property
    def throttled(self) -> bool:
        return self.enforcement_action == "throttle"


@dataclass(frozen=True)
class BudgetTopUp:
    """Manual enterprise budget top-up request."""

    budget_id: str
    tenant_id: str
    amount_cents: int
    reason: str
    actor_id: str
    actor_role: str
    metadata: dict[str, Any] | None = None


def validate_budget(budget: CostBudget) -> None:
    if budget.scope_type not in VALID_SCOPES:
        raise ValueError(f"scope_type must be one of: {', '.join(sorted(VALID_SCOPES))}")
    if budget.reset_period not in VALID_PERIODS:
        raise ValueError(f"reset_period must be one of: {', '.join(sorted(VALID_PERIODS))}")
    if budget.enforcement_action not in VALID_ENFORCEMENT_ACTIONS:
        allowed = ", ".join(sorted(VALID_ENFORCEMENT_ACTIONS))
        raise ValueError(f"enforcement_action must be one of: {allowed}")
    if budget.amount_cents <= 0:
        raise ValueError("amount_cents must be greater than 0")
    if budget.warning_threshold_percent < 1 or budget.warning_threshold_percent > 100:
        raise ValueError("warning_threshold_percent must be between 1 and 100")
    if not budget.scope_value:
        raise ValueError("scope_value is required")
    if budget.scope_type == "tenant" and budget.scope_value != budget.tenant_id:
        raise ValueError("tenant-scope budgets must use tenant_id as scope_value")


def validate_top_up(top_up: BudgetTopUp) -> None:
    if top_up.amount_cents <= 0:
        raise ValueError("amount_cents must be greater than 0")
    if not top_up.reason or not top_up.reason.strip():
        raise ValueError("reason is required")
    if len(top_up.reason.strip()) > 1000:
        raise ValueError("reason must be 1000 characters or fewer")
    if not can_top_up_budget(top_up.actor_role):
        raise PermissionError("budget top-up requires executive role")


def can_top_up_budget(role: str | None) -> bool:
    return (role or "").lower() in TOP_UP_ALLOWED_ROLES


def current_period_window(reset_period: ResetPeriod, now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return deterministic period bounds for a reset period."""
    if reset_period not in VALID_PERIODS:
        raise ValueError(f"reset_period must be one of: {', '.join(sorted(VALID_PERIODS))}")

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)

    if reset_period == "daily":
        start = current.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)

    if reset_period == "weekly":
        start_of_day = current.replace(hour=0, minute=0, second=0, microsecond=0)
        start = start_of_day - timedelta(days=start_of_day.weekday())
        return start, start + timedelta(days=7)

    start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def matching_scope_values(attribution: CostAttribution) -> dict[str, str]:
    """Return scope values that apply to the attribution context."""
    values = {"tenant": attribution.tenant_id}
    if attribution.project_id:
        values["project"] = attribution.project_id
    if attribution.actor_id:
        values["agent"] = attribution.actor_id
    if attribution.api_key_id:
        values["api_key"] = attribution.api_key_id
    return values


def evaluate_budget(
    budget: CostBudget,
    *,
    current_spend_cents: int,
    projected_cost_cents: int,
    now: datetime | None = None,
) -> BudgetDecision:
    """Evaluate one budget against projected spend."""
    validate_budget(budget)
    period_start, period_end = current_period_window(budget.reset_period, now)
    projected_total = current_spend_cents + projected_cost_cents
    warning_at = int(budget.amount_cents * (budget.warning_threshold_percent / 100))

    if projected_total > budget.amount_cents:
        return BudgetDecision(
            allowed=False,
            enforcement_action=budget.enforcement_action,
            reason=(
                f"{budget.scope_type} budget '{budget.name}' would be exceeded: "
                f"{projected_total}/{budget.amount_cents} cents"
            ),
            projected_cost_cents=projected_cost_cents,
            current_spend_cents=current_spend_cents,
            budget_amount_cents=budget.amount_cents,
            period_start=period_start,
            period_end=period_end,
            budget=budget,
            warning=True,
        )

    return BudgetDecision(
        allowed=True,
        enforcement_action="allow",
        reason="Budget check passed",
        projected_cost_cents=projected_cost_cents,
        current_spend_cents=current_spend_cents,
        budget_amount_cents=budget.amount_cents,
        period_start=period_start,
        period_end=period_end,
        budget=budget,
        warning=projected_total >= warning_at,
    )


def evaluate_budget_set(
    budgets: list[CostBudget],
    *,
    spend_by_budget_id: dict[str, int],
    projected_cost_cents: int,
    now: datetime | None = None,
) -> BudgetDecision:
    """Evaluate matching budgets in hierarchy order.

    Most-specific scopes are checked first. Any exceeded budget can enforce.
    """
    if not budgets:
        current = now or datetime.now(timezone.utc)
        return BudgetDecision(
            allowed=True,
            enforcement_action="allow",
            reason="No active budget matched this request",
            projected_cost_cents=projected_cost_cents,
            current_spend_cents=0,
            budget_amount_cents=None,
            period_start=current,
            period_end=current,
            budget=None,
            warning=False,
        )

    ordered = sorted(
        budgets,
        key=lambda budget: SCOPE_PRIORITY[budget.scope_type],
        reverse=True,
    )
    first_decision: BudgetDecision | None = None
    for budget in ordered:
        budget_key = budget.budget_id or f"{budget.scope_type}:{budget.scope_value}"
        decision = evaluate_budget(
            budget,
            current_spend_cents=spend_by_budget_id.get(budget_key, 0),
            projected_cost_cents=projected_cost_cents,
            now=now,
        )
        if first_decision is None:
            first_decision = decision
        if not decision.allowed:
            return decision

    return first_decision or evaluate_budget_set(
        [],
        spend_by_budget_id={},
        projected_cost_cents=projected_cost_cents,
        now=now,
    )


class CostControlService:
    """Persistence and enforcement for cost budgets."""

    def __init__(self, pool):
        self.pool = pool

    async def create_budget(self, budget: CostBudget, *, created_by: str | None = None) -> dict[str, Any]:
        validate_budget(budget)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_tenant_context($1)", budget.tenant_id)
                row = await conn.fetchrow(
                    """
                    INSERT INTO cost_budgets (
                        tenant_id, name, scope_type, scope_value, amount_cents,
                        currency, reset_period, enforcement_action,
                        warning_threshold_percent, is_active, created_by
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, TRUE, $10)
                    RETURNING *
                    """,
                    budget.tenant_id,
                    budget.name,
                    budget.scope_type,
                    budget.scope_value,
                    budget.amount_cents,
                    budget.currency,
                    budget.reset_period,
                    budget.enforcement_action,
                    budget.warning_threshold_percent,
                    created_by,
                )
        return _row_to_dict(row)

    async def list_budgets(self, tenant_id: str) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            await conn.execute("SELECT set_tenant_context($1)", tenant_id)
            rows = await conn.fetch(
                """
                SELECT *
                FROM cost_budgets
                WHERE tenant_id = $1
                ORDER BY is_active DESC, scope_type, name
                """,
                tenant_id,
            )
        return [_row_to_dict(row) for row in rows]

    async def top_up_tenant_budget(self, top_up: BudgetTopUp) -> dict[str, Any]:
        """Increase an existing tenant-scope budget with an audited adjustment."""
        validate_top_up(top_up)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_tenant_context($1)", top_up.tenant_id)
                budget = await conn.fetchrow(
                    """
                    SELECT *
                    FROM cost_budgets
                    WHERE budget_id = $1
                      AND tenant_id = $2
                      AND is_active = TRUE
                    FOR UPDATE
                    """,
                    top_up.budget_id,
                    top_up.tenant_id,
                )
                if not budget:
                    raise ValueError("budget not found")
                if budget["scope_type"] != "tenant":
                    raise ValueError("MVP top-up only supports tenant-scope budgets")

                previous_amount = int(budget["amount_cents"])
                resulting_amount = previous_amount + top_up.amount_cents

                updated_budget = await conn.fetchrow(
                    """
                    UPDATE cost_budgets
                    SET amount_cents = $1, updated_at = NOW()
                    WHERE budget_id = $2 AND tenant_id = $3
                    RETURNING *
                    """,
                    resulting_amount,
                    top_up.budget_id,
                    top_up.tenant_id,
                )
                adjustment = await conn.fetchrow(
                    """
                    INSERT INTO cost_budget_adjustments (
                        budget_id, tenant_id, adjustment_type, amount_cents,
                        previous_amount_cents, resulting_amount_cents,
                        reason, actor_id, actor_role, metadata_json
                    )
                    VALUES ($1, $2, 'top_up', $3, $4, $5, $6, $7, $8, $9::jsonb)
                    RETURNING *
                    """,
                    top_up.budget_id,
                    top_up.tenant_id,
                    top_up.amount_cents,
                    previous_amount,
                    resulting_amount,
                    top_up.reason.strip(),
                    top_up.actor_id,
                    top_up.actor_role,
                    json.dumps(top_up.metadata or {}, sort_keys=True),
                )

                await self._record_top_up_audit(
                    conn,
                    top_up=top_up,
                    previous_amount_cents=previous_amount,
                    resulting_amount_cents=resulting_amount,
                    adjustment_id=str(adjustment["adjustment_id"]),
                    budget_name=budget["name"],
                )

        return {
            "budget": _row_to_dict(updated_budget),
            "adjustment": _row_to_dict(adjustment),
        }

    async def check_budget(self, attribution: CostAttribution) -> BudgetDecision:
        budgets = await self._matching_budgets(attribution)
        if not budgets:
            now = datetime.now(timezone.utc)
            return BudgetDecision(
                allowed=True,
                enforcement_action="allow",
                reason="No active budget matched this request",
                projected_cost_cents=attribution.projected_cost_cents,
                current_spend_cents=0,
                budget_amount_cents=None,
                period_start=now,
                period_end=now,
                budget=None,
                warning=False,
            )

        spend_by_budget_id: dict[str, int] = {}
        for budget in budgets:
            period_start, period_end = current_period_window(budget.reset_period)
            spend_by_budget_id[budget.budget_id or f"{budget.scope_type}:{budget.scope_value}"] = await self._current_spend(
                budget=budget,
                period_start=period_start,
                period_end=period_end,
            )

        decision = evaluate_budget_set(
            budgets,
            spend_by_budget_id=spend_by_budget_id,
            projected_cost_cents=attribution.projected_cost_cents,
        )
        await self.record_enforcement(decision, attribution)
        return decision

    async def record_spend(self, attribution: CostAttribution) -> dict[str, Any]:
        if attribution.actual_cost_cents < 0:
            raise ValueError("actual_cost_cents must be greater than or equal to 0")
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_tenant_context($1)", attribution.tenant_id)
                row = await conn.fetchrow(
                    """
                    INSERT INTO cost_spend_events (
                        tenant_id, provider, model, input_tokens, output_tokens,
                        cost_cents, actor_id, project_id, api_key_id,
                        request_id, decision_id, metadata_json
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb)
                    RETURNING *
                    """,
                    attribution.tenant_id,
                    attribution.provider,
                    attribution.model,
                    attribution.input_tokens,
                    attribution.output_tokens,
                    attribution.actual_cost_cents,
                    attribution.actor_id,
                    attribution.project_id,
                    attribution.api_key_id,
                    attribution.request_id,
                    attribution.decision_id,
                    json.dumps(attribution.metadata or {}, sort_keys=True),
                )
        return _row_to_dict(row)

    async def record_enforcement(
        self,
        decision: BudgetDecision,
        attribution: CostAttribution,
    ) -> None:
        budget = decision.budget
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_tenant_context($1)", attribution.tenant_id)
                await conn.execute(
                    """
                    INSERT INTO cost_enforcement_events (
                        tenant_id, budget_id, scope_type, scope_value,
                        enforcement_action, projected_cost_cents,
                        current_spend_cents, budget_amount_cents,
                        period_start, period_end, actor_id, project_id,
                        api_key_id, request_id, decision_id, reason, context_json
                    )
                    VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                        $11, $12, $13, $14, $15, $16, $17::jsonb
                    )
                    """,
                    attribution.tenant_id,
                    budget.budget_id if budget else None,
                    budget.scope_type if budget else "tenant",
                    budget.scope_value if budget else attribution.tenant_id,
                    decision.enforcement_action,
                    decision.projected_cost_cents,
                    decision.current_spend_cents,
                    decision.budget_amount_cents,
                    decision.period_start,
                    decision.period_end,
                    attribution.actor_id,
                    attribution.project_id,
                    attribution.api_key_id,
                    attribution.request_id,
                    attribution.decision_id,
                    decision.reason,
                    json.dumps(attribution.metadata or {}, sort_keys=True),
                )

    async def get_summary(self, tenant_id: str) -> dict[str, Any]:
        budgets = await self.list_budgets(tenant_id)
        period_start, period_end = current_period_window("monthly")
        budget_usage = await self._budget_usage_summary(budgets)
        async with self.pool.acquire() as conn:
            await conn.execute("SELECT set_tenant_context($1)", tenant_id)
            monthly_spend = await conn.fetchval(
                """
                SELECT COALESCE(SUM(cost_cents), 0)
                FROM cost_spend_events
                WHERE tenant_id = $1 AND event_ts >= $2 AND event_ts < $3
                """,
                tenant_id,
                period_start,
                period_end,
            )
            recent_rows = await conn.fetch(
                """
                SELECT *
                FROM cost_spend_events
                WHERE tenant_id = $1
                ORDER BY event_ts DESC
                LIMIT 10
                """,
                tenant_id,
            )
        return {
            "monthly_spend_cents": monthly_spend or 0,
            "monthly_period_start": period_start.isoformat(),
            "monthly_period_end": period_end.isoformat(),
            "budgets": [
                {
                    **budget,
                    **budget_usage.get(str(budget["budget_id"]), {}),
                }
                for budget in budgets
            ],
            "recent_spend_events": [_row_to_dict(row) for row in recent_rows],
        }

    async def _budget_usage_summary(
        self,
        budgets: list[dict[str, Any]],
    ) -> dict[str, dict[str, int]]:
        usage: dict[str, dict[str, int]] = {}
        for row in budgets:
            budget = _budget_from_row(row)
            period_start, period_end = current_period_window(budget.reset_period)
            current_spend = await self._current_spend(
                budget=budget,
                period_start=period_start,
                period_end=period_end,
            )
            usage[str(row["budget_id"])] = {
                "current_spend_cents": current_spend,
                "remaining_cents": max(0, int(row["amount_cents"]) - current_spend),
            }
        return usage

    async def _record_top_up_audit(
        self,
        conn: Any,
        *,
        top_up: BudgetTopUp,
        previous_amount_cents: int,
        resulting_amount_cents: int,
        adjustment_id: str,
        budget_name: str,
    ) -> None:
        await conn.execute("SELECT pg_advisory_xact_lock(2)")
        await conn.execute(
            """
            INSERT INTO governance_audit_log (
                event_type, tenant_id, actor_id, payload_json,
                trace_id, initiator_role, reason, environment
            )
            VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, 'production')
            """,
            "cost.budget_top_up",
            top_up.tenant_id,
            top_up.actor_id,
            json.dumps(
                {
                    "budget_id": top_up.budget_id,
                    "budget_name": budget_name,
                    "scope_type": "tenant",
                    "scope_value": top_up.tenant_id,
                    "adjustment_id": adjustment_id,
                    "amount_cents": top_up.amount_cents,
                    "previous_amount_cents": previous_amount_cents,
                    "resulting_amount_cents": resulting_amount_cents,
                    "reason": top_up.reason.strip(),
                    "actor_role": top_up.actor_role,
                    "metadata": top_up.metadata or {},
                },
                sort_keys=True,
            ),
            f"cost-top-up:{adjustment_id}",
            top_up.actor_role,
            top_up.reason.strip(),
        )

    async def _matching_budgets(self, attribution: CostAttribution) -> list[CostBudget]:
        scope_values = matching_scope_values(attribution)
        async with self.pool.acquire() as conn:
            await conn.execute("SELECT set_tenant_context($1)", attribution.tenant_id)
            rows = await conn.fetch(
                """
                SELECT *
                FROM cost_budgets
                WHERE tenant_id = $1
                  AND is_active = TRUE
                  AND (
                    (scope_type = 'tenant' AND scope_value = $2)
                    OR (scope_type = 'project' AND scope_value = $3)
                    OR (scope_type = 'agent' AND scope_value = $4)
                    OR (scope_type = 'api_key' AND scope_value = $5)
                  )
                """,
                attribution.tenant_id,
                scope_values.get("tenant"),
                scope_values.get("project"),
                scope_values.get("agent"),
                scope_values.get("api_key"),
            )
        budgets = [_budget_from_row(row) for row in rows]
        return sorted(
            budgets,
            key=lambda budget: SCOPE_PRIORITY[budget.scope_type],
            reverse=True,
        )

    async def _current_spend(
        self,
        *,
        budget: CostBudget,
        period_start: datetime,
        period_end: datetime,
    ) -> int:
        column = {
            "tenant": "tenant_id",
            "project": "project_id",
            "agent": "actor_id",
            "api_key": "api_key_id",
        }[budget.scope_type]

        async with self.pool.acquire() as conn:
            await conn.execute("SELECT set_tenant_context($1)", budget.tenant_id)
            value = await conn.fetchval(
                f"""
                SELECT COALESCE(SUM(cost_cents), 0)
                FROM cost_spend_events
                WHERE tenant_id = $1
                  AND {column} = $2
                  AND event_ts >= $3
                  AND event_ts < $4
                """,
                budget.tenant_id,
                budget.scope_value,
                period_start,
                period_end,
            )
        return int(value or 0)


def _budget_from_row(row: Any) -> CostBudget:
    data = dict(row)
    return CostBudget(
        budget_id=str(data.get("budget_id")),
        tenant_id=data["tenant_id"],
        name=data["name"],
        scope_type=data["scope_type"],
        scope_value=data["scope_value"],
        amount_cents=int(data["amount_cents"]),
        currency=data.get("currency") or "usd",
        reset_period=data["reset_period"],
        enforcement_action=data["enforcement_action"],
        warning_threshold_percent=int(data.get("warning_threshold_percent") or 80),
        is_active=bool(data.get("is_active", True)),
    )


def _row_to_dict(row: Any) -> dict[str, Any]:
    data = dict(row)
    for key, value in list(data.items()):
        if isinstance(value, datetime):
            data[key] = value.isoformat()
        elif key.endswith("_id") and value is not None:
            data[key] = str(value)
    metadata = data.get("metadata_json") or data.get("context_json")
    if isinstance(metadata, str):
        try:
            parsed = json.loads(metadata)
        except json.JSONDecodeError:
            parsed = {}
        if "metadata_json" in data:
            data["metadata_json"] = parsed
        if "context_json" in data:
            data["context_json"] = parsed
    return data
