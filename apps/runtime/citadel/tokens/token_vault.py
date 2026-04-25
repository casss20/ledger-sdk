"""
Token Vault — Stores GovernanceDecisions and derived CapabilityTokens.

Why: Decisions are first-class; tokens are optional derivations.
Vault supports resolving by decision_id or token_id.
Strict tenant isolation via RLS.
"""

import json
from typing import Optional

from .governance_token import CapabilityToken


class TokenVault:
    """
    Stores and resolves governance decisions and capability tokens.

    Tenant-isolated via RLS. Vault sets tenant context internally.
    """

    def __init__(self, db_pool, tenant_context_provider=None):
        self.db = db_pool
        self.get_tenant = tenant_context_provider

    async def issue_token_for_decision(
        self,
        decision,
        *,
        lifetime_seconds: int = 120,
        issuer: str = "citadel",
        audience: str = "citadel-runtime",
        tool: str = None,
    ):
        """Persist a decision first, then derive and store its capability token."""
        await self.store_decision(decision)
        token = CapabilityToken.derive(
            decision,
            lifetime_seconds=lifetime_seconds,
            issuer=issuer,
            audience=audience,
            tool=tool,
        )
        await self.store_token(token)
        return token

    async def store_decision(self, decision) -> None:
        """Store a GovernanceDecision."""
        async with self.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_tenant_context($1)", decision.tenant_id)
                await conn.execute(
                    """
                    INSERT INTO governance_decisions (
                        decision_id, decision_type, tenant_id, actor_id,
                        request_id, trace_id, workspace_id, agent_id,
                        subject_type, subject_id, action, resource,
                        risk_level, policy_version, approval_state,
                        approved_by, approved_at, issued_token_id,
                        expires_at, revoked_at, revoked_reason,
                        scope_actions, scope_resources,
                        constraints, expiry, kill_switch_scope,
                        created_at, reason
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8,
                        $9, $10, $11, $12, $13, $14, $15,
                        $16, $17, $18, $19, $20, $21, $22,
                        $23, $24, $25, $26, $27, $28
                    )
                    ON CONFLICT (decision_id) DO UPDATE SET
                        decision_type = EXCLUDED.decision_type,
                        issued_token_id = COALESCE(EXCLUDED.issued_token_id, governance_decisions.issued_token_id),
                        revoked_at = EXCLUDED.revoked_at,
                        revoked_reason = EXCLUDED.revoked_reason,
                        reason = EXCLUDED.reason
                    """,
                    decision.decision_id,
                    decision.decision_type.value,
                    decision.tenant_id,
                    decision.actor_id,
                    decision.request_id,
                    decision.trace_id,
                    decision.workspace_id or decision.tenant_id,
                    decision.agent_id or decision.actor_id,
                    decision.subject_type,
                    decision.subject_id or decision.actor_id,
                    decision.action,
                    decision.resource,
                    decision.risk_level,
                    decision.policy_version,
                    decision.approval_state,
                    decision.approved_by,
                    decision.approved_at,
                    decision.issued_token_id or decision.gt_token,
                    decision.expiry,
                    decision.revoked_at,
                    decision.revoked_reason,
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
                        iss, subject, audience, workspace_id, tool,
                        action, resource_scope, risk_level, not_before,
                        trace_id, approval_ref, revoked_at, revoked_reason,
                        scope_actions, scope_resources, expiry,
                        created_at, chain_hash
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8,
                        $9, $10, $11, $12, $13, $14, $15,
                        $16, $17, $18, $19, $20, $21, $22
                    )
                    """,
                    token.token_id,
                    token.decision_id,
                    token.tenant_id,
                    token.actor_id,
                    token.iss,
                    token.subject or token.actor_id,
                    token.audience,
                    token.workspace_id or token.tenant_id,
                    token.tool,
                    token.action,
                    token.resource_scope,
                    token.risk_level,
                    token.not_before,
                    token.trace_id,
                    token.approval_ref,
                    None,
                    None,
                    token.scope_actions,
                    token.scope_resources,
                    token.expiry,
                    token.created_at,
                    token.chain_hash,
                )
                await conn.execute(
                    """
                    UPDATE governance_decisions
                    SET issued_token_id = $1
                    WHERE decision_id = $2 AND issued_token_id IS NULL
                    """,
                    token.token_id,
                    token.decision_id,
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
                           iss, subject, audience, workspace_id, tool,
                           action, resource_scope, risk_level, not_before,
                           trace_id, approval_ref, revoked_at, revoked_reason,
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
                           request_id, trace_id, workspace_id, agent_id,
                           subject_type, subject_id, action, resource,
                           risk_level, policy_version, approval_state,
                           approved_by, approved_at, issued_token_id,
                           expires_at, revoked_at, revoked_reason,
                           scope_actions, scope_resources,
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

    async def revoke_token(
        self,
        token_id: str,
        tenant_id: str,
        reason: str = "revoked",
    ) -> bool:
        """Centrally revoke one capability token."""
        async with self.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_tenant_context($1)", tenant_id)
                result = await conn.execute(
                    """
                    UPDATE governance_tokens
                    SET revoked_at = NOW(), revoked_reason = $2
                    WHERE token_id = $1 AND revoked_at IS NULL
                    """,
                    token_id,
                    reason,
                )
                return "UPDATE 1" in result

    async def revoke_decision(
        self,
        decision_id: str,
        tenant_id: str,
        reason: str = "revoked",
    ) -> bool:
        """Mark a decision as no longer executable."""
        async with self.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_tenant_context($1)", tenant_id)
                result = await conn.execute(
                    """
                    UPDATE governance_decisions
                    SET decision_type = 'revoked',
                        revoked_at = NOW(),
                        revoked_reason = $2
                    WHERE decision_id = $1 AND revoked_at IS NULL
                    """,
                    decision_id,
                    reason,
                )
                return "UPDATE 1" in result

    async def check_kill_switch(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        action: str,
        resource: str = None,
        tool: str = None,
    ) -> Optional[dict]:
        """Check central kill_switches state for introspection enforcement."""
        async with self.db.acquire() as conn:
            async with conn.transaction():
                # Introspection must see global/tool emergency state even when
                # a row is not tenant-scoped, so this deliberately uses the
                # existing explicit admin bypass inside this read-only check.
                await conn.execute("SET LOCAL app.admin_bypass = 'true'")
                row = await conn.fetchrow(
                    """
                    SELECT switch_id, tenant_id, scope_type::text AS scope_type,
                           scope_value, reason
                    FROM kill_switches
                    WHERE enabled = TRUE
                      AND (
                        scope_type = 'global'
                        OR (scope_type = 'tenant' AND scope_value = $1)
                        OR (scope_type = 'actor' AND scope_value = $2)
                        OR (scope_type = 'action' AND scope_value IN ($3, COALESCE($5, $3)))
                        OR ($4::text IS NOT NULL AND scope_type = 'resource' AND scope_value = $4)
                      )
                    ORDER BY
                      CASE scope_type
                        WHEN 'resource' THEN 1
                        WHEN 'action' THEN 2
                        WHEN 'actor' THEN 3
                        WHEN 'tenant' THEN 4
                        ELSE 5
                      END,
                      created_at DESC
                    LIMIT 1
                    """,
                    tenant_id,
                    actor_id,
                    action,
                    resource,
                    tool,
                )
                return dict(row) if row else None
