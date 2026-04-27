import uuid
from datetime import datetime

import pytest
from citadel.actions import Action
from citadel.policy_resolver import PolicyEvaluator, PolicySnapshot
from citadel.services.policy_controls import (
    ApprovalThresholdControl,
    build_approval_threshold_rules,
    preview_approval_threshold_policy,
    validate_approval_threshold,
)


def _action() -> Action:
    return Action(
        action_id=uuid.uuid4(),
        actor_id="agent_1",
        actor_type="agent",
        action_name="email.send",
        resource="customer_email",
        tenant_id="test_tenant",
        payload={},
        context={},
        session_id=None,
        request_id=None,
        idempotency_key=None,
        created_at=datetime.now(),
    )


def _snapshot(rules_json: dict) -> PolicySnapshot:
    return PolicySnapshot(
        snapshot_id=uuid.uuid4(),
        policy_id=uuid.uuid4(),
        policy_version="approval-threshold-test",
        snapshot_hash="abc",
        snapshot_json=rules_json,
    )


def test_approval_threshold_generates_runtime_policy_rule():
    control = ApprovalThresholdControl(
        risk_score_threshold=70,
        approval_priority="high",
        approval_expiry_hours=12,
        reason="High-risk action requires review",
    )

    rules_json = build_approval_threshold_rules(control)
    rule = rules_json["rules"][0]

    assert rule["effect"] == "PENDING_APPROVAL"
    assert rule["condition"] == "risk_score > 70"
    assert rule["requires_approval"] is True
    assert rule["approval_priority"] == "high"
    assert rule["approval_expiry_hours"] == 12


def test_approval_threshold_matches_existing_policy_evaluator():
    control = ApprovalThresholdControl(risk_score_threshold=70)
    evaluator = PolicyEvaluator()

    result = evaluator.evaluate(
        _snapshot(build_approval_threshold_rules(control)),
        _action(),
        {"risk_score": 71},
    )

    assert result.matched is True
    assert result.effect == "PENDING_APPROVAL"
    assert result.requires_approval is True
    assert result.rule_name == "approval_threshold_risk_score_gt_70"


def test_approval_threshold_does_not_match_at_or_below_threshold():
    control = ApprovalThresholdControl(risk_score_threshold=70)
    evaluator = PolicyEvaluator()

    result = evaluator.evaluate(
        _snapshot(build_approval_threshold_rules(control)),
        _action(),
        {"risk_score": 70},
    )

    assert result.matched is True
    assert result.rule_name == "default_allow"


@pytest.mark.parametrize(
    "control, message",
    [
        (ApprovalThresholdControl(risk_score_threshold=-1), "risk_score_threshold"),
        (ApprovalThresholdControl(risk_score_threshold=101), "risk_score_threshold"),
        (
            ApprovalThresholdControl(risk_score_threshold=50, approval_priority="urgent"),
            "approval_priority",
        ),
        (
            ApprovalThresholdControl(risk_score_threshold=50, approval_expiry_hours=0),
            "approval_expiry_hours",
        ),
        (
            ApprovalThresholdControl(risk_score_threshold=50, approval_expiry_hours=169),
            "approval_expiry_hours",
        ),
    ],
)
def test_approval_threshold_validation_rejects_unsafe_values(control, message):
    with pytest.raises(ValueError, match=message):
        validate_approval_threshold(control)


def test_preview_uses_tenant_scope_and_draft_status():
    preview = preview_approval_threshold_policy(
        ApprovalThresholdControl(risk_score_threshold=85),
        tenant_id="tenant_a",
    )

    assert preview["name"] == "No-code Approval Threshold"
    assert preview["scope_type"] == "tenant"
    assert preview["scope_value"] == "tenant_a"
    assert preview["status"] == "draft"
    assert preview["rules_json"]["control"]["risk_score_threshold"] == 85
