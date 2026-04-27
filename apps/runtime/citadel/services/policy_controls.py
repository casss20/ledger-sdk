"""Constrained no-code policy controls.

The helpers in this module generate normal runtime policies. They do not
introduce a second policy engine; every control emits deterministic
``rules_json`` consumed by ``PolicyEvaluator``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

ALLOWED_APPROVAL_PRIORITIES = {"low", "medium", "high", "critical"}


@dataclass(frozen=True)
class ApprovalThresholdControl:
    """Operator-managed threshold for routing risky actions to approval."""

    risk_score_threshold: int
    approval_priority: str = "high"
    approval_expiry_hours: int = 24
    reason: str | None = None


def validate_approval_threshold(control: ApprovalThresholdControl) -> None:
    """Validate a no-code approval-threshold control."""
    if control.risk_score_threshold < 0 or control.risk_score_threshold > 100:
        raise ValueError("risk_score_threshold must be between 0 and 100")

    if control.approval_priority not in ALLOWED_APPROVAL_PRIORITIES:
        allowed = ", ".join(sorted(ALLOWED_APPROVAL_PRIORITIES))
        raise ValueError(f"approval_priority must be one of: {allowed}")

    if control.approval_expiry_hours < 1 or control.approval_expiry_hours > 168:
        raise ValueError("approval_expiry_hours must be between 1 and 168")


def build_approval_threshold_rules(control: ApprovalThresholdControl) -> dict[str, Any]:
    """Build runtime ``rules_json`` for the approval-threshold control."""
    validate_approval_threshold(control)

    threshold = control.risk_score_threshold
    reason = control.reason or f"Risk score above {threshold} requires human approval"

    return {
        "rules": [
            {
                "name": f"approval_threshold_risk_score_gt_{threshold}",
                "effect": "PENDING_APPROVAL",
                "condition": f"risk_score > {threshold}",
                "requires_approval": True,
                "approval_priority": control.approval_priority,
                "approval_expiry_hours": control.approval_expiry_hours,
                "reason": reason,
                "risk_level": _risk_level_for_threshold(threshold),
                "risk_score": threshold + 1 if threshold < 100 else 100,
            }
        ],
        "generated_by": "no_code_approval_threshold_control",
        "control": {
            "risk_score_threshold": threshold,
            "approval_priority": control.approval_priority,
            "approval_expiry_hours": control.approval_expiry_hours,
        },
    }


def preview_approval_threshold_policy(
    control: ApprovalThresholdControl,
    *,
    tenant_id: str,
    version: str = "preview",
) -> dict[str, Any]:
    """Return the policy shape that would be stored for this control."""
    rules_json = build_approval_threshold_rules(control)
    return {
        "name": NoCodePolicyControlService.APPROVAL_THRESHOLD_POLICY_NAME,
        "version": version,
        "scope_type": "tenant",
        "scope_value": tenant_id,
        "status": "draft",
        "description": (
            "No-code control: require human approval for actions whose "
            f"risk score is greater than {control.risk_score_threshold}."
        ),
        "rules_json": rules_json,
    }


class NoCodePolicyControlService:
    """Persistence for safe no-code policy controls."""

    APPROVAL_THRESHOLD_POLICY_NAME = "No-code Approval Threshold"

    def __init__(self, pool):
        self.pool = pool

    async def get_active_approval_threshold(self, tenant_id: str) -> dict[str, Any] | None:
        """Fetch the active no-code approval-threshold policy, if configured."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT *
                FROM policies
                WHERE tenant_id = $1
                  AND name = $2
                  AND scope_type = 'tenant'
                  AND scope_value = $1
                  AND status = 'active'
                ORDER BY activated_at DESC NULLS LAST, created_at DESC
                LIMIT 1
                """,
                tenant_id,
                self.APPROVAL_THRESHOLD_POLICY_NAME,
            )
        return _policy_row_to_dict(row) if row else None

    async def apply_approval_threshold(
        self,
        tenant_id: str,
        control: ApprovalThresholdControl,
        *,
        created_by: str,
    ) -> dict[str, Any]:
        """Create and activate a new immutable approval-threshold policy version."""
        validate_approval_threshold(control)
        now = datetime.now(timezone.utc)
        version = f"approval-threshold-{now.strftime('%Y%m%d%H%M%S')}"
        preview = preview_approval_threshold_policy(
            control,
            tenant_id=tenant_id,
            version=version,
        )

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE policies
                    SET status = 'retired',
                        retired_at = NOW()
                    WHERE tenant_id = $1
                      AND name = $2
                      AND scope_type = 'tenant'
                      AND scope_value = $1
                      AND status = 'active'
                    """,
                    tenant_id,
                    self.APPROVAL_THRESHOLD_POLICY_NAME,
                )

                row = await conn.fetchrow(
                    """
                    INSERT INTO policies (
                        tenant_id, name, version, scope_type, scope_value,
                        rules_json, status, description, created_by, activated_at
                    )
                    VALUES ($1, $2, $3, 'tenant', $1, $4::jsonb, 'active', $5, $6, NOW())
                    RETURNING *
                    """,
                    tenant_id,
                    preview["name"],
                    version,
                    json.dumps(preview["rules_json"], sort_keys=True),
                    preview["description"],
                    created_by,
                )

        return _policy_row_to_dict(row)


def _policy_row_to_dict(row: Any) -> dict[str, Any]:
    policy = dict(row)
    rules_json = policy.get("rules_json")
    if isinstance(rules_json, str):
        policy["rules_json"] = json.loads(rules_json)
    return policy


def _risk_level_for_threshold(threshold: int) -> str:
    if threshold >= 90:
        return "critical"
    if threshold >= 70:
        return "high"
    if threshold >= 40:
        return "medium"
    return "low"
