"""
Approval Queue — Pending human decisions for EU AI Act Article 14.

Why: Article 14 requires human oversight. This is the UI surface
where humans exercise that oversight.

Queue items:
  - High-risk actions awaiting approval
  - Policy changes requiring sign-off
  - Kill switch activation confirmations
  - Trust level modifications
  - Agent registration approvals
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"


@dataclass
class ApprovalRequest:
    approval_id: str
    tenant_id: str
    status: ApprovalStatus
    created_at: datetime
    expires_at: datetime  # Auto-expire after SLA
    priority: str  # "critical" | "high" | "medium" | "low"
    action_summary: str
    requester_id: str
    assigned_approver: str | None
    gt_token: str
    time_remaining_seconds: int


@dataclass
class UrgencyMetrics:
    total_pending: int
    immediate_count: int
    standard_count: int
    scheduled_count: int
    breaching_sla: int  # Past expiry
    high_risk_pending: int
    avg_wait_time_seconds: float


class ApprovalQueueService:
    """Manage pending approval queue for human oversight."""

    # SLA thresholds
    SLA_IMMEDIATE = 300  # 5 minutes
    SLA_STANDARD = 3600  # 1 hour
    SLA_SCHEDULED = 86400  # 24 hours

    def __init__(self, db_pool):
        self.pool = db_pool

    async def get_pending(
        self,
        tenant_id: str,
        assigned_to: str | None = None,
        limit: int = 50,
    ) -> list[ApprovalRequest]:
        """Pending approvals, optionally filtered to specific user."""
        async with self.pool.acquire() as conn:
            if assigned_to:
                rows = await conn.fetch(
                    """
                    SELECT * FROM approvals
                    WHERE tenant_id = $1
                    AND status = 'pending'
                    AND escalated_to = $2
                    ORDER BY 
                        CASE priority
                            WHEN 'critical' THEN 1
                            WHEN 'high' THEN 2
                            WHEN 'medium' THEN 3
                            WHEN 'low' THEN 4
                        END,
                        created_at ASC
                    LIMIT $3
                    """,
                    tenant_id,
                    assigned_to,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM approvals
                    WHERE tenant_id = $1
                    AND status = 'pending'
                    ORDER BY 
                        CASE priority
                            WHEN 'critical' THEN 1
                            WHEN 'high' THEN 2
                            WHEN 'medium' THEN 3
                            WHEN 'low' THEN 4
                        END,
                        created_at ASC
                    LIMIT $2
                    """,
                    tenant_id,
                    limit,
                )

        return [self._row_to_request(row) for row in rows]

    async def approve(
        self,
        approval_id: str,
        approver_id: str,
        mfa_token: str,
        reason: str,
    ) -> ApprovalRequest:
        """Approve with MFA confirmation."""
        # Verify MFA token (simplified - would call MFA service)
        if not self._verify_mfa(mfa_token):
            raise ValueError("MFA verification failed")

        async with self.pool.acquire() as conn:
            # Update approval status
            await conn.execute(
                """
                UPDATE approvals
                SET status = 'approved',
                    reviewed_by = $1,
                    decided_at = $2,
                    decision_reason = $3
                WHERE approval_id = $4
                """,
                approver_id,
                datetime.now(timezone.utc),
                reason,
                approval_id,
            )

            # Fetch updated record
            row = await conn.fetchrow(
                "SELECT * FROM approvals WHERE approval_id = $1",
                approval_id,
            )

        return self._row_to_request(row)

    async def reject(
        self,
        approval_id: str,
        approver_id: str,
        mfa_token: str,
        reason: str,
    ) -> ApprovalRequest:
        """Reject with MFA confirmation."""
        # Verify MFA token
        if not self._verify_mfa(mfa_token):
            raise ValueError("MFA verification failed")

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE approvals
                SET status = 'rejected',
                    reviewed_by = $1,
                    decided_at = $2,
                    decision_reason = $3
                WHERE approval_id = $4
                """,
                approver_id,
                datetime.now(timezone.utc),
                reason,
                approval_id,
            )

            row = await conn.fetchrow(
                "SELECT * FROM approvals WHERE approval_id = $1",
                approval_id,
            )

        return self._row_to_request(row)

    async def get_urgency_metrics(self, tenant_id: str) -> UrgencyMetrics:
        """SLA tracking: how many approvals breaching SLA?"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE priority = 'critical') as immediate,
                    COUNT(*) FILTER (WHERE priority = 'high') as standard,
                    COUNT(*) FILTER (WHERE priority IN ('medium', 'low')) as scheduled,
                    COUNT(*) FILTER (WHERE expires_at < $1) as breaching,
                    COUNT(*) FILTER (WHERE priority IN ('critical', 'high')) as high_risk,
                    AVG(EXTRACT(EPOCH FROM ($1 - created_at))) as avg_wait
                FROM approvals
                WHERE tenant_id = $2
                AND status = 'pending'
                """,
                datetime.now(timezone.utc),
                tenant_id,
            )

        row = rows[0]
        return UrgencyMetrics(
            total_pending=row["total"] or 0,
            immediate_count=row["immediate"] or 0,
            standard_count=row["standard"] or 0,
            scheduled_count=row["scheduled"] or 0,
            breaching_sla=row["breaching"] or 0,
            high_risk_pending=row["high_risk"] or 0,
            avg_wait_time_seconds=float(row["avg_wait"] or 0),
        )

    async def auto_expire(self, tenant_id: str) -> int:
        """Auto-expire approvals past their SLA."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE approvals
                SET status = 'expired'
                WHERE tenant_id = $1
                AND status = 'pending'
                AND expires_at < $2
                """,
                tenant_id,
                datetime.now(timezone.utc),
            )
            # asyncpg execute returns a status string like "UPDATE 3"
            # Extract count from it
            import re
            match = re.search(r'UPDATE\s+(\d+)', result)
            return int(match.group(1)) if match else 0

    def _row_to_request(self, row) -> ApprovalRequest:
        """Convert database row to ApprovalRequest."""
        now = datetime.now(timezone.utc)
        time_remaining = max(0, int((row["expires_at"] - now).total_seconds())) if row["expires_at"] else 0

        # Map priority to urgency for display
        priority = row.get("priority", "medium")
        if isinstance(priority, str):
            priority_str = priority
        else:
            # Handle enum types
            priority_str = str(priority)

        return ApprovalRequest(
            approval_id=str(row["approval_id"]),
            tenant_id=row["tenant_id"],
            status=ApprovalStatus(row["status"]),
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            priority=priority_str,
            action_summary=row.get("reason", "Action awaiting approval"),
            requester_id=row.get("requested_by", ""),
            assigned_approver=row.get("escalated_to"),
            gt_token=f"gt_app_{row['approval_id']}",
            time_remaining_seconds=time_remaining,
        )

    def _verify_mfa(self, mfa_token: str) -> bool:
        """Verify MFA token. Simplified - would call MFA provider."""
        # In production, this calls Twilio/Auth0/etc
        # For tests, accept tokens starting with "mfa_"
        return mfa_token.startswith("mfa_") and len(mfa_token) >= 8
