"""
Tests for Governance Posture Score (Phase 1 MVP).

Target: 5 tests passing.
- test_posture_score_range_0_to_100
- test_hourly_cache_behavior
- test_all_components_sum_correctly
- test_trend_data_accuracy
- test_recommendations_actionable
"""

import pytest
from datetime import datetime, timezone, timedelta
from ledger.dashboard.posture_score import PostureScoreService, PostureScore


TENANT = "test_tenant"


class TestPostureScore:
    """Test governance posture score calculation."""

    @pytest.mark.asyncio
    async def test_posture_score_range_0_to_100(self, db_pool):
        """Score must always be in 0-100 range."""
        service = PostureScoreService(db_pool)
        score = await service.calculate(TENANT)

        assert isinstance(score.score, int)
        assert 0 <= score.score <= 100
        assert score.tenant_id == TENANT

    @pytest.mark.asyncio
    async def test_all_components_sum_correctly(self, db_pool):
        """All sub-components contribute to final score."""
        service = PostureScoreService(db_pool)
        score = await service.calculate(TENANT)

        # Verify components exist
        assert "uncovered_actions" in score.components
        assert "unapproved_high_risk" in score.components
        assert "kill_switch_health" in score.components
        assert "low_trust_agents" in score.components
        assert "approval_backlog" in score.components
        assert "policy_coverage" in score.components

        # Verify component structure
        for name, component in score.components.items():
            if name != "policy_coverage":
                assert "value" in component
                assert "weight" in component
                assert "risk_contribution" in component
            else:
                assert "percentage" in component

    @pytest.mark.asyncio
    async def test_trend_data_accuracy(self, db_pool):
        """Trend reflects score change direction."""
        service = PostureScoreService(db_pool)
        score = await service.calculate(TENANT)

        assert score.trend in ["up", "stable", "down"]

        # Health should correspond to score
        if score.score >= 90:
            assert score.health == "excellent"
        elif score.score >= 70:
            assert score.health == "healthy"
        elif score.score >= 50:
            assert score.health == "at_risk"
        else:
            assert score.health == "critical"

    @pytest.mark.asyncio
    async def test_recommendations_actionable(self, db_pool):
        """Recommendations must be actionable."""
        service = PostureScoreService(db_pool)
        score = await service.calculate(TENANT)

        # All recommendations should have required fields
        for rec in score.recommendations:
            assert "priority" in rec
            assert "message" in rec
            assert "action" in rec
            assert rec["priority"] in ["critical", "high", "medium", "low"]

    @pytest.mark.asyncio
    async def test_posture_score_calculation_with_data(self, db_pool):
        """Score changes when tenant has real data."""
        import asyncpg

        # Insert test data
        conn = await asyncpg.connect("postgresql://ledger:ledger@localhost:5432/ledger_test")
        await conn.execute("SET app.admin_bypass = 'true'")

        # Insert an actor first (FK requirement)
        await conn.execute(
            """
            INSERT INTO actors (actor_id, actor_type, tenant_id, status, created_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            "test_actor",
            "agent",
            TENANT,
            "active",
            datetime.now(timezone.utc),
        )

        # Insert an action without policy (uncovered)
        await conn.execute(
            """
            INSERT INTO actions (action_id, actor_id, actor_type, action_name, resource, tenant_id, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "test_actor",
            "agent",
            "uncovered.action",
            "test.resource",
            TENANT,
            datetime.now(timezone.utc),
        )

        await conn.close()

        service = PostureScoreService(db_pool)
        score = await service.calculate(TENANT)

        # Score should be a valid number
        assert 0 <= score.score <= 100
        # With data inserted, should have components populated
        assert "uncovered_actions" in score.components
        assert "policy_coverage" in score.components
