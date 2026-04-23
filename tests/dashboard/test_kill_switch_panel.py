"""
Tests for Kill Switch Panel (Phase 2 Compliance).

Target: 6 tests passing.
"""

import pytest
from datetime import datetime, timezone, timedelta
from ledger.dashboard.kill_switch_panel import (
    KillSwitchPanelService, KillSwitchScope, KillSwitchStatus,
)


import uuid

TENANT = "test_tenant"


class TestKillSwitchPanel:
    """Test kill switch panel service."""

    @pytest.fixture(autouse=True, scope="function")
    async def setup_test_data(self, db_pool):
        """Insert test kill switch data."""
        async with db_pool.acquire() as conn:
            await conn.execute("SET app.admin_bypass = 'true'")

            # Clear old test data
            await conn.execute("DELETE FROM kill_switches WHERE tenant_id = $1", TENANT)

            now = datetime.now(timezone.utc)

            # Insert active kill switches
            await conn.execute(
                """
                INSERT INTO kill_switches (switch_id, tenant_id, scope_type, scope_value, enabled, reason, created_by, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                uuid.uuid4(), TENANT, "tenant", TENANT, True, "Test tenant kill switch", "admin", now, now,
            )

            await conn.execute(
                """
                INSERT INTO kill_switches (switch_id, tenant_id, scope_type, scope_value, enabled, reason, created_by, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                uuid.uuid4(), TENANT, "actor", "agent_123", True, "Test agent kill switch", "admin", now, now,
            )

    @pytest.mark.asyncio
    async def test_get_status_returns_kill_switches(self, db_pool):
        """Status includes all active kill switches."""
        service = KillSwitchPanelService(db_pool)
        statuses = await service.get_status(TENANT)

        # Should have tenant + at least one agent
        assert len(statuses) >= 2
        tenant_status = next((s for s in statuses if s.scope == KillSwitchScope.TENANT), None)
        assert tenant_status is not None
        assert tenant_status.is_active is True

    @pytest.mark.asyncio
    async def test_initiate_kill_requires_confirmation(self, db_pool):
        """Kill switch initiation is pending until confirmed."""
        service = KillSwitchPanelService(db_pool)

        initiation = await service.initiate_kill(
            TENANT,
            KillSwitchScope.AGENT,
            "agent_456",
            "admin",
            "Emergency stop",
        )

        assert initiation.status == "pending_confirmation"
        assert initiation.requires_second_approver is False

    @pytest.mark.asyncio
    async def test_global_kill_requires_second_approver(self, db_pool):
        """Global scope kill switch requires second approver."""
        service = KillSwitchPanelService(db_pool)

        initiation = await service.initiate_kill(
            TENANT,
            KillSwitchScope.GLOBAL,
            "global",
            "admin",
            "Emergency stop all",
        )

        assert initiation.requires_second_approver is True

    @pytest.mark.asyncio
    async def test_confirm_kill_requires_mfa(self, db_pool):
        """MFA required to confirm kill switch."""
        service = KillSwitchPanelService(db_pool)

        # Bad MFA should fail
        with pytest.raises(ValueError, match="MFA verification failed"):
            await service.confirm_kill("some_id", "bad_token")

    @pytest.mark.asyncio
    async def test_test_kill_switch_returns_result(self, db_pool):
        """Kill switch test returns success/failure result."""
        service = KillSwitchPanelService(db_pool)

        result = await service.test_kill_switch(TENANT)

        assert isinstance(result.success, bool)
        assert result.test_duration_ms >= 0
        assert result.tested_at is not None

    @pytest.mark.asyncio
    async def test_history_returns_events(self, db_pool):
        """History returns kill switch events."""
        service = KillSwitchPanelService(db_pool)

        events = await service.get_history(TENANT, days=30)

        assert len(events) >= 2
        for event in events:
            assert event.tenant_id == TENANT
            assert event.action == "triggered"
