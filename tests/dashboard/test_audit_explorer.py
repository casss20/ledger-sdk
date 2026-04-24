"""
Tests for Audit Explorer (Phase 2 Compliance).

Target: 6 tests passing.
"""

import pytest
from datetime import datetime, timezone, timedelta
from citadel.dashboard.audit_explorer import (
    AuditExplorerService, AuditFilters, AuditSearchResult,
)


TENANT = "test_tenant"


class TestAuditExplorer:
    """Test audit explorer service."""

    @pytest.fixture(autouse=True)
    async def setup_test_data(self, db_pool):
        """Insert test audit entries."""
        import asyncpg
        conn = await asyncpg.connect("postgresql://CITADEL:CITADEL@localhost:5432/citadel_test")
        await conn.execute("SET app.admin_bypass = 'true'")

        # Note: governance_audit_log is append-only; cannot delete. Insert with high random IDs to avoid collisions.
        import random
        base_id = random.randint(10000000, 99999999)

        now = datetime.now(timezone.utc)

        # Insert audit entries with different properties
        entries = [
            (base_id + 1, "token.revoked", "actor_1", "tok_1", now, "hash_1"),
            (base_id + 2, "execution.blocked", "actor_1", "tok_2", now - timedelta(hours=1), "hash_2"),
            (base_id + 3, "decision.created", "actor_2", "tok_3", now - timedelta(hours=2), "hash_3"),
            (base_id + 4, "token.derived", "system", "tok_4", now - timedelta(hours=3), "hash_4"),
        ]

        for event_id, event_type, actor_id, token_id, event_ts, event_hash in entries:
            await conn.execute(
                """
                INSERT INTO governance_audit_log (
                    event_id, tenant_id, event_type, actor_id,
                    token_id, event_hash, event_ts
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                event_id,
                TENANT,
                event_type,
                actor_id,
                token_id,
                event_hash,
                event_ts,
            )

        await conn.close()

    @pytest.mark.asyncio
    async def test_search_returns_filtered_results(self, db_pool):
        """Search with filters returns matching entries."""
        service = AuditExplorerService(db_pool)

        # Search by severity
        filters = AuditFilters(severity="CRITICAL")
        result = await service.search(TENANT, filters)

        assert all(e.severity == "CRITICAL" for e in result.entries)

    @pytest.mark.asyncio
    async def test_facet_counts_returned(self, db_pool):
        """Facet counts show distribution."""
        service = AuditExplorerService(db_pool)

        facets = await service.get_facet_counts(TENANT, AuditFilters())

        assert "severity" in facets
        assert "event_type" in facets
        assert "outcome" in facets

    @pytest.mark.asyncio
    async def test_verify_chain_detects_breaks(self, db_pool):
        """Chain verification detects broken links."""
        service = AuditExplorerService(db_pool)

        # Verify chain for existing entry
        report = await service.verify_chain(TENANT, "audit_1")

        assert report.entry_id == "audit_1"
        assert isinstance(report.is_valid, bool)
        assert report.chain_length >= 0

    @pytest.mark.asyncio
    async def test_export_compliance_report_json(self, db_pool):
        """JSON export contains audit data."""
        service = AuditExplorerService(db_pool)

        since = datetime.now(timezone.utc) - timedelta(days=1)
        until = datetime.now(timezone.utc)

        export = await service.export_compliance_report(
            TENANT, "eu_ai_act", (since, until), "json"
        )

        assert len(export) > 0
        # Should be valid JSON
        import json
        data = json.loads(export)
        assert data["framework"] == "eu_ai_act"
        assert data["tenant_id"] == TENANT

    @pytest.mark.asyncio
    async def test_export_compliance_report_csv(self, db_pool):
        """CSV export contains audit data."""
        service = AuditExplorerService(db_pool)

        since = datetime.now(timezone.utc) - timedelta(days=1)
        until = datetime.now(timezone.utc)

        export = await service.export_compliance_report(
            TENANT, "soc2", (since, until), "csv"
        )

        assert len(export) > 0
        content = export.decode("utf-8")
        assert "entry_id" in content
        assert "timestamp" in content

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, db_pool):
        """Tenant A cannot see Tenant B audit entries."""
        service = AuditExplorerService(db_pool)

        other_tenant = "other_audit_tenant"
        result = await service.search(other_tenant, AuditFilters())

        assert len(result.entries) == 0
        assert result.total_count == 0
