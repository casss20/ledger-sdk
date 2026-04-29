"""
Tests for trust policy engine: action matrix, decision integration, determinism.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from citadel.agent_identity.trust_bands import TrustBand
from citadel.agent_identity.trust_policy import (
    TrustPolicyEngine,
    TrustPolicyResult,
    TrustPolicyContext,
    ACTION_MATRIX,
    get_action_matrix_status,
    TrustCircuitBreaker,
)


class TestActionMatrix:
    """Test the action matrix for all bands."""

    def test_revoked_blocks_all_orchestration(self):
        for action in ["execute", "delegate", "handoff", "gather", "introspect"]:
            status = get_action_matrix_status(action, TrustBand.REVOKED)
            assert status == "blocked", f"{action} should be blocked in REVOKED"

    def test_probation_blocks_orchestration(self):
        assert get_action_matrix_status("delegate", TrustBand.PROBATION) == "blocked"
        assert get_action_matrix_status("handoff", TrustBand.PROBATION) == "blocked"
        assert get_action_matrix_status("gather", TrustBand.PROBATION) == "blocked"

    def test_probation_allows_execute_with_introspection(self):
        assert get_action_matrix_status("execute", TrustBand.PROBATION) == "introspection_required"

    def test_standard_allows_basic_actions(self):
        assert get_action_matrix_status("execute", TrustBand.STANDARD) == "allowed"
        assert get_action_matrix_status("introspect", TrustBand.STANDARD) == "allowed"

    def test_standard_requires_approval_for_handoff(self):
        assert get_action_matrix_status("handoff", TrustBand.STANDARD) == "approval"
        assert get_action_matrix_status("gather", TrustBand.STANDARD) == "approval"

    def test_trusted_allows_orchestration(self):
        assert get_action_matrix_status("delegate", TrustBand.TRUSTED) == "allowed"
        assert get_action_matrix_status("handoff", TrustBand.TRUSTED) == "allowed"
        assert get_action_matrix_status("gather", TrustBand.TRUSTED) == "allowed"

    def test_all_bands_block_destroy_for_protection(self):
        """Even highly trusted agents need approval for destructive actions."""
        for band in [TrustBand.STANDARD, TrustBand.TRUSTED, TrustBand.HIGHLY_TRUSTED]:
            status = get_action_matrix_status("destroy", band)
            assert status == "approval", f"destroy should require approval in {band.value}"

    def test_revoked_blocks_destroy(self):
        assert get_action_matrix_status("destroy", TrustBand.REVOKED) == "blocked"
        assert get_action_matrix_status("destroy", TrustBand.PROBATION) == "blocked"

    def test_unknown_action_defaults_to_approval(self):
        """Unknown actions should be safe by default."""
        assert get_action_matrix_status("unknown_action", TrustBand.STANDARD) == "approval"

    def test_kill_switch_trigger_approval_standard(self):
        assert get_action_matrix_status("kill_switch_trigger", TrustBand.STANDARD) == "approval"
        assert get_action_matrix_status("kill_switch_trigger", TrustBand.TRUSTED) == "allowed"


class TestTrustPolicyResult:
    """Test trust policy result data structure."""

    def test_default_result(self):
        r = TrustPolicyResult()
        assert r.requires_approval is False
        assert r.max_spend_multiplier == 1.0
        assert r.rate_limit_multiplier == 1.0
        assert r.action_blocked is False

    def test_result_serialization(self):
        r = TrustPolicyResult(
            requires_approval=True,
            approval_reason="Test reason",
            trust_band="STANDARD",
            trust_snapshot_id="snap-123",
        )
        d = r.to_dict()
        assert d["requires_approval"] is True
        assert d["approval_reason"] == "Test reason"
        assert d["trust_band"] == "STANDARD"
        assert d["trust_snapshot_id"] == "snap-123"


class TestTrustPolicyContext:
    """Test trust policy context data structure."""

    def test_context_serialization(self):
        ctx = TrustPolicyContext(
            band=TrustBand.STANDARD,
            score=0.55,
            snapshot_id="snap-123",
            probation_active=False,
        )
        d = ctx.to_dict()
        assert d["trust_band"] == "standard"
        assert d["trust_score"] == 0.55
        assert d["trust_snapshot_id"] == "snap-123"
        assert d["trust_probation_active"] is False

    def test_probation_context(self):
        ctx = TrustPolicyContext(
            band=TrustBand.PROBATION,
            score=0.30,
            probation_active=True,
            probation_until=datetime.now(timezone.utc) + timedelta(days=7),
            probation_reason="New agent",
        )
        d = ctx.to_dict()
        assert d["trust_probation_active"] is True
        assert d["trust_probation_reason"] == "New agent"


class TestTrustPolicyEngineEvaluation:
    """Test the trust policy engine with mocked database."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database pool."""
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        return pool, conn

    @pytest.mark.asyncio
    async def test_no_trust_data_defaults_to_probation(self, mock_db):
        pool, conn = mock_db
        conn.fetchrow.return_value = None  # No trust snapshot

        engine = TrustPolicyEngine(pool)
        result = await engine.evaluate(
            action="execute",
            actor_id="agent-1",
            tenant_id="tenant-1",
            base_context={},
        )

        assert result.trust_band == "probation"
        assert result.requires_approval is True
        assert result.requires_introspection is True

    @pytest.mark.asyncio
    async def test_standard_band_allows_execute(self, mock_db):
        pool, conn = mock_db
        conn.fetchrow.return_value = {
            "snapshot_id": "snap-1",
            "score": 0.55,
            "band": "STANDARD",
            "factors": {"health": 0.2},
            "probation_until": None,
        }

        engine = TrustPolicyEngine(pool)
        result = await engine.evaluate(
            action="execute",
            actor_id="agent-1",
            tenant_id="tenant-1",
            base_context={},
        )

        assert result.trust_band == "standard"
        assert result.action_blocked is False
        assert result.requires_approval is False
        assert result.trust_snapshot_id == "snap-1"

    @pytest.mark.asyncio
    async def test_probation_blocks_delegate(self, mock_db):
        pool, conn = mock_db
        conn.fetchrow.return_value = {
            "snapshot_id": "snap-1",
            "score": 0.30,
            "band": "PROBATION",
            "factors": {},
            "probation_until": datetime.now(timezone.utc) + timedelta(days=3),
        }

        engine = TrustPolicyEngine(pool)
        result = await engine.evaluate(
            action="delegate",
            actor_id="agent-1",
            tenant_id="tenant-1",
            base_context={},
        )

        assert result.action_blocked is True
        assert "delegate" in result.block_reason

    @pytest.mark.asyncio
    async def test_active_probation_overrides_band(self, mock_db):
        """If probation_until > now, band is forced to PROBATION."""
        pool, conn = mock_db
        conn.fetchrow.return_value = {
            "snapshot_id": "snap-1",
            "score": 0.70,  # Would normally be TRUSTED
            "band": "TRUSTED",
            "factors": {},
            "probation_until": datetime.now(timezone.utc) + timedelta(days=3),
        }

        engine = TrustPolicyEngine(pool)
        result = await engine.evaluate(
            action="delegate",
            actor_id="agent-1",
            tenant_id="tenant-1",
            base_context={},
        )

        assert result.trust_band == "probation"
        assert result.action_blocked is True  # Probation blocks delegate

    @pytest.mark.asyncio
    async def test_destroy_requires_approval(self, mock_db):
        pool, conn = mock_db
        conn.fetchrow.return_value = {
            "snapshot_id": "snap-1",
            "score": 0.90,
            "band": "HIGHLY_TRUSTED",
            "factors": {},
            "probation_until": None,
        }

        engine = TrustPolicyEngine(pool)
        result = await engine.evaluate(
            action="destroy",
            actor_id="agent-1",
            tenant_id="tenant-1",
            base_context={},
        )

        assert result.trust_band == "highly_trusted"
        assert result.requires_approval is True  # Even highly trusted need approval for destroy
        assert result.action_blocked is False

    @pytest.mark.asyncio
    async def test_trusted_gets_spend_multiplier(self, mock_db):
        pool, conn = mock_db
        conn.fetchrow.return_value = {
            "snapshot_id": "snap-1",
            "score": 0.70,
            "band": "TRUSTED",
            "factors": {},
            "probation_until": None,
        }

        engine = TrustPolicyEngine(pool)
        result = await engine.evaluate(
            action="execute",
            actor_id="agent-1",
            tenant_id="tenant-1",
            base_context={},
        )

        assert result.max_spend_multiplier == 1.5
        assert result.rate_limit_multiplier == 2.0

    @pytest.mark.asyncio
    async def test_revoked_blocks_everything(self, mock_db):
        pool, conn = mock_db
        conn.fetchrow.return_value = {
            "snapshot_id": "snap-1",
            "score": 0.10,
            "band": "REVOKED",
            "factors": {},
            "probation_until": None,
        }

        engine = TrustPolicyEngine(pool)
        result = await engine.evaluate(
            action="execute",
            actor_id="agent-1",
            tenant_id="tenant-1",
            base_context={},
        )

        assert result.action_blocked is True
        assert result.max_spend_multiplier == 0.0
        assert result.rate_limit_multiplier == 0.0


class TestTrustCircuitBreaker:
    """Test circuit breaker behavior."""

    @pytest.mark.asyncio
    async def test_fires_below_threshold(self):
        cb = TrustCircuitBreaker()
        should_fire, reason, target = await cb.check(
            actor_id="agent-1",
            current_score=0.10,
            current_band=TrustBand.REVOKED,
            db_pool=None,
        )
        assert should_fire is True
        assert target == TrustBand.REVOKED

    @pytest.mark.asyncio
    async def test_does_not_fire_above_threshold(self):
        cb = TrustCircuitBreaker()
        should_fire, reason, target = await cb.check(
            actor_id="agent-1",
            current_score=0.50,
            current_band=TrustBand.STANDARD,
            db_pool=None,
        )
        assert should_fire is False

    @pytest.mark.asyncio
    async def test_fires_for_revoked_band(self):
        cb = TrustCircuitBreaker()
        should_fire, reason, target = await cb.check(
            actor_id="agent-1",
            current_score=0.50,  # Score is fine but band is revoked
            current_band=TrustBand.REVOKED,
            db_pool=None,
        )
        assert should_fire is True


class TestDeterminism:
    """Test that trust policy evaluation is deterministic."""

    @pytest.fixture
    def mock_db(self):
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        return pool, conn

    @pytest.mark.asyncio
    async def test_same_inputs_same_outputs(self, mock_db):
        """Evaluating twice with same snapshot should produce same result."""
        pool, conn = mock_db
        conn.fetchrow.return_value = {
            "snapshot_id": "snap-1",
            "score": 0.55,
            "band": "STANDARD",
            "factors": {},
            "probation_until": None,
        }

        engine = TrustPolicyEngine(pool)

        r1 = await engine.evaluate("execute", "agent-1", "tenant-1", {})
        r2 = await engine.evaluate("execute", "agent-1", "tenant-1", {})

        assert r1.to_dict() == r2.to_dict()

    @pytest.mark.asyncio
    async def test_band_mapping_is_deterministic(self, mock_db):
        """Score 0.55 always maps to STANDARD, never anything else."""
        pool, conn = mock_db
        conn.fetchrow.return_value = {
            "snapshot_id": "snap-1",
            "score": 0.55,
            "band": "STANDARD",
            "factors": {},
            "probation_until": None,
        }

        engine = TrustPolicyEngine(pool)
        result = await engine.evaluate("execute", "agent-1", "tenant-1", {})

        assert result.trust_band == "standard"
