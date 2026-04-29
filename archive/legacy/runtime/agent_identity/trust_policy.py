"""
Trust Policy Engine — Integrates trust bands into governance policy.

This module is the bridge between trust scores and policy decisions.
It does NOT replace the policy engine. It enriches the policy context
with trust-derived constraints that the policy engine evaluates.

Key design principles:
1. Trust bands modify policy CONTEXT, not policy RULES.
2. The policy engine remains the sole authority on ALLOW/DENY.
3. Trust bands add constraints (approval requirements, rate limits, etc.).
4. Trust never overrides lineage, entitlements, or kill switches.
5. Every trust influence on a decision is recorded in the decision context.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .trust_bands import (
    TrustBand,
    BandConstraints,
    BAND_CONSTRAINTS,
    PROBATION_CONFIG,
    get_band_constraints,
    is_band_transition_allowed,
    get_transition_reason_code,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TrustPolicyContext:
    """
    Trust-derived constraints added to the policy evaluation context.

    This object is passed to the policy backend as part of the context dict.
    It is immutable (frozen) so it cannot be modified during evaluation.
    """
    band: TrustBand
    score: float
    snapshot_id: Optional[str] = None
    probation_active: bool = False
    probation_until: Optional[datetime] = None
    probation_reason: Optional[str] = None
    constraints: BandConstraints = field(default_factory=lambda: BAND_CONSTRAINTS[TrustBand.STANDARD])

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for policy engine context."""
        return {
            "trust_band": self.band.value,
            "trust_score": round(self.score, 4),
            "trust_snapshot_id": self.snapshot_id,
            "trust_probation_active": self.probation_active,
            "trust_probation_until": self.probation_until.isoformat() if self.probation_until else None,
            "trust_probation_reason": self.probation_reason,
            "trust_constraints": self.constraints.to_dict(),
        }


@dataclass(frozen=True)
class TrustPolicyResult:
    """
    Result of applying trust-derived constraints to a policy decision.

    The policy engine combines this with the base policy result to produce
    the final GovernanceDecision. Trust NEVER directly produces ALLOW or DENY.
    """
    # Override flags
    requires_approval: bool = False
    approval_reason: Optional[str] = None

    # Scope modifiers
    max_spend_multiplier: float = 1.0
    rate_limit_multiplier: float = 1.0

    # Action restrictions
    action_blocked: bool = False
    block_reason: Optional[str] = None

    # Introspection requirements
    requires_introspection: bool = False

    # Audit level override
    audit_level: str = "normal"

    # Trust metadata (for decision record)
    trust_band: Optional[str] = None
    trust_snapshot_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requires_approval": self.requires_approval,
            "approval_reason": self.approval_reason,
            "max_spend_multiplier": self.max_spend_multiplier,
            "rate_limit_multiplier": self.rate_limit_multiplier,
            "action_blocked": self.action_blocked,
            "block_reason": self.block_reason,
            "requires_introspection": self.requires_introspection,
            "audit_level": self.audit_level,
            "trust_band": self.trust_band,
            "trust_snapshot_id": self.trust_snapshot_id,
        }


class TrustPolicyEngine:
    """
    Applies trust band constraints to policy evaluation.

    This is NOT a policy backend. It is a pre-processor that computes
trust-derived constraints, which the policy backend then evaluates
    alongside policy rules.
    """

    def __init__(self, db_pool=None):
        self.db = db_pool

    async def evaluate(
        self,
        action: str,
        actor_id: str,
        tenant_id: str,
        base_context: Dict[str, Any],
    ) -> TrustPolicyResult:
        """
        Compute trust-derived constraints for a policy evaluation.

        Returns TrustPolicyResult with constraints that the policy backend
        will apply to the final decision.
        """
        # Get current trust snapshot for the actor
        snapshot = await self._get_current_snapshot(actor_id)

        if not snapshot:
            # No trust data available — treat as PROBATION (safest default)
            logger.warning(f"No trust snapshot for actor {actor_id}, defaulting to PROBATION")
            return self._make_probation_result(actor_id, "no_trust_data")

        band = TrustBand(snapshot["band"].lower())
        score = float(snapshot["score"])
        snapshot_id = str(snapshot["snapshot_id"])
        probation_until = snapshot.get("probation_until")

        # Check if probation is active
        probation_active = False
        if probation_until and probation_until > datetime.now(timezone.utc):
            probation_active = True
            # Probation overrides band for enforcement purposes
            band = TrustBand.PROBATION

        constraints = get_band_constraints(band)

        # Build the trust policy context
        trust_context = TrustPolicyContext(
            band=band,
            score=score,
            snapshot_id=snapshot_id,
            probation_active=probation_active,
            probation_until=probation_until,
            constraints=constraints,
        )

        # Determine if action is blocked by band
        action_blocked = action in constraints.forbidden_actions
        block_reason = None
        if action_blocked:
            block_reason = f"Action '{action}' is forbidden in trust band '{band.value}'"

        # Determine if approval is required
        requires_approval = action in constraints.require_approval_for
        approval_reason = None
        if requires_approval:
            approval_reason = f"Trust band '{band.value}' requires approval for '{action}'"

        # Determine if introspection is required
        requires_introspection = action in constraints.force_introspection_before

        # Log for audit
        logger.info(
            f"Trust evaluation: actor={actor_id} action={action} "
            f"band={band.value} score={score:.4f} "
            f"blocked={action_blocked} approval={requires_approval}"
        )

        return TrustPolicyResult(
            requires_approval=requires_approval,
            approval_reason=approval_reason,
            max_spend_multiplier=constraints.max_spend_multiplier,
            rate_limit_multiplier=constraints.rate_limit_multiplier,
            action_blocked=action_blocked,
            block_reason=block_reason,
            requires_introspection=requires_introspection,
            audit_level=constraints.audit_level,
            trust_band=band.value,
            trust_snapshot_id=snapshot_id,
        )

    async def _get_current_snapshot(self, actor_id: str) -> Optional[Dict[str, Any]]:
        """Fetch the currently active trust snapshot for an actor."""
        if not self.db:
            return None

        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT snapshot_id, score, band, factors, probation_until, computed_at
                FROM actor_trust_snapshots
                WHERE actor_id = $1 AND valid_until IS NULL
                ORDER BY computed_at DESC
                LIMIT 1
                """,
                actor_id,
            )
            return dict(row) if row else None

    def _make_probation_result(self, actor_id: str, reason: str) -> TrustPolicyResult:
        """Default to PROBATION when no trust data is available."""
        constraints = get_band_constraints(TrustBand.PROBATION)
        return TrustPolicyResult(
            requires_approval=True,
            approval_reason=f"No trust data available for actor {actor_id} ({reason}). Defaulting to PROBATION.",
            max_spend_multiplier=constraints.max_spend_multiplier,
            rate_limit_multiplier=constraints.rate_limit_multiplier,
            action_blocked=False,
            requires_introspection=True,
            audit_level="full",
            trust_band=TrustBand.PROBATION.value,
        )


# ── Action Matrix ─────────────────────────────────────────────────────────
# The action matrix defines what each trust band allows for core actions.
# This is used by the TrustPolicyEngine and is also documented for operators.

ACTION_MATRIX: Dict[str, Dict[TrustBand, str]] = {
    # Format: action -> {band -> "allowed" | "approval" | "blocked" | "rate_limited" | "introspection_required"}

    "execute": {
        TrustBand.REVOKED:      "blocked",
        TrustBand.PROBATION:    "introspection_required",  # Allowed only after explicit introspection
        TrustBand.STANDARD:     "allowed",
        TrustBand.TRUSTED:      "allowed",
        TrustBand.HIGHLY_TRUSTED: "allowed",
    },
    "delegate": {
        TrustBand.REVOKED:      "blocked",
        TrustBand.PROBATION:    "blocked",  # No orchestration during probation
        TrustBand.STANDARD:     "allowed",
        TrustBand.TRUSTED:      "allowed",
        TrustBand.HIGHLY_TRUSTED: "allowed",
    },
    "handoff": {
        TrustBand.REVOKED:      "blocked",
        TrustBand.PROBATION:    "blocked",
        TrustBand.STANDARD:     "approval",  # Authority transfer needs approval at STANDARD
        TrustBand.TRUSTED:      "allowed",
        TrustBand.HIGHLY_TRUSTED: "allowed",
    },
    "gather": {
        TrustBand.REVOKED:      "blocked",
        TrustBand.PROBATION:    "blocked",
        TrustBand.STANDARD:     "approval",
        TrustBand.TRUSTED:      "allowed",
        TrustBand.HIGHLY_TRUSTED: "allowed",
    },
    "introspect": {
        TrustBand.REVOKED:      "blocked",
        TrustBand.PROBATION:    "allowed",  # Required during probation, but allowed
        TrustBand.STANDARD:     "allowed",
        TrustBand.TRUSTED:      "allowed",
        TrustBand.HIGHLY_TRUSTED: "allowed",
    },
    "protected_tool_use": {
        TrustBand.REVOKED:      "blocked",
        TrustBand.PROBATION:    "approval",
        TrustBand.STANDARD:     "allowed",
        TrustBand.TRUSTED:      "allowed",
        TrustBand.HIGHLY_TRUSTED: "allowed",
    },
    "destroy": {  # Destructive actions
        TrustBand.REVOKED:      "blocked",
        TrustBand.PROBATION:    "blocked",
        TrustBand.STANDARD:     "approval",
        TrustBand.TRUSTED:      "approval",
        TrustBand.HIGHLY_TRUSTED: "approval",  # Even highly trusted need approval for destruction
    },
    "revoke": {  # Emergency revocation
        TrustBand.REVOKED:      "blocked",  # Can't revoke if already revoked
        TrustBand.PROBATION:    "blocked",
        TrustBand.STANDARD:     "approval",
        TrustBand.TRUSTED:      "approval",
        TrustBand.HIGHLY_TRUSTED: "approval",
    },
    "quota_change": {  # Changing quotas
        TrustBand.REVOKED:      "blocked",
        TrustBand.PROBATION:    "blocked",
        TrustBand.STANDARD:     "approval",
        TrustBand.TRUSTED:      "allowed",
        TrustBand.HIGHLY_TRUSTED: "allowed",
    },
    "kill_switch_trigger": {  # Triggering emergency stop
        TrustBand.REVOKED:      "blocked",
        TrustBand.PROBATION:    "blocked",
        TrustBand.STANDARD:     "approval",
        TrustBand.TRUSTED:      "allowed",
        TrustBand.HIGHLY_TRUSTED: "allowed",
    },
}


def get_action_matrix_status(action: str, band: TrustBand) -> str:
    """
    Get the status of an action for a given trust band.

    Returns one of: "allowed", "approval", "blocked", "introspection_required"
    """
    action_lower = action.lower()
    if action_lower not in ACTION_MATRIX:
        # Unknown actions default to "approval" for safety
        return "approval"

    matrix = ACTION_MATRIX[action_lower]
    return matrix.get(band, "approval")


# ── Circuit Breaker Logic ────────────────────────────────────────────────

class TrustCircuitBreaker:
    """
    Circuit breaker for trust-based escalation.

    When trust drops below critical thresholds, the circuit breaker
    stages the transition rather than applying it immediately. This gives
    operators a window to intervene before the band changes.
    """

    # Score thresholds that trigger staging
    STAGE_THRESHOLD = 0.15  # Below this, stage a transition to REVOKED

    # Time window for staging (seconds)
    STAGE_WINDOW_SECONDS = 300  # 5 minutes

    async def check(
        self,
        actor_id: str,
        current_score: float,
        current_band: TrustBand,
        db_pool,
    ) -> Tuple[bool, Optional[str], Optional[TrustBand]]:
        """
        Check if a circuit breaker should fire.

        Returns: (should_fire, reason, target_band)
        """
        if current_score < self.STAGE_THRESHOLD:
            return True, "Score below emergency threshold (0.15)", TrustBand.REVOKED

        # Check for rapid band drops (REVOKED by kill switch, etc.)
        if current_band == TrustBand.REVOKED:
            return True, "Actor is in REVOKED band", TrustBand.REVOKED

        return False, None, None


__all__ = [
    "TrustPolicyContext",
    "TrustPolicyResult",
    "TrustPolicyEngine",
    "ACTION_MATRIX",
    "get_action_matrix_status",
    "TrustCircuitBreaker",
]
