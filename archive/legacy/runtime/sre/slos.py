import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class SLOStatus(Enum):
    """SLO compliance status."""
    MEETING = "meeting"
    AT_RISK = "at_risk"
    BREACHING = "breaching"
    UNKNOWN = "unknown"


@dataclass
class SLODefinition:
    """Service Level Objective definition."""
    name: str
    description: str
    target: float  # Target value (e.g., 0.99 for 99%)
    window: str  # Time window (e.g., "30d", "7d", "24h")
    metric: str  # Metric name
    unit: str  # Unit (e.g., "percent", "ms", "count")
    alert_threshold: float  # Threshold to trigger alert
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "target": self.target,
            "window": self.window,
            "metric": self.metric,
            "unit": self.unit,
            "alert_threshold": self.alert_threshold,
        }


@dataclass
class SLOResult:
    """SLO evaluation result."""
    slo: SLODefinition
    current_value: float
    status: SLOStatus
    observations: int
    violations: int
    last_evaluation: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "slo": self.slo.to_dict(),
            "current_value": self.current_value,
            "status": self.status.value,
            "observations": self.observations,
            "violations": self.violations,
            "last_evaluation": self.last_evaluation.isoformat() + "Z",
        }


# Default SLOs for Citadel
DEFAULT_SLOS = [
    SLODefinition(
        name="api_availability",
        description="API endpoint availability (2xx responses / total requests)",
        target=0.995,  # 99.5%
        window="30d",
        metric="availability",
        unit="percent",
        alert_threshold=0.99,
    ),
    SLODefinition(
        name="api_latency_p95",
        description="95th percentile API response time",
        target=500.0,  # 500ms
        window="7d",
        metric="latency_p95",
        unit="ms",
        alert_threshold=1000.0,
    ),
    SLODefinition(
        name="auth_success_rate",
        description="Successful authentication rate",
        target=0.99,  # 99%
        window="7d",
        metric="auth_success",
        unit="percent",
        alert_threshold=0.95,
    ),
    SLODefinition(
        name="db_query_latency_p99",
        description="99th percentile database query time",
        target=100.0,  # 100ms
        window="7d",
        metric="db_latency_p99",
        unit="ms",
        alert_threshold=250.0,
    ),
    SLODefinition(
        name="governance_decision_time",
        description="Time to make a governance decision",
        target=50.0,  # 50ms
        window="24h",
        metric="decision_time",
        unit="ms",
        alert_threshold=100.0,
    ),
    SLODefinition(
        name="error_rate",
        description="Rate of 5xx responses",
        target=0.001,  # 0.1%
        window="7d",
        metric="error_rate",
        unit="percent",
        alert_threshold=0.01,
    ),
]


class SLOTracker:
    """
    SLO tracking and evaluation.
    
    Tracks:
    - Request latencies
    - Success/error rates
    - Decision times
    - Auth success rates
    
    Evaluates:
    - Is the SLO being met?
    - Are we at risk of breaching?
    - Historical trends
    """
    
    def __init__(self, slos: Optional[List[SLODefinition]] = None):
        self.slos = slos or DEFAULT_SLOS
        self._observations: Dict[str, List[Dict[str, Any]]] = {slo.name: [] for slo in self.slos}
        self._results: Dict[str, SLOResult] = {}
        self.logger = logging.getLogger("citadel.slo")
        self._evaluation_interval = 300  # 5 minutes
        self._last_evaluation = datetime.utcnow()
    
    def record_observation(self, slo_name: str, value: float, timestamp: Optional[datetime] = None) -> None:
        """Record a single observation for an SLO."""
        if slo_name not in self._observations:
            self.logger.warning(f"Unknown SLO: {slo_name}")
            return
        
        obs = {
            "value": value,
            "timestamp": timestamp or datetime.utcnow(),
        }
        self._observations[slo_name].append(obs)
        
        # Keep only last 10,000 observations per SLO
        if len(self._observations[slo_name]) > 10000:
            self._observations[slo_name] = self._observations[slo_name][-10000:]
    
    def record_request(self, latency_ms: float, success: bool) -> None:
        """Record an API request observation."""
        self.record_observation("api_latency_p95", latency_ms)
        self.record_observation("api_availability", 1.0 if success else 0.0)
        
        if not success:
            self.record_observation("error_rate", 1.0)
        else:
            self.record_observation("error_rate", 0.0)
    
    def record_auth(self, success: bool) -> None:
        """Record an auth attempt observation."""
        self.record_observation("auth_success_rate", 1.0 if success else 0.0)
    
    def record_db_query(self, latency_ms: float) -> None:
        """Record a database query observation."""
        self.record_observation("db_query_latency_p99", latency_ms)
    
    def record_decision(self, latency_ms: float) -> None:
        """Record a governance decision observation."""
        self.record_observation("governance_decision_time", latency_ms)
    
    def evaluate(self, slo_name: Optional[str] = None) -> Dict[str, SLOResult]:
        """Evaluate SLOs and return results."""
        now = datetime.utcnow()
        self._last_evaluation = now
        
        slos_to_eval = [s for s in self.slos if slo_name is None or s.name == slo_name]
        
        for slo in slos_to_eval:
            observations = self._observations.get(slo.name, [])
            
            if not observations:
                self._results[slo.name] = SLOResult(
                    slo=slo,
                    current_value=0.0,
                    status=SLOStatus.UNKNOWN,
                    observations=0,
                    violations=0,
                    last_evaluation=now,
                )
                continue
            
            # Filter by window
            window_delta = self._parse_window(slo.window)
            cutoff = now - window_delta
            recent_obs = [o for o in observations if o["timestamp"] > cutoff]
            
            if not recent_obs:
                self._results[slo.name] = SLOResult(
                    slo=slo,
                    current_value=0.0,
                    status=SLOStatus.UNKNOWN,
                    observations=0,
                    violations=0,
                    last_evaluation=now,
                )
                continue
            
            values = [o["value"] for o in recent_obs]
            
            # Calculate current value based on metric type
            if slo.metric == "availability" or slo.metric == "auth_success":
                current_value = sum(values) / len(values)
            elif slo.metric == "error_rate":
                current_value = sum(values) / len(values)
            elif slo.metric in ["latency_p95", "db_latency_p99", "decision_time"]:
                # For latency, check if P95/P99 is within target
                import statistics
                current_value = statistics.quantiles(values, n=100)[94] if len(values) >= 2 else values[0]
            else:
                current_value = sum(values) / len(values)
            
            # Count violations
            if slo.metric in ["latency_p95", "db_latency_p99", "decision_time"]:
                # For latency, lower is better
                violations = sum(1 for v in values if v > slo.target)
            elif slo.metric == "error_rate":
                # For error rate, lower is better
                violations = sum(1 for v in values if v > slo.target)
            else:
                # For availability/auth, higher is better
                violations = sum(1 for v in values if v < slo.target)
            
            # Determine status
            if slo.metric in ["latency_p95", "db_latency_p99", "decision_time", "error_rate"]:
                # Lower is better
                if current_value <= slo.target:
                    status = SLOStatus.MEETING
                elif current_value <= slo.alert_threshold:
                    status = SLOStatus.AT_RISK
                else:
                    status = SLOStatus.BREACHING
            else:
                # Higher is better
                if current_value >= slo.target:
                    status = SLOStatus.MEETING
                elif current_value >= slo.alert_threshold:
                    status = SLOStatus.AT_RISK
                else:
                    status = SLOStatus.BREACHING
            
            self._results[slo.name] = SLOResult(
                slo=slo,
                current_value=current_value,
                status=status,
                observations=len(recent_obs),
                violations=violations,
                last_evaluation=now,
            )
        
        return self._results
    
    def _parse_window(self, window: str) -> timedelta:
        """Parse a window string like '30d', '7d', '24h' into a timedelta."""
        unit = window[-1]
        value = int(window[:-1])
        
        if unit == "d":
            return timedelta(days=value)
        elif unit == "h":
            return timedelta(hours=value)
        elif unit == "m":
            return timedelta(minutes=value)
        else:
            return timedelta(days=30)
    
    def get_results(self) -> Dict[str, SLOResult]:
        """Get current SLO results."""
        return self._results
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all SLO statuses."""
        results = self._results
        
        return {
            "total_slos": len(self.slos),
            "meeting": sum(1 for r in results.values() if r.status == SLOStatus.MEETING),
            "at_risk": sum(1 for r in results.values() if r.status == SLOStatus.AT_RISK),
            "breaching": sum(1 for r in results.values() if r.status == SLOStatus.BREACHING),
            "unknown": sum(1 for r in results.values() if r.status == SLOStatus.UNKNOWN),
            "slos": {name: result.to_dict() for name, result in results.items()},
        }


# Global instance
_slo_tracker: Optional[SLOTracker] = None


def get_slo_tracker() -> SLOTracker:
    """Get or create the global SLO tracker."""
    global _slo_tracker
    if _slo_tracker is None:
        _slo_tracker = SLOTracker()
    return _slo_tracker