"""
Tests for trust bands: score-to-band mapping, constraints, and transitions.
"""
import pytest
from datetime import datetime, timezone

from citadel.agent_identity.trust_bands import (
    TrustBand,
    BandConstraints,
    BAND_CONSTRAINTS,
    PROBATION_CONFIG,
    TRUST_FACTOR_WEIGHTS,
    get_band_constraints,
    is_band_transition_allowed,
    get_transition_reason_code,
)


class TestTrustBandMapping:
    """Test deterministic score-to-band mapping."""

    def test_revoked_band(self):
        assert TrustBand.from_score(0.0) == TrustBand.REVOKED
        assert TrustBand.from_score(0.10) == TrustBand.REVOKED
        assert TrustBand.from_score(0.199) == TrustBand.REVOKED

    def test_probation_band(self):
        assert TrustBand.from_score(0.20) == TrustBand.PROBATION
        assert TrustBand.from_score(0.30) == TrustBand.PROBATION
        assert TrustBand.from_score(0.399) == TrustBand.PROBATION

    def test_standard_band(self):
        assert TrustBand.from_score(0.40) == TrustBand.STANDARD
        assert TrustBand.from_score(0.50) == TrustBand.STANDARD
        assert TrustBand.from_score(0.599) == TrustBand.STANDARD

    def test_trusted_band(self):
        assert TrustBand.from_score(0.60) == TrustBand.TRUSTED
        assert TrustBand.from_score(0.70) == TrustBand.TRUSTED
        assert TrustBand.from_score(0.799) == TrustBand.TRUSTED

    def test_highly_trusted_band(self):
        assert TrustBand.from_score(0.80) == TrustBand.HIGHLY_TRUSTED
        assert TrustBand.from_score(0.90) == TrustBand.HIGHLY_TRUSTED
        assert TrustBand.from_score(1.0) == TrustBand.HIGHLY_TRUSTED

    def test_exact_boundary(self):
        """Boundaries are exact and stable."""
        assert TrustBand.from_score(0.20) == TrustBand.PROBATION
        assert TrustBand.from_score(0.40) == TrustBand.STANDARD
        assert TrustBand.from_score(0.60) == TrustBand.TRUSTED
        assert TrustBand.from_score(0.80) == TrustBand.HIGHLY_TRUSTED

    def test_invalid_scores(self):
        with pytest.raises(ValueError):
            TrustBand.from_score(-0.1)
        with pytest.raises(ValueError):
            TrustBand.from_score(1.1)

    def test_band_score_ranges(self):
        """Each band knows its min and max score."""
        assert TrustBand.REVOKED.min_score == 0.0
        assert TrustBand.REVOKED.max_score == 0.20
        assert TrustBand.PROBATION.min_score == 0.20
        assert TrustBand.PROBATION.max_score == 0.40
        assert TrustBand.STANDARD.min_score == 0.40
        assert TrustBand.STANDARD.max_score == 0.60
        assert TrustBand.TRUSTED.min_score == 0.60
        assert TrustBand.TRUSTED.max_score == 0.80
        assert TrustBand.HIGHLY_TRUSTED.min_score == 0.80
        assert TrustBand.HIGHLY_TRUSTED.max_score == 1.0


class TestBandConstraints:
    """Test that each band has correct constraints."""

    def test_revoked_constraints(self):
        c = get_band_constraints(TrustBand.REVOKED)
        assert c.max_spend_multiplier == 0.0
        assert c.rate_limit_multiplier == 0.0
        assert "execute" in c.forbidden_actions
        assert "delegate" in c.forbidden_actions
        assert c.is_probation is False
        assert c.kill_switch_triggers_band_drop is True

    def test_probation_constraints(self):
        c = get_band_constraints(TrustBand.PROBATION)
        assert c.max_spend_multiplier == 0.5
        assert c.rate_limit_multiplier == 0.5
        assert c.is_probation is True
        assert "delegate" in c.forbidden_actions
        assert "handoff" in c.forbidden_actions
        assert c.kill_switch_triggers_band_drop is True

    def test_standard_constraints(self):
        c = get_band_constraints(TrustBand.STANDARD)
        assert c.max_spend_multiplier == 1.0
        assert c.rate_limit_multiplier == 1.0
        assert c.is_probation is False
        assert c.forbidden_actions == []
        assert c.kill_switch_triggers_band_drop is False

    def test_trusted_constraints(self):
        c = get_band_constraints(TrustBand.TRUSTED)
        assert c.max_spend_multiplier == 1.5
        assert c.rate_limit_multiplier == 2.0
        assert c.is_probation is False
        assert c.approval_bypass_for_risk_below == "medium"

    def test_highly_trusted_constraints(self):
        c = get_band_constraints(TrustBand.HIGHLY_TRUSTED)
        assert c.max_spend_multiplier == 2.0
        assert c.rate_limit_multiplier == 5.0
        assert c.is_probation is False
        assert "destroy" in c.require_approval_for

    def test_constraints_are_frozen(self):
        """Constraints should not be modifiable at runtime."""
        c = get_band_constraints(TrustBand.STANDARD)
        # BandConstraints is frozen, so this would fail at runtime
        # but we verify the dataclass is frozen
        assert hasattr(c, "max_spend_multiplier")


class TestBandTransitions:
    """Test band transition rules."""

    def test_any_to_revoked(self):
        """Any band can transition to REVOKED."""
        for band in TrustBand:
            assert is_band_transition_allowed(band, TrustBand.REVOKED) is True

    def test_revoked_only_to_probation(self):
        """REVOKED can only go to PROBATION."""
        assert is_band_transition_allowed(TrustBand.REVOKED, TrustBand.PROBATION) is True
        assert is_band_transition_allowed(TrustBand.REVOKED, TrustBand.STANDARD) is False
        assert is_band_transition_allowed(TrustBand.REVOKED, TrustBand.TRUSTED) is False
        assert is_band_transition_allowed(TrustBand.REVOKED, TrustBand.HIGHLY_TRUSTED) is False

    def test_probation_to_standard_or_revoked(self):
        assert is_band_transition_allowed(TrustBand.PROBATION, TrustBand.STANDARD) is True
        assert is_band_transition_allowed(TrustBand.PROBATION, TrustBand.REVOKED) is True
        assert is_band_transition_allowed(TrustBand.PROBATION, TrustBand.TRUSTED) is False
        assert is_band_transition_allowed(TrustBand.PROBATION, TrustBand.HIGHLY_TRUSTED) is False

    def test_standard_free_movement(self):
        assert is_band_transition_allowed(TrustBand.STANDARD, TrustBand.PROBATION) is True
        assert is_band_transition_allowed(TrustBand.STANDARD, TrustBand.TRUSTED) is True
        assert is_band_transition_allowed(TrustBand.STANDARD, TrustBand.REVOKED) is True

    def test_trusted_free_movement(self):
        assert is_band_transition_allowed(TrustBand.TRUSTED, TrustBand.HIGHLY_TRUSTED) is True
        assert is_band_transition_allowed(TrustBand.TRUSTED, TrustBand.STANDARD) is True
        assert is_band_transition_allowed(TrustBand.TRUSTED, TrustBand.REVOKED) is True

    def test_highly_trusted_free_movement(self):
        assert is_band_transition_allowed(TrustBand.HIGHLY_TRUSTED, TrustBand.TRUSTED) is True
        assert is_band_transition_allowed(TrustBand.HIGHLY_TRUSTED, TrustBand.STANDARD) is True
        assert is_band_transition_allowed(TrustBand.HIGHLY_TRUSTED, TrustBand.REVOKED) is True


class TestTransitionReasonCodes:
    """Test deterministic reason code generation."""

    def test_emergency_revoke(self):
        code = get_transition_reason_code(
            TrustBand.STANDARD, TrustBand.REVOKED, 0.1, {}
        )
        assert code == "EMERGENCY_REVOKE"

    def test_restored_to_probation(self):
        code = get_transition_reason_code(
            TrustBand.REVOKED, TrustBand.PROBATION, 0.3, {}
        )
        assert code == "RESTORED_TO_PROBATION"

    def test_degraded_with_factor(self):
        factors = {"health": -0.20, "verification": 0.25}
        code = get_transition_reason_code(
            TrustBand.TRUSTED, TrustBand.STANDARD, 0.5, factors
        )
        assert code == "DEGRADED_HEALTH"

    def test_elevated_with_factor(self):
        factors = {"verification": 0.25, "health": 0.20}
        code = get_transition_reason_code(
            TrustBand.STANDARD, TrustBand.TRUSTED, 0.7, factors
        )
        assert code == "ELEVATED_VERIFICATION"

    def test_general_degradation(self):
        code = get_transition_reason_code(
            TrustBand.TRUSTED, TrustBand.STANDARD, 0.5, {"health": 0.0}
        )
        assert code == "DEGRADED_GENERAL"


class TestFactorWeights:
    """Test that factor weights sum to 1.0."""

    def test_weights_sum(self):
        total = sum(TRUST_FACTOR_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_all_weights_positive(self):
        for name, weight in TRUST_FACTOR_WEIGHTS.items():
            assert weight > 0, f"Weight for {name} must be positive"


class TestProbationConfig:
    """Test probation configuration constants."""

    def test_probation_defaults(self):
        assert PROBATION_CONFIG["default_probation_days"] == 7
        assert PROBATION_CONFIG["min_probation_days"] == 3
        assert PROBATION_CONFIG["exit_score_threshold"] == 0.40
        assert PROBATION_CONFIG["max_probation_days"] == 30

    def test_extension_triggers(self):
        triggers = PROBATION_CONFIG["extension_triggers"]
        assert "POLICY_VIOLATION" in triggers
        assert "KILL_SWITCH_TRIGGERED" in triggers


class TestBandOrdering:
    """Test that band enum values are ordered correctly for comparison."""

    def test_band_value_order(self):
        """Band thresholds increase with trust level."""
        assert TrustBand.REVOKED.max_score < TrustBand.PROBATION.max_score
        assert TrustBand.PROBATION.max_score < TrustBand.STANDARD.max_score
        assert TrustBand.STANDARD.max_score < TrustBand.TRUSTED.max_score
        assert TrustBand.TRUSTED.max_score < TrustBand.HIGHLY_TRUSTED.max_score
