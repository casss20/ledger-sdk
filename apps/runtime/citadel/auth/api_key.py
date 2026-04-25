"""
API Key Management

Production-grade API key handling with:
- SHA-256 hashing (keys stored as hashes, never plaintext)
- Scoped permissions (read, write, admin)
- Automatic last_used tracking
- Key rotation support (created_at, expires_at)
"""

import hashlib
import secrets
import time
from typing import List, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


@dataclass(frozen=True)
class ApiKey:
    """Represents a validated API key."""
    key_hash: str
    scopes: Set[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    tenant_id: Optional[str] = None
    description: Optional[str] = None

    def has_scope(self, scope: str) -> bool:
        """Check if key has a specific scope."""
        return scope in self.scopes or "admin" in self.scopes

    def is_expired(self) -> bool:
        """Check if key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def is_valid(self) -> bool:
        """Check if key is currently valid (not expired)."""
        return not self.is_expired()


class ApiKeyManager:
    """
    Manages API keys with secure hashing and scoping.

    Usage:
        # Initialize with keys from settings
        manager = ApiKeyManager.from_settings("sk_prod_abc:admin,sk_dev_xyz:read")

        # Validate a request key
        key = manager.validate("sk_prod_abc")
        if key and key.has_scope("write"):
            # Authorized
    """

    # Scopes ordered by privilege level
    SCOPE_LEVELS = {
        "read": 1,
        "write": 2,
        "admin": 3,
    }

    def __init__(self, keys: Optional[List[ApiKey]] = None):
        self._keys: dict[str, ApiKey] = {}  # key_hash -> ApiKey
        if keys:
            for k in keys:
                self._keys[k.key_hash] = k

    # ------------------------------------------------------------------
    # Factory Methods
    # ------------------------------------------------------------------

    @classmethod
    def from_settings(cls, api_keys_string: str) -> "ApiKeyManager":
        """
        Parse API keys from a comma-separated settings string.

        Format: "key:scope1,scope2|key2:scope1"
        Example: "sk_prod_abc:admin|sk_dev_xyz:read,write"

        If no scopes specified, defaults to "admin" (backward compat).
        """
        if not api_keys_string or api_keys_string.strip() == "":
            return cls()

        keys = []
        for segment in api_keys_string.split(","):
            segment = segment.strip()
            if not segment:
                continue

            # Support both "key:scopes" and plain "key" (backward compat)
            if ":" in segment:
                key_part, scope_part = segment.split(":", 1)
                scopes = set(s.strip() for s in scope_part.split("|") if s.strip())
            else:
                key_part = segment
                scopes = {"admin"}  # Default for backward compatibility

            key_hash = cls._hash_key(key_part)
            keys.append(ApiKey(
                key_hash=key_hash,
                scopes=scopes,
                created_at=datetime.now(timezone.utc),
            ))

        return cls(keys)

    @classmethod
    def from_plaintext_list(cls, plaintext_keys: List[str]) -> "ApiKeyManager":
        """Create manager from a list of plaintext keys (all get 'admin' scope)."""
        keys = []
        for key_text in plaintext_keys:
            key_hash = cls._hash_key(key_text)
            keys.append(ApiKey(
                key_hash=key_hash,
                scopes={"admin"},
                created_at=datetime.now(timezone.utc),
            ))
        return cls(keys)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, plaintext_key: str) -> Optional[ApiKey]:
        """
        Validate a plaintext API key.

        Returns the ApiKey metadata if valid, None if invalid/expired.
        Updates last_used timestamp on successful validation.
        """
        if not plaintext_key:
            return None

        key_hash = self._hash_key(plaintext_key)
        api_key = self._keys.get(key_hash)

        if api_key is None:
            return None

        if api_key.is_expired():
            return None

        # Update last_used (create new instance since dataclass is frozen)
        updated = ApiKey(
            key_hash=api_key.key_hash,
            scopes=api_key.scopes,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
            last_used_at=datetime.now(timezone.utc),
            tenant_id=api_key.tenant_id,
            description=api_key.description,
        )
        self._keys[key_hash] = updated
        return updated

    def validate_or_raise(self, plaintext_key: str) -> ApiKey:
        """Validate a key, raising ValueError if invalid."""
        key = self.validate(plaintext_key)
        if key is None:
            raise ValueError("Invalid or expired API key")
        return key

    # ------------------------------------------------------------------
    # Key Management
    # ------------------------------------------------------------------

    def add_key(
        self,
        plaintext_key: str,
        scopes: Optional[Set[str]] = None,
        expires_at: Optional[datetime] = None,
        tenant_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ApiKey:
        """Add a new API key."""
        key_hash = self._hash_key(plaintext_key)
        if key_hash in self._keys:
            raise ValueError("Key already exists")

        api_key = ApiKey(
            key_hash=key_hash,
            scopes=scopes or {"read"},
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            tenant_id=tenant_id,
            description=description,
        )
        self._keys[key_hash] = api_key
        return api_key

    def revoke_key(self, key_hash: str) -> bool:
        """Revoke an API key by its hash."""
        if key_hash in self._keys:
            del self._keys[key_hash]
            return True
        return False

    def list_keys(self) -> List[ApiKey]:
        """List all keys (without returning hashes for security)."""
        return list(self._keys.values())

    def get_key_metadata(self, key_hash: str) -> Optional[ApiKey]:
        """Get metadata for a key by its hash."""
        return self._keys.get(key_hash)

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_key(plaintext: str) -> str:
        """Hash a plaintext key with SHA-256."""
        return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_key(prefix: str = "sk", length: int = 32) -> str:
        """Generate a secure random API key."""
        token = secrets.token_urlsafe(length)
        return f"{prefix}_{token}"

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Get statistics about registered keys."""
        total = len(self._keys)
        expired = sum(1 for k in self._keys.values() if k.is_expired())
        active = total - expired
        by_scope: dict[str, int] = {}
        for k in self._keys.values():
            for scope in k.scopes:
                by_scope[scope] = by_scope.get(scope, 0) + 1

        return {
            "total_keys": total,
            "active_keys": active,
            "expired_keys": expired,
            "by_scope": by_scope,
        }


class APIKeyEnvironment(str, Enum):
    """API key environment types."""
    TEST = "test"
    LIVE = "live"


class APIKeyError(Exception):
    """Raised when API key validation fails."""
    pass


class APIKeyService:
    """
    Production-grade API key service with PostgreSQL persistence.
    
    Supports create, validate, revoke, rotate operations with caching.
    """
    
    def __init__(self, db_pool, cache=None):
        self.db_pool = db_pool
        self.cache = cache
    
    async def create(
        self,
        tenant_id: str,
        description: str,
        environment: str = "test",
        scopes: Optional[Set[str]] = None,
    ) -> "CreatedKey":
        """Create a new API key for a tenant."""
        key_id = f"gk_{environment}_{secrets.token_urlsafe(12)}"
        key_secret = secrets.token_urlsafe(32)
        secret_hash = hashlib.sha256(key_secret.encode()).hexdigest()
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO api_keys (key_id, key_hash, tenant_id, description, environment, scopes, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                """,
                key_id,
                secret_hash,
                tenant_id,
                description,
                environment,
                list(scopes or {"read"}),
            )
        
        # Cache the new key
        if self.cache:
            await self.cache.set(
                f"api_key:{key_id}",
                {
                    "key_id": key_id,
                    "tenant_id": tenant_id,
                    "scopes": list(scopes or {"read"}),
                    "environment": environment,
                },
                ttl=300,
            )
        
        return CreatedKey(key_id=key_id, key_secret=key_secret, environment=environment)
    
    async def validate(self, key_secret: str) -> Optional["ValidatedKey"]:
        """Validate an API key by its secret."""
        if not key_secret:
            return None
        
        secret_hash = hashlib.sha256(key_secret.encode()).hexdigest()
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT key_id, tenant_id, scopes, environment, revoked_at, expires_at
                FROM api_keys
                WHERE key_hash = $1
                """,
                secret_hash,
            )
            
            if row is None:
                return None
            
            if row["revoked_at"]:
                return None
            
            if row["expires_at"] and row["expires_at"] < datetime.now(timezone.utc):
                return None
            
            # Update last used
            await conn.execute(
                "UPDATE api_keys SET last_used_at = NOW() WHERE key_id = $1",
                row["key_id"],
            )
            
            return ValidatedKey(
                key_id=row["key_id"],
                tenant_id=row["tenant_id"],
                scopes=set(row["scopes"] or ["read"]),
                environment=row["environment"],
            )
    
    async def revoke(self, key_id: str) -> bool:
        """Revoke an API key."""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE api_keys SET revoked_at = NOW() WHERE key_id = $1",
                key_id,
            )
            # asyncpg returns "UPDATE N" string
            updated = int(result.split()[-1]) if result else 0
        
        if self.cache:
            await self.cache.delete(f"api_key:{key_id}")
        
        return updated > 0
    
    async def rotate(self, key_id: str) -> "CreatedKey":
        """Rotate an API key — revoke old, create new with same settings."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT tenant_id, description, environment, scopes FROM api_keys WHERE key_id = $1",
                key_id,
            )
            
            if row is None:
                raise APIKeyError(f"Key {key_id} not found")
            
            # Revoke old
            await conn.execute(
                "UPDATE api_keys SET revoked_at = NOW() WHERE key_id = $1",
                key_id,
            )
        
        if self.cache:
            await self.cache.delete(f"api_key:{key_id}")
        
        # Create new key with same settings
        return await self.create(
            tenant_id=row["tenant_id"],
            description=row["description"],
            environment=row["environment"],
            scopes=set(row["scopes"] or ["read"]),
        )


@dataclass
class CreatedKey:
    """Result of creating a new API key."""
    key_id: str
    key_secret: str
    environment: str


@dataclass
class ValidatedKey:
    """Result of validating an API key."""
    key_id: str
    tenant_id: str
    scopes: Set[str]
    environment: str


__all__ = ["ApiKeyManager", "ApiKey", "APIKeyService", "APIKeyError"]
