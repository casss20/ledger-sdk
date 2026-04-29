"""Decision evidence export and verification."""

import uuid
from datetime import datetime, timezone

import pytest

from citadel.audit_evidence import (
    AuditEvent,
    DecisionEvidence,
    _compute_root_hash,
)


def test_audit_event_to_dict():
    """AuditEvent.to_dict() returns canonical JSON-serializable dict."""
    now = datetime(2026, 4, 29, 12, 0, 0, tzinfo=timezone.utc)
    event = AuditEvent(
        event_id=1,
        event_type="decision_made",
        actor_id="system",
        payload={"decision_id": "abc123", "status": "executed"},
        event_ts=now,
    )
    d = event.to_dict()
    assert d["event_id"] == 1
    assert d["event_type"] == "decision_made"
    assert d["actor_id"] == "system"
    assert d["payload"] == {"decision_id": "abc123", "status": "executed"}
    assert d["event_ts"] == "2026-04-29T12:00:00+00:00"


def test_compute_root_hash_deterministic():
    """Root hash is deterministic over the same event sequence."""
    events = [
        AuditEvent(
            event_id=1,
            event_type="action_received",
            actor_id=None,
            payload={"action": "test"},
            event_ts=datetime(2026, 4, 29, 12, 0, 0, tzinfo=timezone.utc),
        ),
        AuditEvent(
            event_id=2,
            event_type="decision_made",
            actor_id="kernel",
            payload={"status": "executed"},
            event_ts=datetime(2026, 4, 29, 12, 0, 1, tzinfo=timezone.utc),
        ),
    ]
    hash1 = _compute_root_hash(events)
    hash2 = _compute_root_hash(events)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex is 64 chars


def test_compute_root_hash_order_matters():
    """Changing event order changes the root hash."""
    now = datetime(2026, 4, 29, 12, 0, 0, tzinfo=timezone.utc)
    event1 = AuditEvent(
        event_id=1,
        event_type="action_received",
        actor_id=None,
        payload={"a": 1},
        event_ts=now,
    )
    event2 = AuditEvent(
        event_id=2,
        event_type="decision_made",
        actor_id="kernel",
        payload={"b": 2},
        event_ts=now,
    )
    hash_forward = _compute_root_hash([event1, event2])
    hash_reverse = _compute_root_hash([event2, event1])
    assert hash_forward != hash_reverse


def test_decision_evidence_verify_valid():
    """DecisionEvidence.verify() returns True when hash matches."""
    now = datetime(2026, 4, 29, 12, 0, 0, tzinfo=timezone.utc)
    events = [
        AuditEvent(
            event_id=1,
            event_type="action_received",
            actor_id=None,
            payload={},
            event_ts=now,
        )
    ]
    root_hash = _compute_root_hash(events)

    evidence = DecisionEvidence(
        decision_id="dec-1",
        action_id="act-1",
        status="executed",
        winning_rule="policy_allow",
        reason="OK",
        created_at=now,
        policy_snapshot_id="snap-1",
        audit_events=events,
        root_hash=root_hash,
    )

    assert evidence.verify() is True


def test_decision_evidence_verify_tampered():
    """DecisionEvidence.verify() returns False if events were modified."""
    now = datetime(2026, 4, 29, 12, 0, 0, tzinfo=timezone.utc)
    events = [
        AuditEvent(
            event_id=1,
            event_type="action_received",
            actor_id=None,
            payload={},
            event_ts=now,
        )
    ]
    root_hash = _compute_root_hash(events)

    modified_events = [
        AuditEvent(
            event_id=1,
            event_type="action_received",
            actor_id=None,
            payload={"tampered": True},  # Modified payload
            event_ts=now,
        )
    ]

    evidence = DecisionEvidence(
        decision_id="dec-1",
        action_id="act-1",
        status="executed",
        winning_rule="policy_allow",
        reason="OK",
        created_at=now,
        policy_snapshot_id="snap-1",
        audit_events=modified_events,
        root_hash=root_hash,
    )

    assert evidence.verify() is False


def test_decision_evidence_to_dict():
    """DecisionEvidence.to_dict() includes all fields."""
    now = datetime(2026, 4, 29, 12, 0, 0, tzinfo=timezone.utc)
    events = [
        AuditEvent(
            event_id=1,
            event_type="decision_made",
            actor_id="kernel",
            payload={"status": "executed"},
            event_ts=now,
        )
    ]
    root_hash = _compute_root_hash(events)

    evidence = DecisionEvidence(
        decision_id=str(uuid.uuid4()),
        action_id=str(uuid.uuid4()),
        status="executed",
        winning_rule="policy_allow",
        reason="OK",
        created_at=now,
        policy_snapshot_id=str(uuid.uuid4()),
        audit_events=events,
        root_hash=root_hash,
    )

    d = evidence.to_dict()
    assert "decision_id" in d
    assert "action_id" in d
    assert "status" in d
    assert "winning_rule" in d
    assert "reason" in d
    assert "created_at" in d
    assert "policy_snapshot_id" in d
    assert "audit_events" in d
    assert len(d["audit_events"]) == 1
    assert "root_hash" in d
    assert d["root_hash"] == root_hash


def test_decision_evidence_to_json():
    """DecisionEvidence.to_json() returns valid JSON."""
    now = datetime(2026, 4, 29, 12, 0, 0, tzinfo=timezone.utc)
    events = [
        AuditEvent(
            event_id=1,
            event_type="decision_made",
            actor_id="kernel",
            payload={"status": "executed"},
            event_ts=now,
        )
    ]
    root_hash = _compute_root_hash(events)

    evidence = DecisionEvidence(
        decision_id="dec-1",
        action_id="act-1",
        status="executed",
        winning_rule="policy_allow",
        reason="OK",
        created_at=now,
        policy_snapshot_id="snap-1",
        audit_events=events,
        root_hash=root_hash,
    )

    json_str = evidence.to_json()
    assert "dec-1" in json_str
    assert "decision_made" in json_str
    assert root_hash in json_str
