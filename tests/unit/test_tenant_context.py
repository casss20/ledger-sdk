import pytest
import asyncio
from CITADEL.middleware.tenant_context import (
    tenant_scope,
    get_tenant_context,
    get_tenant_id,
    is_admin_context,
    TenantContextError,
)

@pytest.mark.asyncio
async def test_tenant_context_set_and_get():
    """Test 1: Set context and get it within scope"""
    async with tenant_scope(tenant_id="acme", user_id="u1"):
        ctx = get_tenant_context()
        assert ctx.tenant_id == "acme"
        assert ctx.user_id == "u1"
        assert get_tenant_id() == "acme"

@pytest.mark.asyncio
async def test_tenant_context_auto_clears():
    """Test 2: Context is cleared after exiting scope"""
    async with tenant_scope(tenant_id="acme"):
        assert get_tenant_id() == "acme"
    
    with pytest.raises(TenantContextError):
        get_tenant_context()

@pytest.mark.asyncio
async def test_missing_context_raises_error():
    """Test 3: Calling get_tenant_context outside scope raises error"""
    with pytest.raises(TenantContextError, match="No tenant context"):
        get_tenant_context()

    with pytest.raises(TenantContextError, match="No tenant context"):
        get_tenant_id()

@pytest.mark.asyncio
async def test_admin_context_flag():
    """Test 4: Admin flag is correctly read"""
    assert not is_admin_context()
    
    async with tenant_scope(tenant_id="acme", is_admin=True):
        assert is_admin_context()
        
    async with tenant_scope(tenant_id="acme", is_admin=False):
        assert not is_admin_context()

@pytest.mark.asyncio
async def test_context_isolation_between_requests():
    """Test 5: asyncio.gather with different scopes preserves isolation"""
    
    async def run_as_tenant(tenant_id: str):
        async with tenant_scope(tenant_id=tenant_id):
            # simulate some async work
            await asyncio.sleep(0.01)
            # assert that context hasn't been clobbered by other coroutine
            assert get_tenant_id() == tenant_id
            return get_tenant_id()
            
    results = await asyncio.gather(
        run_as_tenant("tenant_a"),
        run_as_tenant("tenant_b"),
        run_as_tenant("tenant_c")
    )
    
    assert results == ["tenant_a", "tenant_b", "tenant_c"]
