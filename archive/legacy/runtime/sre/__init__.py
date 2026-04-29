"""
SRE Infrastructure Package for Citadel

Provides:
- Structured logging with JSON output
- Custom Prometheus metrics collection
- Alerting webhook system for critical events
- Enhanced health checks with dependency verification
- SLO/SLA definitions and tracking
"""

from .structured_logging import StructuredLoggingMiddleware, configure_logging
from .prometheus_metrics import CitadelMetrics, setup_metrics
from .alerting import AlertManager, AlertSeverity
from .health_checks import HealthCheckManager, HealthStatus
from .slos import SLOTracker, SLODefinition

__all__ = [
    "StructuredLoggingMiddleware",
    "configure_logging",
    "CitadelMetrics",
    "setup_metrics",
    "AlertManager",
    "AlertSeverity",
    "HealthCheckManager",
    "HealthStatus",
    "SLOTracker",
    "SLODefinition",
]