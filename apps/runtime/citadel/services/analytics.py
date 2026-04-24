"""
Cross-Action Analytics â€” Citadel SDK

Time-windowed rate analysis, anomaly detection, agent behavior profiling.

Like a SIEM for AI agents â€” detect when "normal" becomes "abnormal".
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
import logging
import statistics

from .governor import get_governor, ActionState, ActionRecord

logger = logging.getLogger(__name__)


@dataclass
class TimeWindow:
    """Defines a time window for analysis."""
    start: datetime
    end: datetime
    label: str = ""
    
    @property
    def duration_seconds(self) -> float:
        return (self.end - self.start).total_seconds()
    
    @classmethod
    def last_minute(cls) -> "TimeWindow":
        now = datetime.utcnow()
        return cls(now - timedelta(minutes=1), now, "last_minute")
    
    @classmethod
    def last_hour(cls) -> "TimeWindow":
        now = datetime.utcnow()
        return cls(now - timedelta(hours=1), now, "last_hour")
    
    @classmethod
    def last_day(cls) -> "TimeWindow":
        now = datetime.utcnow()
        return cls(now - timedelta(days=1), now, "last_day")


@dataclass
class ActionMetrics:
    """Metrics for a specific action over a time window."""
    action: str
    window: TimeWindow
    
    # Counts
    total: int = 0
    success: int = 0
    failed: int = 0
    denied: int = 0
    skipped: int = 0
    
    # Timing
    durations_ms: List[int] = field(default_factory=list)
    avg_duration_ms: float = 0.0
    max_duration_ms: int = 0
    
    # Risk distribution
    by_risk: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Anomaly flags
    is_anomalous: bool = False
    anomaly_reasons: List[str] = field(default_factory=list)
    
    def calculate_stats(self):
        """Calculate derived statistics."""
        if self.durations_ms:
            self.avg_duration_ms = statistics.mean(self.durations_ms)
            self.max_duration_ms = max(self.durations_ms)


@dataclass
class AnomalyAlert:
    """An anomaly detected in agent behavior."""
    severity: str  # "low", "medium", "high", "critical"
    category: str  # "rate_spike", "failure_spike", "risk_escalation", "pattern_break"
    description: str
    affected_actions: List[str]
    window: TimeWindow
    metrics: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=datetime.utcnow)


class AnalyticsEngine:
    """
    Cross-action analytics for detecting abnormal agent behavior.
    
    Detects:
    - Rate spikes: "50 emails in 1 minute"
    - Failure spikes: "90% failure rate on payments"
    - Risk escalation: "Sudden shift to HIGH risk actions"
    - Pattern breaks: "Actions outside normal hours"
    """
    
    def __init__(self):
        self._baseline: Dict[str, Dict[str, float]] = {}  # action -> metric -> baseline
        self._anomaly_handlers: List[Callable[[AnomalyAlert], None]] = []
        self._thresholds = {
            "rate_spike_multiplier": 5.0,  # 5x baseline = spike
            "failure_rate_threshold": 0.3,  # 30% failure = alert
            "high_risk_burst": 10,  # 10 HIGH risk in window = escalation
        }
    
    def set_baseline(self, action: str, metric: str, value: float):
        """Set baseline for anomaly detection."""
        if action not in self._baseline:
            self._baseline[action] = {}
        self._baseline[action][metric] = value
    
    def on_anomaly(self, handler: Callable[[AnomalyAlert], None]):
        """Register callback for anomaly alerts."""
        self._anomaly_handlers.append(handler)
    
    async def analyze_window(
        self,
        window: TimeWindow,
        agent: Optional[str] = None
    ) -> Dict[str, ActionMetrics]:
        """
        Analyze all actions within a time window.
        
        Args:
            window: Time period to analyze
            agent: Optional filter by agent
            
        Returns:
            Dict of action -> metrics
        """
        governor = get_governor()
        
        # Get all records (this is simplified; real implementation would query by time)
        # For now, scan recent records from Governor
        all_records = list(governor._records.values())
        
        # Filter by window
        records = [
            r for r in all_records
            if window.start <= r.created_at <= window.end
            and (agent is None or r.agent == agent)
        ]
        
        # Group by action
        by_action: Dict[str, List[ActionRecord]] = defaultdict(list)
        for r in records:
            by_action[r.action].append(r)
        
        # Calculate metrics per action
        metrics: Dict[str, ActionMetrics] = {}
        for action, action_records in by_action.items():
            m = ActionMetrics(action=action, window=window)
            
            for r in action_records:
                m.total += 1
                m.by_risk[r.risk] += 1
                
                if r.state == ActionState.SUCCESS:
                    m.success += 1
                elif r.state == ActionState.FAILED:
                    m.failed += 1
                elif r.state == ActionState.DENIED:
                    m.denied += 1
                elif r.state == ActionState.SKIPPED:
                    m.skipped += 1
                
                if r.duration_ms():
                    m.durations_ms.append(r.duration_ms())
            
            m.calculate_stats()
            metrics[action] = m
        
        # Detect anomalies
        await self._detect_anomalies(metrics, window)
        
        return metrics
    
    async def _detect_anomalies(
        self,
        metrics: Dict[str, ActionMetrics],
        window: TimeWindow
    ):
        """Detect anomalies in the metrics."""
        alerts: List[AnomalyAlert] = []
        
        for action, m in metrics.items():
            reasons = []
            
            # Check rate spike
            baseline_rate = self._baseline.get(action, {}).get("rate_per_minute", 1.0)
            current_rate = m.total / (window.duration_seconds / 60)
            
            if current_rate > baseline_rate * self._thresholds["rate_spike_multiplier"]:
                reasons.append(f"Rate spike: {current_rate:.1f}/min vs baseline {baseline_rate:.1f}/min")
            
            # Check failure rate
            if m.total > 0:
                failure_rate = m.failed / m.total
                if failure_rate > self._thresholds["failure_rate_threshold"]:
                    reasons.append(f"High failure rate: {failure_rate:.1%}")
            
            # Check risk escalation
            high_risk_count = m.by_risk.get("HIGH", 0)
            if high_risk_count > self._thresholds["high_risk_burst"]:
                reasons.append(f"High risk burst: {high_risk_count} HIGH risk actions")
            
            if reasons:
                m.is_anomalous = True
                m.anomaly_reasons = reasons
                
                severity = "medium"
                if high_risk_count > 20 or failure_rate > 0.5:
                    severity = "critical"
                elif high_risk_count > 15 or failure_rate > 0.4:
                    severity = "high"
                
                alert = AnomalyAlert(
                    severity=severity,
                    category="rate_spike" if current_rate > baseline_rate * 5 else "failure_spike",
                    description="; ".join(reasons),
                    affected_actions=[action],
                    window=window,
                    metrics={
                        "total_actions": m.total,
                        "failure_rate": m.failed / m.total if m.total > 0 else 0,
                        "high_risk_count": high_risk_count,
                        "rate_per_minute": current_rate,
                    }
                )
                alerts.append(alert)
        
        # Fire alerts
        for alert in alerts:
            await self._fire_alert(alert)
    
    async def _fire_alert(self, alert: AnomalyAlert):
        """Fire anomaly alert to all handlers."""
        logger.warning(f"[Analytics] ANOMALY DETECTED: {alert.description}")
        
        for handler in self._anomaly_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"[Analytics] Alert handler failed: {e}")
    
    async def check_agent_health(
        self,
        agent: str,
        window: TimeWindow = None
    ) -> Dict[str, Any]:
        """
        Check health of a specific agent.
        
        Returns health score and flagged issues.
        """
        window = window or TimeWindow.last_hour()
        metrics = await self.analyze_window(window, agent=agent)
        
        if not metrics:
            return {
                "agent": agent,
                "status": "no_data",
                "health_score": None,
                "issues": []
            }
        
        # Calculate health score (0-100)
        total_actions = sum(m.total for m in metrics.values())
        total_failed = sum(m.failed for m in metrics.values())
        total_anomalous = sum(1 for m in metrics.values() if m.is_anomalous)
        
        if total_actions == 0:
            health_score = 100
        else:
            failure_penalty = (total_failed / total_actions) * 50
            anomaly_penalty = (total_anomalous / len(metrics)) * 30
            health_score = max(0, 100 - failure_penalty - anomaly_penalty)
        
        issues = [
            {
                "action": m.action,
                "reasons": m.anomaly_reasons
            }
            for m in metrics.values()
            if m.is_anomalous
        ]
        
        return {
            "agent": agent,
            "window": {
                "start": window.start.isoformat(),
                "end": window.end.isoformat()
            },
            "status": "healthy" if health_score > 80 else "degraded" if health_score > 50 else "critical",
            "health_score": round(health_score, 1),
            "total_actions": total_actions,
            "total_failed": total_failed,
            "anomalous_actions": total_anomalous,
            "issues": issues
        }
    
    def get_summary(
        self,
        metrics: Dict[str, ActionMetrics]
    ) -> Dict[str, Any]:
        """Get executive summary of metrics."""
        if not metrics:
            return {"status": "no_data"}
        
        total = sum(m.total for m in metrics.values())
        success = sum(m.success for m in metrics.values())
        failed = sum(m.failed for m in metrics.values())
        anomalous = sum(1 for m in metrics.values() if m.is_anomalous)
        
        # Top actions by volume
        top_actions = sorted(
            metrics.items(),
            key=lambda x: x[1].total,
            reverse=True
        )[:5]
        
        return {
            "total_actions": total,
            "success_rate": success / total if total > 0 else 0,
            "failure_rate": failed / total if total > 0 else 0,
            "anomalous_actions_count": anomalous,
            "top_actions": [
                {
                    "action": action,
                    "count": m.total,
                    "is_anomalous": m.is_anomalous
                }
                for action, m in top_actions
            ]
        }


class BehaviorProfiler:
    """
    Profile normal agent behavior to detect deviations.
    
    Builds baselines over time, detects when behavior changes.
    """
    
    def __init__(self, analytics: AnalyticsEngine = None):
        self.analytics = analytics or AnalyticsEngine()
        self._profiles: Dict[str, Dict[str, Any]] = {}  # agent -> profile
    
    async def build_profile(self, agent: str, days: int = 7) -> Dict[str, Any]:
        """
        Build behavioral baseline for an agent.
        
        Analyzes last N days to establish "normal".
        """
        end = datetime.utcnow()
        start = end - timedelta(days=days)
        window = TimeWindow(start, end, f"last_{days}_days")
        
        metrics = await self.analytics.analyze_window(window, agent=agent)
        
        # Calculate baselines
        profile = {
            "agent": agent,
            "period_days": days,
            "baseline_rates": {},
            "normal_hours": [],
            "typical_risk_mix": {},
        }
        
        for action, m in metrics.items():
            rate_per_hour = m.total / (days * 24)
            profile["baseline_rates"][action] = {
                "per_hour": rate_per_hour,
                "per_day": m.total / days,
                "failure_rate": m.failed / m.total if m.total > 0 else 0,
            }
        
        # Store for future comparison
        self._profiles[agent] = profile
        
        # Update analytics baselines
        for action, rates in profile["baseline_rates"].items():
            self.analytics.set_baseline(action, "rate_per_minute", rates["per_hour"] / 60)
        
        return profile
    
    def compare_to_profile(
        self,
        agent: str,
        current_metrics: Dict[str, ActionMetrics]
    ) -> List[str]:
        """Compare current behavior to established profile."""
        profile = self._profiles.get(agent)
        if not profile:
            return ["No profile established for this agent"]
        
        deviations = []
        
        for action, m in current_metrics.items():
            baseline = profile["baseline_rates"].get(action)
            if not baseline:
                deviations.append(f"New action detected: {action}")
                continue
            
            current_rate = m.total / 24  # Assuming 1 hour window
            expected_rate = baseline["per_hour"]
            
            if current_rate > expected_rate * 3:
                deviations.append(
                    f"{action}: {current_rate:.1f}/h vs baseline {expected_rate:.1f}/h"
                )
        
        return deviations


# Singleton
_engine_instance: Optional[AnalyticsEngine] = None
_profiler_instance: Optional[BehaviorProfiler] = None


def get_analytics() -> AnalyticsEngine:
    """Get or create the global analytics engine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AnalyticsEngine()
    return _engine_instance


def get_profiler() -> BehaviorProfiler:
    """Get or create the global behavior profiler."""
    global _profiler_instance
    if _profiler_instance is None:
        _profiler_instance = BehaviorProfiler(get_analytics())
    return _profiler_instance


__all__ = [
    'AnalyticsEngine',
    'BehaviorProfiler',
    'TimeWindow',
    'ActionMetrics',
    'AnomalyAlert',
    'get_analytics',
    'get_profiler',
]
