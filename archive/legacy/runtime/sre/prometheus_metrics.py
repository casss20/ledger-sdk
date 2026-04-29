import time
import asyncio
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest

# Custom metrics registry
CITADEL_REGISTRY = CollectorRegistry()

# Info metric for app metadata
APP_INFO = Info(
    "citadel_app",
    "Citadel application metadata",
    registry=CITADEL_REGISTRY,
)

# Request metrics
REQUEST_COUNT = Counter(
    "citadel_requests_total",
    "Total requests by method, path, status",
    ["method", "path", "status_code"],
    registry=CITADEL_REGISTRY,
)

REQUEST_DURATION = Histogram(
    "citadel_request_duration_seconds",
    "Request duration in seconds",
    ["method", "path"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=CITADEL_REGISTRY,
)

# Governance metrics
GOVERNANCE_DECISIONS = Counter(
    "citadel_governance_decisions_total",
    "Governance decisions by outcome",
    ["outcome", "risk_level"],
    registry=CITADEL_REGISTRY,
)

APPROVAL_QUEUE_SIZE = Gauge(
    "citadel_approval_queue_size",
    "Current pending approvals",
    registry=CITADEL_REGISTRY,
)

KILL_SWITCH_ACTIVE = Gauge(
    "citadel_kill_switch_active",
    "Active kill switches",
    ["scope_type", "scope_value"],
    registry=CITADEL_REGISTRY,
)

# Database metrics
DB_CONNECTIONS = Gauge(
    "citadel_db_connections",
    "Database connections",
    ["state"],
    registry=CITADEL_REGISTRY,
)

DB_QUERY_DURATION = Histogram(
    "citadel_db_query_duration_seconds",
    "Database query duration",
    ["query_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
    registry=CITADEL_REGISTRY,
)

# Auth metrics
AUTH_ATTEMPTS = Counter(
    "citadel_auth_attempts_total",
    "Authentication attempts by result",
    ["method", "result"],
    registry=CITADEL_REGISTRY,
)

RATE_LIMIT_HITS = Counter(
    "citadel_rate_limit_hits_total",
    "Rate limit hits by endpoint",
    ["endpoint", "limit_type"],
    registry=CITADEL_REGISTRY,
)

# Agent metrics
AGENT_ACTIONS = Counter(
    "citadel_agent_actions_total",
    "Agent actions by agent and action type",
    ["agent_id", "action_type", "result"],
    registry=CITADEL_REGISTRY,
)

AGENT_HEALTH = Gauge(
    "citadel_agent_health_score",
    "Agent health score",
    ["agent_id"],
    registry=CITADEL_REGISTRY,
)

# Error metrics
ERRORS_TOTAL = Counter(
    "citadel_errors_total",
    "Total errors by type",
    ["error_type", "endpoint"],
    registry=CITADEL_REGISTRY,
)

# Business metrics
TENANT_COUNT = Gauge(
    "citadel_tenant_count",
    "Active tenants",
    registry=CITADEL_REGISTRY,
)

API_KEY_COUNT = Gauge(
    "citadel_api_key_count",
    "Active API keys by tenant",
    ["tenant_id"],
    registry=CITADEL_REGISTRY,
)


class CitadelMetrics:
    """
    Metrics collection for Citadel SRE.
    
    Tracks:
    - Request latency and throughput
    - Governance decision outcomes
    - Database performance
    - Auth success/failure rates
    - Agent activity
    - Error rates
    """
    
    def __init__(self, app_version: str = "0.1.0"):
        self.app_version = app_version
        self._setup_app_info()
        self._active_timers: Dict[str, float] = {}
    
    def _setup_app_info(self) -> None:
        """Set application metadata in metrics."""
        APP_INFO.info({"version": self.app_version, "name": "citadel-governance"})
    
    def record_request(self, method: str, path: str, status_code: int, duration_ms: float) -> None:
        """Record an HTTP request metric."""
        REQUEST_COUNT.labels(method=method, path=path, status_code=str(status_code)).inc()
        REQUEST_DURATION.labels(method=method, path=path).observe(duration_ms / 1000)
    
    def record_governance_decision(self, outcome: str, risk_level: str) -> None:
        """Record a governance decision outcome."""
        GOVERNANCE_DECISIONS.labels(outcome=outcome, risk_level=risk_level).inc()
    
    def record_auth_attempt(self, method: str, success: bool) -> None:
        """Record an authentication attempt."""
        result = "success" if success else "failure"
        AUTH_ATTEMPTS.labels(method=method, result=result).inc()
    
    def record_rate_limit_hit(self, endpoint: str, limit_type: str) -> None:
        """Record a rate limit hit."""
        RATE_LIMIT_HITS.labels(endpoint=endpoint, limit_type=limit_type).inc()
    
    def record_error(self, error_type: str, endpoint: str) -> None:
        """Record an error occurrence."""
        ERRORS_TOTAL.labels(error_type=error_type, endpoint=endpoint).inc()
    
    def record_agent_action(self, agent_id: str, action_type: str, success: bool) -> None:
        """Record an agent action."""
        result = "success" if success else "failure"
        AGENT_ACTIONS.labels(agent_id=agent_id, action_type=action_type, result=result).inc()
    
    def update_agent_health(self, agent_id: str, health_score: int) -> None:
        """Update agent health score."""
        AGENT_HEALTH.labels(agent_id=agent_id).set(health_score)
    
    def update_approval_queue(self, size: int) -> None:
        """Update pending approval count."""
        APPROVAL_QUEUE_SIZE.set(size)
    
    def update_kill_switch(self, scope_type: str, scope_value: str, active: bool) -> None:
        """Update kill switch status."""
        KILL_SWITCH_ACTIVE.labels(scope_type=scope_type, scope_value=scope_value).set(1 if active else 0)
    
    def update_db_connections(self, state: str, count: int) -> None:
        """Update database connection count."""
        DB_CONNECTIONS.labels(state=state).set(count)
    
    def start_db_query_timer(self, query_id: str) -> None:
        """Start timing a database query."""
        self._active_timers[query_id] = time.time()
    
    def stop_db_query_timer(self, query_id: str, query_type: str) -> float:
        """Stop timing a database query and record metric."""
        start = self._active_timers.pop(query_id, None)
        if start:
            duration = time.time() - start
            DB_QUERY_DURATION.labels(query_type=query_type).observe(duration)
            return duration
        return 0.0
    
    def update_tenant_count(self, count: int) -> None:
        """Update active tenant count."""
        TENANT_COUNT.set(count)
    
    def update_api_key_count(self, tenant_id: str, count: int) -> None:
        """Update API key count for a tenant."""
        API_KEY_COUNT.labels(tenant_id=tenant_id).set(count)
    
    def get_metrics(self) -> bytes:
        """Generate Prometheus metrics output."""
        return generate_latest(CITADEL_REGISTRY)


# Global instance
_metrics: Optional[CitadelMetrics] = None


def setup_metrics(app_version: str = "0.1.0") -> CitadelMetrics:
    """Initialize and return the global metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = CitadelMetrics(app_version)
    return _metrics


def get_metrics() -> CitadelMetrics:
    """Get the global metrics instance."""
    if _metrics is None:
        return setup_metrics()
    return _metrics