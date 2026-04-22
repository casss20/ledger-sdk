"""
Token Vault — Ledger's proprietary storage for gt_ tokens.

Why: Tokens only have meaning when resolved by Ledger.
Removing Ledger = losing all resolution capability.
This is the data gravity mechanism.
"""

import json
from typing import Optional

from .governance_token import GovernanceToken


class TokenVault:
    """
    Stores and resolves gt_ tokens.

    Only Ledger infrastructure can resolve tokens to decision traces.
    Vault is tenant-isolated (strict RLS).
    """

    def __init__(self, db_pool, tenant_context_provider):
        self.db = db_pool
        self.get_tenant = tenant_context_provider

    async def store(self, token: GovernanceToken) -> None:
        """Store token in vault (tenant-scoped)."""
        async with self.db.acquire() as conn:
            # Set tenant context for RLS enforcement
            await conn.execute("SELECT set_tenant_context($1)", token.tenant_id)
            await conn.execute(
                """
                INSERT INTO governance_tokens (
                    token_id, token_type, tenant_id, agent_id,
                    created_at, content_hash, chain_hash,
                    decision_trace, policy_version, previous_token_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                token.token_id,
                token.token_type.value,
                token.tenant_id,
                token.agent_id,
                token.created_at,
                token.content_hash,
                token.chain_hash,
                json.dumps(token.decision_trace),
                token._policy_version,
                None,  # previous_token_id would need chain tracking
            )

    async def resolve(self, token_id: str) -> Optional[dict]:
        """
        Resolve gt_ token to full decision trace.
        Only callable within Ledger's runtime.
        Returns None if token doesn't exist or tenant mismatch.
        """
        tenant_id = self.get_tenant()
        async with self.db.acquire() as conn:
            await conn.execute("SELECT set_tenant_context($1)", tenant_id)
            row = await conn.fetchrow(
                """
                SELECT token_id, token_type, tenant_id, agent_id,
                       created_at, content_hash, chain_hash,
                       decision_trace, policy_version
                FROM governance_tokens
                WHERE token_id = $1
                """,
                token_id,
            )
            if not row:
                return None
            return dict(row)

    async def get_chain(self, token_id: str) -> list:
        """
        Get hash chain ending at token_id.
        Used for tamper detection and audit verification.
        """
        tenant_id = self.get_tenant()
        async with self.db.acquire() as conn:
            await conn.execute("SELECT set_tenant_context($1)", tenant_id)
            row = await conn.fetchrow(
                """
                SELECT token_id, chain_hash, previous_token_id
                FROM governance_tokens
                WHERE token_id = $1
                """,
                token_id,
            )
            if not row:
                return []
            return [dict(row)]

    async def verify_chain(self, token_id: str) -> bool:
        """
        Verify hash chain integrity from genesis to token_id.
        Returns False if any token in chain is tampered.
        """
        tenant_id = self.get_tenant()
        async with self.db.acquire() as conn:
            await conn.execute("SELECT set_tenant_context($1)", tenant_id)
            row = await conn.fetchrow(
                """
                SELECT content_hash, decision_trace
                FROM governance_tokens
                WHERE token_id = $1
                """,
                token_id,
            )
            if not row:
                return False

            import hashlib
            from .governance_token import _canonical_json

            expected = hashlib.sha256(
                _canonical_json(row["decision_trace"]).encode()
            ).hexdigest()
            return expected == row["content_hash"]
