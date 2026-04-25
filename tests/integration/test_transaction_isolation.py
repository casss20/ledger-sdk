import pytest
import asyncpg
import asyncio
from citadel.middleware.tenant_context import (
    tenant_scope,
    TenantAwarePool,
    get_tenant_id,
)


# These tests need a pool WITHOUT the conftest's setup hook (which pre-sets
# `test_tenant` on every connection). Build a fresh pool here.
@pytest.fixture
async def raw_pool(postgres_dsn):
    pool = await asyncpg.create_pool(postgres_dsn, min_size=1, max_size=5)
    yield pool
    await pool.close()


@pytest.mark.asyncio
async def test_transaction_scoped_isolation(raw_pool):
    """
    Test that tenant context is strictly bound to transactions and auto-clears.
    """
    pool = TenantAwarePool(raw_pool)

    tenant_a = "tenant_a"
    tenant_b = "tenant_b"

    async def check_rls_works(tenant_id):
        async with tenant_scope(tenant_id=tenant_id):
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1")
                db_tenant = await conn.fetchval("SELECT current_setting('app.current_tenant_id', TRUE)")
                assert db_tenant == tenant_id

    await check_rls_works(tenant_a)
    await check_rls_works(tenant_b)

    async with raw_pool.acquire() as raw_conn:
        db_tenant = await raw_conn.fetchval("SELECT current_setting('app.current_tenant_id', TRUE)")
        assert db_tenant is None or db_tenant == ""


@pytest.mark.asyncio
async def test_transaction_rollback_clears_context(raw_pool):
    """
    Test that even on error/rollback, context doesn't leak.
    """
    pool = TenantAwarePool(raw_pool)

    async with tenant_scope(tenant_id="leak_test"):
        try:
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1/0")
        except Exception:
            pass

    async with raw_pool.acquire() as raw_conn:
        db_tenant = await raw_conn.fetchval("SELECT current_setting('app.current_tenant_id', TRUE)")
        assert db_tenant is None or db_tenant == ""
