"""
Trust Bands — Deterministic score-to-band mapping and band effects.

This module defines:
- The 5 trust bands with explicit score thresholds
- What each band means operationally
- How each band affects policy constraints
- Deterministic transitions (no hidden logic, no ML)

Design principle: Trust bands are governance signals, not authority sources.
They modify the *conditions* under which policy rules evaluate, never the
*rules themselves*. Authority is always granted by policy + capability tokens.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


class TrustBand(Enum):
    """
    Five trust bands with explicit score thresholds.

    Thresholds are immutable. Changing them requires a code change
    and a new policy version — they are not configurable at runtime.
    This prevents silent threshold drift that would make policy
    evaluation non-deterministic.
    """
    REVOKED = "revoked"           # 0.00 - 0.19: Identity disabled
    PROBATION = "probation"       # 0.20 - 0.39: New or low-trust, strict monitoring
    STANDARD = "standard"         # 0.40 - 0.59: Normal operation
    TRUSTED = "trusted"           # 0.60 - 0.79: Elevated privileges
    HIGHLY_TRUSTED = "highly_trusted"  # 0.80 - 1.00: Full privileges

    @classmethod
    def from_score(cls, score: float) -> "TrustBand":
        """
        Deterministic score-to-band mapping.

        >>> TrustBand.from_score(0.15)
        <TrustBand.REVOKED>
        >>> TrustBand.from_score(0.45)
        <TrustBand.STANDARD>
        >>> TrustBand.from_score(0.85)
        <TrustBand.HIGHLY_TRUSTED>
        """
        if score < 0.0 or score > 1.0:
            raise ValueError(f"Trust score must be in [0.0, 1.0], got {score}")

        # Explicit thresholds — these are code-level constants.
        # Changing them is a breaking policy change.
        if score < 0.20:
            return cls.REVOKED
        elif score < 0.40:
            return cls.PROBATION
        elif score < 0.60:
            return cls.STANDARD
        elif score < 0.80:
            return cls.TRUSTED
        else:
            return cls.HIGHLY_TRUSTED

    @property
    def min_score(self) -> float:
        """Minimum score for this band (inclusive)."""
        return {
            TrustBand.REVOKED: 0.0,
            TrustBand.PROBATION: 0.20,
            TrustBand.STANDARD: 0.40,
            TrustBand.TRUSTED: 0.60,
            TrustBand.HIGHLY_TRUSTED: 0.80,
        }[self]

    @property
    def max_score(self) -> float:
        """Maximum score for this band (exclusive except for top)."""
        return {
            TrustBand.REVOKED: 0.20,
            TrustBand.PROBATION: 0.40,
            TrustBand.STANDARD: 0.60,
            TrustBand.TRUSTED: 0.80,
            TrustBand.HIGHLY_TRUSTED: 1.0,
        }[self]


@dataclass(frozen=True)
class BandConstraints:
    """
    Policy constraints that apply to a specific trust band.

    These are NOT overrides. They are default constraints that policy rules
    can reference. A policy rule may set stricter constraints; it may NEVER
    set looser constraints than the band allows. This is enforced by the
    policy engine at rule validation time.
    """
    # Approval behavior
    require_approval_for: List[str] = field(default_factory=list)
    """Action types that always require human approval in this band."""

    approval_bypass_for_risk_below: Optional[str] = None
    """Risk levels below which approval can be bypassed (e.g., 'medium')."""

    # Quota modifiers
    max_spend_multiplier: float = 1.0
    """Multiplier applied to base max_spend from policy/entitlements."""

    rate_limit_multiplier: float = 1.0
    """Multiplier applied to base rate_limit from policy/entitlements."""

    # Probation flag
    is_probation: bool = False
    """True if this band represents a probationary state."""

    # Monitoring
    audit_level: str = "normal"
    """Audit intensity: 'minimal', 'normal', 'enhanced', 'full'."""

    # Kill switch sensitivity
    kill_switch_triggers_band_drop: bool = False
    """If True, a kill switch activation automatically drops the actor to REVOKED."""

    # Scope restrictions
    forbidden_actions: List[str] = field(default_factory=list)
    """Actions that are completely blocked in this band (regardless of policy)."""

    # Introspection requirements
    force_introspection_before: List[str] = field(default_factory=list)
    """Actions that require explicit introspection() call before execution."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for audit / API response."""
        return {
            "require_approval_for": self.require_approval_for,
            "approval_bypass_for_risk_below": self.approval_bypass_for_risk_below,
            "max_spend_multiplier": self.max_spend_multiplier,
            "rate_limit_multiplier": self.rate_limit_multiplier,
            "is_probation": self.is_probation,
            "audit_level": self.audit_level,
            "kill_switch_triggers_band_drop": self.kill_switch_triggers_band_drop,
            "forbidden_actions": self.forbidden_actions,
            "force_introspection_before": self.force_introspection_before,
        }


# ── Band constraint definitions (immutable, versioned) ─────────────────────
# These are the canonical constraints for each band. They are part of the
# policy engine specification. Changing them is a policy version bump.

BAND_CONSTRAINTS: Dict[TrustBand, BandConstraints] = {
    TrustBand.REVOKED: BandConstraints(
        require_approval_for=["*"],  # All actions blocked
        max_spend_multiplier=0.0,
        rate_limit_multiplier=0.0,
        is_probation=False,
        audit_level="full",
        kill_switch_triggers_band_drop=True,
        forbidden_actions=["execute", "delegate", "handoff", "gather", "introspect"],
        force_introspection_before=[],
    ),

    TrustBand.PROBATION: BandConstraints(
        require_approval_for=["delegate", "handoff", "gather", "destroy", "revoke"],
        approval_bypass_for_risk_below=None,  # No bypass during probation
        max_spend_multiplier=0.5,
        rate_limit_multiplier=0.5,
        is_probation=True,
        audit_level="full",
        kill_switch_triggers_band_drop=True,
        forbidden_actions=["delegate", "handoff"],  # No orchestration during probation
        force_introspection_before=["execute", "protected_tool_use"],
    ),

    TrustBand.STANDARD: BandConstraints(
        require_approval_for=["destroy", "revoke"],
        approval_bypass_for_risk_below="low",
        max_spend_multiplier=1.0,
        rate_limit_multiplier=1.0,
        is_probation=False,
        audit_level="normal",
        kill_switch_triggers_band_drop=False,
        forbidden_actions=[],
        force_introspection_before=["destroy"],
    ),

    TrustBand.TRUSTED: BandConstraints(
        require_approval_for=["destroy", "revoke"],
        approval_bypass_for_risk_below="medium",
        max_spend_multiplier=1.5,
        rate_limit_multiplier=2.0,
        is_probation=False,
        audit_level="enhanced",  # More logging, not less
        kill_switch_triggers_band_drop=False,
        forbidden_actions=[],
        force_introspection_before=["destroy"],
    ),

    TrustBand.HIGHLY_TRUSTED: BandConstraints(
        require_approval_for=["destroy"],  # Only destructive actions need approval
        approval_bypass_for_risk_below="medium",
        max_spend_multiplier=2.0,
        rate_limit_multiplier=5.0,
        is_probation=False,
        audit_level="enhanced",
        kill_switch_triggers_band_drop=False,
        forbidden_actions=[],
        force_introspection_before=["destroy"],
    ),
}


# ── Probation configuration ────────────────────────────────────────────────

PROBATION_CONFIG = {
    # How long probation lasts for new agents
    "default_probation_days": 7,

    # Minimum days in probation before automatic exit
    "min_probation_days": 3,

    # Score threshold for exiting probation (must be >= this to exit early)
    "exit_score_threshold": 0.40,

    # Score threshold that extends probation (if score drops below, extend)
    "extend_score_threshold": 0.25,

    # Extension duration when score drops
    "extension_days": 7,

    # Maximum total probation duration (hard cap)
    "max_probation_days": 30,

    # Events that trigger probation extension
    "extension_triggers": [
        "POLICY_VIOLATION",
        "KILL_SWITCH_TRIGGERED",
        "FAILED_HARDENING",
        "AUDIT_ANOMALY",
    ],
}


# ── Trust score computation weights ───────────────────────────────────────
# These weights are part of the policy specification. They are deterministic
# and documented. Changing them is a policy version change.

TRUST_FACTOR_WEIGHTS = {
    "verification": 0.25,       # Verified identity
    "age": 0.15,                # Age of identity (capped)
    "health": 0.20,             # Health score from agents table
    "quarantine": 0.10,         # Not quarantined (bonus) / quarantined (penalty)
    "action_rate": 0.10,        # Normal action rate (bonus) / excessive (penalty)
    "compliance": 0.15,          # Compliance certifications
    "budget_adherence": 0.05,    # Token budget adherence
}

# Sum must be 1.0 for normalization
assert abs(sum(TRUST_FACTOR_WEIGHTS.values()) - 1.0) < 0.001, \
    f"Trust factor weights must sum to 1.0, got {sum(TRUST_FACTOR_WEIGHTS.values())}"


def get_band_constraints(band: TrustBand) -> BandConstraints:
    """Get the canonical constraints for a trust band."""
    return BAND_CONSTRAINTS[band]


def is_band_transition_allowed(from_band: TrustBand, to_band: TrustBand) -> bool:
    """
    Check if a direct band transition is allowed.

    Rules:
    - Any band can transition to REVOKED (emergency)
    - REVOKED can only transition to PROBATION (not directly to STANDARD+)
    - PROBATION can transition to STANDARD or REVOKED
    - STANDARD can transition to any band
    - TRUSTED can transition to any band
    - HIGHLY_TRUSTED can transition to any band
    - No skipping from REVOKED to HIGHLY_TRUSTED (must go through PROBATION)
    """
    if to_band == TrustBand.REVOKED:
        return True  # Any band can be revoked

    if from_band == TrustBand.REVOKED:
        return to_band == TrustBand.PROBATION  # Must go through probation

    if from_band == TrustBand.PROBATION:
        return to_band in (TrustBand.STANDARD, TrustBand.REVOKED)

    # STANDARD, TRUSTED, HIGHLY_TRUSTED can move to any band (up or down)
    return True


def get_transition_reason_code(
    from_band: TrustBand,
    to_band: TrustBand,
    score: float,
    factors: Dict[str, float],
) -> str:
    """
    Generate a deterministic reason code for a band transition.

    This is used in audit events to explain WHY the band changed.
    """
    if to_band == TrustBand.REVOKED:
        return "EMERGENCY_REVOKE"

    if from_band == TrustBand.REVOKED and to_band == TrustBand.PROBATION:
        return "RESTORED_TO_PROBATION"

    if to_band.value < from_band.value:  # Score decreased (band order is REVOKED < PROBATION < ...)
        # Identify the dominant negative factor
        negative_factors = {k: v for k, v in factors.items() if v < 0}
        if negative_factors:
            worst = min(negative_factors, key=negative_factors.get)
            return f"DEGRADED_{worst.upper()}"
        return "DEGRADED_GENERAL"

    if to_band.value > from_band.value:  # Score increased
        # Identify the dominant positive factor
        positive_factors = {k: v for k, v in factors.items() if v > 0}
        if positive_factors:
            best = max(positive_factors, key=positive_factors.get)
            return f"ELEVATED_{best.upper()}"
        return "ELEVATED_GENERAL"

    return "NO_CHANGE"


__all__ = [
    "TrustBand",
    "BandConstraints",
    "BAND_CONSTRAINTS",
    "PROBATION_CONFIG",
    "TRUST_FACTOR_WEIGHTS",
    "get_band_constraints",
    "is_band_transition_allowed",
    "get_transition_reason_code",
]
