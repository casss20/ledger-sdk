import pytest
import time
from citadel.auth.jwt_token import JWTService, JWTError, TokenType

class MockCache:
    def __init__(self):
        self.store = {}
    
    async def set(self, key, value, ttl=None):
        self.store[key] = value

@pytest.fixture
def jwt_service():
    return JWTService(secret_key="test_secret_key_12345")

@pytest.fixture
def cache():
    return MockCache()

@pytest.mark.asyncio
async def test_create_jwt_token(jwt_service):
    token = jwt_service.create_token(
        user_id="user1",
        tenant_id="acme",
        email="user@acme.com",
        role="admin"
    )
    
    assert token
    assert isinstance(token, str)
    assert token.count(".") == 2  # JWT has 3 parts

@pytest.mark.asyncio
async def test_verify_valid_jwt(jwt_service):
    token = jwt_service.create_token(
        user_id="user1",
        tenant_id="acme",
        email="user@acme.com",
        role="admin"
    )
    
    claims = jwt_service.verify_token(token)
    assert claims.user_id == "user1"
    assert claims.tenant_id == "acme"
    assert claims.email == "user@acme.com"

@pytest.mark.asyncio
async def test_verify_expired_jwt(jwt_service):
    # Create token that expires immediately
    claims_dict = {
        "user_id": "user1",
        "tenant_id": "acme",
        "email": "user@acme.com",
        "role": "admin",
        "token_type": "access",
        "exp": int(time.time()) - 20,  # Already expired
        "iat": int(time.time()) - 20,
    }
    
    import jwt
    token = jwt.encode(claims_dict, jwt_service.secret_key, algorithm="HS256")
    
    with pytest.raises(JWTError):
        jwt_service.verify_token(token)

@pytest.mark.asyncio
async def test_verify_tampered_jwt(jwt_service):
    token = jwt_service.create_token(
        user_id="user1",
        tenant_id="acme",
        email="user@acme.com",
        role="admin"
    )
    
    # Tamper with token
    tampered = token[:-10] + "TAMPERED123"
    
    with pytest.raises(JWTError):
        jwt_service.verify_token(tampered)

@pytest.mark.asyncio
async def test_jwt_refresh_token(jwt_service):
    refresh_token = jwt_service.create_token(
        user_id="user1",
        tenant_id="acme",
        email="user@acme.com",
        role="admin",
        token_type="refresh"
    )
    
    new_access_token = jwt_service.refresh_token(refresh_token, cache=None)
    
    claims = jwt_service.verify_token(new_access_token)
    assert claims.token_type == TokenType.ACCESS

@pytest.mark.asyncio
async def test_jwt_role_scoping(jwt_service):
    token = jwt_service.create_token(
        user_id="user1",
        tenant_id="acme",
        email="user@acme.com",
        role="viewer"
    )
    
    claims = jwt_service.verify_token(token)
    assert claims.role.value == "viewer"

@pytest.mark.asyncio
async def test_jwt_mfa_flag(jwt_service):
    token = jwt_service.create_token(
        user_id="user1",
        tenant_id="acme",
        email="user@acme.com",
        role="admin",
        mfa_verified=True
    )
    
    claims = jwt_service.verify_token(token)
    assert claims.mfa_verified is True

@pytest.mark.asyncio
async def test_jwt_revocation(jwt_service, cache):
    token = jwt_service.create_token(
        user_id="user1",
        tenant_id="acme",
        email="user@acme.com",
        role="admin"
    )
    
    claims = jwt_service.verify_token(token)
    # Revoke token
    await jwt_service.revoke_token(token, cache)
    
    # Check cache has the revoked token
    assert f"revoked_token:{claims.jti}" in cache.store

@pytest.mark.asyncio
async def test_jwt_access_token_expiration(jwt_service):
    token = jwt_service.create_token(
        user_id="user1",
        tenant_id="acme",
        email="user@acme.com",
        role="admin",
        token_type="access"
    )
    
    claims = jwt_service.verify_token(token)
    # Access token should have ~1 hour expiration
    exp_in_seconds = claims.exp - claims.iat
    assert exp_in_seconds == 3600  # 1 hour

@pytest.mark.asyncio
async def test_jwt_refresh_token_expiration(jwt_service):
    token = jwt_service.create_token(
        user_id="user1",
        tenant_id="acme",
        email="user@acme.com",
        role="admin",
        token_type="refresh"
    )
    
    claims = jwt_service.verify_token(token)
    # Refresh token should have ~7 day expiration
    exp_in_seconds = claims.exp - claims.iat
    assert exp_in_seconds == 604800  # 7 days

@pytest.mark.asyncio
async def test_jwt_unique_jti(jwt_service):
    token1 = jwt_service.create_token(
        user_id="user1",
        tenant_id="acme",
        email="user@acme.com",
        role="admin"
    )
    
    token2 = jwt_service.create_token(
        user_id="user1",
        tenant_id="acme",
        email="user@acme.com",
        role="admin"
    )
    
    claims1 = jwt_service.verify_token(token1)
    claims2 = jwt_service.verify_token(token2)
    
    # Each token should have unique JTI
    assert claims1.jti != claims2.jti

@pytest.mark.asyncio
async def test_jwt_refresh_fails_with_access_token(jwt_service):
    access_token = jwt_service.create_token(
        user_id="user1",
        tenant_id="acme",
        email="user@acme.com",
        role="admin",
        token_type="access"
    )
    
    with pytest.raises(JWTError, match="refresh token"):
        jwt_service.refresh_token(access_token, cache=None)
