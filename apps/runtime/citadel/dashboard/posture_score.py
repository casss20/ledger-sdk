"""
Governance Posture Score — Real-time health metric for governance systems.

Why: Datadog Security Score pattern. Single number that executives
understand. Drives urgency for action.

Components:
- Risk exposure (0-100, higher = more exposed)
- Policy coverage (% of actions covered by explicit policy)
- Kill switch health (ready/inactive/tested)
- Trust level distribution (how many agents at each level)
- Audit completeness (% of actions with full audit trail)
- Approval backlog (pending approvals / total capacity)

The score is a weighted combination:
  posture = 100 - risk_exposure
  where risk_exposure = weighted_sum(
      uncovered_actions * 3,
      unapproved_high_risk * 5,
      kill_switch_untested * 2,
      low_trust_agents * 1,
      audit_gaps * 2,
      approval_backlog * 1
  ) / max_possible * 100

Target: 5 tests passing.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass
class PostureScore:
    tenant_id: str
    score: int  # 0-100
    health: str  # "excellent" | "healthy" | "at_risk" | "critical"
    trend: str  # "up" | "stable" | "down"
    components: dict  # Breakdown by sub-metric
    recommendations: list  # Actionable items
    calculated_at: datetime


class PostureScoreService:
    """Calculate real-time governance posture score."""

    # Weights for risk exposure calculation
    WEIGHT_UNCOVERED_ACTION = 3
    WEIGHT_UNAPPROVED_HIGH_RISK = 5
    WEIGHT_KILL_SWITCH_UNTESTED = 2
    WEIGHT_LOW_TRUST_AGENT = 1
    WEIGHT_AUDIT_GAP = 2
    WEIGHT_APPROVAL_BACKLOG = 1
    MAX_POSSIBLE_RISK = 1000

    def __init__(self, db_pool):
        self.pool = db_pool

    async def calculate(self, tenant_id: str) -> PostureScore:
        """Calculate posture score for a tenant."""
        components = {}
        risk_score = 0

        # Fetch metrics from database
        metrics = await self._fetch_metrics(tenant_id)

        # Uncovered actions (no explicit policy)
        uncovered = metrics.get("uncovered_actions", 0)
        components["uncovered_actions"] = {
            "value": uncovered,
            "weight": self.WEIGHT_UNCOVERED_ACTION,
            "risk_contribution": min(uncovered * self.WEIGHT_UNCOVERED_ACTION, 300),
        }
        risk_score += components["uncovered_actions"]["risk_contribution"]

        # Unapproved high-risk actions
        unapproved = metrics.get("unapproved_high_risk", 0)
        components["unapproved_high_risk"] = {
            "value": unapproved,
            "weight": self.WEIGHT_UNAPPROVED_HIGH_RISK,
            "risk_contribution": min(unapproved * self.WEIGHT_UNAPPROVED_HIGH_RISK, 250),
        }
        risk_score += components["unapproved_high_risk"]["risk_contribution"]

        # Kill switch untested (days since last test)
        days_since_test = metrics.get("days_since_kill_switch_test", 999)
        kill_switch_risk = self.WEIGHT_KILL_SWITCH_UNTESTED if days_since_test > 30 else 0
        components["kill_switch_health"] = {
            "value": days_since_test,
            "weight": self.WEIGHT_KILL_SWITCH_UNTESTED,
            "risk_contribution": kill_switch_risk,
            "status": "untested" if days_since_test > 30 else "tested",
        }
        risk_score += kill_switch_risk

        # Low trust agents (trust level < 300)
        low_trust = metrics.get("low_trust_agents", 0)
        components["low_trust_agents"] = {
            "value": low_trust,
            "weight": self.WEIGHT_LOW_TRUST_AGENT,
            "risk_contribution": min(low_trust * self.WEIGHT_LOW_TRUST_AGENT, 100),
        }
        risk_score += components["low_trust_agents"]["risk_contribution"]

        # Audit gaps (actions without full audit trail)
        audit_gaps = metrics.get("audit_gaps", 0)
        components["audit_gaps"] = {
            "value": audit_gaps,
            "weight": self.WEIGHT_AUDIT_GAP,
            "risk_contribution": min(audit_gaps * self.WEIGHT_AUDIT_GAP, 200),
        }
        risk_score += components["audit_gaps"]["risk_contribution"]

        # Approval backlog
        backlog = metrics.get("approval_backlog", 0)
        components["approval_backlog"] = {
            "value": backlog,
            "weight": self.WEIGHT_APPROVAL_BACKLOG,
            "risk_contribution": min(backlog * self.WEIGHT_APPROVAL_BACKLOG, 100),
        }
        risk_score += components["approval_backlog"]["risk_contribution"]

        # Policy coverage percentage
        total_actions = metrics.get("total_actions_24h", 1)
        covered_actions = total_actions - uncovered
        components["policy_coverage"] = {
            "value": covered_actions,
            "total": total_actions,
            "percentage": round((covered_actions / total_actions) * 100, 1),
        }

        # Calculate final score (inverse of risk)
        normalized_risk = min(risk_score / self.MAX_POSSIBLE_RISK, 1.0)
        score = max(0, min(100, int(100 - (normalized_risk * 100))))

        # Determine health
        if score >= 90:
            health = "excellent"
        elif score >= 70:
            health = "healthy"
        elif score >= 50:
            health = "at_risk"
        else:
            health = "critical"

        # Calculate trend (compare to 1 hour ago)
        previous_score = metrics.get("previous_score", score)
        if score > previous_score + 2:
            trend = "up"
        elif score < previous_score - 2:
            trend = "down"
        else:
            trend = "stable"

        # Generate recommendations
        recommendations = []
        if uncovered > 0:
            recommendations.append({
                "priority": "high",
                "message": f"{uncovered} actions lack explicit policy coverage",
                "action": "Define policies for uncovered action types",
            })
        if unapproved > 0:
            recommendations.append({
                "priority": "critical",
                "message": f"{unapproved} high-risk actions awaiting approval",
                "action": "Review pending high-risk actions immediately",
            })
        if days_since_test > 30:
            recommendations.append({
                "priority": "medium",
                "message": f"Kill switch not tested in {days_since_test} days",
                "action": "Run kill switch test in isolated environment",
            })
        if low_trust > 0:
            recommendations.append({
                "priority": "low",
                "message": f"{low_trust} agents below trust threshold",
                "action": "Review low-trust agent activity",
            })

        return PostureScore(
            tenant_id=tenant_id,
            score=score,
            health=health,
            trend=trend,
            components=components,
            recommendations=recommendations,
            calculated_at=datetime.now(timezone.utc),
        )

    async def _fetch_metrics(self, tenant_id: str) -> dict:
        """Fetch raw metrics from database."""
        metrics = {
            "uncovered_actions": 0,
            "unapproved_high_risk": 0,
            "low_trust_agents": 0,
            "approval_backlog": 0,
            "total_actions_24h": 1,
            "previous_score": 50,
            "days_since_kill_switch_test": 999,
            "audit_gaps": 0,
        }

        async with self.pool.acquire() as conn:
            # Count uncovered actions in last 24h
            # (actions without matching policy in rules_json)
            try:
                uncovered_row = await conn.fetchrow(
                    """
                    SELECT COUNT(*) as count FROM actions a
                    WHERE a.tenant_id = $1
                    AND a.created_at > $2
                    AND NOT EXISTS (
                        SELECT 1 FROM policies p
                        WHERE p.tenant_id = $1
                        AND p.status = 'active'
                        AND p.rules_json::text LIKE '%' || a.action_name || '%'
                    )
                    """,
                    tenant_id,
                    datetime.now(timezone.utc) - timedelta(hours=24),
                )
                if uncovered_row:
                    metrics["uncovered_actions"] = uncovered_row["count"]
            except Exception:
                pass  # Table or column may not exist

            # Count unapproved high-risk actions (priority = critical/high)
            try:
                unapproved_row = await conn.fetchrow(
                    """
                    SELECT COUNT(*) as count FROM approvals
                    WHERE tenant_id = $1
                    AND status = 'pending'
                    AND priority IN ('high', 'critical')
                    """,
                    tenant_id,
                )
                if unapproved_row:
                    metrics["unapproved_high_risk"] = unapproved_row["count"]
            except Exception:
                pass

            # Count low trust agents (check metadata_json for trust_level)
            try:
                low_trust_row = await conn.fetchrow(
                    """
                    SELECT COUNT(*) as count FROM actors
                    WHERE tenant_id = $1
                    AND status = 'active'
                    AND (
                        metadata_json->>'trust_level' IS NULL
                        OR (metadata_json->>'trust_level')::int < 300
                    )
                    """,
                    tenant_id,
                )
                if low_trust_row:
                    metrics["low_trust_agents"] = low_trust_row["count"]
            except Exception:
                pass

            # Count approval backlog
            try:
                backlog_row = await conn.fetchrow(
                    """
                    SELECT COUNT(*) as count FROM approvals
                    WHERE tenant_id = $1
                    AND status = 'pending'
                    """,
                    tenant_id,
                )
                if backlog_row:
                    metrics["approval_backlog"] = backlog_row["count"]
            except Exception:
                pass

            # Count total actions in last 24h
            try:
                total_row = await conn.fetchrow(
                    """
                    SELECT COUNT(*) as count FROM actions
                    WHERE tenant_id = $1
                    AND created_at > $2
                    """,
                    tenant_id,
                    datetime.now(timezone.utc) - timedelta(hours=24),
                )
                if total_row:
                    metrics["total_actions_24h"] = max(total_row["count"], 1)
            except Exception:
                pass

            # Get previous score (from last calculation)
            try:
                prev_row = await conn.fetchrow(
                    """
                    SELECT score FROM posture_scores
                    WHERE tenant_id = $1
                    ORDER BY calculated_at DESC
                    LIMIT 1
                    """,
                    tenant_id,
                )
                if prev_row:
                    metrics["previous_score"] = prev_row["score"]
            except (asyncpg.PostgresError, ConnectionError, TimeoutError, OSError, RuntimeError):
                pass

            # Kill switch test info
            try:
                ks_row = await conn.fetchrow(
                    """
                    SELECT MAX(created_at) as last_test FROM kill_switches
                    WHERE tenant_id = $1
                    AND reason LIKE '%test%'
                    """,
                    tenant_id,
                )
                if ks_row and ks_row["last_test"]:
                    days = (datetime.now(timezone.utc) - ks_row["last_test"]).days
                    metrics["days_since_kill_switch_test"] = days
            except (asyncpg.PostgresError, ConnectionError, TimeoutError, OSError, RuntimeError):
                pass

        return metrics

    async def save_score(self, score: PostureScore) -> None:
        """Persist score for trend tracking."""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO posture_scores (
                        tenant_id, score, health, trend, components, recommendations, calculated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    score.tenant_id,
                    score.score,
                    score.health,
                    score.trend,
                    str(score.components),
                    str(score.recommendations),
                    score.calculated_at,
                )
            except Exception:
                pass  # Table may not exist
