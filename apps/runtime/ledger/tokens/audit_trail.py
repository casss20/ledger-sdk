"""
Governance Audit Trail — Separated audit log for decisions, tokens, and execution events.

Why separate from audit_events:
  - audit_events tracks the action lifecycle (received → evaluated → executed)
  - governance_audit_log tracks decision/token verification and execution gating
  - Different query patterns, retention policies, and compliance scopes

Properties:
  - Append-only (no UPDATE/DELETE triggers enforce this at DB level)
  - Hash-chained (tamper-evident)
  - Tenant-isolated via RLS
  - Advisory-lock serialized to guarantee correct prev_hash under concurrency

EU AI Act Article 14(4)(e): Every decision must be explainable and auditable.
"""

import json
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class GovernanceAuditTrail:
    """
    Writes governance events to the separated governance_audit_log table.

    All writes are append-only with hash-chain integrity.
    Uses advisory lock to serialize concurrent appends.
    """

    def __init__(self, db_pool, tenant_context_provider=None):
        self.db = db_pool
        self.get_tenant = tenant_context_provider

    async def record(
        self,
        *,
        event_type: str,
        tenant_id: str,
        actor_id: str,
        decision_id: Optional[str] = None,
        token_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> int:
        """
        Append a governance audit event.

        Returns the event_id (BIGSERIAL) for traceability.
        """
        async with self.db.acquire() as conn:
            async with conn.transaction():
                # Set tenant context for RLS — always use explicit tenant_id
                await conn.execute("SELECT set_tenant_context($1)", tenant_id)

                # Serialize all governance audit appends via advisory lock
                await conn.execute("SELECT pg_advisory_xact_lock(2)")

                # Insert (triggers compute prev_hash + event_hash automatically)
                row = await conn.fetchrow(
                    """
                    INSERT INTO governance_audit_log (
                        event_type, tenant_id, actor_id,
                        decision_id, token_id,
                        payload_json, session_id, request_id
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING event_id, event_hash
                    """,
                    event_type,
                    tenant_id,
                    actor_id,
                    decision_id,
                    token_id,
                    json.dumps(payload) if payload is not None else '{}',
                    session_id,
                    request_id,
                )
                return row["event_id"]

    async def record_token_verification(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        token_id: str,
        decision_id: str,
        valid: bool,
        reason: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Record token.verification event."""
        return await self.record(
            event_type="token.verification",
            tenant_id=tenant_id,
            actor_id=actor_id,
            token_id=token_id,
            decision_id=decision_id,
            payload={
                "valid": valid,
                "reason": reason,
                "context": context or {},
            },
        )

    async def record_decision_verification(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        decision_id: str,
        valid: bool,
        reason: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Record decision.verification event."""
        return await self.record(
            event_type="decision.verification",
            tenant_id=tenant_id,
            actor_id=actor_id,
            decision_id=decision_id,
            payload={
                "valid": valid,
                "reason": reason,
                "context": context or {},
            },
        )

    async def record_execution_allowed(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        decision_id: str,
        action: str,
        resource: Optional[str] = None,
    ) -> int:
        """Record execution.allowed event."""
        return await self.record(
            event_type="execution.allowed",
            tenant_id=tenant_id,
            actor_id=actor_id,
            decision_id=decision_id,
            payload={
                "action": action,
                "resource": resource,
            },
        )

    async def record_execution_blocked(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        decision_id: Optional[str] = None,
        action: str,
        resource: Optional[str] = None,
        reason: str,
        credential_type: str = "unknown",
    ) -> int:
        """Record execution.blocked event."""
        return await self.record(
            event_type="execution.blocked",
            tenant_id=tenant_id,
            actor_id=actor_id,
            decision_id=decision_id,
            payload={
                "action": action,
                "resource": resource,
                "reason": reason,
                "credential_type": credential_type,
            },
        )

    async def record_execution_rate_limited(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        decision_id: str,
        action: str,
    ) -> int:
        """Record execution.rate_limited event."""
        return await self.record(
            event_type="execution.rate_limited",
            tenant_id=tenant_id,
            actor_id=actor_id,
            decision_id=decision_id,
            payload={
                "action": action,
            },
        )

    async def record_decision_created(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        decision_id: str,
        decision_type: str,
        action: str,
        reason: str,
    ) -> int:
        """Record decision.created event."""
        return await self.record(
            event_type="decision.created",
            tenant_id=tenant_id,
            actor_id=actor_id,
            decision_id=decision_id,
            payload={
                "decision_type": decision_type,
                "action": action,
                "reason": reason,
            },
        )

    async def record_token_derived(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        token_id: str,
        decision_id: str,
    ) -> int:
        """Record token.derived event."""
        return await self.record(
            event_type="token.derived",
            tenant_id=tenant_id,
            actor_id=actor_id,
            token_id=token_id,
            decision_id=decision_id,
            payload={},
        )

    async def verify_chain(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Verify hash chain integrity of governance_audit_log.

        If tenant_id is provided, verifies chain for that tenant only.
        If omitted, uses admin bypass to verify the entire chain.
        """
        async with self.db.acquire() as conn:
            if tenant_id:
                await conn.execute("SELECT set_tenant_context($1)", tenant_id)
            else:
                # Admin bypass for full chain verification
                await conn.execute("SET app.admin_bypass = 'true'")
            row = await conn.fetchrow("SELECT * FROM verify_governance_audit_chain()")
            return {
                "valid": row["valid"],
                "checked_count": row["checked_count"],
                "first_event_id": row["first_event_id"],
                "last_event_id": row["last_event_id"],
                "broken_at_event_id": row["broken_at_event_id"],
            }

    async def query_by_decision(
        self,
        decision_id: str,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> list:
        """Query audit events by decision_id."""
        tid = tenant_id or (self.get_tenant() if self.get_tenant else None)
        async with self.db.acquire() as conn:
            async with conn.transaction():
                if tid:
                    await conn.execute("SELECT set_tenant_context($1)", tid)
                rows = await conn.fetch(
                    """
                    SELECT event_id, event_ts, event_type, tenant_id, actor_id,
                           decision_id, token_id, payload_json, event_hash
                    FROM governance_audit_log
                    WHERE decision_id = $1
                    ORDER BY event_id DESC
                    LIMIT $2
                    """,
                    decision_id,
                    limit,
                )
                return [dict(r) for r in rows]
