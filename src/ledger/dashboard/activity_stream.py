"""
Activity Stream — Real-time prioritized governance event queue.

Why: Pattern from Datadog Security Inbox.
Security team gets real-time situational awareness without
querying raw logs.

Severity-based ranking:
  CRITICAL: Kill switch, policy violations, trust score drops
  HIGH: Blocked actions, approval rejections
  MEDIUM: Approvals required, policy evaluations
  LOW: Routine approved actions
  INFO: System events

Filtering:
  - By agent ID
  - By policy ID
  - By severity (FATAL/ERROR/WARN/INFO per OTel SeverityNumber)
  - By time range (last hour, 24h, 7d, custom)
  - By event type (all 12 GovernanceEventType values)
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, AsyncIterator


@dataclass
class ActivityEvent:
    event_id: str
    timestamp: datetime
    severity: str  # CRITICAL/HIGH/MEDIUM/LOW/INFO
    severity_number: int  # OTel 1-24 scale
    event_type: str
    agent_id: str | None
    policy_id: str | None
    summary: str  # Human-readable one-liner
    details_url: str  # Deep link to full details
    gt_token: str  # Governance token reference
    actionable: bool  # Requires human intervention?
    related_events: list  # Other events in same causal chain


@dataclass
class ActivityFilters:
    agent_id: str | None = None
    policy_id: str | None = None
    severity: str | None = None
    event_type: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    actionable_only: bool = False


class ActivityStreamService:
    """Real-time prioritized governance event stream."""

    # Severity ranking (higher = more urgent)
    SEVERITY_ORDER = {
        "CRITICAL": 5,
        "HIGH": 4,
        "MEDIUM": 3,
        "LOW": 2,
        "INFO": 1,
    }

    # OTel severity mapping
    OTEL_SEVERITY = {
        "CRITICAL": 24,  # FATAL
        "HIGH": 17,      # ERROR
        "MEDIUM": 13,    # WARN
        "LOW": 9,        # INFO
        "INFO": 1,       # TRACE
    }

    def __init__(self, db_pool):
        self.pool = db_pool

    async def get_stream(
        self,
        tenant_id: str,
        filters: Optional[ActivityFilters] = None,
        since: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ActivityEvent]:
        """Paginated activity stream with filters."""
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=24)

        events = await self._fetch_events(tenant_id, filters, since, limit, offset)
        return sorted(events, key=lambda e: self.SEVERITY_ORDER.get(e.severity, 0), reverse=True)

    async def get_by_severity(
        self,
        tenant_id: str,
        severity: str,
        limit: int = 50,
    ) -> list[ActivityEvent]:
        """Filter by severity level."""
        filters = ActivityFilters(severity=severity)
        return await self.get_stream(tenant_id, filters=filters, limit=limit)

    async def search(
        self,
        tenant_id: str,
        query: str,
        limit: int = 50,
    ) -> list[ActivityEvent]:
        """Full-text search across activity."""
        all_events = await self.get_stream(tenant_id, limit=1000)
        query_lower = query.lower()
        return [
            e for e in all_events
            if query_lower in e.summary.lower()
            or query_lower in (e.agent_id or "").lower()
            or query_lower in (e.policy_id or "").lower()
        ][:limit]

    async def _fetch_events(
        self,
        tenant_id: str,
        filters: Optional[ActivityFilters],
        since: datetime,
        limit: int,
        offset: int,
    ) -> list[ActivityEvent]:
        """Fetch events from database."""
        conditions = ["tenant_id = $1", "event_ts > $2"]
        params = [tenant_id, since]
        param_idx = 3

        if filters:
            if filters.agent_id:
                conditions.append(f"actor_id = ${param_idx}")
                params.append(filters.agent_id)
                param_idx += 1
            if filters.severity:
                # Map severity to event_type patterns since we don't have severity column
                severity_map = {
                    "CRITICAL": ["token.revoked", "decision.revoked"],
                    "HIGH": ["execution.blocked"],
                    "MEDIUM": ["execution.rate_limited", "decision.created"],
                    "LOW": ["execution.allowed"],
                    "INFO": ["token.derived", "token.verification", "decision.verification"],
                }
                event_types = severity_map.get(filters.severity, [])
                if event_types:
                    placeholders = ", ".join(f"${i}" for i in range(param_idx, param_idx + len(event_types)))
                    conditions.append(f"event_type IN ({placeholders})")
                    params.extend(event_types)
                    param_idx += len(event_types)
            if filters.event_type:
                conditions.append(f"event_type = ${param_idx}")
                params.append(filters.event_type)
                param_idx += 1
            if filters.actionable_only:
                # Actionable events are critical/high severity
                conditions.append(f"event_type = ANY(${param_idx})")
                params.append(["token.revoked", "decision.revoked", "execution.blocked"])
                param_idx += 1

        where_clause = " AND ".join(conditions)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT * FROM governance_audit_log
                WHERE {where_clause}
                ORDER BY event_ts DESC
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
                """,
                *params,
                limit,
                offset,
            )

        events = []
        for row in rows:
            # Map event_type to severity
            severity = self._event_type_to_severity(row.get("event_type", "unknown"))
            events.append(ActivityEvent(
                event_id=str(row["event_id"]),
                timestamp=row["event_ts"],
                severity=severity,
                severity_number=self.OTEL_SEVERITY.get(severity, 1),
                event_type=row.get("event_type", "unknown"),
                agent_id=row.get("actor_id"),
                policy_id=None,  # Not in schema
                summary=self._event_type_to_summary(row.get("event_type", "unknown")),
                details_url=f"/dashboard/events/{row['event_id']}",
                gt_token=row.get("token_id", ""),
                actionable=severity in ["CRITICAL", "HIGH"],
                related_events=[],
            ))

        return events

    def _event_type_to_severity(self, event_type: str) -> str:
        """Map event type to severity level."""
        mapping = {
            "token.revoked": "CRITICAL",
            "decision.revoked": "CRITICAL",
            "execution.blocked": "HIGH",
            "execution.rate_limited": "MEDIUM",
            "decision.created": "MEDIUM",
            "execution.allowed": "LOW",
            "token.derived": "INFO",
            "token.verification": "INFO",
            "decision.verification": "INFO",
        }
        return mapping.get(event_type, "INFO")

    def _event_type_to_summary(self, event_type: str) -> str:
        """Generate human-readable summary from event type."""
        mapping = {
            "token.revoked": "Token revoked",
            "decision.revoked": "Decision revoked",
            "execution.blocked": "Action blocked by policy",
            "execution.rate_limited": "Action rate limited",
            "decision.created": "Decision created",
            "execution.allowed": "Action approved and executed",
            "token.derived": "Token derived",
            "token.verification": "Token verified",
            "decision.verification": "Decision verified",
        }
        return mapping.get(event_type, f"Event: {event_type}")

    async def get_event_count(
        self,
        tenant_id: str,
        filters: Optional[ActivityFilters] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """Get total count of events matching filters."""
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=24)

        conditions = ["tenant_id = $1", "event_ts > $2"]
        params = [tenant_id, since]
        param_idx = 3

        if filters:
            if filters.agent_id:
                conditions.append(f"actor_id = ${param_idx}")
                params.append(filters.agent_id)
                param_idx += 1
            if filters.severity:
                # Use the event_type mapping
                severity_map = {
                    "CRITICAL": ["token.revoked", "decision.revoked"],
                    "HIGH": ["execution.blocked"],
                }
                event_types = severity_map.get(filters.severity, [])
                if event_types:
                    placeholders = ", ".join(f"${i}" for i in range(param_idx, param_idx + len(event_types)))
                    conditions.append(f"event_type IN ({placeholders})")
                    params.extend(event_types)
                    param_idx += len(event_types)

        where_clause = " AND ".join(conditions)

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                SELECT COUNT(*) as count FROM governance_audit_log
                WHERE {where_clause}
                """,
                *params,
            )
            return row["count"] if row else 0
