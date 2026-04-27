"""
Shared pytest fixtures for Citadel SDK test suite.

All database tests run under strict RLS. Every connection that touches
tenant data must have tenant context set. Admin operations (cleanup,
migrations) use explicit admin bypass.
"""

import pytest
import uuid
import asyncpg


@pytest.fixture
def postgres_dsn():
    return "postgresql://citadel:citadel@localhost:5432/citadel_test"


@pytest.fixture
def tenant_id():
    return f"test_tenant_{uuid.uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
async def clean_database(postgres_dsn):
    """Clean database before each test with admin bypass."""
    try:
        conn = await asyncpg.connect(postgres_dsn)
    except (OSError, asyncpg.PostgresError, ConnectionRefusedError) as e:
        # PostgreSQL not available — skip silently for non-DB tests
        yield
        return
    try:
        conn = await asyncpg.connect(postgres_dsn)
    except (OSError, asyncpg.PostgresError, ConnectionRefusedError) as e:
        # PostgreSQL not available — skip silently for non-DB tests
        yield
        return
    await conn.execute("SET app.admin_bypass = 'true'")
    await conn.execute("SET LOCAL lock_timeout = '3s'")
    
    # Truncate tables individually so one failure doesn't roll back others
    for stmt in (
        "DELETE FROM policy_snapshots WHERE EXISTS (SELECT 1 FROM policies p WHERE p.policy_id = policy_snapshots.policy_id AND p.tenant_id LIKE 'test_%');",
        "DELETE FROM capabilities WHERE token_id LIKE 'test_%' OR token_id LIKE 'cap_%' OR token_id LIKE 'gt_%';",
        "DELETE FROM kill_switches WHERE tenant_id LIKE 'test_%';",
        "DELETE FROM approvals WHERE tenant_id LIKE 'test_%';",
        "DELETE FROM decisions WHERE tenant_id LIKE 'test_%';",
        "DELETE FROM execution_results;",
        "DELETE FROM api_keys;",
        "DELETE FROM governance_tokens;",
        "DELETE FROM governance_decisions;",
        "DELETE FROM actions WHERE tenant_id LIKE 'test_%';",
        "DELETE FROM policies WHERE tenant_id LIKE 'test_%';",
        "DELETE FROM actors WHERE tenant_id LIKE 'test_%';",
    ):
        try:
            await conn.execute(stmt)
        except Exception as e:
            print(f"Warning: clean_database delete failed for {stmt.split()[2]}: {e}")
    await conn.close()
    yield


@pytest.fixture
async def db_pool(postgres_dsn):
    """Database pool for tests that need it.
    
    Sets tenant context on each connection to allow queries through RLS.
    Tests that need specific tenant isolation should create their own pool.
    """
    async def _setup(conn):
        await conn.execute("SET app.current_tenant_id = 'test_tenant'")
    
    pool = await asyncpg.create_pool(
        postgres_dsn, 
        min_size=1, 
        max_size=5,
        setup=_setup,
    )
    yield pool
    await pool.close()
