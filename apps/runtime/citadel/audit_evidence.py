"""Decision evidence export — tamper-evident audit bundles."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional, List
from uuid import UUID

from citadel.repository import Repository
from citadel.actions import Decision, KernelStatus


@dataclass(frozen=True)
class AuditEvent:
    """Single audit event."""

    event_id: int
    event_type: str
    actor_id: Optional[str]
    payload: Dict[str, Any]
    event_ts: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "payload": self.payload,
            "event_ts": self.event_ts.isoformat() if self.event_ts else None,
        }


@dataclass(frozen=True)
class DecisionEvidence:
    """Immutable decision evidence bundle."""

    decision_id: str
    action_id: str
    status: str
    winning_rule: str
    reason: str
    created_at: datetime
    policy_snapshot_id: Optional[str]
    audit_events: List[AuditEvent]
    root_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "action_id": self.action_id,
            "status": self.status,
            "winning_rule": self.winning_rule,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
            "policy_snapshot_id": self.policy_snapshot_id,
            "audit_events": [e.to_dict() for e in self.audit_events],
            "root_hash": self.root_hash,
        }

    def to_json(self) -> str:
        """Export as JSON."""
        return json.dumps(self.to_dict(), sort_keys=True, indent=2)

    def verify(self) -> bool:
        """Verify root hash matches current events."""
        computed = _compute_root_hash(self.audit_events)
        return computed == self.root_hash


def _compute_root_hash(events: List[AuditEvent]) -> str:
    """Compute deterministic SHA256 hash over all audit events in order."""
    h = hashlib.sha256()
    for event in events:
        event_json = json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":"))
        h.update(event_json.encode("utf-8"))
    return h.hexdigest()


class EvidenceExporter:
    """Exports decision evidence bundles from the audit log."""

    def __init__(self, repository: Repository):
        self.repo = repository

    async def export_decision(
        self,
        decision_id: str | UUID,
        tenant_id: Optional[str] = None,
    ) -> Optional[DecisionEvidence]:
        """Export all evidence for a single decision.

        Returns None if the decision does not exist.
        """
        decision_uuid = str(decision_id) if isinstance(decision_id, UUID) else decision_id

        decision = await self.repo.get_decision(decision_uuid)
        if not decision:
            return None

        action = await self.repo.get_action(decision.action_id) if decision.action_id else None
        action_id = str(decision.action_id) if decision.action_id else str(decision.action_id)

        events = await self._fetch_decision_events(decision_uuid, tenant_id)

        root_hash = _compute_root_hash(events)

        return DecisionEvidence(
            decision_id=str(decision.decision_id),
            action_id=action_id,
            status=decision.status.value,
            winning_rule=decision.winning_rule,
            reason=decision.reason,
            created_at=decision.created_at,
            policy_snapshot_id=str(decision.policy_snapshot_id) if decision.policy_snapshot_id else None,
            audit_events=events,
            root_hash=root_hash,
        )

    async def _fetch_decision_events(
        self,
        decision_id: str,
        tenant_id: Optional[str],
    ) -> List[AuditEvent]:
        """Fetch all audit events related to a decision, in chronological order."""
        rows = await self.repo.fetch_audit_events_for_decision(decision_id, tenant_id)
        events = []
        for row in rows:
            payload = row.get("payload_json") or {}
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = {}
            events.append(
                AuditEvent(
                    event_id=int(row.get("event_id", 0)),
                    event_type=row.get("event_type", "unknown"),
                    actor_id=row.get("actor_id"),
                    payload=payload,
                    event_ts=row.get("event_ts"),
                )
            )
        return events
