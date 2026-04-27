"""
Trust Audit — Append-only audit logging for trust transitions.

Every trust-driven change produces a durable audit record.
This module writes to the existing audit_events table and also
provides a convenience wrapper for trust-specific audit patterns.

All records are append-only. No updates, no deletes.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .trust_bands import TrustBand, get_transition_reason_code

logger = logging.getLogger(__name__)


class TrustAuditLogger:
    """
    Audit logger for trust-related events.

    Writes to the audit_events table with structured, queryable data.
    All methods are idempotent-safe: calling them multiple times with
    the same data produces multiple records (by design — audit is append-only).
    """

    def __init__(self, db_pool=None):
        self.db = db_pool

    async def log_band_transition(
        self,
        actor_id: str,
        tenant_id: str,
        from_band: TrustBand,
        to_band: TrustBand,
        score: float,
        snapshot_id: str,
        previous_snapshot_id: Optional[str],
        reason_code: str,
        triggering_event: Optional[str] = None,
        triggering_event_id: Optional[str] = None,
        operator_id: Optional[str] = None,
        operator_reason: Optional[str] = None,
    ) -> None:
        """
        Log a trust band transition.

        This is the primary audit event for trust changes. It captures:
        - Before/after band
        - Score at transition time
        - What triggered the change
        - Human override if present
        """
        if not self.db:
            logger.warning("No DB pool available for trust audit logging")
            return

        async with self.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_events (
                    event_type, actor, tenant_id, target, action, metadata_json, created_at
                ) VALUES (
                    'TRUST_BAND_CHANGED',
                    $1, $2, $3, $4, $5, NOW()
                )
                """,
                actor_id,
                tenant_id,
                actor_id,  # target is self for trust events
                f"{from_band.value}_to_{to_band.value}",
                json.dumps({
                    "from_band": from_band.value,
                    "to_band": to_band.value,
                    "score": round(score, 4),
                    "snapshot_id": snapshot_id,
                    "previous_snapshot_id": previous_snapshot_id,
                    "reason_code": reason_code,
                    "triggering_event": triggering_event,
                    "triggering_event_id": triggering_event_id,
                    "operator_id": operator_id,
                    "operator_reason": operator_reason,
                }),
            )

        logger.info(
            f"Trust audit: actor={actor_id} band={from_band.value} -> {to_band.value} "
            f"score={score:.4f} reason={reason_code}"
        )

    async def log_score_computed(
        self,
        actor_id: str,
        tenant_id: str,
        score: float,
        band: TrustBand,
        snapshot_id: str,
        factors: Dict[str, float],
        raw_inputs: Dict[str, Any],
        computation_method: str,
    ) -> None:
        """
        Log that a new trust snapshot was computed.

        This event is written every time a trust score is recomputed,
        even if the band did not change. It provides a full provenance
        record for the score.
        """
        if not self.db:
            return

        async with self.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_events (
                    event_type, actor, tenant_id, target, action, metadata_json, created_at
                ) VALUES (
                    'TRUST_SCORE_COMPUTED',
                    $1, $2, $3, $4, $5, NOW()
                )
                """,
                actor_id,
                tenant_id,
                actor_id,
                band.value,
                json.dumps({
                    "score": round(score, 4),
                    "band": band.value,
                    "snapshot_id": snapshot_id,
                    "factors": factors,
                    "raw_inputs": raw_inputs,
                    "computation_method": computation_method,
                }),
            )

    async def log_probation_event(
        self,
        actor_id: str,
        tenant_id: str,
        event_type: str,  # "STARTED", "ENDED", "EXTENDED", "VIOLATED"
        probation_until: Optional[datetime],
        reason: str,
        operator_id: Optional[str] = None,
    ) -> None:
        """
        Log a probation-related event.
        """
        if not self.db:
            return

        event_map = {
            "STARTED": "TRUST_PROBATION_STARTED",
            "ENDED": "TRUST_PROBATION_ENDED",
            "EXTENDED": "TRUST_PROBATION_EXTENDED",
            "VIOLATED": "TRUST_PROBATION_VIOLATED",
        }

        event_name = event_map.get(event_type, f"TRUST_PROBATION_{event_type}")

        async with self.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_events (
                    event_type, actor, tenant_id, target, action, metadata_json, created_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, NOW()
                )
                """,
                event_name,
                actor_id,
                tenant_id,
                actor_id,
                event_type,
                json.dumps({
                    "probation_until": probation_until.isoformat() if probation_until else None,
                    "reason": reason,
                    "operator_id": operator_id,
                }),
            )

    async def log_operator_override(
        self,
        actor_id: str,
        tenant_id: str,
        operator_id: str,
        from_band: TrustBand,
        to_band: TrustBand,
        reason: str,
    ) -> None:
        """
        Log a human operator manually setting a trust band.

        This is a HIGH-SEVERITY audit event. It bypasses the normal
        trust computation and must be clearly recorded.
        """
        if not self.db:
            return

        async with self.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_events (
                    event_type, actor, tenant_id, target, action, metadata_json, severity, created_at
                ) VALUES (
                    'TRUST_OVERRIDE',
                    $1, $2, $3, $4, $5, $6, NOW()
                )
                """,
                actor_id,
                tenant_id,
                actor_id,
                f"{from_band.value}_to_{to_band.value}",
                json.dumps({
                    "operator_id": operator_id,
                    "from_band": from_band.value,
                    "to_band": to_band.value,
                    "reason": reason,
                    "manual": True,
                }),
                "HIGH",  # High severity for manual overrides
            )

    async def log_circuit_breaker(
        self,
        actor_id: str,
        tenant_id: str,
        from_score: float,
        to_score: float,
        from_band: TrustBand,
        to_band: TrustBand,
        reason: str,
    ) -> None:
        """
        Log a circuit breaker activation (emergency trust drop).

        This is a CRITICAL audit event.
        """
        if not self.db:
            return

        async with self.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_events (
                    event_type, actor, tenant_id, target, action, metadata_json, severity, created_at
                ) VALUES (
                    'TRUST_CIRCUIT_BREAKER',
                    $1, $2, $3, $4, $5, $6, NOW()
                )
                """,
                actor_id,
                tenant_id,
                actor_id,
                f"{from_band.value}_to_{to_band.value}",
                json.dumps({
                    "from_score": round(from_score, 4),
                    "to_score": round(to_score, 4),
                    "from_band": from_band.value,
                    "to_band": to_band.value,
                    "reason": reason,
                    "emergency": True,
                }),
                "CRITICAL",
            )

    async def log_kill_switch_trust_drop(
        self,
        actor_id: str,
        tenant_id: str,
        previous_band: TrustBand,
        kill_switch_reason: str,
    ) -> None:
        """
        Log when a kill switch activation causes a trust band drop.

        This links the emergency system to the trust system explicitly.
        """
        if not self.db:
            return

        async with self.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_events (
                    event_type, actor, tenant_id, target, action, metadata_json, severity, created_at
                ) VALUES (
                    'TRUST_KILL_SWITCH_DROP',
                    $1, $2, $3, $4, $5, $6, NOW()
                )
                """,
                actor_id,
                tenant_id,
                actor_id,
                f"{previous_band.value}_to_revoked",
                json.dumps({
                    "previous_band": previous_band.value,
                    "kill_switch_reason": kill_switch_reason,
                    "trust_band": "REVOKED",
                }),
                "CRITICAL",
            )


__all__ = [
    "TrustAuditLogger",
]
