"""
Repository - All database reads and writes.

This is the ONLY place that touches the database.
No other module has direct DB access.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import asyncpg

from ledger.actions import Action, Decision


class Repository:
    """
    All database operations for the governance kernel.
    
    Tables managed:
    - actors (read)
    - actions (write)
    - decisions (write)
    - approvals (write)
    - audit_events (write)
    - capabilities (read/update)
    - kill_switches (read)
    - policies (read)
    - policy_snapshots (read/write)
    - execution_results (write)
    """
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    async def save_action(self, action: Action) -> bool:
        """Persist canonical action record. Returns True if inserted, False if conflict."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO actions (
                    action_id, actor_id, actor_type, action_name, resource, tenant_id,
                    payload_json, context_json, session_id, request_id, idempotency_key, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (actor_id, idempotency_key) WHERE idempotency_key IS NOT NULL
                DO NOTHING
                RETURNING action_id
            """,
                action.action_id,
                action.actor_id,
                action.actor_type,
                action.action_name,
                action.resource,
                action.tenant_id,
                json.dumps(action.payload) if action.payload else '{}',
                json.dumps(action.context) if action.context else '{}',
                action.session_id,
                action.request_id,
                action.idempotency_key,
                action.created_at
            )
            return row is not None
    
    async def get_action(self, action_id: uuid.UUID) -> Optional[Dict]:
        """Fetch action by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM actions WHERE action_id = $1",
                action_id
            )
            return dict(row) if row else None
    
    # =========================================================================
    # DECISIONS
    # =========================================================================
    
    async def save_decision(self, decision: Decision) -> None:
        """Persist terminal decision."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO decisions (
                    decision_id, action_id, policy_snapshot_id, status, winning_rule, reason,
                    capability_token, risk_level, risk_score, path_taken, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                decision.decision_id,
                decision.action_id,
                decision.policy_snapshot_id,
                decision.status.value,
                decision.winning_rule,
                decision.reason,
                decision.capability_token,
                decision.risk_level,
                decision.risk_score,
                decision.path_taken,
                decision.created_at
            )
    
    async def find_decision_by_idempotency(
        self,
        actor_id: str,
        idempotency_key: str
    ) -> Optional[Decision]:
        """Find existing decision for idempotent request."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT d.* FROM decisions d
                JOIN actions a ON d.action_id = a.action_id
                WHERE a.actor_id = $1 AND a.idempotency_key = $2
                ORDER BY d.created_at DESC
                LIMIT 1
            """, actor_id, idempotency_key)
            
            if row:
                return self._row_to_decision(row)
            return None
    
    async def get_decision(self, action_id: uuid.UUID) -> Optional[Decision]:
        """Fetch decision for action."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM decisions WHERE action_id = $1",
                action_id
            )
            return self._row_to_decision(row) if row else None
    
    def _row_to_decision(self, row: asyncpg.Record) -> Decision:
        from ledger.actions import Decision, KernelStatus
        return Decision(
            decision_id=row['decision_id'],
            action_id=row['action_id'],
            status=KernelStatus(row['status']),
            winning_rule=row['winning_rule'],
            reason=row['reason'],
            policy_snapshot_id=row['policy_snapshot_id'],
            capability_token=row['capability_token'],
            risk_level=row['risk_level'],
            risk_score=row['risk_score'],
            path_taken=row['path_taken'],
            created_at=row['created_at']
        )
    
    # =========================================================================
    # APPROVALS
    # =========================================================================
    
    async def create_approval(
        self,
        action_id: uuid.UUID,
        priority: str,
        reason: str,
        requested_by: str,
        expires_at: datetime,
    ) -> uuid.UUID:
        """Create pending approval."""
        approval_id = uuid.uuid4()
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO approvals (
                    approval_id, action_id, status, priority, requested_by, reason, expires_at, created_at
                ) VALUES ($1, $2, 'pending', $3, $4, $5, $6, NOW())
            """, approval_id, action_id, priority, requested_by, reason, expires_at)
        return approval_id
    
    async def get_approval(self, approval_id: uuid.UUID) -> Optional[Dict]:
        """Fetch approval by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM approvals WHERE approval_id = $1",
                approval_id
            )
            return dict(row) if row else None
    
    async def get_pending_approvals(self, limit: int = 100) -> List[Dict]:
        """Get pending approvals queue."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM pending_approvals_queue
                LIMIT $1
            """, limit)
            return [dict(r) for r in rows]
    
    # =========================================================================
    # CAPABILITIES
    # =========================================================================
    
    async def get_capability(self, token_id: str) -> Optional[Dict]:
        """Fetch capability by token."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM capabilities WHERE token_id = $1",
                token_id
            )
            return dict(row) if row else None
    
    async def consume_capability(
        self,
        token_id: str,
        actor_id: str,
    ) -> Dict:
        """
        Atomically consume capability use.
        Uses SQL function for atomicity.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM consume_capability($1, $2)",
                token_id, actor_id
            )
            return {
                'success': row['success'],
                'remaining_uses': row['remaining_uses'],
                'error': row['error']
            }
    
    # =========================================================================
    # KILL SWITCHES
    # =========================================================================
    
    async def check_kill_switch(
        self,
        scope_type: str,
        scope_value: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """Check if kill switch is active for scope."""
        async with self.pool.acquire() as conn:
            # Check specific scope
            row = await conn.fetchrow("""
                SELECT * FROM kill_switches
                WHERE scope_type = $1 AND scope_value = $2
                AND ($3::text IS NULL OR tenant_id = $3)
                AND enabled = TRUE
                LIMIT 1
            """, scope_type, scope_value, tenant_id)
            
            if row:
                return dict(row)
            
            # Check global
            row = await conn.fetchrow("""
                SELECT * FROM kill_switches
                WHERE scope_type = 'global' AND enabled = TRUE
                LIMIT 1
            """)
            
            return dict(row) if row else None
    
    # =========================================================================
    # POLICIES
    # =========================================================================
    
    async def get_active_policy(
        self,
        scope_type: str,
        scope_value: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """Fetch active policy for scope."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM policies
                WHERE scope_type = $1 AND scope_value = $2
                AND status = 'active'
                AND ($3::text IS NULL OR tenant_id = $3)
                ORDER BY created_at DESC
                LIMIT 1
            """, scope_type, scope_value, tenant_id)
            return dict(row) if row else None
    
    async def save_policy_snapshot(
        self,
        policy_id: uuid.UUID,
        version: str,
        snapshot_hash: str,
        snapshot_json: Dict,
    ) -> uuid.UUID:
        """Save immutable policy snapshot."""
        snapshot_id = uuid.uuid4()
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO policy_snapshots (snapshot_id, policy_id, policy_version, snapshot_hash, snapshot_json)
                VALUES ($1, $2, $3, $4, $5)
            """, snapshot_id, policy_id, version, snapshot_hash, json.dumps(snapshot_json) if snapshot_json else '{}')
        return snapshot_id
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    
    async def save_audit_event(
        self,
        action_id: uuid.UUID,
        event_type: str,
        payload: Dict[str, Any],
        actor_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> int:
        """Append audit event with hash chain.

        Uses PostgreSQL advisory lock to serialize concurrent appends and
        guarantee correct prev_hash linkage. The lock is transaction-scoped
        (pg_advisory_xact_lock) and auto-releases on commit.
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Serialize all audit chain appends via advisory lock.
                # Lock key 1 = global audit chain. Transaction-scoped so it
                # auto-releases when the INSERT commits.
                await conn.execute("SELECT pg_advisory_xact_lock(1)")

                # Get previous hash (now safe: no concurrent appends in flight)
                prev_row = await conn.fetchrow("""
                    SELECT event_hash FROM audit_events
                    ORDER BY event_id DESC LIMIT 1
                """)
                prev_hash = prev_row['event_hash'] if prev_row else '0' * 64
                
                # Compute event hash with nonce to avoid collisions
                import hashlib
                nonce = uuid.uuid4().hex
                event_data = f"{action_id}{event_type}{datetime.utcnow().isoformat()}{json.dumps(payload)}{prev_hash}{actor_id or ''}{nonce}"
                event_hash = hashlib.sha256(event_data.encode()).hexdigest()
                
                row = await conn.fetchrow("""
                    INSERT INTO audit_events (action_id, event_type, payload_json, prev_hash, event_hash, actor_id, tenant_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING event_id
                """, action_id, event_type, json.dumps(payload) if payload else '{}', prev_hash, event_hash, actor_id, tenant_id)
                return row['event_id']
    
    async def verify_audit_chain(self) -> Dict:
        """Verify hash chain integrity."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM verify_audit_chain()")
            return {
                'valid': row['valid'],
                'checked_count': row['checked_count'],
                'first_event_id': row['first_event_id'],
                'last_event_id': row['last_event_id'],
                'broken_at_event_id': row['broken_at_event_id']
            }
    
    # =========================================================================
    # EXECUTION RESULTS
    # =========================================================================
    
    async def save_execution_result(
        self,
        action_id: uuid.UUID,
        success: bool,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
    ) -> None:
        """Persist execution outcome."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO execution_results (action_id, success, result_json, error_message)
                VALUES ($1, $2, $3, $4)
            """, action_id, success, json.dumps(result) if result else '{}', error)
    
    # =========================================================================
    # ACTORS
    # =========================================================================
    
    async def get_actor(self, actor_id: str) -> Optional[Dict]:
        """Fetch actor by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM actors WHERE actor_id = $1",
                actor_id
            )
            return dict(row) if row else None
    
    async def ensure_actor(self, actor_id: str, actor_type: str, tenant_id: Optional[str] = None) -> None:
        """Ensure actor exists (for bootstrapping)."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO actors (actor_id, actor_type, tenant_id, status)
                VALUES ($1, $2, $3, 'active')
                ON CONFLICT (actor_id) DO NOTHING
            """, actor_id, actor_type, tenant_id)
