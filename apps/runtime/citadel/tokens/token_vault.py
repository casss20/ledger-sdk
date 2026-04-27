"""
Token Vault — Stores GovernanceDecisions and derived CapabilityTokens.

Why: Decisions are first-class; tokens are optional derivations.
Vault supports resolving by decision_id or token_id.
Strict tenant isolation via RLS.
"""

import json
from typing import Optional

from .governance_decision import GovernanceDecision
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
        """Persist a decision and derive/store its capability token atomically.

        Uses a single DB transaction so that a decision is never stored
        without its corresponding token (and vice versa).
        """
        token = CapabilityToken.derive(
            decision,
            lifetime_seconds=lifetime_seconds,
            issuer=issuer,
            audience=audience,
            tool=tool,
        )
        async with self.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_tenant_context($1)", decision.tenant_id)
                # Store decision
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
                        scope_max_spend, scope_rate_limit,
                        constraints, expiry, kill_switch_scope,
                        created_at, reason,
                        root_decision_id, parent_decision_id, parent_actor_id, workflow_id,
                        superseded_at, superseded_reason
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8,
                        $9, $10, $11, $12, $13, $14, $15,
                        $16, $17, $18, $19, $20, $21,
                        $22, $23, $24, $25, $26, $27, $28, $29, $30,
                        $31, $32, $33, $34, $35, $36
                    )
                    ON CONFLICT (decision_id) DO UPDATE SET
                        decision_type = EXCLUDED.decision_type,
                        issued_token_id = COALESCE(EXCLUDED.issued_token_id, governance_decisions.issued_token_id),
                        revoked_at = EXCLUDED.revoked_at,
                        revoked_reason = EXCLUDED.revoked_reason,
                        superseded_at = EXCLUDED.superseded_at,
                        superseded_reason = EXCLUDED.superseded_reason,
                        scope_actions = EXCLUDED.scope_actions,
                        scope_resources = EXCLUDED.scope_resources,
                        scope_max_spend = EXCLUDED.scope_max_spend,
                        scope_rate_limit = EXCLUDED.scope_rate_limit,
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
                    decision.scope.max_spend,
                    decision.scope.rate_limit,
                    json.dumps(decision.constraints) if decision.constraints else '{}',
                    decision.expiry,
                    decision.kill_switch_scope.value,
                    decision.created_at,
                    decision.reason,
                    decision.root_decision_id,
                    decision.parent_decision_id,
                    decision.parent_actor_id,
                    decision.workflow_id,
                    decision.superseded_at,
                    decision.superseded_reason,
                )
                # Store token
                await conn.execute(
                    """
                    INSERT INTO governance_tokens (
                        token_id, decision_id, tenant_id, actor_id,
                        iss, subject, audience, workspace_id, tool,
                        action, resource_scope, risk_level, not_before,
                        trace_id, approval_ref, revoked_at, revoked_reason,
                        scope_actions, scope_resources, expiry,
                        created_at, chain_hash,
                        parent_decision_id, parent_actor_id, workflow_id
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8,
                        $9, $10, $11, $12, $13, $14, $15,
                        $16, $17, $18, $19, $20, $21, $22, $23, $24, $25
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
                    token.parent_decision_id,
                    token.parent_actor_id,
                    token.workflow_id,
                )
                # Link token back to decision
                await conn.execute(
                    """
                    UPDATE governance_decisions
                    SET issued_token_id = $1
                    WHERE decision_id = $2 AND issued_token_id IS NULL
                    """,
                    token.token_id,
                    token.decision_id,
                )
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
                        scope_max_spend, scope_rate_limit,
                        constraints, expiry, kill_switch_scope,
                        created_at, reason,
                        root_decision_id, parent_decision_id, parent_actor_id, workflow_id,
                        superseded_at, superseded_reason
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8,
                        $9, $10, $11, $12, $13, $14, $15,
                        $16, $17, $18, $19, $20, $21,
                        $22, $23, $24, $25, $26, $27, $28, $29, $30,
                        $31, $32, $33, $34, $35, $36
                    )
                    ON CONFLICT (decision_id) DO UPDATE SET
                        decision_type = EXCLUDED.decision_type,
                        issued_token_id = COALESCE(EXCLUDED.issued_token_id, governance_decisions.issued_token_id),
                        revoked_at = EXCLUDED.revoked_at,
                        revoked_reason = EXCLUDED.revoked_reason,
                        superseded_at = EXCLUDED.superseded_at,
                        superseded_reason = EXCLUDED.superseded_reason,
                        scope_actions = EXCLUDED.scope_actions,
                        scope_resources = EXCLUDED.scope_resources,
                        scope_max_spend = EXCLUDED.scope_max_spend,
                        scope_rate_limit = EXCLUDED.scope_rate_limit,
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
                    decision.scope.max_spend,
                    decision.scope.rate_limit,
                    json.dumps(decision.constraints) if decision.constraints else '{}',
                    decision.expiry,
                    decision.kill_switch_scope.value,
                    decision.created_at,
                    decision.reason,
                    decision.root_decision_id,
                    decision.parent_decision_id,
                    decision.parent_actor_id,
                    decision.workflow_id,
                    decision.superseded_at,
                    decision.superseded_reason,
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
                        created_at, chain_hash,
                        parent_decision_id, parent_actor_id, workflow_id
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8,
                        $9, $10, $11, $12, $13, $14, $15,
                        $16, $17, $18, $19, $20, $21, $22, $23, $24, $25
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
                    token.parent_decision_id,
                    token.parent_actor_id,
                    token.workflow_id,
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
            # Read-only: no explicit transaction needed (autocommit)
            await conn.execute("SELECT set_tenant_context($1)", tid)
            row = await conn.fetchrow(
                """
                SELECT token_id, decision_id, tenant_id, actor_id,
                       iss, subject, audience, workspace_id, tool,
                       action, resource_scope, risk_level, not_before,
                       trace_id, approval_ref, revoked_at, revoked_reason,
                       scope_actions, scope_resources, expiry,
                       created_at, chain_hash,
                       parent_decision_id, parent_actor_id, workflow_id
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
            # Read-only: no explicit transaction needed (autocommit)
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
                       scope_max_spend, scope_rate_limit,
                       constraints, expiry, kill_switch_scope,
                       created_at, reason,
                       root_decision_id, parent_decision_id, parent_actor_id, workflow_id,
                       superseded_at, superseded_reason
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
            # Read-only: no explicit transaction needed (autocommit)
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
        """Mark a decision as no longer executable and cascade to active descendants."""
        async with self.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_tenant_context($1)", tenant_id)
                # Revoke the decision itself
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
                # Cascade to active descendants (those with this decision as parent or root)
                await conn.execute(
                    """
                    UPDATE governance_decisions
                    SET decision_type = 'revoked',
                        revoked_at = NOW(),
                        revoked_reason = $2
                    WHERE (parent_decision_id = $1 OR root_decision_id = $1)
                      AND revoked_at IS NULL
                      AND decision_type != 'revoked'
                    """,
                    decision_id,
                    f"cascaded: {reason}",
                )
                # Also revoke any tokens linked to those decisions
                await conn.execute(
                    """
                    UPDATE governance_tokens
                    SET revoked_at = NOW(), revoked_reason = $2
                    WHERE decision_id IN (
                        SELECT decision_id FROM governance_decisions
                        WHERE (parent_decision_id = $1 OR root_decision_id = $1 OR decision_id = $1)
                          AND revoked_at IS NOT NULL
                    )
                      AND revoked_at IS NULL
                    """,
                    decision_id,
                    f"cascaded: {reason}",
                )
                return "UPDATE 1" in result

    async def check_ancestry(
        self,
        decision: GovernanceDecision,
    ) -> tuple[bool, Optional[str]]:
        """Check whether all ancestors of a decision are still active.

        Only REVOCATION cascades to descendants. Superseded status is checked
        at the individual decision level (verify_token / introspect), not here.
        A handoff creates a new independent lineage; delegations made while the
        parent was valid remain valid until expiry or explicit revocation.

        Returns (True, None) if all ancestors are active.
        Returns (False, reason) if any ancestor is revoked or expired.
        """
        # Check immediate parent if present
        if decision.parent_decision_id and decision.parent_decision_id != decision.decision_id:
            parent = await self.resolve_decision(decision.parent_decision_id, tenant_id=decision.tenant_id)
            if parent is None:
                return False, "parent_decision_not_found"
            if parent.get("revoked_at") or parent.get("decision_type") == "revoked":
                return False, "parent_revoked"
            parent_expiry = parent.get("expiry") or parent.get("expires_at")
            if parent_expiry:
                from datetime import datetime, timezone
                try:
                    if isinstance(parent_expiry, str):
                        parent_expiry = datetime.fromisoformat(parent_expiry.replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) > parent_expiry:
                        return False, "parent_expired"
                except (ValueError, TypeError):
                    pass
            # NOTE: parent.superseded_at does NOT cascade — checked at decision level

        # Check root if present and different from parent and self
        root_id = decision.root_decision_id
        if root_id and root_id != decision.decision_id and root_id != decision.parent_decision_id:
            root = await self.resolve_decision(root_id, tenant_id=decision.tenant_id)
            if root is None:
                return False, "root_decision_not_found"
            if root.get("revoked_at") or root.get("decision_type") == "revoked":
                return False, "root_revoked"
            root_expiry = root.get("expiry") or root.get("expires_at")
            if root_expiry:
                from datetime import datetime, timezone
                try:
                    if isinstance(root_expiry, str):
                        root_expiry = datetime.fromisoformat(root_expiry.replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) > root_expiry:
                        return False, "root_expired"
                except (ValueError, TypeError):
                    pass
            # NOTE: root.superseded_at does NOT cascade

        return True, None

    async def check_kill_switch(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        action: str,
        resource: str = None,
        tool: str = None,
        decision_id: str = None,
    ) -> Optional[dict]:
        """Check central kill_switches state for introspection enforcement."""
        async with self.db.acquire() as conn:
            # Read-only: no explicit transaction needed (autocommit)
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
                    OR (scope_type = 'request' AND scope_value = $6)
                    OR (scope_type = 'action' AND scope_value IN ($3, COALESCE($5, $3)))
                    OR ($4::text IS NOT NULL AND scope_type = 'resource' AND scope_value = $4)
                  )
                ORDER BY
                  CASE scope_type
                    WHEN 'request' THEN 1
                    WHEN 'resource' THEN 2
                    WHEN 'action' THEN 3
                    WHEN 'actor' THEN 4
                    WHEN 'tenant' THEN 5
                    ELSE 6
                  END,
                  created_at DESC
                LIMIT 1
                """,
                tenant_id,
                actor_id,
                action,
                resource,
                tool,
                decision_id,
            )
            return dict(row) if row else None
