import hashlib
import hmac
import json
import secrets
import base64
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class AgentIdentity:
    """
    Cryptographic identity for an agent.
    
    Each agent gets:
    - A unique agent_id
    - A public key for verification
    - A secret key for signing (stored hashed)
    - A trust level
    - Verification status
    """
    agent_id: str
    tenant_id: str
    public_key: str  # Ed25519 public key (base64)
    secret_key_hash: str  # bcrypt or argon2 hash of secret key
    trust_level: str = "unverified"
    verification_status: str = "pending"  # pending, verified, revoked
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_verified_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "public_key": self.public_key,
            "trust_level": self.trust_level,
            "verification_status": self.verification_status,
            "created_at": self.created_at.isoformat() + "Z",
            "last_verified_at": self.last_verified_at.isoformat() + "Z" if self.last_verified_at else None,
            "metadata": self.metadata,
        }


@dataclass
class AgentCredentials:
    """Credentials returned after agent registration."""
    agent_id: str
    secret_key: str  # Plain text — only shown once!
    public_key: str
    api_key: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "secret_key": self.secret_key,  # ⚠️ Only for initial setup
            "public_key": self.public_key,
            "api_key": self.api_key,
        }


class IdentityManager:
    """
    Manages agent identities with cryptographic verification.
    
    Uses:
    - Ed25519 for keypairs (if available) or HMAC fallback
    - bcrypt for secret key hashing
    - API keys for initial authentication
    """
    
    def __init__(self, db_pool):
        self.db = db_pool
        self._secret_cache: Dict[str, str] = {}  # agent_id -> secret_key (in-memory only)
    
    def _generate_keypair(self) -> tuple:
        """Generate a keypair. Returns (public_key, secret_key)."""
        try:
            # Try Ed25519 (cryptography library)
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives import serialization
            
            private_key = Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            return (
                base64.b64encode(public_bytes).decode(),
                base64.b64encode(private_bytes).decode(),
            )
        except ImportError:
            # Fallback: HMAC-based identity
            secret = secrets.token_urlsafe(32)
            public = hashlib.sha256(secret.encode()).hexdigest()
            return public, secret
    
    def _hash_secret(self, secret: str) -> str:
        """Hash a secret key."""
        try:
            import bcrypt
            return bcrypt.hashpw(secret.encode(), bcrypt.gensalt(rounds=12)).decode()
        except ImportError:
            # Fallback to HMAC
            salt = secrets.token_hex(16)
            return f"hmac${salt}${hmac.new(salt.encode(), secret.encode(), hashlib.sha256).hexdigest()}"
    
    def _verify_secret(self, secret: str, hashed: str) -> bool:
        """Verify a secret against its hash."""
        if hashed.startswith("hmac$"):
            _, salt, expected = hashed.split("$", 2)
            return hmac.compare_digest(
                hmac.new(salt.encode(), secret.encode(), hashlib.sha256).hexdigest(),
                expected
            )
        try:
            import bcrypt
            return bcrypt.checkpw(secret.encode(), hashed.encode())
        except ImportError:
            return False
    
    def _generate_api_key(self, agent_id: str, tenant_id: str) -> str:
        """Generate a unique API key for an agent."""
        raw = f"{agent_id}:{tenant_id}:{secrets.token_urlsafe(16)}"
        return f"ak_{base64.b64encode(raw.encode()).decode()[:32]}"
    
    async def register_agent(self, agent_id: str, tenant_id: str, name: str, owner: str = "op-1") -> AgentCredentials:
        """
        Register a new agent with cryptographic identity.
        
        Returns credentials including secret_key (shown only once).
        """
        public_key, secret_key = self._generate_keypair()
        secret_hash = self._hash_secret(secret_key)
        api_key = self._generate_api_key(agent_id, tenant_id)
        
        async with self.db.acquire() as conn:
            # Store identity
            await conn.execute(
                """
                INSERT INTO agent_identities (agent_id, tenant_id, public_key, secret_key_hash, trust_level, verification_status, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                ON CONFLICT (agent_id) DO UPDATE SET
                    public_key = EXCLUDED.public_key,
                    secret_key_hash = EXCLUDED.secret_key_hash,
                    updated_at = NOW()
                """,
                agent_id, tenant_id, public_key, secret_hash, "unverified", "pending"
            )
            
            # Also update the agents table
            await conn.execute(
                """
                INSERT INTO agents (agent_id, tenant_id, name, status, owner, created_at, updated_at)
                VALUES ($1, $2, $3, 'healthy', $4, NOW(), NOW())
                ON CONFLICT (agent_id) DO UPDATE SET
                    tenant_id = EXCLUDED.tenant_id,
                    name = EXCLUDED.name,
                    updated_at = NOW()
                """,
                agent_id, tenant_id, name, owner
            )
        
        return AgentCredentials(
            agent_id=agent_id,
            secret_key=secret_key,
            public_key=public_key,
            api_key=api_key,
        )
    
    async def authenticate_agent(self, agent_id: str, secret_key: str) -> Optional[AgentIdentity]:
        """Authenticate an agent using its secret key."""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM agent_identities WHERE agent_id = $1",
                agent_id
            )
        
        if not row:
            return None
        
        if not self._verify_secret(secret_key, row["secret_key_hash"]):
            return None
        
        return AgentIdentity(
            agent_id=row["agent_id"],
            tenant_id=row["tenant_id"],
            public_key=row["public_key"],
            secret_key_hash=row["secret_key_hash"],
            trust_level=row["trust_level"],
            verification_status=row["verification_status"],
            created_at=row["created_at"],
            last_verified_at=row.get("last_verified_at"),
            metadata=row.get("metadata", {}),
        )
    
    async def verify_agent(self, agent_id: str, verifier_id: str) -> bool:
        """Mark an agent as verified by a human operator."""
        async with self.db.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE agent_identities
                SET verification_status = 'verified',
                    trust_level = 'standard',
                    last_verified_at = NOW(),
                    updated_at = NOW(),
                    metadata = jsonb_set(COALESCE(metadata, '{}'), '{verified_by}', $2)
                WHERE agent_id = $1
                """,
                agent_id, json.dumps(verifier_id)
            )
            return "UPDATE 1" in result
    
    async def revoke_agent(self, agent_id: str, reason: str) -> bool:
        """Revoke an agent's identity."""
        async with self.db.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE agent_identities
                SET verification_status = 'revoked',
                    trust_level = 'revoked',
                    updated_at = NOW(),
                    metadata = jsonb_set(COALESCE(metadata, '{}'), '{revocation_reason}', $2)
                WHERE agent_id = $1
                """,
                agent_id, json.dumps(reason)
            )
            return "UPDATE 1" in result
    
    async def get_identity(self, agent_id: str) -> Optional[AgentIdentity]:
        """Get an agent's identity."""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM agent_identities WHERE agent_id = $1",
                agent_id
            )
        
        if not row:
            return None
        
        return AgentIdentity(
            agent_id=row["agent_id"],
            tenant_id=row["tenant_id"],
            public_key=row["public_key"],
            secret_key_hash=row["secret_key_hash"],
            trust_level=row["trust_level"],
            verification_status=row["verification_status"],
            created_at=row["created_at"],
            last_verified_at=row.get("last_verified_at"),
            metadata=row.get("metadata", {}),
        )
    
    async def list_identities(self, tenant_id: Optional[str] = None) -> list:
        """List all agent identities."""
        async with self.db.acquire() as conn:
            if tenant_id:
                rows = await conn.fetch(
                    "SELECT * FROM agent_identities WHERE tenant_id = $1 ORDER BY created_at DESC",
                    tenant_id
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM agent_identities ORDER BY created_at DESC"
                )
        
        return [AgentIdentity(
            agent_id=r["agent_id"],
            tenant_id=r["tenant_id"],
            public_key=r["public_key"],
            secret_key_hash=r["secret_key_hash"],
            trust_level=r["trust_level"],
            verification_status=r["verification_status"],
            created_at=r["created_at"],
            last_verified_at=r.get("last_verified_at"),
            metadata=r.get("metadata", {}),
        ) for r in rows]