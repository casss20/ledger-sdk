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

from citadel.actions import Action, Decision


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
                    payload_json, context_json, session_id, request_id, idempotency_key,
                    root_decision_id, parent_decision_id, trace_id, parent_actor_id, workflow_id,
                    created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
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
                action.root_decision_id,
                action.parent_decision_id,
                action.trace_id,
                action.parent_actor_id,
                action.workflow_id,
                action.created_at
            )
            return row is not None
    
    async def get_action(self, action_id: uuid.UUID, tenant_id: Optional[str] = None) -> Optional[Dict]:
        """Fetch action by ID. If tenant_id provided, enforce tenant isolation."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM actions WHERE action_id = $1 AND ($2::text IS NULL OR tenant_id = $2)",
                action_id,
                tenant_id,
            )
            return dict(row) if row else None
    
    # =========================================================================
    # DECISIONS
    # =========================================================================
    
    async def save_decision(self, decision: Decision) -> None:
        """Persist terminal decision with tenant isolation."""
        # Governance tokens (gt_cap_*) live in governance_tokens, not capabilities.
        # Only old-style capability tokens can be stored in the capability_token FK column.
        cap_token = decision.capability_token
        if cap_token and cap_token.startswith("gt_cap_"):
            cap_token = None
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO decisions (
                    decision_id, action_id, policy_snapshot_id, status, winning_rule, reason,
                    capability_token, risk_level, risk_score, path_taken, created_at, tenant_id,
                    root_decision_id, parent_decision_id, trace_id, parent_actor_id, workflow_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
            """,
                decision.decision_id,
                decision.action_id,
                decision.policy_snapshot_id,
                decision.status.value,
                decision.winning_rule,
                decision.reason,
                cap_token,
                decision.risk_level,
                decision.risk_score,
                decision.path_taken,
                decision.created_at,
                decision.tenant_id,
                decision.root_decision_id,
                decision.parent_decision_id,
                decision.trace_id,
                decision.parent_actor_id,
                decision.workflow_id,
            )
    
    async def find_decision_by_idempotency(
        self,
        actor_id: str,
        idempotency_key: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[Decision]:
        """Find existing decision for idempotent request."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT d.* FROM decisions d
                JOIN actions a ON d.action_id = a.action_id
                WHERE a.actor_id = $1 AND a.idempotency_key = $2
                AND ($3::text IS NULL OR a.tenant_id = $3)
                ORDER BY d.created_at DESC
                LIMIT 1
            """, actor_id, idempotency_key, tenant_id)
            
            if row:
                return self._row_to_decision(row)
            return None
    
    async def get_decision(self, action_id: uuid.UUID, tenant_id: Optional[str] = None) -> Optional[Decision]:
        """Fetch decision for action with tenant isolation."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT d.* FROM decisions d
                JOIN actions a ON d.action_id = a.action_id
                WHERE d.action_id = $1 AND ($2::text IS NULL OR a.tenant_id = $2)
            """, action_id, tenant_id)
            return self._row_to_decision(row) if row else None
    
    def _row_to_decision(self, row: asyncpg.Record) -> Decision:
        from citadel.actions import Decision, KernelStatus
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
            created_at=row['created_at'],
            tenant_id=row.get('tenant_id'),
            root_decision_id=row.get('root_decision_id'),
            parent_decision_id=row.get('parent_decision_id'),
            trace_id=row.get('trace_id'),
            parent_actor_id=row.get('parent_actor_id'),
            workflow_id=row.get('workflow_id'),
        )

    async def fetch_audit_events_for_decision(
        self,
        decision_id: str,
        tenant_id: Optional[str] = None,
    ) -> List[Dict]:
        """Fetch all audit events for a decision, in chronological order."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT event_id, event_type, actor_id, payload_json, event_ts
                FROM governance_audit_log
                WHERE decision_id = $1 AND ($2::text IS NULL OR tenant_id = $2)
                ORDER BY event_ts ASC
                """,
                decision_id,
                tenant_id,
            )
        return [dict(row) for row in rows]

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
        tenant_id: Optional[str] = None,
    ) -> uuid.UUID:
        """Create pending approval with tenant isolation."""
        approval_id = uuid.uuid4()
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO approvals (
                    approval_id, action_id, status, priority, requested_by, reason, expires_at, created_at, tenant_id
                ) VALUES ($1, $2, 'pending', $3, $4, $5, $6, NOW(), $7)
            """, approval_id, action_id, priority, requested_by, reason, expires_at, tenant_id)
        return approval_id
    
    async def get_approval(self, approval_id: uuid.UUID, tenant_id: Optional[str] = None) -> Optional[Dict]:
        """Fetch approval by ID with tenant isolation."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT ap.* FROM approvals ap
                JOIN actions a ON ap.action_id = a.action_id
                WHERE ap.approval_id = $1 AND ($2::text IS NULL OR a.tenant_id = $2)
            """, approval_id, tenant_id)
            return dict(row) if row else None
    
    async def get_pending_approvals(self, limit: int = 100, tenant_id: Optional[str] = None) -> List[Dict]:
        """Get pending approvals queue with tenant isolation."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    ap.approval_id,
                    ap.action_id,
                    ap.priority,
                    ap.reason,
                    ap.requested_by,
                    ap.created_at,
                    ap.expires_at,
                    a.action_name,
                    a.resource,
                    a.payload_json
                FROM approvals ap
                JOIN actions a ON ap.action_id = a.action_id
                WHERE ap.status = 'pending'
                AND ($1::text IS NULL OR a.tenant_id = $1)
                ORDER BY 
                    CASE ap.priority 
                        WHEN 'critical' THEN 1 
                        WHEN 'high' THEN 2 
                        WHEN 'medium' THEN 3 
                        ELSE 4 
                    END,
                    ap.created_at
                LIMIT $2
            """, tenant_id, limit)
            return [dict(r) for r in rows]
    
    # =========================================================================
    # CAPABILITIES
    # =========================================================================
    
    async def get_capability(self, token_id: str, tenant_id: Optional[str] = None) -> Optional[Dict]:
        """Fetch capability by token with tenant isolation."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT c.* FROM capabilities c
                JOIN actors act ON c.actor_id = act.actor_id
                WHERE c.token_id = $1 AND ($2::text IS NULL OR act.tenant_id = $2)
            """, token_id, tenant_id)
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
    
    async def verify_audit_chain(self, tenant_id: Optional[str] = None) -> Dict:
        """Verify hash chain integrity scoped to tenant."""
        async with self.pool.acquire() as conn:
            if tenant_id:
                row = await conn.fetchrow(
                    """SELECT * FROM verify_audit_chain() 
                        WHERE tenant_id = $1""",
                    tenant_id
                )
            else:
                row = await conn.fetchrow("SELECT * FROM verify_audit_chain()")
            if row is None:
                return {'valid': True, 'checked_count': 0, 'first_event_id': None, 'last_event_id': None, 'broken_at_event_id': None}
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
        tenant_id: Optional[str] = None,
    ) -> None:
        """Persist execution outcome with tenant isolation."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO execution_results (action_id, success, result_json, error_message, tenant_id)
                VALUES ($1, $2, $3, $4, $5)
            """, action_id, success, json.dumps(result) if result else '{}', error, tenant_id)
    
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

    # =========================================================================
    # API KEYS
    # =========================================================================
    
    async def create_api_key(
        self,
        key_hash: str,
        tenant_id: str,
        name: Optional[str] = None,
        scopes: Optional[list] = None,
        expires_at: Optional[datetime] = None,
    ) -> Dict:
        """Create a new API key record. Returns the key metadata (not the plaintext)."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO api_keys (key_hash, tenant_id, name, scopes, expires_at)
                VALUES ($1, $2, COALESCE($3, 'API key'), $4::jsonb, $5)
                RETURNING key_id, tenant_id, name, scopes, expires_at, revoked, created_at
            """, key_hash, tenant_id, name, json.dumps(scopes or []), expires_at)
            return dict(row)
    
    async def get_api_key_by_hash(self, key_hash: str) -> Optional[Dict]:
        """Lookup API key by hash. Returns None if not found or revoked/expired."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM api_keys
                WHERE key_hash = $1 AND revoked = FALSE
                AND (expires_at IS NULL OR expires_at > NOW())
            """, key_hash)
            return dict(row) if row else None
    
    async def list_api_keys(self, tenant_id: str) -> List[Dict]:
        """List all non-revoked API keys for a tenant."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT key_id, tenant_id, name, scopes, expires_at, last_used_at, revoked, created_at
                FROM api_keys
                WHERE tenant_id = $1 AND revoked = FALSE
            """, tenant_id)
            return [dict(r) for r in rows]
    
    async def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key. Returns True if key was found and revoked."""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE api_keys SET revoked = TRUE
                WHERE key_id = $1
            """, key_id)
            return 'UPDATE 1' in result
    
    async def update_api_key_last_used(self, key_hash: str) -> None:
        """Update last_used_at timestamp for an API key."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE api_keys SET last_used_at = NOW()
                WHERE key_hash = $1
            """, key_hash)

    # =========================================================================
    # LINEAGE / PROVENANCE
    # =========================================================================

    async def get_decision_lineage(
        self,
        decision_id: uuid.UUID,
        depth: int = 5,
        tenant_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Return ancestor chain for a decision (parents up to `depth` levels).
        Uses recursive CTE over decisions.parent_decision_id.
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                WITH RECURSIVE lineage AS (
                    -- anchor: the target decision
                    SELECT
                        d.decision_id,
                        d.action_id,
                        d.parent_decision_id,
                        d.root_decision_id,
                        d.trace_id,
                        d.workflow_id,
                        d.status,
                        d.winning_rule,
                        d.reason,
                        d.risk_level,
                        d.risk_score,
                        d.created_at,
                        0 AS depth_level
                    FROM decisions d
                    WHERE d.decision_id = $1
                      AND ($2::text IS NULL OR EXISTS (
                          SELECT 1 FROM actions a
                          WHERE a.action_id = d.action_id AND a.tenant_id = $2
                      ))

                    UNION ALL

                    -- recurse upward via parent_decision_id
                    SELECT
                        d.decision_id,
                        d.action_id,
                        d.parent_decision_id,
                        d.root_decision_id,
                        d.trace_id,
                        d.workflow_id,
                        d.status,
                        d.winning_rule,
                        d.reason,
                        d.risk_level,
                        d.risk_score,
                        d.created_at,
                        lin.depth_level + 1
                    FROM decisions d
                    JOIN lineage lin ON d.decision_id = lin.parent_decision_id
                    WHERE lin.depth_level < $3
                )
                SELECT * FROM lineage ORDER BY depth_level ASC;
            """, decision_id, tenant_id, depth)
            return [dict(r) for r in rows]

    async def get_decision_descendants(
        self,
        decision_id: uuid.UUID,
        depth: int = 5,
        tenant_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Return descendant chain for a decision (children down to `depth` levels).
        Uses recursive CTE over decisions.parent_decision_id in reverse.
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                WITH RECURSIVE descendants AS (
                    -- anchor: the target decision
                    SELECT
                        d.decision_id,
                        d.action_id,
                        d.parent_decision_id,
                        d.root_decision_id,
                        d.trace_id,
                        d.workflow_id,
                        d.status,
                        d.winning_rule,
                        d.reason,
                        d.risk_level,
                        d.risk_score,
                        d.created_at,
                        0 AS depth_level
                    FROM decisions d
                    WHERE d.decision_id = $1
                      AND ($2::text IS NULL OR EXISTS (
                          SELECT 1 FROM actions a
                          WHERE a.action_id = d.action_id AND a.tenant_id = $2
                      ))

                    UNION ALL

                    -- recurse downward: find decisions whose parent is in the set
                    SELECT
                        d.decision_id,
                        d.action_id,
                        d.parent_decision_id,
                        d.root_decision_id,
                        d.trace_id,
                        d.workflow_id,
                        d.status,
                        d.winning_rule,
                        d.reason,
                        d.risk_level,
                        d.risk_score,
                        d.created_at,
                        desc.depth_level + 1
                    FROM decisions d
                    JOIN descendants desc ON d.parent_decision_id = desc.decision_id
                    WHERE desc.depth_level < $3
                )
                SELECT * FROM descendants ORDER BY depth_level ASC;
            """, decision_id, tenant_id, depth)
            return [dict(r) for r in rows]

    async def get_workflow_tree(
        self,
        workflow_id: str,
        tenant_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Return all decisions belonging to a workflow, ordered by creation time.
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    d.decision_id,
                    d.action_id,
                    d.parent_decision_id,
                    d.root_decision_id,
                    d.trace_id,
                    d.workflow_id,
                    d.status,
                    d.winning_rule,
                    d.reason,
                    d.risk_level,
                    d.risk_score,
                    d.created_at
                FROM decisions d
                WHERE d.workflow_id = $1
                  AND ($2::text IS NULL OR EXISTS (
                      SELECT 1 FROM actions a
                      WHERE a.action_id = d.action_id AND a.tenant_id = $2
                  ))
                ORDER BY d.created_at ASC;
            """, workflow_id, tenant_id)
            return [dict(r) for r in rows]

    # =========================================================================
    # QUEUE METRICS
    # =========================================================================

    async def get_approval_queue_metrics(
        self,
        tenant_id: Optional[str] = None,
    ) -> Dict:
        """
        Return current approval queue metrics from the approval_queue_metrics view.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    queue_depth,
                    avg_wait_seconds,
                    throughput_per_hour,
                    avg_service_seconds,
                    arrival_rate_per_hour,
                    implied_arrival_rate_per_second,
                    observed_load_factor,
                    computed_at
                FROM approval_queue_metrics
                LIMIT 1
            """)
            if row is None:
                return {
                    'queue_depth': 0,
                    'avg_wait_seconds': 0.0,
                    'throughput_per_hour': 0,
                    'avg_service_seconds': 0.0,
                    'arrival_rate_per_hour': 0,
                    'implied_arrival_rate_per_second': None,
                    'observed_load_factor': None,
                    'computed_at': datetime.utcnow().isoformat(),
                }
            return {
                'queue_depth': row['queue_depth'],
                'avg_wait_seconds': float(row['avg_wait_seconds']) if row['avg_wait_seconds'] is not None else 0.0,
                'throughput_per_hour': row['throughput_per_hour'],
                'avg_service_seconds': float(row['avg_service_seconds']) if row['avg_service_seconds'] is not None else 0.0,
                'arrival_rate_per_hour': row['arrival_rate_per_hour'],
                'implied_arrival_rate_per_second': float(row['implied_arrival_rate_per_second']) if row['implied_arrival_rate_per_second'] is not None else None,
                'observed_load_factor': float(row['observed_load_factor']) if row['observed_load_factor'] is not None else None,
                'computed_at': row['computed_at'].isoformat() if hasattr(row['computed_at'], 'isoformat') else row['computed_at'],
            }
