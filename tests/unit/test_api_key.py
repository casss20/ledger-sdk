import pytest
from citadel.auth.api_key import APIKeyService, APIKeyError, APIKeyEnvironment

class MockCache:
    def __init__(self):
        self.store = {}
    
    async def set(self, key, value, ttl=None):
        self.store[key] = value
        
    async def delete(self, key):
        if key in self.store:
            del self.store[key]
            
    async def get(self, key):
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
async def test_validate_api_key(db_pool, cache):
    service = APIKeyService(db_pool, cache)
    
    # Create key
    created = await service.create("acme", "Test Key", "test")
    
    # Validate with secret
    key = await service.validate(created.key_secret)
    assert key is not None
    assert key.tenant_id == "acme"

@pytest.mark.asyncio
async def test_revoke_api_key(db_pool, cache):
    service = APIKeyService(db_pool, cache)
    
    created = await service.create("acme", "To Revoke", "test")
    await service.revoke(created.key_id)
    
    # Should fail validation after revoke
    key = await service.validate(created.key_secret)
    assert key is None

@pytest.mark.asyncio
async def test_rotate_api_key(db_pool, cache):
    service = APIKeyService(db_pool, cache)
    
    created = await service.create("acme", "To Rotate", "test")
    rotated = await service.rotate(created.key_id)
    
    # Old secret should fail
    assert await service.validate(created.key_secret) is None
    # New secret should work
    assert await service.validate(rotated.key_secret) is not None

@pytest.mark.asyncio
async def test_api_key_environment(db_pool, cache):
    service = APIKeyService(db_pool, cache)
    
    test_key = await service.create("acme", "Test", "test")
    live_key = await service.create("acme", "Live", "live")
    
    assert test_key.environment == APIKeyEnvironment.TEST
    assert live_key.environment == APIKeyEnvironment.LIVE