import pytest
from CITADEL.auth.api_key import APIKeyService, APIKeyError, APIKeyEnvironment

class MockCache:
    def __init__(self):
        self.store = {}
    
    def set(self, key, value, ttl=None):
        self.store[key] = value
        
    def delete(self, key):
        if key in self.store:
            del self.store[key]
            
    def get(self, key):
        return self.store.get(key)

@pytest.fixture
def cache():
    return MockCache()

@pytest.mark.asyncio
async def test_create_api_key(db_pool, cache):
    service = APIKeyService(db_pool, cache)
    response = await service.create("acme", "My Production Key", "live")
    
    assert response.key_id.startswith("gk_live_")
    assert response.key_secret  # Should have secret
    assert response.environment == "live"

@pytest.mark.asyncio
async def test_verify_valid_api_key(db_pool, cache):
    service = APIKeyService(db_pool, cache)
    response = await service.create("acme", "Test Key", "live")
    
    api_key = await service.verify(response.key_id, response.key_secret)
    assert api_key.key_id == response.key_id
    assert api_key.tenant_id == "acme"

@pytest.mark.asyncio
async def test_verify_invalid_api_key(db_pool, cache):
    service = APIKeyService(db_pool, cache)
    
    with pytest.raises(APIKeyError):
        await service.verify("gk_live_invalid", "wrong_secret")

@pytest.mark.asyncio
async def test_api_key_revoke(db_pool, cache):
    service = APIKeyService(db_pool, cache)
    response = await service.create("acme", "Revoke Test", "live")
    
    await service.revoke(response.key_id)
    
    with pytest.raises(APIKeyError):
        await service.verify(response.key_id, response.key_secret)

@pytest.mark.asyncio
async def test_api_key_expiration(db_pool, cache):
    service = APIKeyService(db_pool, cache)
    # create with 0 days expiration means it expires immediately or next microsecond
    response = await service.create("acme", "Expiring Key", "live", expires_in_days=0)
    
    import time
    time.sleep(1)
    
    with pytest.raises(APIKeyError):
        await service.verify(response.key_id, response.key_secret)

@pytest.mark.asyncio
async def test_api_key_list(db_pool, cache):
    service = APIKeyService(db_pool, cache)
    
    await service.create("acme_list", "Key 1", "live")
    await service.create("acme_list", "Key 2", "live")
    
    keys = await service.list_keys("acme_list")
    assert len(keys) == 2

@pytest.mark.asyncio
async def test_api_key_caching(db_pool, cache):
    service = APIKeyService(db_pool, cache)
    response = await service.create("acme", "Cache Test", "live")
    
    # First verify (hits DB)
    key1 = await service.verify(response.key_id, response.key_secret)
    
    # Second verify (hits cache - mock doesn't skip DB in this implementation but it tests the setter)
    key2 = await service.verify(response.key_id, response.key_secret)
    
    assert key1.key_id == key2.key_id
    assert f"api_key:{response.key_id}" in cache.store

@pytest.mark.asyncio
async def test_api_key_permissions(db_pool, cache):
    service = APIKeyService(db_pool, cache)
    response = await service.create("acme", "Scoped Key", "live")
    
    key = await service.verify(response.key_id, response.key_secret)
    assert "actions:*" in key.permissions

@pytest.mark.asyncio
async def test_api_key_audit_logging(db_pool, cache, caplog):
    service = APIKeyService(db_pool, cache)
    response = await service.create("acme", "Log Test", "live")
    
    assert "API key created" in caplog.text
    
    await service.revoke(response.key_id)
    assert "API key revoked" in caplog.text

@pytest.mark.asyncio
async def test_api_key_last_used_tracking(db_pool, cache):
    service = APIKeyService(db_pool, cache)
    response = await service.create("acme", "Usage Test", "live")
    
    # First verify will set last_used_at
    key1 = await service.verify(response.key_id, response.key_secret)
    assert key1.last_used_at is not None
    
    import time
    time.sleep(0.1)
    
    key2 = await service.verify(response.key_id, response.key_secret)
    assert key2.last_used_at is not None
    assert key2.last_used_at > key1.last_used_at

@pytest.mark.asyncio
async def test_api_key_environment_separation(db_pool, cache):
    service = APIKeyService(db_pool, cache)
    
    live_response = await service.create("acme", "Live Key", "live")
    test_response = await service.create("acme", "Test Key", "test")
    
    assert "live" in live_response.key_id
    assert "test" in test_response.key_id

@pytest.mark.asyncio
async def test_api_key_secret_not_returned_on_list(db_pool, cache):
    service = APIKeyService(db_pool, cache)
    await service.create("acme_secret", "List Test", "live")
    
    keys = await service.list_keys("acme_secret")
    # Verify that secret is NOT included in list response
    for key in keys:
        assert not hasattr(key, "key_secret")
