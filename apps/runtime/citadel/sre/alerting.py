import asyncio
import json
import logging
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:
    import aiohttp
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """An alert event."""
    id: str
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    action: Optional[str] = None
    resource: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() + "Z",
            "tenant_id": self.tenant_id,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "action": self.action,
            "resource": self.resource,
            "metadata": self.metadata,
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() + "Z" if self.acknowledged_at else None,
        }


class AlertChannel:
    """Base class for alert channels."""
    
    async def send(self, alert: Alert) -> bool:
        """Send an alert through this channel. Return True if successful."""
        raise NotImplementedError


class WebhookChannel(AlertChannel):
    """Send alerts via HTTP webhook."""
    
    def __init__(
        self,
        webhook_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 10,
    ):
        self.webhook_url = webhook_url
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout
    
    async def send(self, alert: Alert) -> bool:
        """Send alert to webhook endpoint."""
        try:
            async with aiohttp.ClientSession() as session:
                payload = alert.to_dict()
                async with session.post(
                    self.webhook_url,
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    return response.status < 400
        except Exception as e:
            logging.getLogger("citadel.alerting").error(f"Webhook alert failed: {e}")
            return False


class SlackChannel(AlertChannel):
    """Send alerts to Slack webhook."""
    
    def __init__(self, webhook_url: str, channel: Optional[str] = None):
        self.webhook_url = webhook_url
        self.channel = channel
    
    async def send(self, alert: Alert) -> bool:
        """Send alert to Slack."""
        try:
            color = {
                AlertSeverity.INFO: "#36a64f",
                AlertSeverity.WARNING: "#ff9900",
                AlertSeverity.ERROR: "#ff0000",
                AlertSeverity.CRITICAL: "#990000",
            }.get(alert.severity, "#808080")
            
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"[{alert.severity.value.upper()}] {alert.title}",
                        "text": alert.message,
                        "fields": [
                            {"title": "Alert ID", "value": alert.id, "short": True},
                            {"title": "Tenant", "value": alert.tenant_id or "N/A", "short": True},
                            {"title": "Action", "value": alert.action or "N/A", "short": True},
                            {"title": "Resource", "value": alert.resource or "N/A", "short": True},
                            {"title": "Request ID", "value": alert.request_id or "N/A", "short": False},
                        ],
                        "footer": "Citadel SRE",
                        "ts": int(alert.timestamp.timestamp()),
                    }
                ]
            }
            
            if self.channel:
                payload["channel"] = self.channel
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    return response.status < 400
        except Exception as e:
            logging.getLogger("citadel.alerting").error(f"Slack alert failed: {e}")
            return False


class PagerDutyChannel(AlertChannel):
    """Send critical alerts to PagerDuty."""
    
    def __init__(self, integration_key: str, severity_map: Optional[Dict[AlertSeverity, str]] = None):
        self.integration_key = integration_key
        self.severity_map = severity_map or {
            AlertSeverity.WARNING: "warning",
            AlertSeverity.ERROR: "error",
            AlertSeverity.CRITICAL: "critical",
        }
    
    async def send(self, alert: Alert) -> bool:
        """Send alert to PagerDuty Events API v2."""
        if alert.severity not in self.severity_map:
            return True  # Skip non-mapped severities
        
        try:
            payload = {
                "routing_key": self.integration_key,
                "event_action": "trigger",
                "dedup_key": alert.id,
                "payload": {
                    "summary": f"[{alert.severity.value.upper()}] {alert.title}: {alert.message}",
                    "severity": self.severity_map[alert.severity],
                    "source": "citadel-api",
                    "custom_details": {
                        "tenant_id": alert.tenant_id,
                        "request_id": alert.request_id,
                        "action": alert.action,
                        "resource": alert.resource,
                        **alert.metadata,
                    }
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    return response.status < 400
        except Exception as e:
            logging.getLogger("citadel.alerting").error(f"PagerDuty alert failed: {e}")
            return False


class ConsoleChannel(AlertChannel):
    """Log alerts to console (for development)."""
    
    async def send(self, alert: Alert) -> bool:
        """Log alert to console."""
        logger = logging.getLogger("citadel.alerting")
        level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL,
        }.get(alert.severity, logging.INFO)
        
        logger.log(level, f"ALERT [{alert.severity.value.upper()}] {alert.title}: {alert.message} (id={alert.id})")
        return True


class AlertManager:
    """
    Central alert management system.
    
    Routes alerts to configured channels based on severity.
    Supports deduplication, rate limiting, and acknowledgment.
    """
    
    def __init__(
        self,
        channels: Optional[List[AlertChannel]] = None,
        severity_routing: Optional[Dict[AlertSeverity, List[AlertChannel]]] = None,
        dedup_window_seconds: int = 300,
        rate_limit_per_minute: int = 60,
    ):
        self.channels = channels or [ConsoleChannel()]
        self.severity_routing = severity_routing
        self.dedup_window = dedup_window_seconds
        self.rate_limit = rate_limit_per_minute
        
        self._recent_alerts: Dict[str, datetime] = {}
        self._alert_count: int = 0
        self._last_rate_reset: datetime = datetime.utcnow()
        self._alert_history: List[Alert] = []
        self._max_history = 1000
        
        self.logger = logging.getLogger("citadel.alerting")
    
    def _is_duplicate(self, alert: Alert) -> bool:
        """Check if this alert is a duplicate within the dedup window."""
        key = f"{alert.title}:{alert.tenant_id}:{alert.action}"
        now = datetime.utcnow()
        
        if key in self._recent_alerts:
            elapsed = (now - self._recent_alerts[key]).total_seconds()
            if elapsed < self.dedup_window:
                return True
        
        self._recent_alerts[key] = now
        return False
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within the rate limit."""
        now = datetime.utcnow()
        elapsed = (now - self._last_rate_reset).total_seconds()
        
        if elapsed >= 60:
            self._alert_count = 0
            self._last_rate_reset = now
        
        if self._alert_count >= self.rate_limit:
            return False
        
        self._alert_count += 1
        return True
    
    async def send(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        tenant_id: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Alert]:
        """
        Send an alert through configured channels.
        
        Returns the Alert if sent, None if deduplicated or rate limited.
        """
        import uuid
        
        alert = Alert(
            id=str(uuid.uuid4())[:12],
            severity=severity,
            title=title,
            message=message,
            tenant_id=tenant_id,
            request_id=request_id,
            user_id=user_id,
            action=action,
            resource=resource,
            metadata=metadata or {},
        )
        
        # Check deduplication
        if self._is_duplicate(alert):
            self.logger.debug(f"Alert deduplicated: {title}")
            return None
        
        # Check rate limit
        if not self._check_rate_limit():
            self.logger.warning("Alert rate limit exceeded, dropping alert")
            return None
        
        # Determine channels
        channels_to_use = self.channels
        if self.severity_routing:
            channels_to_use = self.severity_routing.get(severity, self.channels)
        
        # Send to all channels
        results = await asyncio.gather(
            *[channel.send(alert) for channel in channels_to_use],
            return_exceptions=True,
        )
        
        success_count = sum(1 for r in results if r is True)
        self.logger.info(f"Alert sent to {success_count}/{len(channels_to_use)} channels: {title}")
        
        # Store in history
        self._alert_history.append(alert)
        if len(self._alert_history) > self._max_history:
            self._alert_history = self._alert_history[-self._max_history:]
        
        return alert
    
    async def info(self, title: str, message: str, **kwargs) -> Optional[Alert]:
        """Send an info alert."""
        return await self.send(AlertSeverity.INFO, title, message, **kwargs)
    
    async def warning(self, title: str, message: str, **kwargs) -> Optional[Alert]:
        """Send a warning alert."""
        return await self.send(AlertSeverity.WARNING, title, message, **kwargs)
    
    async def error(self, title: str, message: str, **kwargs) -> Optional[Alert]:
        """Send an error alert."""
        return await self.send(AlertSeverity.ERROR, title, message, **kwargs)
    
    async def critical(self, title: str, message: str, **kwargs) -> Optional[Alert]:
        """Send a critical alert."""
        return await self.send(AlertSeverity.CRITICAL, title, message, **kwargs)
    
    def acknowledge(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        for alert in self._alert_history:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.utcnow()
                return True
        return False
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get unacknowledged alerts."""
        alerts = [a for a in self._alert_history if not a.acknowledged]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get recent alert history."""
        return self._alert_history[-limit:]


# Global alert manager
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get or create the global alert manager."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def configure_alert_manager(
    slack_webhook: Optional[str] = None,
    pagerduty_key: Optional[str] = None,
    custom_webhook: Optional[str] = None,
    dedup_window: int = 300,
) -> AlertManager:
    """Configure the alert manager with channels."""
    global _alert_manager
    
    channels: List[AlertChannel] = [ConsoleChannel()]
    
    if slack_webhook:
        channels.append(SlackChannel(slack_webhook))
    
    if pagerduty_key:
        channels.append(PagerDutyChannel(pagerduty_key))
    
    if custom_webhook:
        channels.append(WebhookChannel(custom_webhook))
    
    severity_routing = None
    if pagerduty_key:
        # Route critical/error to PagerDuty, everything to all
        severity_routing = {
            AlertSeverity.CRITICAL: [ConsoleChannel(), PagerDutyChannel(pagerduty_key)],
            AlertSeverity.ERROR: [ConsoleChannel(), PagerDutyChannel(pagerduty_key)],
        }
    
    _alert_manager = AlertManager(
        channels=channels,
        severity_routing=severity_routing,
        dedup_window_seconds=dedup_window,
    )
    
    return _alert_manager