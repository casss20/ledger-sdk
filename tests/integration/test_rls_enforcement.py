"""
Verify that RLS actually blocks cross-tenant access.

This is the KEY test. If this passes, data isolation works.
"""

import pytest
import uuid
import json
from datetime import datetime
from CITADEL.middleware.tenant_context import tenant_scope, TenantContextError

@pytest.mark.asyncio
async def test_rls_blocks_cross_tenant_access(db_pool):
    """
    Critical test: Verify RLS prevents seeing other tenants' data.
    """
    action_id = uuid.uuid4()
    
    # Setup: Insert action for tenant "acme"
    async with tenant_scope(tenant_id="acme", is_admin=True):
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO actions (
                    action_id, actor_id, actor_type, action_name, resource, tenant_id,
                    payload_json, context_json, session_id, request_id, created_at
                ) VALUES ($1, 'test_actor', 'system', 'test.action', 'res1', 'acme', '{}', '{}', 's1', 'r1', NOW())
            """, action_id)
            
    # Test 1: Query as "acme" -> should see it
    async with tenant_scope(tenant_id="acme"):
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM actions WHERE action_id = $1", action_id)
            assert row is not None, "acme should see its own action"
            assert row['tenant_id'] == "acme"

    # Test 2: Query as "competitor" -> should NOT see it
    async with tenant_scope(tenant_id="competitor"):
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM actions WHERE action_id = $1", action_id)
            assert row is None, "competitor should NOT see acme's action (RLS blocked it)"

@pytest.mark.asyncio
async def test_rls_blocks_update_cross_tenant(db_pool):
    """Verify RLS also blocks UPDATE to other tenants' data"""
    action_id = uuid.uuid4()
    
    async with tenant_scope(tenant_id="acme", is_admin=True):
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO actions (
                    action_id, actor_id, actor_type, action_name, resource, tenant_id,
                    payload_json, context_json, session_id, request_id, created_at
                ) VALUES ($1, 'test_actor', 'system', 'test.action', 'res1', 'acme', '{}', '{}', 's1', 'r1', NOW())
            """, action_id)

    # Try to UPDATE as "competitor"
    async with tenant_scope(tenant_id="competitor"):
        async with db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE actions SET payload_json = '{"hacked": true}' WHERE action_id = $1
            """, action_id)
            assert result == "UPDATE 0", "competitor should NOT be able to update acme's action"

@pytest.mark.asyncio
async def test_rls_blocks_delete_cross_tenant(db_pool):
    """Verify RLS also blocks DELETE to other tenants' data"""
    action_id = uuid.uuid4()
    
    async with tenant_scope(tenant_id="acme", is_admin=True):
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO actions (
                    action_id, actor_id, actor_type, action_name, resource, tenant_id,
                    payload_json, context_json, session_id, request_id, created_at
                ) VALUES ($1, 'test_actor', 'system', 'test.action', 'res1', 'acme', '{}', '{}', 's1', 'r1', NOW())
            """, action_id)

    # Try to DELETE as "competitor"
    async with tenant_scope(tenant_id="competitor"):
        async with db_pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM actions WHERE action_id = $1
            """, action_id)
            assert result == "DELETE 0", "competitor should NOT be able to delete acme's action"

@pytest.mark.asyncio
async def test_missing_tenant_context_fails(db_pool):
    """
    Critical test: Verify that missing tenant context causes queries to fail.
    This ensures we never have silent data leaks (queries succeeding without context).
    """
    # Try to query WITHOUT entering tenant_scope
    # But db_pool from conftest sets context by default in test suite.
    # To really test this, we need a raw pool without the conftest fixture setup,
    # OR we can just rely on the fact that TenantAwarePool raises TenantContextError.
    from CITADEL.middleware.tenant_context import TenantAwarePool
    aware_pool = TenantAwarePool(db_pool)
    
    with pytest.raises(TenantContextError):
        async with aware_pool.acquire() as conn:
            pass

@pytest.mark.asyncio
async def test_tenant_context_prevents_silent_bypass(db_pool):
    """
    Verify that forgetting tenant_id causes a loud error, not silent bypass.
    """
    from CITADEL.middleware.tenant_context import TenantAwarePool
    aware_pool = TenantAwarePool(db_pool)
    
    # Simulate a developer forgetting to set tenant context
    with pytest.raises(TenantContextError):
        async with aware_pool.acquire() as conn:
            await conn.fetchrow("SELECT * FROM actions")
