"""
API Key Provisioning Tests (Stream 2)

Covers:
- Key creation with SHA-256 hashing
- Key lookup by hash
- Cross-tenant key isolation (RLS)
- Revocation
- Expiration handling
- last_used_at tracking
"""

import pytest
import uuid
import hashlib
from datetime import datetime, timedelta

import asyncpg
from ledger.repository import Repository


@pytest.fixture
async def db(postgres_dsn, tenant_id):
    """Database connection with tenant context set."""
    conn = await asyncpg.connect(postgres_dsn)
    await conn.execute("SELECT set_tenant_context($1)", tenant_id)
    yield conn
    await conn.close()


@pytest.fixture
async def repo(postgres_dsn, tenant_id):
    """Repository with tenant-scoped pool."""
    async def setup_tenant(conn):
        await conn.execute("SELECT set_tenant_context($1)", tenant_id)

    pool = await asyncpg.create_pool(postgres_dsn, min_size=1, max_size=2, setup=setup_tenant)
    repo = Repository(pool)
    yield repo
    await pool.close()


def _hash_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


async def test_create_api_key(repo, tenant_id):
    """Create an API key and verify it can be looked up by hash."""
    plaintext = f"ledger_{uuid.uuid4().hex}"
    key_hash = _hash_key(plaintext)

    key = await repo.create_api_key(
        key_hash=key_hash,
        tenant_id=tenant_id,
        name="test-key",
        scopes=["actions:write", "actions:read"],
    )

    assert key['tenant_id'] == tenant_id
    assert key['name'] == "test-key"
    assert key['revoked'] is False

    # Lookup by hash
    found = await repo.get_api_key_by_hash(key_hash)
    assert found is not None
    assert found['key_id'] == key['key_id']
    assert found['tenant_id'] == tenant_id


async def test_api_key_cross_tenant_isolation(postgres_dsn, db):
    """Tenant A should not see Tenant B's API keys (strict RLS)."""
    tenant_a = "tenant_a_key"
    tenant_b = "tenant_b_key"

    # Setup with admin bypass
    await db.execute("SET app.admin_bypass = 'true'")

    hash_a = _hash_key(f"key_a_{uuid.uuid4().hex}")
    hash_b = _hash_key(f"key_b_{uuid.uuid4().hex}")

    await db.execute("""
        INSERT INTO api_keys (key_hash, tenant_id, name)
        VALUES ($1, $2, 'key-a')
    """, hash_a, tenant_a)
    await db.execute("""
        INSERT INTO api_keys (key_hash, tenant_id, name)
        VALUES ($1, $2, 'key-b')
    """, hash_b, tenant_b)

    await db.execute("SET app.admin_bypass = 'false'")

    # Tenant A scoped repo
    async def setup_a(conn):
        await conn.execute("SELECT set_tenant_context($1)", tenant_a)
    pool_a = await asyncpg.create_pool(postgres_dsn, min_size=1, max_size=1, setup=setup_a)
    repo_a = Repository(pool_a)

    try:
        # Can find own key
        found_a = await repo_a.get_api_key_by_hash(hash_a)
        assert found_a is not None
        assert found_a['tenant_id'] == tenant_a

        # Cannot find tenant B's key (RLS blocks it)
        found_b = await repo_a.get_api_key_by_hash(hash_b)
        assert found_b is None

        # list_api_keys only returns tenant A keys
        keys = await repo_a.list_api_keys(tenant_a)
        assert len(keys) == 1
        assert keys[0]['tenant_id'] == tenant_a
    finally:
        await pool_a.close()


async def test_api_key_revocation(repo, db, tenant_id):
    """Revoke an API key and verify it can no longer be looked up."""
    plaintext = f"ledger_{uuid.uuid4().hex}"
    key_hash = _hash_key(plaintext)

    key = await repo.create_api_key(key_hash=key_hash, tenant_id=tenant_id)
    key_id = key['key_id']

    # Verify it exists
    assert await repo.get_api_key_by_hash(key_hash) is not None

    # Revoke
    revoked = await repo.revoke_api_key(key_id)
    assert revoked is True

    # After revocation, lookup returns None
    found = await repo.get_api_key_by_hash(key_hash)
    assert found is None

    # list_api_keys excludes revoked
    keys = await repo.list_api_keys(tenant_id)
    assert len(keys) == 0


async def test_api_key_expiration(repo, db, tenant_id):
    """Expired keys should not be returned by lookup."""
    plaintext = f"ledger_{uuid.uuid4().hex}"
    key_hash = _hash_key(plaintext)

    # Create key that expired 1 hour ago
    await db.execute("SET app.admin_bypass = 'true'")
    await db.execute("""
        INSERT INTO api_keys (key_hash, tenant_id, name, expires_at)
        VALUES ($1, $2, 'expired-key', NOW() - interval '1 hour')
    """, key_hash, tenant_id)
    await db.execute("SET app.admin_bypass = 'false'")

    # Lookup should return None (expired)
    found = await repo.get_api_key_by_hash(key_hash)
    assert found is None


async def test_api_key_last_used(repo, db, tenant_id):
    """update_api_key_last_used should update the timestamp."""
    plaintext = f"ledger_{uuid.uuid4().hex}"
    key_hash = _hash_key(plaintext)

    await db.execute("SET app.admin_bypass = 'true'")
    await db.execute("""
        INSERT INTO api_keys (key_hash, tenant_id, name)
        VALUES ($1, $2, 'track-usage')
    """, key_hash, tenant_id)
    await db.execute("SET app.admin_bypass = 'false'")

    # last_used_at should be NULL initially
    row = await db.fetchrow("SELECT last_used_at FROM api_keys WHERE key_hash = $1", key_hash)
    assert row['last_used_at'] is None

    # Update last_used
    await repo.update_api_key_last_used(key_hash)

    # Verify updated
    row = await db.fetchrow("SELECT last_used_at FROM api_keys WHERE key_hash = $1", key_hash)
    assert row['last_used_at'] is not None


async def test_api_key_name_optional(repo, tenant_id):
    """API key creation should succeed when name is omitted (nullable field)."""
    plaintext = f"ledger_{uuid.uuid4().hex}"
    key_hash = _hash_key(plaintext)

    key = await repo.create_api_key(
        key_hash=key_hash,
        tenant_id=tenant_id,
        name=None,
        scopes=["test"],
    )

    assert key['key_id'] is not None
    assert key['name'] is None
    assert key['tenant_id'] == tenant_id


async def test_list_api_keys_pagination(repo, tenant_id):
    """list_api_keys should return only active keys for the tenant."""
    # Create 3 keys
    for i in range(3):
        await repo.create_api_key(
            key_hash=_hash_key(f"key_{i}_{uuid.uuid4().hex}"),
            tenant_id=tenant_id,
            name=f"key-{i}",
        )

    keys = await repo.list_api_keys(tenant_id)
    assert len(keys) == 3
    for k in keys:
        assert k['tenant_id'] == tenant_id
        assert k['revoked'] is False
