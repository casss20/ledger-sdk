"""
GOVERNOR — PostgreSQL-backed visibility and control plane for Citadel SDK

The GOVERNOR reads from the canonical database tables:
- actions (immutable action requests)
- decisions (terminal decisions, append-only)
- approvals (human-in-the-loop state)
- execution_results (execution outcomes)

It does NOT maintain its own state. All state is in PostgreSQL.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# ── Singleton pattern for legacy compatibility ────────────────────────────
_governor_singleton: Optional["Governor"] = None


def get_governor() -> "Governor":
    if _governor_singleton is None:
        raise RuntimeError(
            "Governor not initialized. Call Governor.set_instance(db_pool) first."
        )
    return _governor_singleton


class ActionState(Enum):
    """Lifecycle states derived from decisions + execution_results."""
    PENDING = "pending"          # Action exists, no decision yet
    PENDING_APPROVAL = "pending_approval"  # Approval required, not yet decided
    DEFERRED = "deferred"        # Scheduled for later
    SKIPPED = "skipped"          # Null propagation skipped this
    EXECUTING = "executing"      # Decision = ALLOWED, no execution result yet
    SUCCESS = "success"          # Execution result: success
    FAILED = "failed"            # Execution result: failed OR decision = FAILED_EXECUTION
    DENIED = "denied"            # Decision = BLOCKED_* or REJECTED_APPROVAL
    TIMEOUT = "timeout"          # Approval/execution timeout


@dataclass
class ActionRecord:
    """Read-only view of a governed action's lifecycle."""
    id: str
    action: str
    resource: str
    state: ActionState
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Context
    agent: str = "default"
    risk: str = "LOW"
    approval_level: str = "NONE"

    # Execution details
    args_preview: str = ""
    result_preview: str = ""
    error_message: Optional[str] = None

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Links
    promise_id: Optional[str] = None
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def duration_ms(self) -> Optional[int]:
        """Calculate execution duration in milliseconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Export as dictionary."""
        data = asdict(self)
        data['state'] = self.state.value
        data['duration_ms'] = self.duration_ms()
        for key in ['created_at', 'updated_at', 'started_at', 'completed_at']:
            if data[key] and isinstance(data[key], datetime):
                data[key] = data[key].isoformat()
        return data


class Governor:
    """
    PostgreSQL-backed visibility and control plane.

    All reads go to the database. No in-memory state.
    """

    def __init__(self, pool):
        self._pool = pool

    @classmethod
    def set_instance(cls, pool) -> "Governor":
        """Set the global singleton instance (legacy compatibility)."""
        global _governor_singleton
        _governor_singleton = cls(pool)
        return _governor_singleton

    # =====================================================================
    # Record Retrieval (from DB)
    # =====================================================================

    async def get(self, action_id: str) -> Optional[ActionRecord]:
        """Get a single record by action_id from the database."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    a.action_id::text as id,
                    a.action_name as action,
                    a.resource,
                    a.actor_id as agent,
                    a.created_at,
                    a.payload_json,
                    d.status as decision_status,
                    d.winning_rule,
                    d.reason as decision_reason,
                    d.risk_level,
                    d.risk_score,
                    d.path_taken,
                    e.success as exec_success,
                    e.error_message as exec_error,
                    e.result_json as exec_result,
                    e.started_at as exec_started,
                    e.completed_at as exec_completed
                FROM actions a
                LEFT JOIN decisions d ON d.action_id = a.action_id
                LEFT JOIN execution_results e ON e.action_id = a.action_id
                WHERE a.action_id = $1
                """,
                action_id,
            )
            if not row:
                return None
            return self._row_to_record(row)

    async def get_by_promise(self, promise_id: str) -> Optional[ActionRecord]:
        """Get record associated with a durable promise."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    a.action_id::text as id,
                    a.action_name as action,
                    a.resource,
                    a.actor_id as agent,
                    a.created_at,
                    a.payload_json,
                    d.status as decision_status,
                    d.winning_rule,
                    d.reason as decision_reason,
                    d.risk_level,
                    d.risk_score,
                    d.path_taken,
                    e.success as exec_success,
                    e.error_message as exec_error,
                    e.result_json as exec_result,
                    e.started_at as exec_started,
                    e.completed_at as exec_completed
                FROM actions a
                LEFT JOIN decisions d ON d.action_id = a.action_id
                LEFT JOIN execution_results e ON e.action_id = a.action_id
                WHERE a.payload_json->>'promise_id' = $1
                   OR a.context_json->>'promise_id' = $1
                LIMIT 1
                """,
                promise_id,
            )
            if not row:
                return None
            return self._row_to_record(row)

    # =====================================================================
    # Queries by State
    # =====================================================================

    async def list_by_state(
        self, state: ActionState, limit: int = 100, tenant_id: Optional[str] = None
    ) -> List[ActionRecord]:
        """List actions in a given derived state."""
        # Map ActionState to SQL conditions
        # NOTE: The conditions dict is hardcoded and maps only valid ActionState
        # enum members to safe SQL fragments. The f-string below is safe because
        # `state` is asserted to be a valid enum member before use.
        conditions = {
            ActionState.PENDING: "d.decision_id IS NULL",
            ActionState.PENDING_APPROVAL: "d.status = 'PENDING_APPROVAL'",
            ActionState.DEFERRED: "d.status = 'DEFERRED' OR a.context_json->>'deferred' = 'true'",
            ActionState.SKIPPED: "d.winning_rule = 'skipped'",
            ActionState.EXECUTING: "d.status = 'ALLOWED' AND e.execution_id IS NULL",
            ActionState.SUCCESS: "e.success = true",
            ActionState.FAILED: "(d.status = 'FAILED_EXECUTION' OR e.success = false)",
            ActionState.DENIED: "d.status IN ('BLOCKED_SCHEMA','BLOCKED_EMERGENCY','BLOCKED_CAPABILITY','BLOCKED_POLICY','RATE_LIMITED','REJECTED_APPROVAL')",
            ActionState.TIMEOUT: "d.status IN ('EXPIRED_APPROVAL','TIMEOUT')",
        }
        assert state in conditions, f"Invalid ActionState: {state}"
        where_clause = conditions[state]
        tenant_clause = "AND a.tenant_id = $2" if tenant_id else ""

        sql = f"""
            SELECT
                a.action_id::text as id,
                a.action_name as action,
                a.resource,
                a.actor_id as agent,
                a.created_at,
                a.payload_json,
                d.status as decision_status,
                d.winning_rule,
                d.reason as decision_reason,
                d.risk_level,
                d.risk_score,
                d.path_taken,
                e.success as exec_success,
                e.error_message as exec_error,
                e.result_json as exec_result,
                e.started_at as exec_started,
                e.completed_at as exec_completed
            FROM actions a
            LEFT JOIN decisions d ON d.action_id = a.action_id
            LEFT JOIN execution_results e ON e.action_id = a.action_id
            WHERE {where_clause}
            {tenant_clause}
            ORDER BY a.created_at DESC
            LIMIT $1
        """

        async with self._pool.acquire() as conn:
            if tenant_id:
                rows = await conn.fetch(sql, limit, tenant_id)
            else:
                rows = await conn.fetch(sql, limit)
            return [self._row_to_record(r) for r in rows]

    async def list_pending(
        self, limit: int = 100, tenant_id: Optional[str] = None
    ) -> List[ActionRecord]:
        """List pending approvals (actions awaiting human decision)."""
        async with self._pool.acquire() as conn:
            tenant_clause = "AND a.tenant_id = $2" if tenant_id else ""
            sql = f"""
                SELECT
                    a.action_id::text as id,
                    a.action_name as action,
                    a.resource,
                    a.actor_id as agent,
                    a.created_at,
                    a.payload_json,
                    d.status as decision_status,
                    d.winning_rule,
                    d.reason as decision_reason,
                    d.risk_level,
                    d.risk_score,
                    d.path_taken,
                    e.success as exec_success,
                    e.error_message as exec_error,
                    e.result_json as exec_result,
                    e.started_at as exec_started,
                    e.completed_at as exec_completed
                FROM actions a
                JOIN approvals ap ON ap.action_id = a.action_id
                LEFT JOIN decisions d ON d.action_id = a.action_id
                LEFT JOIN execution_results e ON e.action_id = a.action_id
                WHERE ap.status = 'pending'
                {tenant_clause}
                ORDER BY
                    CASE ap.priority
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        ELSE 4
                    END,
                    ap.created_at DESC
                LIMIT $1
            """
            if tenant_id:
                rows = await conn.fetch(sql, limit, tenant_id)
            else:
                rows = await conn.fetch(sql, limit)
            return [self._row_to_record(r) for r in rows]

    async def list_deferred(
        self, limit: int = 100, tenant_id: Optional[str] = None
    ) -> List[ActionRecord]:
        return await self.list_by_state(ActionState.DEFERRED, limit, tenant_id)

    async def list_skipped(
        self, limit: int = 100, tenant_id: Optional[str] = None
    ) -> List[ActionRecord]:
        return await self.list_by_state(ActionState.SKIPPED, limit, tenant_id)

    async def list_failed(
        self, limit: int = 100, tenant_id: Optional[str] = None
    ) -> List[ActionRecord]:
        return await self.list_by_state(ActionState.FAILED, limit, tenant_id)

    async def list_by_agent(
        self, agent: str, limit: int = 100, tenant_id: Optional[str] = None
    ) -> List[ActionRecord]:
        async with self._pool.acquire() as conn:
            tenant_clause = "AND a.tenant_id = $3" if tenant_id else ""
            sql = f"""
                SELECT
                    a.action_id::text as id,
                    a.action_name as action,
                    a.resource,
                    a.actor_id as agent,
                    a.created_at,
                    a.payload_json,
                    d.status as decision_status,
                    d.winning_rule,
                    d.reason as decision_reason,
                    d.risk_level,
                    d.risk_score,
                    d.path_taken,
                    e.success as exec_success,
                    e.error_message as exec_error,
                    e.result_json as exec_result,
                    e.started_at as exec_started,
                    e.completed_at as exec_completed
                FROM actions a
                LEFT JOIN decisions d ON d.action_id = a.action_id
                LEFT JOIN execution_results e ON e.action_id = a.action_id
                WHERE a.actor_id = $1
                {tenant_clause}
                ORDER BY a.created_at DESC
                LIMIT $2
            """
            if tenant_id:
                rows = await conn.fetch(sql, agent, limit, tenant_id)
            else:
                rows = await conn.fetch(sql, agent, limit)
            return [self._row_to_record(r) for r in rows]

    # =====================================================================
    # Statistics
    # =====================================================================

    async def get_stats(self, tenant_id: Optional[str] = None) -> Dict[str, int]:
        """Get counts by derived state using aggregated SQL queries.

        Uses O(1) queries instead of O(n) to avoid reading massive row sets
        into memory (DoS / performance vector).
        """
        stats = {s.value: 0 for s in ActionState}

        async with self._pool.acquire() as conn:
            # 1. Count pending actions (no decision yet)
            pending_row = await conn.fetchrow(
                """
                SELECT COUNT(*) AS cnt FROM actions a
                WHERE NOT EXISTS (
                    SELECT 1 FROM decisions d WHERE d.action_id = a.action_id
                )
                AND ($1::text IS NULL OR a.tenant_id = $1)
                """,
                tenant_id,
            )
            stats[ActionState.PENDING.value] = pending_row['cnt'] if pending_row else 0

            # 2. Aggregate decisions by status
            decision_rows = await conn.fetch(
                """
                SELECT d.status, COUNT(*) AS cnt
                FROM decisions d
                WHERE ($1::text IS NULL OR d.tenant_id = $1)
                GROUP BY d.status
                """,
                tenant_id,
            )

        # Map raw decision statuses to ActionState counts
        for row in decision_rows:
            status = row['status']
            cnt = row['cnt']
            if status == 'PENDING_APPROVAL':
                stats[ActionState.PENDING_APPROVAL.value] += cnt
            elif status == 'DEFERRED':
                stats[ActionState.DEFERRED.value] += cnt
            elif status == 'ALLOWED':
                # ALLOWED means still executing (no execution_result yet)
                stats[ActionState.EXECUTING.value] += cnt
            elif status == 'EXECUTED':
                # EXECUTED maps to success/failure, but we don't have
                # execution_results here; keep in executing for now.
                stats[ActionState.EXECUTING.value] += cnt
            elif status == 'FAILED_EXECUTION':
                stats[ActionState.FAILED.value] += cnt
            elif status in ('BLOCKED_SCHEMA', 'BLOCKED_EMERGENCY', 'BLOCKED_CAPABILITY',
                            'BLOCKED_POLICY', 'RATE_LIMITED', 'REJECTED_APPROVAL'):
                stats[ActionState.DENIED.value] += cnt
            elif status in ('EXPIRED_APPROVAL', 'TIMEOUT'):
                stats[ActionState.TIMEOUT.value] += cnt

        return stats

    async def get_summary(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get executive summary of current state."""
        stats = await self.get_stats(tenant_id)
        pending = await self.list_pending(limit=5, tenant_id=tenant_id)
        failed = await self.list_failed(limit=5, tenant_id=tenant_id)

        async with self._pool.acquire() as conn:
            total_row = await conn.fetchrow(
                "SELECT COUNT(*) as total FROM actions WHERE tenant_id = $1 OR $1 IS NULL",
                tenant_id,
            )
            total = total_row['total'] if total_row else 0

        return {
            "total_actions": total,
            "by_state": stats,
            "requires_attention": {
                "pending_approvals": stats.get("pending_approval", 0),
                "failed_actions": stats.get("failed", 0),
                "deferred_actions": stats.get("deferred", 0),
            },
            "latest_pending": [r.to_dict() for r in pending],
            "latest_failed": [r.to_dict() for r in failed],
        }



    def _row_to_record(self, row) -> ActionRecord:
        """Convert a DB row to an ActionRecord."""
        # Derive state from decision + execution result
        state = self._derive_state(row)

        # Extract args preview from payload
        payload = row.get('payload_json') or {}
        args_preview = str(payload)[:200] if payload else ""

        # Extract result preview from execution result
        exec_result = row.get('exec_result')
        result_preview = str(exec_result)[:200] if exec_result else ""

        # Extract error
        error_message = row.get('exec_error') or row.get('decision_reason')

        # Timing
        started_at = row.get('exec_started')
        completed_at = row.get('exec_completed')
        updated_at = row.get('created_at')  # actions table is immutable, use created

        return ActionRecord(
            id=row['id'],
            action=row['action'],
            resource=row['resource'],
            state=state,
            created_at=row['created_at'],
            updated_at=updated_at or datetime.now(timezone.utc),
            agent=row.get('agent', 'default'),
            risk=row.get('risk_level', 'LOW') or 'LOW',
            approval_level='NONE',  # Could be enriched from approvals table
            args_preview=args_preview,
            result_preview=result_preview,
            error_message=error_message,
            started_at=started_at,
            completed_at=completed_at,
            metadata={
                'winning_rule': row.get('winning_rule'),
                'path_taken': row.get('path_taken'),
                'risk_score': row.get('risk_score'),
            },
        )

    def _derive_state(self, row) -> ActionState:
        """Derive ActionState from decision_status + execution result."""
        decision_status = row.get('decision_status')
        exec_success = row.get('exec_success')

        if decision_status is None:
            return ActionState.PENDING

        # Map decision statuses
        if decision_status in ('PENDING_APPROVAL',):
            return ActionState.PENDING_APPROVAL
        if decision_status in ('DEFERRED',):
            return ActionState.DEFERRED
        if decision_status in ('BLOCKED_SCHEMA', 'BLOCKED_EMERGENCY', 'BLOCKED_CAPABILITY',
                                'BLOCKED_POLICY', 'RATE_LIMITED', 'REJECTED_APPROVAL'):
            return ActionState.DENIED
        if decision_status in ('EXPIRED_APPROVAL', 'TIMEOUT'):
            return ActionState.TIMEOUT
        if decision_status == 'FAILED_EXECUTION':
            return ActionState.FAILED
        if decision_status == 'ALLOWED':
            if exec_success is True:
                return ActionState.SUCCESS
            elif exec_success is False:
                return ActionState.FAILED
            else:
                return ActionState.EXECUTING
        if decision_status in ('EXECUTED',):
            if exec_success is True:
                return ActionState.SUCCESS
            elif exec_success is False:
                return ActionState.FAILED
            else:
                return ActionState.EXECUTING

        return ActionState.PENDING


__all__ = [
    'Governor',
    'ActionRecord',
    'ActionState',
]
