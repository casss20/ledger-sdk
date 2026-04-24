"""
Token Vault — Stores GovernanceDecisions and derived CapabilityTokens.

Why: Decisions are first-class; tokens are optional derivations.
Vault supports resolving by decision_id or token_id.
Strict tenant isolation via RLS.
"""

import json
from typing import Optional


class TokenVault:
    """
    Stores and resolves governance decisions and capability tokens.

    Tenant-isolated via RLS. Vault sets tenant context internally.
    """

    def __init__(self, db_pool, tenant_context_provider=None):
        self.db = db_pool
        self.get_tenant = tenant_context_provider

    async def store_decision(self, decision) -> None:
        """Store a GovernanceDecision."""
        async with self.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_tenant_context($1)", decision.tenant_id)
                await conn.execute(
                    """
                    INSERT INTO governance_decisions (
                        decision_id, decision_type, tenant_id, actor_id,
                        action, scope_actions, scope_resources,
                        constraints, expiry, kill_switch_scope,
                        created_at, reason
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (decision_id) DO UPDATE SET
                        decision_type = EXCLUDED.decision_type,
                        reason = EXCLUDED.reason
                    """,
                    decision.decision_id,
                    decision.decision_type.value,
                    decision.tenant_id,
                    decision.actor_id,
                    decision.action,
                    decision.scope.actions,
                    decision.scope.resources,
                    json.dumps(decision.constraints),
                    decision.expiry,
                    decision.kill_switch_scope.value,
                    decision.created_at,
                    decision.reason,
                )

    async def store_token(self, token) -> None:
        """Store a CapabilityToken (links to a decision)."""
        async with self.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_tenant_context($1)", token.tenant_id)
                await conn.execute(
                    """
                    INSERT INTO governance_tokens (
                        token_id, decision_id, tenant_id, actor_id,
                        scope_actions, scope_resources, expiry,
                        created_at, chain_hash
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    token.token_id,
                    token.decision_id,
                    token.tenant_id,
                    token.actor_id,
                    token.scope_actions,
                    token.scope_resources,
                    token.expiry,
                    token.created_at,
                    token.chain_hash,
                )

    async def resolve_token(self, token_id: str, tenant_id: str = None) -> Optional[dict]:
        """Resolve a capability token by ID."""
        tid = tenant_id or (self.get_tenant() if self.get_tenant else None)
        async with self.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_tenant_context($1)", tid)
                row = await conn.fetchrow(
                    """
                    SELECT token_id, decision_id, tenant_id, actor_id,
                           scope_actions, scope_resources, expiry,
                           created_at, chain_hash
                    FROM governance_tokens
                    WHERE token_id = $1
                    """,
                    token_id,
                )
                return dict(row) if row else None

    async def resolve_decision(self, decision_id: str, tenant_id: str = None) -> Optional[dict]:
        """Resolve a governance decision by ID."""
        tid = tenant_id or (self.get_tenant() if self.get_tenant else None)
        async with self.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_tenant_context($1)", tid)
                row = await conn.fetchrow(
                    """
                    SELECT decision_id, decision_type, tenant_id, actor_id,
                           action, scope_actions, scope_resources,
                           constraints, expiry, kill_switch_scope,
                           created_at, reason
                    FROM governance_decisions
                    WHERE decision_id = $1
                    """,
                    decision_id,
                )
                return dict(row) if row else None

    async def get_chain(self, token_id: str, tenant_id: str = None) -> list:
        """Get token chain for tamper detection."""
        tid = tenant_id or (self.get_tenant() if self.get_tenant else None)
        async with self.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_tenant_context($1)", tid)
                row = await conn.fetchrow(
                    "SELECT token_id, chain_hash FROM governance_tokens WHERE token_id = $1",
                    token_id,
                )
                return [dict(row)] if row else []

    async def verify_chain(self, token_id: str) -> bool:
        """Verify token integrity by checking linked decision exists."""
        token_data = await self.resolve_token(token_id)
        if not token_data:
            return False
        decision = await self.resolve_decision(token_data["decision_id"])
        return decision is not None
