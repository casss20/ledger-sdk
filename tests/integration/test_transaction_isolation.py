import pytest
import asyncpg
import asyncio
from ledger.middleware.tenant_context import (
    tenant_scope,
    TenantAwarePool,
    get_tenant_id,
)

@pytest.mark.asyncio
async def test_transaction_scoped_isolation(db_pool):
    """
    Test that tenant context is strictly bound to transactions and auto-clears.
    """
    pool = TenantAwarePool(db_pool)
    
    tenant_a = "tenant_a"
    tenant_b = "tenant_b"
    
    async def check_rls_works(tenant_id):
        async with tenant_scope(tenant_id=tenant_id):
            async with pool.acquire() as conn:
                # This should work
                await conn.execute("SELECT 1")
                # Verify DB setting
                db_tenant = await conn.fetchval("SELECT current_setting('app.current_tenant_id', TRUE)")
                assert db_tenant == tenant_id
    
    await check_rls_works(tenant_a)
    await check_rls_works(tenant_b)
    
    # Verify that outside pool.acquire() on a raw connection, setting is gone
    async with db_pool.acquire() as raw_conn:
        db_tenant = await raw_conn.fetchval("SELECT current_setting('app.current_tenant_id', TRUE)")
        assert db_tenant is None or db_tenant == ""

@pytest.mark.asyncio
async def test_transaction_rollback_clears_context(db_pool):
    """
    Test that even on error/rollback, context doesn't leak.
    """
    pool = TenantAwarePool(db_pool)
    
    async with tenant_scope(tenant_id="leak_test"):
        try:
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1/0") # Force error
        except Exception:
            pass
            
    # Next acquisition should have clean slate
    async with db_pool.acquire() as raw_conn:
        db_tenant = await raw_conn.fetchval("SELECT current_setting('app.current_tenant_id', TRUE)")
        assert db_tenant is None or db_tenant == ""
