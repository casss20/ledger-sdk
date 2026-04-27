import hashlib
import hmac
import time
import logging
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

from .trust_bands import (
    TrustBand,
    PROBATION_CONFIG,
    TRUST_FACTOR_WEIGHTS,
    get_band_constraints,
    is_band_transition_allowed,
    get_transition_reason_code,
)
from .trust_audit import TrustAuditLogger


logger = logging.getLogger(__name__)


class TrustLevel(Enum):
    """DEPRECATED: Use TrustBand instead. Kept for backward compatibility."""
    REVOKED = "revoked"
    UNVERIFIED = "unverified"
    STANDARD = "standard"
    TRUSTED = "trusted"
    HIGHLY_TRUSTED = "highly_trusted"

    def to_trust_band(self) -> TrustBand:
        """Map deprecated TrustLevel to new TrustBand."""
        mapping = {
            TrustLevel.REVOKED: TrustBand.REVOKED,
            TrustLevel.UNVERIFIED: TrustBand.PROBATION,
            TrustLevel.STANDARD: TrustBand.STANDARD,
            TrustLevel.TRUSTED: TrustBand.TRUSTED,
            TrustLevel.HIGHLY_TRUSTED: TrustBand.HIGHLY_TRUSTED,
        }
        return mapping[self]


@dataclass
class TrustScore:
    """Computed trust score for an agent."""
    agent_id: str
    score: float  # 0.0 to 1.0
    level: TrustBand
    factors: Dict[str, float] = field(default_factory=dict)
    snapshot_id: Optional[str] = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "score": round(self.score, 3),
            "level": self.level.value,
            "factors": self.factors,
            "snapshot_id": self.snapshot_id,
            "updated_at": self.updated_at.isoformat() + "Z",
        }


class TrustSnapshotEngine:
    """
    Computes trust scores and stores them as append-only snapshots.

    This replaces the old TrustScorer that overwrote agent_identities.metadata.
    Every computation produces a new row in actor_trust_snapshots.

    Features:
    - Deterministic score computation from raw inputs
    - Automatic band mapping with explicit thresholds
    - Probation management
    - Audit logging for all transitions
    - Backward compatibility with existing TrustScorer API
    """

    def __init__(self, db_pool=None):
        self.db = db_pool
        self.audit = TrustAuditLogger(db_pool)

    # ── Public API ───────────────────────────────────────────────────────

    async def compute_and_store(
        self,
        agent_id: str,
        tenant_id: str = "dev_tenant",
        computation_method: str = "batch",
        triggering_event: Optional[str] = None,
        triggering_event_id: Optional[str] = None,
        operator_id: Optional[str] = None,
        operator_reason: Optional[str] = None,
    ) -> TrustScore:
        """
        Compute trust score for an agent and store as a new snapshot.

        This is the primary method for trust computation. It:
        1. Fetches raw inputs from agents + agent_identities tables
        2. Computes score deterministically
        3. Determines band from score
        4. Checks probation status
        5. Creates a new snapshot row
        6. Updates the agents.trust_band cache
        7. Audits the transition (if band changed)
        8. Returns the TrustScore with snapshot_id
        """
        if not self.db:
            logger.warning("No DB pool available for trust computation")
            return TrustScore(
                agent_id=agent_id,
                score=0.0,
                level=TrustBand.REVOKED,
            )

        # 1. Fetch raw inputs
        raw_inputs = await self._fetch_raw_inputs(agent_id)

        if raw_inputs is None:
            logger.warning(f"Agent {agent_id} not found, returning REVOKED")
            return TrustScore(agent_id=agent_id, score=0.0, level=TrustBand.REVOKED)

        # 2. Compute score
        score, factors = self._compute_score(raw_inputs)

        # 3. Determine band
        new_band = TrustBand.from_score(score)

        # 4. Check probation
        probation_until = raw_inputs.get("probation_until")
        probation_active = False
        if probation_until and probation_until > datetime.now(timezone.utc):
            probation_active = True
            new_band = TrustBand.PROBATION

        # 5. Get previous snapshot for transition detection
        previous_snapshot = await self._get_previous_snapshot(agent_id)

        # 6. Create new snapshot
        snapshot_id = await self._create_snapshot(
            agent_id=agent_id,
            tenant_id=tenant_id,
            score=score,
            band=new_band,
            probation_until=probation_until,
            probation_reason=raw_inputs.get("probation_reason"),
            factors=factors,
            raw_inputs=raw_inputs,
            computation_method=computation_method,
            triggering_event=triggering_event,
            triggering_event_id=triggering_event_id,
            operator_id=operator_id,
            operator_reason=operator_reason,
            supersedes_snapshot_id=previous_snapshot.get("snapshot_id") if previous_snapshot else None,
        )

        # 7. Update agents.trust_band cache
        await self._update_agent_cache(agent_id, new_band.value, probation_until)

        # 8. Audit transition if band changed
        if previous_snapshot:
            old_band = TrustBand(previous_snapshot.get("band", "standard").lower())
            if old_band != new_band:
                reason_code = get_transition_reason_code(old_band, new_band, score, factors)
                await self.audit.log_band_transition(
                    actor_id=agent_id,
                    tenant_id=tenant_id,
                    from_band=old_band,
                    to_band=new_band,
                    score=score,
                    snapshot_id=str(snapshot_id),
                    previous_snapshot_id=str(previous_snapshot["snapshot_id"]),
                    reason_code=reason_code,
                    triggering_event=triggering_event,
                    triggering_event_id=triggering_event_id,
                    operator_id=operator_id,
                    operator_reason=operator_reason,
                )

        # 9. Audit score computation
        await self.audit.log_score_computed(
            actor_id=agent_id,
            tenant_id=tenant_id,
            score=score,
            band=new_band,
            snapshot_id=str(snapshot_id),
            factors=factors,
            raw_inputs=raw_inputs,
            computation_method=computation_method,
        )

        return TrustScore(
            agent_id=agent_id,
            score=score,
            level=new_band,
            factors=factors,
            snapshot_id=str(snapshot_id),
        )

    async def evaluate_all(
        self,
        tenant_id: str = "dev_tenant",
        batch_size: int = 100,
    ) -> Dict[str, TrustScore]:
        """
        Evaluate trust scores for all agents in batches.

        Safe for large datasets — processes in chunks to avoid long transactions.
        """
        if not self.db:
            return {}

        scores = {}
        offset = 0

        while True:
            async with self.db.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT agent_id FROM agents ORDER BY agent_id LIMIT $1 OFFSET $2",
                    batch_size,
                    offset,
                )

            if not rows:
                break

            for row in rows:
                score = await self.compute_and_store(
                    agent_id=row["agent_id"],
                    tenant_id=tenant_id,
                    computation_method="batch",
                )
                scores[row["agent_id"]] = score

            offset += batch_size
            logger.info(f"Trust batch evaluated: {offset} agents processed")

        return scores

    async def operator_override(
        self,
        agent_id: str,
        tenant_id: str,
        operator_id: str,
        target_band: TrustBand,
        reason: str,
    ) -> TrustScore:
        """
        Human operator manually sets a trust band.

        This creates a snapshot with computation_method='override'.
        The operator's action is logged as a HIGH severity audit event.
        """
        # Get previous snapshot for transition detection
        previous_snapshot = await self._get_previous_snapshot(agent_id)
        old_band = TrustBand(previous_snapshot["band"]) if previous_snapshot else TrustBand.STANDARD

        # Create override snapshot
        snapshot_id = await self._create_snapshot(
            agent_id=agent_id,
            tenant_id=tenant_id,
            score=target_band.min_score + 0.01,  # Midpoint of band
            band=target_band,
            probation_until=None,
            probation_reason=f"Operator override: {reason}",
            factors={"operator_override": 1.0},
            raw_inputs={"operator_id": operator_id, "reason": reason},
            computation_method="override",
            operator_id=operator_id,
            operator_reason=reason,
            supersedes_snapshot_id=previous_snapshot.get("snapshot_id") if previous_snapshot else None,
        )

        # Update cache
        await self._update_agent_cache(agent_id, target_band.value, None)

        # Audit
        await self.audit.log_operator_override(
            actor_id=agent_id,
            tenant_id=tenant_id,
            operator_id=operator_id,
            from_band=old_band,
            to_band=target_band,
            reason=reason,
        )

        return TrustScore(
            agent_id=agent_id,
            score=target_band.min_score + 0.01,
            level=target_band,
            snapshot_id=str(snapshot_id),
        )

    # ── Private: Score Computation ───────────────────────────────────────

    async def _fetch_raw_inputs(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Fetch all raw inputs needed for trust computation."""
        if not self.db:
            return None

        async with self.db.acquire() as conn:
            # Get agent behavior data
            agent = await conn.fetchrow(
                "SELECT * FROM agents WHERE agent_id = $1",
                agent_id,
            )

            if not agent:
                return None

            # Get identity metadata
            identity = await conn.fetchrow(
                "SELECT * FROM agent_identities WHERE agent_id = $1",
                agent_id,
            )

            # Count recent violations (7 days)
            violations = await conn.fetchval(
                """
                SELECT COUNT(*) FROM audit_events
                WHERE actor = $1
                AND action LIKE '%violation%'
                AND created_at > NOW() - INTERVAL '7 days'
                """,
                agent_id,
            )

            # Count total recent audit events (for action rate context)
            total_events = await conn.fetchval(
                """
                SELECT COUNT(*) FROM audit_events
                WHERE actor = $1
                AND created_at > NOW() - INTERVAL '7 days'
                """,
                agent_id,
            )

            # Get previous snapshot for trend analysis
            prev = await conn.fetchrow(
                """
                SELECT score, band, computed_at
                FROM actor_trust_snapshots
                WHERE actor_id = $1 AND valid_until IS NULL
                ORDER BY computed_at DESC
                LIMIT 1
                """,
                agent_id,
            )

        return {
            "agent_id": agent_id,
            "health_score": agent.get("health_score", 100),
            "quarantined": agent.get("quarantined", False),
            "actions_today": agent.get("actions_today", 0),
            "token_spend": agent.get("token_spend", 0),
            "token_budget": agent.get("token_budget", 100000),
            "compliance_tags": agent.get("compliance", []),
            "created_at": agent.get("created_at"),
            "probation_until": agent.get("probation_until"),
            "probation_reason": agent.get("probation_reason"),
            "identity_verified": identity.get("verification_status") == "verified" if identity else False,
            "identity_created_at": identity.get("created_at") if identity else agent.get("created_at"),
            "failed_challenges": identity.get("failed_challenges", 0) if identity else 0,
            "challenge_count": identity.get("challenge_count", 0) if identity else 0,
            "violations_7d": violations or 0,
            "total_events_7d": total_events or 0,
            "previous_score": prev.get("score") if prev else None,
            "previous_band": prev.get("band") if prev else None,
        }

    def _compute_score(self, raw_inputs: Dict[str, Any]) -> tuple[float, Dict[str, float]]:
        """
        Deterministic trust score computation from raw inputs.

        This is the heart of the trust engine. It must be:
        - Fully deterministic: same inputs always produce same output
        - Documented: every factor is explained
        - Bounded: score always in [0.0, 1.0]
        - Verifiable: factors sum to the score
        """
        factors = {}

        # 1. Verification (weight: 0.25)
        if raw_inputs.get("identity_verified", False):
            factors["verification"] = 0.25
        else:
            factors["verification"] = 0.0

        # 2. Age of identity (weight: 0.15, max)
        created_at = raw_inputs.get("identity_created_at")
        if created_at:
            age_days = (datetime.now(timezone.utc) - created_at).days
            age_bonus = min(age_days * 0.005, 0.15)  # 0.5% per day, cap at 30 days
            factors["age"] = age_bonus
        else:
            factors["age"] = 0.0

        # 3. Health score (weight: 0.20)
        health_score = raw_inputs.get("health_score", 100)
        factors["health"] = (health_score / 100.0) * 0.20

        # 4. Quarantine (weight: 0.10)
        if raw_inputs.get("quarantined", False):
            factors["quarantine"] = -0.30  # Major penalty
        else:
            factors["quarantine"] = 0.10

        # 5. Action rate (weight: 0.10)
        actions_today = raw_inputs.get("actions_today", 0)
        if actions_today > 1000:
            factors["action_rate"] = -0.10  # Suspicious volume
        elif actions_today > 100:
            factors["action_rate"] = 0.05
        else:
            factors["action_rate"] = 0.10

        # 6. Compliance (weight: 0.15)
        violations = raw_inputs.get("violations_7d", 0)
        if violations == 0:
            factors["compliance"] = 0.15
        elif violations < 3:
            factors["compliance"] = 0.05
        else:
            factors["compliance"] = -0.15

        # 7. Budget adherence (weight: 0.05)
        token_budget = raw_inputs.get("token_budget", 100000)
        if token_budget > 0:
            budget_ratio = raw_inputs.get("token_spend", 0) / token_budget
            if budget_ratio > 0.9:
                factors["budget_adherence"] = -0.05
            else:
                factors["budget_adherence"] = 0.05
        else:
            factors["budget_adherence"] = 0.0

        # 8. Challenge reliability (bonus, not in core weights)
        challenge_count = raw_inputs.get("challenge_count", 0)
        failed_challenges = raw_inputs.get("failed_challenges", 0)
        if challenge_count > 0:
            fail_rate = failed_challenges / max(challenge_count, 1)
            if fail_rate > 0.5:
                factors["challenge_reliability"] = -0.05
            else:
                factors["challenge_reliability"] = 0.05
        else:
            factors["challenge_reliability"] = 0.0

        # 9. Trend bonus/penalty (small, based on previous score)
        previous_score = raw_inputs.get("previous_score")
        if previous_score is not None:
            score_diff = sum(factors.values()) - previous_score
            if score_diff < -0.15:
                # Rapid drop — small additional penalty for instability
                factors["trend"] = -0.03
            elif score_diff > 0.15:
                # Rapid improvement — small bonus for recovery
                factors["trend"] = 0.02
            else:
                factors["trend"] = 0.0
        else:
            factors["trend"] = 0.0

        # Compute total score
        score = sum(factors.values())
        score = max(0.0, min(1.0, score))

        return score, factors

    # ── Private: Snapshot Management ─────────────────────────────────────

    async def _get_previous_snapshot(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get the currently active snapshot for an agent."""
        if not self.db:
            return None

        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT snapshot_id, score, band, computed_at, factors
                FROM actor_trust_snapshots
                WHERE actor_id = $1 AND valid_until IS NULL
                ORDER BY computed_at DESC
                LIMIT 1
                """,
                agent_id,
            )
            return dict(row) if row else None

    async def _create_snapshot(
        self,
        agent_id: str,
        tenant_id: str,
        score: float,
        band: TrustBand,
        probation_until: Optional[datetime],
        probation_reason: Optional[str],
        factors: Dict[str, float],
        raw_inputs: Dict[str, Any],
        computation_method: str,
        triggering_event: Optional[str] = None,
        triggering_event_id: Optional[str] = None,
        operator_id: Optional[str] = None,
        operator_reason: Optional[str] = None,
        supersedes_snapshot_id: Optional[Any] = None,
    ) -> Any:
        """Create a new trust snapshot and expire the previous one."""
        if not self.db:
            raise RuntimeError("DB pool required for snapshot creation")

        async with self.db.acquire() as conn:
            # Expire previous snapshot (if any)
            if supersedes_snapshot_id:
                await conn.execute(
                    """
                    UPDATE actor_trust_snapshots
                    SET valid_until = NOW(),
                        superseded_reason = $2
                    WHERE snapshot_id = $1
                    """,
                    supersedes_snapshot_id,
                    f"Superseded by new computation ({computation_method})",
                )

            # Insert new snapshot
            row = await conn.fetchrow(
                """
                INSERT INTO actor_trust_snapshots (
                    actor_id, tenant_id, score, band,
                    probation_until, probation_reason,
                    factors, raw_inputs, computation_method,
                    triggering_event, triggering_event_id,
                    operator_id, operator_reason,
                    supersedes_snapshot_id, valid_from
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, NOW()
                )
                RETURNING snapshot_id
                """,
                agent_id,
                tenant_id,
                score,
                band.value,
                probation_until,
                probation_reason,
                factors,
                raw_inputs,
                computation_method,
                triggering_event,
                triggering_event_id,
                operator_id,
                operator_reason,
                supersedes_snapshot_id,
            )

            return row["snapshot_id"]

    async def _update_agent_cache(
        self,
        agent_id: str,
        trust_band: str,
        probation_until: Optional[datetime],
    ) -> None:
        """Update the denormalized trust_band cache on agents table."""
        if not self.db:
            return

        async with self.db.acquire() as conn:
            await conn.execute(
                """
                UPDATE agents
                SET trust_band = $2,
                    probation_until = $3,
                    updated_at = NOW()
                WHERE agent_id = $1
                """,
                agent_id,
                trust_band,
                probation_until,
            )


# ── Backward Compatibility ─────────────────────────────────────────────────
# The old TrustScorer class is preserved but delegates to TrustSnapshotEngine.
# It is DEPRECATED and will be removed in a future release.


class TrustScorer:
    """
    DEPRECATED: Use TrustSnapshotEngine instead.

    This class is kept for backward compatibility with existing code.
    All methods now delegate to TrustSnapshotEngine.
    """

    def __init__(self, db_pool=None):
        self.engine = TrustSnapshotEngine(db_pool)
        self.db = db_pool

    async def calculate_score(self, agent_id: str) -> TrustScore:
        """DEPRECATED: Use TrustSnapshotEngine.compute_and_store()."""
        return await self.engine.compute_and_store(agent_id)

    async def update_trust_level(self, agent_id: str) -> TrustScore:
        """DEPRECATED: Use TrustSnapshotEngine.compute_and_store()."""
        return await self.engine.compute_and_store(agent_id)

    async def get_trust_score(self, agent_id: str) -> Optional[TrustScore]:
        """DEPRECATED: Use TrustSnapshotEngine.compute_and_store()."""
        return await self.engine.compute_and_store(agent_id)

    async def evaluate_all(self) -> Dict[str, TrustScore]:
        """DEPRECATED: Use TrustSnapshotEngine.evaluate_all()."""
        return await self.engine.evaluate_all()

    @staticmethod
    def compute_score(
        verified: bool,
        health_score: int,
        quarantined: bool,
        actions_today: int,
        token_spend: int,
        token_budget: int,
        compliance_tags: list,
        created_at: datetime,
        failed_challenges: int = 0,
        challenge_count: int = 0,
    ) -> tuple[float, TrustLevel, Dict[str, float]]:
        """
        DEPRECATED: Use TrustSnapshotEngine._compute_score() or TrustBand.from_score().

        Kept for backward compatibility with callers that compute synchronously.
        """
        # Build raw inputs dict
        raw_inputs = {
            "identity_verified": verified,
            "health_score": health_score,
            "quarantined": quarantined,
            "actions_today": actions_today,
            "token_spend": token_spend,
            "token_budget": token_budget,
            "compliance_tags": compliance_tags,
            "created_at": created_at,
            "failed_challenges": failed_challenges,
            "challenge_count": challenge_count,
            "violations_7d": 0,
        }

        engine = TrustSnapshotEngine(None)
        score, factors = engine._compute_score(raw_inputs)
        band = TrustBand.from_score(score)

        # Map back to deprecated TrustLevel
        level_map = {
            TrustBand.REVOKED: TrustLevel.REVOKED,
            TrustBand.PROBATION: TrustLevel.UNVERIFIED,
            TrustBand.STANDARD: TrustLevel.STANDARD,
            TrustBand.TRUSTED: TrustLevel.TRUSTED,
            TrustBand.HIGHLY_TRUSTED: TrustLevel.HIGHLY_TRUSTED,
        }
        level = level_map[band]

        return score, level, factors


__all__ = [
    "TrustBand",
    "TrustLevel",
    "TrustScore",
    "TrustSnapshotEngine",
    "TrustScorer",
]
