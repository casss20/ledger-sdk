"""
Audit Chain Anchoring — Merkle Root Signing

Provides external anchoring for the audit chain:
- Compute Merkle roots over batches of audit events
- Sign roots with Ed25519 or HMAC
- Verify chain integrity against stored roots
- Optional: Publish to transparency logs

Usage:
    from citadel.audit_anchoring import AuditAnchorService
    
    anchor = AuditAnchorService(db_pool, signing_key)
    
    # Sign the latest batch of audit events
    root_hash = await anchor.sign_batch(from_event_id=1, to_event_id=1000)
    
    # Verify the entire chain including Merkle roots
    result = await anchor.verify_chain()
    assert result.merkle_root_valid is True
"""

import hashlib
import hmac
import secrets
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timezone

import asyncpg


@dataclass
class AnchorResult:
    """Result of signing a Merkle root."""
    root_hash: str
    from_event_id: int
    to_event_id: int
    event_count: int
    signature: str
    key_id: str
    signed_at: datetime
    external_anchor: Optional[str] = None


@dataclass
class ChainVerification:
    """Result of full chain verification."""
    chain_valid: bool
    chain_checked_count: int
    chain_broken_at: Optional[int]
    merkle_root_valid: Optional[bool]
    latest_root_hash: Optional[str]
    latest_root_signed_at: Optional[datetime]


class AuditAnchorService:
    """
    Signs and verifies Merkle roots for the audit chain.
    
    Supports two signing modes:
    1. HMAC-SHA256 (symmetric) — simpler, suitable for single-tenant deployments
    2. Ed25519 (asymmetric) — preferred for multi-tenant, supports public verification
    """
    
    def __init__(
        self,
        db_pool: asyncpg.Pool,
        signing_key: bytes,
        key_id: str = "audit-anchor-1",
        algorithm: str = "hmac-sha256",
    ):
        self.pool = db_pool
        self.signing_key = signing_key
        self.key_id = key_id
        self.algorithm = algorithm
    
    # ------------------------------------------------------------------
    # Merkle Root Computation
    # ------------------------------------------------------------------
    
    async def compute_merkle_root(
        self,
        from_event_id: int,
        to_event_id: int,
    ) -> str:
        """Compute Merkle root over a range of audit events."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT event_hash
                FROM audit_events
                WHERE event_id BETWEEN $1 AND $2
                ORDER BY event_id
                """,
                from_event_id,
                to_event_id,
            )
        
        # Iterative hash combination (simplified Merkle)
        combined = b""
        for row in rows:
            combined = hashlib.sha256(combined + row["event_hash"].encode()).digest()
        
        return combined.hex()
    
    # ------------------------------------------------------------------
    # Signing
    # ------------------------------------------------------------------
    
    def _sign(self, message: bytes) -> str:
        """Sign a message with the configured algorithm."""
        if self.algorithm == "hmac-sha256":
            return hmac.new(self.signing_key, message, hashlib.sha256).hexdigest()
        elif self.algorithm == "ed25519":
            # Requires cryptography library
            try:
                from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                    Ed25519PrivateKey
                )
                private_key = Ed25519PrivateKey.from_private_bytes(self.signing_key)
                signature = private_key.sign(message)
                return signature.hex()
            except ImportError:
                raise ImportError(
                    "Ed25519 signing requires 'cryptography' package. "
                    "Install with: pip install cryptography"
                )
        else:
            raise ValueError(f"Unsupported signing algorithm: {self.algorithm}")
    
    def _verify_signature(self, message: bytes, signature: str) -> bool:
        """Verify a signature."""
        if self.algorithm == "hmac-sha256":
            expected = hmac.new(self.signing_key, message, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, signature)
        elif self.algorithm == "ed25519":
            try:
                from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                    Ed25519PrivateKey
                )
                private_key = Ed25519PrivateKey.from_private_bytes(self.signing_key)
                public_key = private_key.public_key()
                public_key.verify(bytes.fromhex(signature), message)
                return True
            except (ValueError, TypeError, RuntimeError, ImportError) as crypto_err:
                logger.warning(f"Ed25519 signature verification failed ({type(crypto_err).__name__}): {crypto_err}")
                return False
        return False
    
    # ------------------------------------------------------------------
    # Batch Signing
    # ------------------------------------------------------------------
    
    async def sign_batch(
        self,
        from_event_id: int,
        to_event_id: int,
        tenant_id: Optional[str] = None,
        external_anchor: Optional[str] = None,
    ) -> AnchorResult:
        """
        Sign a batch of audit events and store the Merkle root.
        
        Args:
            from_event_id: First event in the batch
            to_event_id: Last event in the batch
            tenant_id: Optional tenant scoping
            external_anchor: Optional external reference (e.g., tx hash)
        """
        # Compute root
        root_hash = await self.compute_merkle_root(from_event_id, to_event_id)
        
        # Sign
        signature = self._sign(root_hash.encode())
        
        # Count events
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COUNT(*) as cnt
                FROM audit_events
                WHERE event_id BETWEEN $1 AND $2
                """,
                from_event_id,
                to_event_id,
            )
            event_count = row["cnt"]
            
            # Store in database
            await conn.execute(
                """
                INSERT INTO audit_merkle_roots (
                    root_hash, from_event_id, to_event_id, event_count,
                    signature, key_id, external_anchor, tenant_id, signed_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                ON CONFLICT (root_hash) DO UPDATE SET
                    signature = EXCLUDED.signature,
                    key_id = EXCLUDED.key_id,
                    external_anchor = EXCLUDED.external_anchor,
                    signed_at = NOW()
                """,
                root_hash,
                from_event_id,
                to_event_id,
                event_count,
                signature,
                self.key_id,
                external_anchor,
                tenant_id,
            )
        
        return AnchorResult(
            root_hash=root_hash,
            from_event_id=from_event_id,
            to_event_id=to_event_id,
            event_count=event_count,
            signature=signature,
            key_id=self.key_id,
            signed_at=datetime.now(timezone.utc),
            external_anchor=external_anchor,
        )
    
    async def sign_all_unanchored(
        self,
        batch_size: int = 1000,
        tenant_id: Optional[str] = None,
    ) -> List[AnchorResult]:
        """
        Sign all audit events not yet covered by a Merkle root.
        
        Processes in batches for large backlogs.
        """
        results = []
        
        async with self.pool.acquire() as conn:
            # Find the latest anchored event
            row = await conn.fetchrow(
                """
                SELECT COALESCE(MAX(to_event_id), 0) as last_anchored
                FROM audit_merkle_roots
                WHERE tenant_id IS NOT DISTINCT FROM $1
                """,
                tenant_id,
            )
            last_anchored = row["last_anchored"]
            
            # Get max event id
            row = await conn.fetchrow("SELECT MAX(event_id) as max_id FROM audit_events")
            max_event_id = row["max_id"] or 0
        
        if max_event_id <= last_anchored:
            return results  # Nothing to anchor
        
        # Process in batches
        current = last_anchored + 1
        while current <= max_event_id:
            batch_end = min(current + batch_size - 1, max_event_id)
            result = await self.sign_batch(
                from_event_id=current,
                to_event_id=batch_end,
                tenant_id=tenant_id,
            )
            results.append(result)
            current = batch_end + 1
        
        return results
    
    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------
    
    async def verify_chain(self) -> ChainVerification:
        """
        Verify the full audit chain including the latest Merkle root.
        
        Uses the database function for chain verification, then
        independently verifies the Merkle root signature.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM verify_audit_chain_with_merkle()")
        
        # Independently verify the Merkle root signature
        merkle_valid = None
        if row["latest_root_hash"]:
            root_hash = row["latest_root_hash"]
            # Fetch the stored signature
            async with self.pool.acquire() as conn:
                sig_row = await conn.fetchrow(
                    "SELECT signature FROM audit_merkle_roots WHERE root_hash = $1",
                    root_hash,
                )
            
            if sig_row:
                merkle_valid = self._verify_signature(
                    root_hash.encode(),
                    sig_row["signature"],
                )
        
        return ChainVerification(
            chain_valid=row["chain_valid"],
            chain_checked_count=row["chain_checked_count"],
            chain_broken_at=row["chain_broken_at"],
            merkle_root_valid=merkle_valid,
            latest_root_hash=row["latest_root_hash"],
            latest_root_signed_at=row["latest_root_signed_at"],
        )
    
    async def verify_root(
        self,
        root_hash: str,
        signature: str,
        key_id: Optional[str] = None,
    ) -> bool:
        """Verify a specific Merkle root signature."""
        # Recompute the root from the database
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT from_event_id, to_event_id
                FROM audit_merkle_roots
                WHERE root_hash = $1
                """,
                root_hash,
            )
        
        if not row:
            return False
        
        recomputed = await self.compute_merkle_root(
            row["from_event_id"],
            row["to_event_id"],
        )
        
        if recomputed != root_hash:
            return False
        
        return self._verify_signature(root_hash.encode(), signature)
    
    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    
    @staticmethod
    def generate_hmac_key() -> bytes:
        """Generate a 256-bit key for HMAC-SHA256."""
        return secrets.token_bytes(32)
    
    @staticmethod
    def generate_ed25519_keypair() -> tuple[bytes, bytes]:
        """Generate an Ed25519 keypair (private_key, public_key)."""
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            private_key = Ed25519PrivateKey.generate()
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption(),
            )
            public_bytes = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            return private_bytes, public_bytes
        except ImportError:
            raise ImportError(
                "Ed25519 key generation requires 'cryptography' package. "
                "Install with: pip install cryptography"
            )


__all__ = [
    "AuditAnchorService",
    "AnchorResult",
    "ChainVerification",
]
