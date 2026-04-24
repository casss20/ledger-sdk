"""
Phase 4: Governance Integration into Action Execution Pipeline

Tests that governance tokens (gt_cap_*) and kill switches are enforced
when actions are submitted via the kernel execution pipeline.
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta

import httpx

import CITADEL.config
CITADEL.config.settings.require_auth = True
CITADEL.config.settings.api_keys = "test-key"
CITADEL.config.settings.database_url = "postgresql://CITADEL:CITADEL@localhost:5432/citadel_test"

from CITADEL.api import app
from CITADEL.tokens import (
    GovernanceDecision,
    DecisionType,
    DecisionScope,
    CapabilityToken,
    TokenVault,
    KillSwitch,
    KillSwitchScope,
    TokenVerifier,
)


BASE_URL = "http://test"
API_KEY = "test-key"
TENANT = "exec_test_tenant"
ACTOR = "exec_test_agent"


def _headers(tenant: str = TENANT):
    return {
        "X-API-Key": API_KEY,
        "X-Tenant-ID": tenant,
        "Content-Type": "application/json",
    }


class MockAuditLogger:
    """Minimal mock for KillSwitch / TokenVerifier audit dependency."""
    async def record(self, **kwargs):
        pass


class TestGovernanceTokenExecution:
    """Actions submitted with governance tokens flow through the kernel."""

    @pytest.mark.asyncio
    async def test_action_allowed_with_governance_token(self, db_pool):
        """Submit action with a valid gt_cap_* token â†’ allowed + executed."""
        import asyncpg

        # Create a tenant-scoped pool so RLS works through the HTTP layer
        async def _setup(conn):
            await conn.execute("SELECT set_tenant_context($1)", TENANT)

        scoped_pool = await asyncpg.create_pool(
            "postgresql://CITADEL:CITADEL@localhost:5432/citadel_test",
            min_size=1, max_size=2, setup=_setup,
        )
        app.state.db_pool = scoped_pool
        vault = TokenVault(scoped_pool)

        # Insert actor first (FK constraint on actions table)
        conn = await asyncpg.connect("postgresql://CITADEL:CITADEL@localhost:5432/citadel_test")
        await conn.execute("SET app.admin_bypass = 'true'")
        await conn.execute(
            """
            INSERT INTO actors (actor_id, actor_type, tenant_id, status)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (actor_id) DO NOTHING
            """,
            ACTOR, "agent", TENANT, "active",
        )
        await conn.close()

        # 1. Create an ALLOW decision
        decision = GovernanceDecision(
            decision_id=GovernanceDecision.generate_id(),
            decision_type=DecisionType.ALLOW,
            actor_id=ACTOR,
            action="test.scope_match",
            scope=DecisionScope(
                actions=["test.scope_match"],
                resources=["resource_42"],
            ),
            expiry=datetime.now(timezone.utc) + timedelta(minutes=10),
            tenant_id=TENANT,
        )
        await vault.store_decision(decision)

        # 2. Derive and store token
        token = CapabilityToken.derive(decision)
        await vault.store_token(token)
        assert token.token_id.startswith("gt_cap_")

        # 3. Submit action with the token via ASGI transport
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as client:
            resp = await client.post(
                "/v1/actions",
                headers=_headers(),
                json={
                    "actor_id": ACTOR,
                    "actor_type": "agent",
                    "action_name": "test.scope_match",
                    "resource": "resource_42",
                    "tenant_id": TENANT,
                    "payload": {},
                    "capability_token": token.token_id,
                },
            )
        await scoped_pool.close()
        assert resp.status_code == 202, resp.text
        data = resp.json()
        assert data["status"] == "executed"
        assert data["executed"] is True
        # winning_rule is set by kernel terminal decision: "execution_complete" for successful execution

    @pytest.mark.asyncio
    async def test_action_blocked_by_governance_kill_switch(self):
        """Governance kill switch at TENANT scope blocks execution."""
        ks = KillSwitch(audit_logger=MockAuditLogger())
        await ks.trigger(
            scope=KillSwitchScope.TENANT,
            target_id=TENANT,
            triggered_by="test_admin",
            triggered_by_type="human",
            reason="Emergency maintenance",
        )

        from CITADEL.precedence import Precedence
        from CITADEL.policy_resolver import PolicyEvaluator
        from CITADEL.actions import Action, KernelStatus

        precedence = Precedence(
            repository=None,
            policy_evaluator=PolicyEvaluator(),
            token_verifier=None,
            governance_kill_switch=ks,
        )

        action = Action(
            action_id=uuid.uuid4(),
            actor_id=ACTOR,
            actor_type="agent",
            action_name="test.anything",
            resource="resource_x",
            tenant_id=TENANT,
            payload={},
            context={},
            session_id=None,
            request_id=None,
            idempotency_key=None,
            created_at=datetime.now(timezone.utc),
        )

        result = await precedence.evaluate(action, None, None, {})
        assert result.blocked is True
        assert result.status == KernelStatus.BLOCKED_EMERGENCY
        assert result.winning_rule == "kill_switch_active"
        # KillSwitch returns scope-level reason, not the trigger reason
        assert "tenant" in (result.reason or "").lower()

    @pytest.mark.asyncio
    async def test_action_blocked_by_expired_governance_token(self, db_pool):
        """Expired governance token blocks action at capability check."""
        vault = TokenVault(db_pool)

        decision = GovernanceDecision(
            decision_id=GovernanceDecision.generate_id(),
            decision_type=DecisionType.ALLOW,
            actor_id=ACTOR,
            action="test.expired",
            scope=DecisionScope(
                actions=["test.expired"],
                resources=["res"],
            ),
            expiry=datetime.now(timezone.utc) - timedelta(minutes=1),
            tenant_id=TENANT,
        )
        await vault.store_decision(decision)
        token = CapabilityToken.derive(decision)
        await vault.store_token(token)

        from CITADEL.precedence import Precedence
        from CITADEL.policy_resolver import PolicyEvaluator
        from CITADEL.actions import Action, KernelStatus

        verifier = TokenVerifier(vault, None, MockAuditLogger())
        precedence = Precedence(
            repository=None,
            policy_evaluator=PolicyEvaluator(),
            token_verifier=verifier,
            governance_kill_switch=None,
        )

        action = Action(
            action_id=uuid.uuid4(),
            actor_id=ACTOR,
            actor_type="agent",
            action_name="test.expired",
            resource="res",
            tenant_id=TENANT,
            payload={},
            context={},
            session_id=None,
            request_id=None,
            idempotency_key=None,
            created_at=datetime.now(timezone.utc),
        )

        result = await precedence.evaluate(action, None, token.token_id, {})
        assert result.blocked is True
        assert result.status == KernelStatus.BLOCKED_CAPABILITY
        assert result.winning_rule == "capability_invalid"

    @pytest.mark.asyncio
    async def test_action_blocked_by_mismatched_scope(self, db_pool):
        """Token for action 'foo.bar' rejected for action 'baz.qux'."""
        vault = TokenVault(db_pool)

        decision = GovernanceDecision(
            decision_id=GovernanceDecision.generate_id(),
            decision_type=DecisionType.ALLOW,
            actor_id=ACTOR,
            action="test.allowed_action",
            scope=DecisionScope(
                actions=["test.allowed_action"],
                resources=["res_a"],
            ),
            expiry=datetime.now(timezone.utc) + timedelta(minutes=10),
            tenant_id=TENANT,
        )
        await vault.store_decision(decision)
        token = CapabilityToken.derive(decision)
        await vault.store_token(token)

        from CITADEL.precedence import Precedence
        from CITADEL.policy_resolver import PolicyEvaluator
        from CITADEL.actions import Action, KernelStatus

        verifier = TokenVerifier(vault, None, MockAuditLogger())
        precedence = Precedence(
            repository=None,
            policy_evaluator=PolicyEvaluator(),
            token_verifier=verifier,
            governance_kill_switch=None,
        )

        action = Action(
            action_id=uuid.uuid4(),
            actor_id=ACTOR,
            actor_type="agent",
            action_name="test.different_action",  # mismatched
            resource="res_a",
            tenant_id=TENANT,
            payload={},
            context={},
            session_id=None,
            request_id=None,
            idempotency_key=None,
            created_at=datetime.now(timezone.utc),
        )

        result = await precedence.evaluate(action, None, token.token_id, {})
        assert result.blocked is True
        assert result.status == KernelStatus.BLOCKED_CAPABILITY
        assert result.winning_rule == "capability_invalid"

    @pytest.mark.asyncio
    async def test_old_style_capability_still_works(self, db_pool):
        """Non-governance tokens (old style) still flow through repo-based check."""
        import asyncpg

        # Create a tenant-scoped pool so RLS works through the HTTP layer
        async def _setup(conn):
            await conn.execute("SELECT set_tenant_context($1)", TENANT)

        scoped_pool = await asyncpg.create_pool(
            "postgresql://CITADEL:CITADEL@localhost:5432/citadel_test",
            min_size=1, max_size=2, setup=_setup,
        )
        app.state.db_pool = scoped_pool

        cap_token = f"cap_old_{uuid.uuid4().hex[:12]}"

        conn = await asyncpg.connect("postgresql://CITADEL:CITADEL@localhost:5432/citadel_test")
        # Bypass RLS for direct test insertion
        await conn.execute("SET app.admin_bypass = 'true'")
        # Insert actor first (FK constraint)
        await conn.execute(
            """
            INSERT INTO actors (actor_id, actor_type, tenant_id, status)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (actor_id) DO NOTHING
            """,
            ACTOR, "agent", TENANT, "active",
        )
        await conn.execute(
            """
            INSERT INTO capabilities (
                token_id, actor_id, action_scope, resource_scope,
                max_uses, uses, expires_at, revoked, tenant_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            cap_token,
            ACTOR,
            "test.old_style",
            "res_old",
            5,
            0,
            datetime.now(timezone.utc) + timedelta(minutes=10),
            False,
            TENANT,
        )
        await conn.close()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as client:
            resp = await client.post(
                "/v1/actions",
                headers=_headers(),
                json={
                    "actor_id": ACTOR,
                    "actor_type": "agent",
                    "action_name": "test.old_style",
                    "resource": "res_old",
                    "tenant_id": TENANT,
                    "payload": {},
                    "capability_token": cap_token,
                },
            )
        await scoped_pool.close()
        assert resp.status_code == 202, resp.text
        data = resp.json()
        # With valid old-style cap and no policy block, action executes
        assert data["executed"] is True

    @pytest.mark.asyncio
    async def test_token_verifier_used_for_gt_cap_prefix(self, db_pool):
        """Precedence delegates gt_cap_* tokens to TokenVerifier."""
        vault = TokenVault(db_pool)

        decision = GovernanceDecision(
            decision_id=GovernanceDecision.generate_id(),
            decision_type=DecisionType.ALLOW,
            actor_id=ACTOR,
            action="test.verify",
            scope=DecisionScope(
                actions=["test.verify"],
                resources=["res_v"],
            ),
            expiry=datetime.now(timezone.utc) + timedelta(minutes=10),
            tenant_id=TENANT,
        )
        await vault.store_decision(decision)
        token = CapabilityToken.derive(decision)
        await vault.store_token(token)

        from CITADEL.precedence import Precedence
        from CITADEL.policy_resolver import PolicyEvaluator
        from CITADEL.actions import Action

        verifier = TokenVerifier(vault, None, MockAuditLogger())
        precedence = Precedence(
            repository=None,
            policy_evaluator=PolicyEvaluator(),
            token_verifier=verifier,
            governance_kill_switch=None,
        )

        action = Action(
            action_id=uuid.uuid4(),
            actor_id=ACTOR,
            actor_type="agent",
            action_name="test.verify",
            resource="res_v",
            tenant_id=TENANT,
            payload={},
            context={},
            session_id=None,
            request_id=None,
            idempotency_key=None,
            created_at=datetime.now(timezone.utc),
        )

        result = await precedence.evaluate(action, None, token.token_id, {})
        assert result.blocked is False
        assert result.winning_rule == "allowed"
