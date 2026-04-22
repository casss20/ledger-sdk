"""Tests for token vault with tenant isolation."""

import uuid

import asyncpg
import pytest

from ledger.tokens import GovernanceToken, TokenType, TokenVault

DSN = "postgresql://ledger:ledger@localhost:5432/ledger_test"


async def get_pool():
    return await asyncpg.create_pool(DSN, min_size=1, max_size=2)


@pytest.fixture(scope="module")
def tenant_id():
    return str(uuid.uuid4())


class TestStoreAndResolve:
    @pytest.mark.asyncio
    async def test_store_and_resolve(self, tenant_id):
        """Store a token and resolve it back."""
        pool = await get_pool()
        vault = TokenVault(pool, lambda: tenant_id)

        token = GovernanceToken.generate(
            token_type=TokenType.POLICY_DECISION,
            tenant_id=tenant_id,
            decision_trace={"action": "file.read"},
        )

        await vault.store(token)

        # Resolve back
        result = await vault.resolve(token.token_id)

        assert result is not None
        assert result["token_id"] == token.token_id
        assert result["token_type"] == "policy"

    @pytest.mark.asyncio
    async def test_resolve_nonexistent(self, tenant_id):
        """Resolving non-existent token returns None."""
        pool = await get_pool()
        vault = TokenVault(pool, lambda: tenant_id)

        result = await vault.resolve("gt_pol_nonexistent12345")
        assert result is None


class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_cross_tenant_access_blocked(self, tenant_id):
        """Tenant A cannot resolve Tenant B's tokens."""
        pool = await get_pool()
        tenant_a = str(uuid.uuid4())
        tenant_b = str(uuid.uuid4())

        # Create token for tenant A
        token = GovernanceToken.generate(
            token_type=TokenType.AUDIT_EVENT,
            tenant_id=tenant_a,
            decision_trace={"event": "test"},
        )

        vault_a = TokenVault(pool, lambda: tenant_a)
        await vault_a.store(token)

        # Tenant B tries to resolve it
        vault_b = TokenVault(pool, lambda: tenant_b)
        result = await vault_b.resolve(token.token_id)

        # Should be None due to RLS
        assert result is None


class TestChainVerification:
    @pytest.mark.asyncio
    async def test_verify_chain_detects_tampering(self, tenant_id):
        """Verification detects if decision trace was tampered."""
        pool = await get_pool()
        vault = TokenVault(pool, lambda: tenant_id)

        token = GovernanceToken.generate(
            token_type=TokenType.AUDIT_EVENT,
            tenant_id=tenant_id,
            decision_trace={"action": "read", "resource": "file.txt"},
        )

        await vault.store(token)

        # Direct tamper in DB (bypass RLS)
        async with pool.acquire() as conn:
            await conn.execute("SET app.admin_bypass = 'true'")
            await conn.execute(
                "UPDATE governance_tokens SET decision_trace = $1 WHERE token_id = $2",
                '{"tampered": true}',
                token.token_id,
            )

        # Verify should detect mismatch
        is_valid = await vault.verify_chain(token.token_id)

        assert is_valid is False


class TestAppendOnly:
    @pytest.mark.asyncio
    async def test_no_delete_permission(self, tenant_id):
        """Tokens are append-only — no DELETE via vault API."""
        pool = await get_pool()

        token = GovernanceToken.generate(
            token_type=TokenType.POLICY_DECISION,
            tenant_id=tenant_id,
            decision_trace={"action": "test"},
        )

        vault = TokenVault(pool, lambda: tenant_id)
        await vault.store(token)

        # Verify token exists
        result = await vault.resolve(token.token_id)
        assert result is not None

        # Vault has no delete method (architectural immutability)
        assert not hasattr(vault, 'delete')
        assert not hasattr(vault, 'remove')
