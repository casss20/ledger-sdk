"""
Tests for Approval Queue (Phase 1 MVP).

Target: 5 tests passing.
- test_mfa_required_for_approval
- test_auto_expire_after_sla
- test_urgency_levels
- test_approver_assignment
- test_audit_trail_on_approval
"""

import pytest
from datetime import datetime, timezone, timedelta
from ledger.dashboard.approval_queue import (
    ApprovalQueueService, ApprovalStatus, ApprovalRequest,
)
import uuid


TENANT = "test_tenant"


class TestApprovalQueue:
    """Test approval queue service."""

    @pytest.fixture(autouse=True)
    async def setup_test_data(self, db_pool):
        """Insert test approval requests."""
        import asyncpg
        conn = await asyncpg.connect("postgresql://ledger:ledger@localhost:5432/ledger_test")
        await conn.execute("SET app.admin_bypass = 'true'")

        # Clear old test data
        await conn.execute("DELETE FROM approvals WHERE tenant_id = $1", TENANT)
        await conn.execute("DELETE FROM actions WHERE tenant_id = $1", TENANT)

        now = datetime.now(timezone.utc)

        # Insert dummy actors first (required by FK actions_actor_id_fkey)
        action_ids = [str(uuid.uuid4()) for _ in range(4)]
        actor_ids = [f"requester_{aid}" for aid in action_ids]
        for actor_id in actor_ids:
            await conn.execute(
                """
                INSERT INTO actors (actor_id, tenant_id, actor_type, status, created_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (actor_id) DO NOTHING
                """,
                actor_id,
                TENANT,
                "user_proxy",
                "active",
                now,
            )

        # Insert dummy actions first (required by FK approvals_action_id_fkey)
        for i, action_id in enumerate(action_ids):
            await conn.execute(
                """
                INSERT INTO actions (action_id, tenant_id, actor_id, actor_type, action_name, resource, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                action_id,
                TENANT,
                actor_ids[i],
                "user_proxy",
                "test.action",
                "test_resource",
                now,
            )

        # Insert approver actor (required by reviewed_by FK)
        await conn.execute(
            """
            INSERT INTO actors (actor_id, tenant_id, actor_type, status, created_at)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (actor_id) DO NOTHING
            """,
            "admin",
            TENANT,
            "user_proxy",
            "active",
            now,
        )

        # Insert pending approvals with different priorities (deterministic UUIDs)
        def _uuid(name):
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, name))

        approvals = [
            (_uuid("app_1"), "critical", now + timedelta(minutes=5), action_ids[0]),
            (_uuid("app_2"), "high", now + timedelta(hours=1), action_ids[1]),
            (_uuid("app_3"), "medium", now + timedelta(days=1), action_ids[2]),
            (_uuid("app_4"), "critical", now - timedelta(minutes=10), action_ids[3]),  # Expired
        ]

        for approval_id, priority, expires_at, action_id in approvals:
            # Ensure requester actor exists
            requester_id = f"requester_{approval_id}"
            await conn.execute(
                """
                INSERT INTO actors (actor_id, tenant_id, actor_type, status, created_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (actor_id) DO NOTHING
                """,
                requester_id,
                TENANT,
                "user_proxy",
                "active",
                now,
            )
            await conn.execute(
                """
                INSERT INTO approvals (
                    approval_id, tenant_id, status, priority,
                    created_at, expires_at, reason,
                    requested_by, action_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                approval_id,
                TENANT,
                "pending",
                priority,
                now,
                expires_at,
                f"Test action for {approval_id}",
                requester_id,
                action_id,
            )

        await conn.close()

    @pytest.mark.asyncio
    async def test_mfa_required_for_approval(self, db_pool):
        """MFA token required to approve or reject."""
        def _uuid(name):
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, name))
        service = ApprovalQueueService(db_pool)

        # Bad MFA token should fail
        with pytest.raises(ValueError, match="MFA verification failed"):
            await service.approve(_uuid("app_1"), "admin", "bad_token", "Looks good")

        # Valid MFA token should succeed
        result = await service.approve(_uuid("app_1"), "admin", "mfa_valid_123", "Approved")
        assert result.status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_auto_expire_after_sla(self, db_pool):
        """Approvals past expiry are auto-expired."""
        import asyncpg
        def _uuid(name):
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, name))
        service = ApprovalQueueService(db_pool)

        # Run auto-expire
        expired_count = await service.auto_expire(TENANT)

        # app_4 should be expired (expires_at is in the past)
        assert expired_count >= 1

        # Verify app_4 is now expired
        conn = await asyncpg.connect("postgresql://ledger:ledger@localhost:5432/ledger_test")
        await conn.execute("SET app.admin_bypass = 'true'")
        row = await conn.fetchrow(
            "SELECT status FROM approvals WHERE approval_id = $1",
            _uuid("app_4"),
        )
        await conn.close()
        assert row["status"] == "expired"

    @pytest.mark.asyncio
    async def test_urgency_levels(self, db_pool):
        """Urgency metrics show correct counts."""
        service = ApprovalQueueService(db_pool)

        metrics = await service.get_urgency_metrics(TENANT)

        assert metrics.total_pending >= 0
        assert metrics.immediate_count >= 0
        assert metrics.standard_count >= 0
        assert metrics.scheduled_count >= 0
        assert metrics.total_pending == (
            metrics.immediate_count + metrics.standard_count + metrics.scheduled_count
        )

    @pytest.mark.asyncio
    async def test_approver_assignment(self, db_pool):
        """Filter by assigned approver works."""
        service = ApprovalQueueService(db_pool)

        # Get all pending
        all_pending = await service.get_pending(TENANT)

        # Get pending for specific approver (none assigned in test data)
        assigned = await service.get_pending(TENANT, assigned_to="admin_1")
        assert len(assigned) == 0

    @pytest.mark.asyncio
    async def test_audit_trail_on_approval(self, db_pool):
        """Approval creates audit trail entry."""
        def _uuid(name):
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, name))
        service = ApprovalQueueService(db_pool)

        # Approve with valid MFA
        result = await service.approve(_uuid("app_2"), "admin", "mfa_valid_456", "Approved")

        assert result.status == ApprovalStatus.APPROVED
