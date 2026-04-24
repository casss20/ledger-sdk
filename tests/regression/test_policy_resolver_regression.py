"""
Regression tests for policy resolver dict-condition bug.

Issue: Policy rules stored with dict conditions (e.g. {"always": true})
cause crashes in _eval_condition which expects string conditions.
"""

import pytest
import uuid
from datetime import datetime

from CITADEL.actions import Action
from CITADEL.policy_resolver import PolicyEvaluator, PolicySnapshot


def test_dict_condition_always_true():
    """Given: Policy rule with condition={"always": true}. When: Evaluated. Then: Should match."""
    ev = PolicyEvaluator()
    snap = PolicySnapshot(
        snapshot_id=uuid.uuid4(),
        policy_id=uuid.uuid4(),
        policy_version="1.0",
        snapshot_hash="abc",
        snapshot_json={
            "rules": [
                {
                    "name": "needs_approval",
                    "effect": "PENDING_APPROVAL",
                    "condition": {"always": True},
                }
            ]
        },
    )
    action = Action(
        action_id=uuid.uuid4(),
        actor_id="test",
        actor_type="agent",
        action_name="test.approve",
        resource="test",
        tenant_id=None,
        payload={},
        context={},
        session_id=None,
        request_id=None,
        idempotency_key=None,
        created_at=datetime.now(),
    )
    result = ev.evaluate(snap, action, {})
    assert result.matched is True
    assert result.effect == "PENDING_APPROVAL"
    assert result.rule_name == "needs_approval"


def test_dict_condition_always_false():
    """Given: Policy rule with condition={"always": false}. When: Evaluated. Then: Should NOT match."""
    ev = PolicyEvaluator()
    snap = PolicySnapshot(
        snapshot_id=uuid.uuid4(),
        policy_id=uuid.uuid4(),
        policy_version="1.0",
        snapshot_hash="abc",
        snapshot_json={
            "rules": [
                {
                    "name": "needs_approval",
                    "effect": "PENDING_APPROVAL",
                    "condition": {"always": False},
                }
            ]
        },
    )
    action = Action(
        action_id=uuid.uuid4(),
        actor_id="test",
        actor_type="agent",
        action_name="test.approve",
        resource="test",
        tenant_id=None,
        payload={},
        context={},
        session_id=None,
        request_id=None,
        idempotency_key=None,
        created_at=datetime.now(),
    )
    result = ev.evaluate(snap, action, {})
    assert result.matched is True  # default_allow fallback
    assert result.rule_name == "default_allow"


def test_dict_condition_unknown_key():
    """Given: Dict condition with unknown key. When: Evaluated. Then: Should NOT match (fail closed)."""
    ev = PolicyEvaluator()
    snap = PolicySnapshot(
        snapshot_id=uuid.uuid4(),
        policy_id=uuid.uuid4(),
        policy_version="1.0",
        snapshot_hash="abc",
        snapshot_json={
            "rules": [
                {
                    "name": "bad_rule",
                    "effect": "BLOCK",
                    "condition": {"unknown_key": "whatever"},
                }
            ]
        },
    )
    action = Action(
        action_id=uuid.uuid4(),
        actor_id="test",
        actor_type="agent",
        action_name="test.action",
        resource="test",
        tenant_id=None,
        payload={},
        context={},
        session_id=None,
        request_id=None,
        idempotency_key=None,
        created_at=datetime.now(),
    )
    result = ev.evaluate(snap, action, {})
    # Should fall through to default_allow because the rule didn't match
    assert result.matched is True
    assert result.rule_name == "default_allow"


def test_string_condition_still_works():
    """Guardrail: string conditions (original format) must still work."""
    ev = PolicyEvaluator()
    snap = PolicySnapshot(
        snapshot_id=uuid.uuid4(),
        policy_id=uuid.uuid4(),
        policy_version="1.0",
        snapshot_hash="abc",
        snapshot_json={
            "rules": [
                {"name": "block_test", "effect": "BLOCK", "condition": "true"}
            ]
        },
    )
    action = Action(
        action_id=uuid.uuid4(),
        actor_id="test",
        actor_type="agent",
        action_name="test.action",
        resource="test",
        tenant_id=None,
        payload={},
        context={},
        session_id=None,
        request_id=None,
        idempotency_key=None,
        created_at=datetime.now(),
    )
    result = ev.evaluate(snap, action, {})
    assert result.matched is True
    assert result.effect == "BLOCK"
    assert result.rule_name == "block_test"
