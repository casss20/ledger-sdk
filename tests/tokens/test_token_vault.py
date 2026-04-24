"""Tests for token vault with decision-centric storage."""

import uuid

import asyncpg
import pytest

from CITADEL.tokens import (
    CapabilityToken,
    DecisionScope,
    DecisionType,
    GovernanceDecision,
    TokenVault,
)

DSN = "postgresql://citadel:citadel@localhost:5432/citadel_test"


async def get_pool():
    return await asyncpg.create_pool(DSN, min_size=1, max_size=2)


@pytest.fixture(scope="module")
def tenant_id():
    return str(uuid.uuid4())


class TestDecisionStorage:
    @pytest.mark.asyncio
    async def test_store_and_resolve_decision(self, tenant_id):
        """Store a decision and resolve it back."""
        pool = await get_pool()
        vault = TokenVault(pool, lambda: tenant_id)

        decision = GovernanceDecision(
            decision_id="gd_test_001",
            decision_type=DecisionType.ALLOW,
            tenant_id=tenant_id,
            actor_id="agent_1",
            action="file.read",
            scope=DecisionScope(actions=["file.read"]),
        )

        await vault.store_decision(decision)
        result = await vault.resolve_decision("gd_test_001")

        assert result is not None
        assert result["decision_id"] == "gd_test_001"
        assert result["decision_type"] == "allow"

    @pytest.mark.asyncio
    async def test_store_and_resolve_token(self, tenant_id):
        """Store a token linked to a decision and resolve it."""
        pool = await get_pool()
        vault = TokenVault(pool, lambda: tenant_id)

        decision = GovernanceDecision(
            decision_id="gd_test_002",
            decision_type=DecisionType.ALLOW,
            tenant_id=tenant_id,
            actor_id="agent_1",
            action="file.write",
            scope=DecisionScope(actions=["file.write"]),
        )
        token = CapabilityToken.derive(decision)

        await vault.store_decision(decision)
        await vault.store_token(token)

        result = await vault.resolve_token(token.token_id)
        assert result is not None
        assert result["token_id"] == token.token_id
        assert result["decision_id"] == decision.decision_id


class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_cross_tenant_access_blocked(self, tenant_id):
        """Tenant A cannot resolve Tenant B's decisions."""
        pool = await get_pool()
        tenant_a = str(uuid.uuid4())
        tenant_b = str(uuid.uuid4())

        decision = GovernanceDecision(
            decision_id="gd_a_001",
            decision_type=DecisionType.ALLOW,
            tenant_id=tenant_a,
            actor_id="agent_1",
            action="file.read",
            scope=DecisionScope(),
        )

        vault_a = TokenVault(pool, lambda: tenant_a)
        await vault_a.store_decision(decision)

        vault_b = TokenVault(pool, lambda: tenant_b)
        result = await vault_b.resolve_decision("gd_a_001")
        assert result is None


class TestTokenChain:
    @pytest.mark.asyncio
    async def test_verify_chain(self, tenant_id):
        """Token chain verification works."""
        pool = await get_pool()
        vault = TokenVault(pool, lambda: tenant_id)

        decision = GovernanceDecision(
            decision_id="gd_chain_001",
            decision_type=DecisionType.ALLOW,
            tenant_id=tenant_id,
            actor_id="agent_1",
            action="file.read",
            scope=DecisionScope(),
        )
        token = CapabilityToken.derive(decision)

        await vault.store_decision(decision)
        await vault.store_token(token)

        is_valid = await vault.verify_chain(token.token_id)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_chain_missing_token(self, tenant_id):
        """Chain verification fails for non-existent token."""
        pool = await get_pool()
        vault = TokenVault(pool, lambda: tenant_id)

        is_valid = await vault.verify_chain("gt_cap_nonexistent")
        assert is_valid is False
