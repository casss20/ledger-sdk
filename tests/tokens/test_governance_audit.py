"""
Tests for GovernanceAuditTrail — separated audit log.

Covers:
- Hash chain integrity (tamper-evident)
- Append-only enforcement (no UPDATE/DELETE)
- Tenant isolation via RLS
- Integration with TokenVerifier / ExecutionMiddleware
- Event querying by decision
"""

import pytest
import asyncpg
from datetime import datetime, timezone

from ledger.tokens import (
    CapabilityToken,
    DecisionScope,
    DecisionType,
    GovernanceDecision,
    GovernanceAuditTrail,
    KillSwitch,
    TokenVerifier,
    ExecutionMiddleware,
)


@pytest.fixture
async def db_pool(postgres_dsn):
    pool = await asyncpg.create_pool(postgres_dsn, min_size=1, max_size=2)
    yield pool
    await pool.close()


@pytest.fixture
async def audit(db_pool):
    return GovernanceAuditTrail(db_pool)


@pytest.fixture
async def kill_switch(audit):
    return KillSwitch(audit)


class TestGovernanceAuditTrail:
    @pytest.mark.asyncio
    async def test_record_event(self, audit, tenant_id):
        """Can record an event and get back an event_id."""
        event_id = await audit.record(
            event_type="decision.created",
            tenant_id=tenant_id,
            actor_id="agent_1",
            decision_id="gd_001",
            payload={"action": "file.read"},
        )
        assert isinstance(event_id, int)
        assert event_id > 0

    @pytest.mark.asyncio
    async def test_hash_chain_links(self, audit, tenant_id):
        """Consecutive events have prev_hash pointing to previous event_hash."""
        e1 = await audit.record(
            event_type="decision.created",
            tenant_id=tenant_id,
            actor_id="agent_1",
            decision_id="gd_chain_001",
            payload={"step": 1},
        )
        e2 = await audit.record(
            event_type="token.derived",
            tenant_id=tenant_id,
            actor_id="agent_1",
            decision_id="gd_chain_001",
            token_id="gt_cap_abc",
            payload={"step": 2},
        )

        async with audit.db.acquire() as conn:
            await conn.execute("SELECT set_tenant_context($1)", tenant_id)
            row1 = await conn.fetchrow(
                "SELECT event_hash FROM governance_audit_log WHERE event_id = $1", e1
            )
            row2 = await conn.fetchrow(
                "SELECT prev_hash, event_hash FROM governance_audit_log WHERE event_id = $1", e2
            )
            assert row2["prev_hash"] == row1["event_hash"]
            assert row2["event_hash"] != row2["prev_hash"]

    @pytest.mark.asyncio
    async def test_first_event_genesis_hash(self, audit, tenant_id):
        """First event in empty table has prev_hash = zeros (genesis)."""
        e = await audit.record(
            event_type="decision.created",
            tenant_id=tenant_id,
            actor_id="agent_1",
            decision_id="gd_genesis",
            payload={},
        )

        async with audit.db.acquire() as conn:
            await conn.execute("SELECT set_tenant_context($1)", tenant_id)
            row = await conn.fetchrow(
                "SELECT prev_hash FROM governance_audit_log WHERE event_id = $1", e
            )
            assert row["prev_hash"] == "0" * 64

    @pytest.mark.asyncio
    async def test_verify_chain_valid(self, audit, tenant_id):
        """verify_chain returns valid=True for uncorrupted chain."""
        for i in range(3):
            await audit.record(
                event_type="decision.created",
                tenant_id=tenant_id,
                actor_id="agent_1",
                decision_id=f"gd_verify_{i}",
                payload={"index": i},
            )

        result = await audit.verify_chain(tenant_id=tenant_id)
        assert result["valid"] is True
        assert result["checked_count"] == 3

    @pytest.mark.asyncio
    async def test_append_only_blocks_update(self, audit, tenant_id):
        """UPDATE on governance_audit_log is blocked by trigger."""
        e = await audit.record(
            event_type="decision.created",
            tenant_id=tenant_id,
            actor_id="agent_1",
            decision_id="gd_update_test",
            payload={},
        )

        async with audit.db.acquire() as conn:
            await conn.execute("SET app.admin_bypass = 'true'")
            with pytest.raises(Exception, match="append-only"):
                await conn.execute(
                    "UPDATE governance_audit_log SET payload_json = '{\"tampered\": true}'::jsonb WHERE event_id = $1",
                    e,
                )

    @pytest.mark.asyncio
    async def test_append_only_blocks_delete(self, audit, tenant_id):
        """DELETE on governance_audit_log is blocked by trigger."""
        e = await audit.record(
            event_type="decision.created",
            tenant_id=tenant_id,
            actor_id="agent_1",
            decision_id="gd_delete_test",
            payload={},
        )

        async with audit.db.acquire() as conn:
            await conn.execute("SET app.admin_bypass = 'true'")
            with pytest.raises(Exception, match="append-only"):
                await conn.execute(
                    "DELETE FROM governance_audit_log WHERE event_id = $1", e
                )

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, audit, postgres_dsn, tenant_id):
        """Tenant A cannot see Tenant B's audit events."""
        tenant_a = tenant_id
        tenant_b = f"other_{tenant_id}"

        # Record as tenant A
        await audit.record(
            event_type="decision.created",
            tenant_id=tenant_a,
            actor_id="agent_a",
            decision_id="gd_iso_a",
            payload={},
        )

        # Try to read as tenant B via new connection
        pool_b = await asyncpg.create_pool(
            postgres_dsn,
            min_size=1,
            max_size=1,
            init=lambda conn: conn.execute("SELECT set_tenant_context($1)", tenant_b),
        )
        try:
            async with pool_b.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM governance_audit_log WHERE tenant_id = $1", tenant_a
                )
                assert len(rows) == 0
        finally:
            await pool_b.close()

    @pytest.mark.asyncio
    async def test_query_by_decision(self, audit, tenant_id):
        """query_by_decision returns events for that decision."""
        decision_id = "gd_query_test"
        for i in range(3):
            await audit.record(
                event_type="token.verification",
                tenant_id=tenant_id,
                actor_id="agent_1",
                decision_id=decision_id,
                payload={"seq": i},
            )
        # Unrelated decision
        await audit.record(
            event_type="decision.created",
            tenant_id=tenant_id,
            actor_id="agent_1",
            decision_id="gd_other",
            payload={},
        )

        events = await audit.query_by_decision(decision_id, tenant_id=tenant_id)
        assert len(events) == 3
        for ev in events:
            assert ev["decision_id"] == decision_id
            assert ev["event_type"] == "token.verification"

    @pytest.mark.asyncio
    async def test_typed_methods(self, audit, tenant_id):
        """Typed record methods work and return event_ids."""
        e1 = await audit.record_token_verification(
            tenant_id=tenant_id,
            actor_id="agent_1",
            token_id="gt_cap_t1",
            decision_id="gd_t1",
            valid=True,
            reason="verified",
        )
        e2 = await audit.record_execution_allowed(
            tenant_id=tenant_id,
            actor_id="agent_1",
            decision_id="gd_t1",
            action="file.read",
        )
        e3 = await audit.record_execution_blocked(
            tenant_id=tenant_id,
            actor_id="agent_1",
            decision_id="gd_t1",
            action="file.delete",
            reason="scope_mismatch",
        )
        assert all(isinstance(e, int) for e in (e1, e2, e3))

        events = await audit.query_by_decision("gd_t1", tenant_id=tenant_id)
        assert len(events) == 3
        types = {e["event_type"] for e in events}
        assert types == {"token.verification", "execution.allowed", "execution.blocked"}


class TestAuditIntegrationWithVerifier:
    @pytest.mark.asyncio
    async def test_verifier_uses_governance_audit(self, db_pool, tenant_id):
        """TokenVerifier with GovernanceAuditTrail records to separated audit log."""
        audit = GovernanceAuditTrail(db_pool)
        ks = KillSwitch(audit)

        # Minimal in-memory vault
        class MiniVault:
            def __init__(self):
                self._tokens = {}
                self._decisions = {}

            async def resolve_token(self, token_id, **kwargs):
                return self._tokens.get(token_id)

            async def resolve_decision(self, decision_id, **kwargs):
                return self._decisions.get(decision_id)

        vault = MiniVault()
        verifier = TokenVerifier(vault, ks, audit)

        decision = GovernanceDecision(
            decision_id="gd_integ",
            decision_type=DecisionType.ALLOW,
            tenant_id=tenant_id,
            actor_id="agent_integ",
            action="file.read",
            scope=DecisionScope(actions=["file.read"]),
        )
        token = CapabilityToken.derive(decision)

        vault._tokens[token.token_id] = {
            "token_id": token.token_id,
            "decision_id": decision.decision_id,
            "tenant_id": tenant_id,
            "actor_id": "agent_integ",
            "scope_actions": ["file.read"],
            "scope_resources": [],
            "expiry": None,
        }
        vault._decisions[decision.decision_id] = {
            "decision_id": decision.decision_id,
            "decision_type": "allow",
            "tenant_id": tenant_id,
            "actor_id": "agent_integ",
            "action": "file.read",
            "scope_actions": ["file.read"],
            "scope_resources": [],
            "expiry": None,
            "kill_switch_scope": "request",
        }

        result = await verifier.verify_token(token.token_id, "file.read")
        assert result.valid is True

        # Check audit was recorded
        events = await audit.query_by_decision("gd_integ", tenant_id=tenant_id)
        assert len(events) >= 1
        assert any(e["event_type"] == "token.verification" for e in events)

    @pytest.mark.asyncio
    async def test_middleware_uses_governance_audit(self, db_pool, tenant_id):
        """ExecutionMiddleware with GovernanceAuditTrail records execution events."""
        audit = GovernanceAuditTrail(db_pool)
        ks = KillSwitch(audit)

        class MiniVault:
            async def resolve_token(self, token_id, **kwargs):
                return None
            async def resolve_decision(self, decision_id, **kwargs):
                return None

        vault = MiniVault()
        verifier = TokenVerifier(vault, ks, audit)
        middleware = ExecutionMiddleware(verifier, audit)

        # Try with non-existent token → should record execution.blocked
        result = await middleware.check(
            "gt_cap_nonexistent", "file.read", context={"tenant_id": tenant_id, "actor_id": "agent_x"}
        )
        assert result.valid is False

        events = await audit.query_by_decision(None, tenant_id=tenant_id)
        # None decision_id filter won't work well; just check all events for tenant
        async with audit.db.acquire() as conn:
            await conn.execute("SELECT set_tenant_context($1)", tenant_id)
            rows = await conn.fetch(
                "SELECT event_type FROM governance_audit_log WHERE tenant_id = $1",
                tenant_id,
            )
        types = [r["event_type"] for r in rows]
        assert "execution.blocked" in types
