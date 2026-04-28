"""
Tests for trust snapshot engine: computation, storage, backward compatibility.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from citadel.agent_identity.trust_score import (
    TrustBand,
    TrustLevel,
    TrustScore,
    TrustScorer,
    TrustSnapshotEngine,
)
from citadel.api.routers.dashboard import _trust_factor_breakdown


class TestTrustScoreComputation:
    """Test deterministic score computation from raw inputs."""

    def test_perfect_agent(self):
        """A perfect agent should score highly."""
        engine = TrustSnapshotEngine(None)
        raw = {
            "identity_verified": True,
            "health_score": 100,
            "quarantined": False,
            "actions_today": 50,
            "token_spend": 100,
            "token_budget": 10000,
            "compliance_tags": ["gdpr", "soc2"],
            "identity_created_at": datetime.now(timezone.utc) - timedelta(days=30),
            "violations_7d": 0,
            "challenge_count": 10,
            "failed_challenges": 0,
        }
        score, factors = engine._compute_score(raw)
        assert score >= 0.70  # Should be in TRUSTED or HIGHLY_TRUSTED
        assert factors["verification"] == 0.25
        assert factors["health"] == 0.20
        assert factors["compliance"] == 0.15
        assert score <= 1.0

    def test_dashboard_factor_breakdown_uses_current_factor_names(self):
        """Dashboard explanations should match the live trust engine factors."""
        factors = {
            "verification": 0.25,
            "age": 0.15,
            "health": 0.20,
            "quarantine": 0.10,
            "action_rate": 0.10,
            "compliance": 0.15,
            "budget_adherence": 0.05,
            "challenge_reliability": 0.05,
            "trend": -0.03,
        }

        rows = _trust_factor_breakdown(factors)

        assert [row["key"] for row in rows] == [
            "verification",
            "age",
            "health",
            "quarantine",
            "action_rate",
            "compliance",
            "budget_adherence",
            "challenge_reliability",
            "trend",
        ]
        assert rows[-1]["direction"] == "negative"

    def test_unverified_agent_low_score(self):
        """An unverified agent should score lower."""
        engine = TrustSnapshotEngine(None)
        raw = {
            "identity_verified": False,
            "health_score": 50,
            "quarantined": False,
            "actions_today": 50,
            "token_spend": 100,
            "token_budget": 10000,
            "compliance_tags": [],
            "identity_created_at": datetime.now(timezone.utc) - timedelta(days=1),
            "violations_7d": 0,
            "challenge_count": 0,
            "failed_challenges": 0,
        }
        score, factors = engine._compute_score(raw)
        assert score < 0.60  # Should be STANDARD or lower
        assert factors["verification"] == 0.0

    def test_quarantined_agent_penalty(self):
        """Quarantine should significantly lower score."""
        engine = TrustSnapshotEngine(None)
        raw = {
            "identity_verified": False,
            "health_score": 50,
            "quarantined": True,
            "actions_today": 50,
            "token_spend": 100,
            "token_budget": 10000,
            "compliance_tags": [],
            "identity_created_at": datetime.now(timezone.utc) - timedelta(days=1),
            "violations_7d": 0,
            "challenge_count": 10,
            "failed_challenges": 0,
        }
        score, factors = engine._compute_score(raw)
        assert factors["quarantine"] == -0.30
        assert score < 0.50  # Should be PROBATION or lower


    def test_excessive_actions_penalty(self):
        """Too many actions should lower score."""
        engine = TrustSnapshotEngine(None)
        raw = {
            "identity_verified": True,
            "health_score": 100,
            "quarantined": False,
            "actions_today": 1500,
            "token_spend": 100,
            "token_budget": 10000,
            "compliance_tags": ["gdpr"],
            "identity_created_at": datetime.now(timezone.utc) - timedelta(days=30),
            "violations_7d": 0,
            "challenge_count": 10,
            "failed_challenges": 0,
        }
        score, factors = engine._compute_score(raw)
        assert factors["action_rate"] == -0.10

    def test_violations_penalty(self):
        """Multiple violations should lower score."""
        engine = TrustSnapshotEngine(None)
        raw = {
            "identity_verified": True,
            "health_score": 100,
            "quarantined": False,
            "actions_today": 50,
            "token_spend": 100,
            "token_budget": 10000,
            "compliance_tags": ["gdpr"],
            "identity_created_at": datetime.now(timezone.utc) - timedelta(days=30),
            "violations_7d": 5,
            "challenge_count": 10,
            "failed_challenges": 0,
        }
        score, factors = engine._compute_score(raw)
        assert factors["compliance"] == -0.15

    def test_score_clamped(self):
        """Score should never exceed [0.0, 1.0]."""
        engine = TrustSnapshotEngine(None)
        # Perfect everything
        raw = {
            "identity_verified": True,
            "health_score": 100,
            "quarantined": False,
            "actions_today": 50,
            "token_spend": 0,
            "token_budget": 100000,
            "compliance_tags": ["gdpr", "hipaa", "soc2"],
            "identity_created_at": datetime.now(timezone.utc) - timedelta(days=100),
            "violations_7d": 0,
            "challenge_count": 100,
            "failed_challenges": 0,
        }
        score, _ = engine._compute_score(raw)
        assert 0.0 <= score <= 1.0

    def test_trend_bonus(self):
        """Rapid improvement should get a small bonus."""
        engine = TrustSnapshotEngine(None)
        raw = {
            "identity_verified": True,
            "health_score": 100,
            "quarantined": False,
            "actions_today": 50,
            "token_spend": 100,
            "token_budget": 10000,
            "compliance_tags": ["gdpr"],
            "identity_created_at": datetime.now(timezone.utc) - timedelta(days=30),
            "violations_7d": 0,
            "challenge_count": 10,
            "failed_challenges": 0,
            "previous_score": 0.10,
        }
        score, factors = engine._compute_score(raw)
        assert factors["trend"] == 0.02

    def test_trend_penalty(self):
        """Rapid drop should get a small additional penalty."""
        engine = TrustSnapshotEngine(None)
        raw = {
            "identity_verified": False,
            "health_score": 50,
            "quarantined": True,
            "actions_today": 2000,
            "token_spend": 90000,
            "token_budget": 100000,
            "compliance_tags": [],
            "identity_created_at": datetime.now(timezone.utc) - timedelta(days=1),
            "violations_7d": 0,
            "challenge_count": 10,
            "failed_challenges": 9,
            "previous_score": 0.95,
        }
        score, factors = engine._compute_score(raw)
        assert factors["trend"] == -0.03



class TestBandMapping:
    """Test that computed scores map to correct bands."""

    def test_low_score_maps_to_revoked(self):
        engine = TrustSnapshotEngine(None)
        raw = {
            "identity_verified": False,
            "health_score": 0,
            "quarantined": True,
            "actions_today": 2000,
            "token_spend": 90000,
            "token_budget": 100000,
            "compliance_tags": [],
            "identity_created_at": datetime.now(timezone.utc) - timedelta(days=1),
            "violations_7d": 10,
            "challenge_count": 10,
            "failed_challenges": 9,
        }
        score, _ = engine._compute_score(raw)
        band = TrustBand.from_score(score)
        assert band == TrustBand.REVOKED

    def test_medium_score_maps_to_standard(self):
        engine = TrustSnapshotEngine(None)
        raw = {
            "identity_verified": True,
            "health_score": 80,
            "quarantined": False,
            "actions_today": 150,
            "token_spend": 9500,
            "token_budget": 10000,
            "compliance_tags": [],
            "identity_created_at": datetime.now(timezone.utc) - timedelta(days=10),
            "violations_7d": 3,
            "challenge_count": 5,
            "failed_challenges": 1,
        }
        score, _ = engine._compute_score(raw)
        band = TrustBand.from_score(score)
        assert band == TrustBand.STANDARD


class TestBackwardCompatibility:
    """Test that old TrustScorer API still works."""

    def test_old_compute_score(self):
        """The static compute_score method should still work."""
        score, level, factors = TrustScorer.compute_score(
            verified=True,
            health_score=100,
            quarantined=False,
            actions_today=50,
            token_spend=100,
            token_budget=10000,
            compliance_tags=["gdpr"],
            created_at=datetime.now(timezone.utc) - timedelta(days=30),
            failed_challenges=0,
            challenge_count=10,
        )
        assert 0.0 <= score <= 1.0
        assert isinstance(level, TrustLevel)

    def test_old_level_to_new_band_mapping(self):
        """TrustLevel should map correctly to TrustBand."""
        assert TrustLevel.REVOKED.to_trust_band() == TrustBand.REVOKED
        assert TrustLevel.UNVERIFIED.to_trust_band() == TrustBand.PROBATION
        assert TrustLevel.STANDARD.to_trust_band() == TrustBand.STANDARD
        assert TrustLevel.TRUSTED.to_trust_band() == TrustBand.TRUSTED
        assert TrustLevel.HIGHLY_TRUSTED.to_trust_band() == TrustBand.HIGHLY_TRUSTED

    def test_trust_score_dataclass(self):
        """TrustScore dataclass should work with new TrustBand."""
        ts = TrustScore(
            agent_id="agent-1",
            score=0.75,
            level=TrustBand.TRUSTED,
            snapshot_id="snap-123",
        )
        d = ts.to_dict()
        assert d["level"] == "trusted"
        assert d["snapshot_id"] == "snap-123"


class TestSnapshotCreation:
    """Test snapshot database operations."""

    @pytest.fixture
    def mock_db(self):
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        return pool, conn

    @pytest.mark.asyncio
    async def test_compute_and_store_no_db(self):
        """Without DB, should return a score but not store."""
        engine = TrustSnapshotEngine(None)
        result = await engine.compute_and_store("agent-1")
        assert result.score == 0.0
        assert result.level == TrustBand.REVOKED

    @pytest.mark.asyncio
    async def test_compute_and_store_agent_not_found(self, mock_db):
        pool, conn = mock_db
        conn.fetchrow.return_value = None  # No agent found

        engine = TrustSnapshotEngine(pool)
        result = await engine.compute_and_store("agent-1")

        assert result.score == 0.0
        assert result.level == TrustBand.REVOKED

    @pytest.mark.asyncio
    async def test_snapshot_creation_expires_previous(self, mock_db):
        pool, conn = mock_db
        # First call: fetch agent data
        conn.fetchrow.side_effect = [
            {  # agent
                "agent_id": "agent-1",
                "health_score": 100,
                "quarantined": False,
                "actions_today": 50,
                "token_spend": 100,
                "token_budget": 10000,
                "compliance": ["gdpr"],
                "created_at": datetime.now(timezone.utc) - timedelta(days=30),
                "probation_until": None,
            },
            {  # identity
                "agent_id": "agent-1",
                "verification_status": "verified",
                "created_at": datetime.now(timezone.utc) - timedelta(days=30),
                "failed_challenges": 0,
                "challenge_count": 10,
            },
            {  # previous snapshot
                "snapshot_id": "prev-snap",
                "score": 0.50,
                "band": "STANDARD",
                "computed_at": datetime.now(timezone.utc) - timedelta(hours=1),
            },
            {  # new snapshot insert result
                "snapshot_id": "new-snap",
            },
        ]
        conn.fetchval.side_effect = [0, 5]  # violations, total events

        engine = TrustSnapshotEngine(pool)

        # Mock the _create_snapshot to return a fixed ID
        with patch.object(engine, '_create_snapshot', return_value="new-snap"):
            with patch.object(engine, '_update_agent_cache', return_value=None):
                with patch.object(engine.audit, 'log_band_transition', return_value=None):
                    with patch.object(engine.audit, 'log_score_computed', return_value=None):
                        result = await engine.compute_and_store("agent-1")

        assert result is not None


class TestProbationManagement:
    """Test probation logic."""

    @pytest.fixture
    def mock_db(self):
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        return pool, conn

    @pytest.mark.asyncio
    async def test_probation_active_overrides_band(self, mock_db):
        pool, conn = mock_db
        conn.fetchrow.side_effect = [
            {  # agent with active probation
                "agent_id": "agent-1",
                "health_score": 100,
                "quarantined": False,
                "actions_today": 50,
                "token_spend": 100,
                "token_budget": 10000,
                "compliance": ["gdpr"],
                "created_at": datetime.now(timezone.utc) - timedelta(days=30),
                "probation_until": datetime.now(timezone.utc) + timedelta(days=3),
            },
            {  # identity
                "agent_id": "agent-1",
                "verification_status": "verified",
                "created_at": datetime.now(timezone.utc) - timedelta(days=30),
                "failed_challenges": 0,
                "challenge_count": 10,
            },
            None,  # no previous snapshot (from _get_agent_data)
            None,  # no previous snapshot (from compute_and_store)
        ]
        conn.fetchval.side_effect = [0, 5]

        engine = TrustSnapshotEngine(pool)
        with patch.object(engine, '_create_snapshot', return_value="snap-1"):
            with patch.object(engine, '_update_agent_cache', return_value=None):
                with patch.object(engine.audit, 'log_score_computed', return_value=None):
                    result = await engine.compute_and_store("agent-1")

        assert result.level == TrustBand.PROBATION
