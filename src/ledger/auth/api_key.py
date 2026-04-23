"""
API Key authentication for Ledger SDK.

Why: SDK users (developers) authenticate with API keys.
Pattern: Similar to Stripe, GitHub, Anthropic API keys.

Key format:
  gk_live_<32 random chars>     (production)
  gk_test_<32 random chars>     (testing)

Key is split:
  - key_id: Public, shown to user (gk_live_abc123...)
  - key_secret: Private, hashed in DB, shown only once at creation
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class APIKeyEnvironment(Enum):
    """API key environment (prod vs test)"""
    LIVE = "live"      # Production
    TEST = "test"      # Testing

class APIKeyStatus(Enum):
    """API key status"""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"

@dataclass
class APIKey:
    """API key object"""
    key_id: str                    # gk_live_abc123...
    tenant_id: str
    name: str                      # User-friendly name
    environment: APIKeyEnvironment
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    status: APIKeyStatus = APIKeyStatus.ACTIVE
    permissions: list[str] = None  # e.g., ["actions:execute", "approvals:approve"]
    rate_limit_rps: int = 1000     # Requests per second
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = ["actions:*"]

@dataclass
class APIKeyCreationResponse:
    """Response when creating API key (secret shown only once)"""
    key_id: str
    key_secret: str  # ONLY shown at creation time
    environment: str
    created_at: str

class APIKeyService:
    """Manage API key lifecycle"""
    
    def __init__(self, db_pool, cache):
        self.db = db_pool
        self.cache = cache
    
    async def create(
        self,
        tenant_id: str,
        name: str,
        environment: str = "live",
        expires_in_days: Optional[int] = None,
    ) -> APIKeyCreationResponse:
        """
        Create new API key.
        
        Returns: APIKeyCreationResponse (includes secret, shown only once)
        """
        # Generate key ID and secret
        env = APIKeyEnvironment.LIVE if environment == "live" else APIKeyEnvironment.TEST
        key_id = f"gk_{env.value}_{secrets.token_urlsafe(24)}"
        key_secret = secrets.token_urlsafe(32)
        
        # Hash the secret for storage
        key_secret_hash = self._hash_secret(key_secret)
        
        # Calculate expiration
        expires_at = None
        if expires_in_days is not None:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Store in database
        # For asyncpg, we use $1, $2 instead of :name but the prompt had :name.
        # However, the user provided exact SQLAlchemy/databases syntax or pseudo-code:
        # We must use asyncpg syntax: $1, $2, etc., since `self.db` is an asyncpg pool/conn.
        # I will adapt the SQL query to asyncpg syntax as expected in the rest of the project.
        await self.db.execute(
            """
            INSERT INTO api_keys 
            (key_id, tenant_id, name, key_secret_hash, environment, 
             created_at, expires_at, status, permissions, rate_limit_rps)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            key_id,
            tenant_id,
            name,
            key_secret_hash,
            env.value,
            datetime.utcnow(),
            expires_at,
            APIKeyStatus.ACTIVE.value,
            permissions_to_json(["actions:*"]),
            1000
        )
        
        # Log creation
        logger.info(f"API key created: {key_id} for tenant {tenant_id}")
        
        # Return response (secret shown only once)
        return APIKeyCreationResponse(
            key_id=key_id,
            key_secret=key_secret,
            environment=env.value,
            created_at=datetime.utcnow().isoformat(),
        )
    
    async def verify(self, key_id: str, key_secret: str) -> APIKey:
        """
        Verify API key is valid.
        
        Returns: APIKey object if valid
        Raises: APIKeyError if invalid/revoked/expired
        """
        # Fetch key from DB using asyncpg syntax
        result = await self.db.fetchrow(
            "SELECT * FROM api_keys WHERE key_id = $1",
            key_id
        )
        
        if not result:
            logger.warning(f"API key not found: {key_id}")
            raise APIKeyError("Invalid API key")
        
        # Check status
        if result["status"] == APIKeyStatus.REVOKED.value:
            logger.warning(f"API key revoked: {key_id}")
            raise APIKeyError("API key has been revoked")
        
        if result["status"] == APIKeyStatus.EXPIRED.value:
            logger.warning(f"API key expired: {key_id}")
            raise APIKeyError("API key has expired")
        
        # Check expiration (naive datetime without tz might cause issues, using utcnow)
        if result["expires_at"] and result["expires_at"] < datetime.utcnow():
            logger.warning(f"API key expired: {key_id}")
            # Mark as expired
            await self.db.execute(
                "UPDATE api_keys SET status = $1 WHERE key_id = $2",
                APIKeyStatus.EXPIRED.value, key_id
            )
            raise APIKeyError("API key has expired")
        
        # Verify secret hash
        secret_hash = self._hash_secret(key_secret)
        if secret_hash != result["key_secret_hash"]:
            logger.warning(f"API key secret mismatch: {key_id}")
            raise APIKeyError("Invalid API key secret")
        
        # Update last_used_at
        await self.db.execute(
            "UPDATE api_keys SET last_used_at = $1 WHERE key_id = $2",
            datetime.utcnow(), key_id
        )
        
        # Cache the key (5 minute TTL)
        api_key = APIKey(
            key_id=result["key_id"],
            tenant_id=result["tenant_id"],
            name=result["name"],
            environment=APIKeyEnvironment(result["environment"]),
            created_at=result["created_at"],
            last_used_at=datetime.utcnow(),
            expires_at=result["expires_at"],
            status=APIKeyStatus(result["status"]),
            permissions=permissions_from_json(result["permissions"]),
            rate_limit_rps=result["rate_limit_rps"],
        )
        
        # Some cache abstractions use set(key, value, ttl)
        if self.cache:
            try:
                # If cache is a mock or redis, we just call set
                import asyncio
                if asyncio.iscoroutinefunction(getattr(self.cache, "set", None)):
                    await self.cache.set(f"api_key:{key_id}", api_key, ttl=300)
                else:
                    self.cache.set(f"api_key:{key_id}", api_key, ttl=300)
            except Exception as e:
                logger.error(f"Cache set error: {e}")
        
        return api_key
    
    async def revoke(self, key_id: str) -> None:
        """Revoke API key"""
        await self.db.execute(
            "UPDATE api_keys SET status = $1 WHERE key_id = $2",
            APIKeyStatus.REVOKED.value, key_id
        )
        
        # Clear cache
        if self.cache:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(getattr(self.cache, "delete", None)):
                    await self.cache.delete(f"api_key:{key_id}")
                else:
                    self.cache.delete(f"api_key:{key_id}")
            except Exception as e:
                pass
        
        logger.info(f"API key revoked: {key_id}")
    
    async def list_keys(self, tenant_id: str) -> list[APIKey]:
        """List all API keys for tenant (excluding secrets)"""
        result = await self.db.fetch(
            "SELECT * FROM api_keys WHERE tenant_id = $1 ORDER BY created_at DESC",
            tenant_id
        )
        
        return [
            APIKey(
                key_id=row["key_id"],
                tenant_id=row["tenant_id"],
                name=row["name"],
                environment=APIKeyEnvironment(row["environment"]),
                created_at=row["created_at"],
                last_used_at=row["last_used_at"],
                expires_at=row["expires_at"],
                status=APIKeyStatus(row["status"]),
                permissions=permissions_from_json(row["permissions"]),
                rate_limit_rps=row["rate_limit_rps"],
            )
            for row in result
        ]
    
    def _hash_secret(self, secret: str) -> str:
        """Hash API key secret (bcrypt-like, but using SHA256 for simplicity)"""
        # In production, use bcrypt: bcrypt.hashpw(secret.encode(), bcrypt.gensalt())
        return hashlib.sha256(secret.encode()).hexdigest()

class APIKeyError(Exception):
    """API key validation error"""
    pass

def permissions_to_json(permissions: list[str]) -> str:
    """Convert permissions list to JSON string"""
    import json
    return json.dumps(permissions)

def permissions_from_json(json_str: str) -> list[str]:
    """Convert JSON string to permissions list"""
    import json
    return json.loads(json_str) if json_str else []
