"""
Shared pytest fixtures for Ledger SDK test suite.

All database tests run under strict RLS. Every connection that touches
tenant data must have tenant context set. Admin operations (cleanup,
migrations) use explicit admin bypass.
"""

import pytest
import uuid
import asyncpg


@pytest.fixture
def postgres_dsn():
    return "postgresql://ledger:ledger@localhost:5432/ledger_test"


@pytest.fixture
def tenant_id():
    return f"test_tenant_{uuid.uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
async def clean_database(postgres_dsn):
    """Clean database before each test with admin bypass."""
    conn = await asyncpg.connect(postgres_dsn)
    # Admin bypass allows TRUNCATE under strict RLS
    await conn.execute("SET app.admin_bypass = 'true'")
    await conn.execute("""
        TRUNCATE actors, policies, policy_snapshots, capabilities,
                    kill_switches, approvals, actions, decisions,
                    audit_events, execution_results, api_keys
        CASCADE
    """)
    await conn.close()
    yield
