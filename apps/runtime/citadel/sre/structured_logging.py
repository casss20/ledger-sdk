import json
import logging
import sys
import time
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from citadel.config import settings


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, "tenant_id"):
            log_data["tenant_id"] = record.tenant_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "action"):
            log_data["action"] = record.action
        if hasattr(record, "resource"):
            log_data["resource"] = record.resource
        if hasattr(record, "risk_level"):
            log_data["risk_level"] = record.risk_level
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }
        
        return json.dumps(log_data, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter for development."""
    
    def format(self, record: logging.LogRecord) -> str:
        extra = ""
        if hasattr(record, "tenant_id"):
            extra += f" [tenant={record.tenant_id}]"
        if hasattr(record, "request_id"):
            extra += f" [req={record.request_id}]"
        if hasattr(record, "duration_ms"):
            extra += f" ({record.duration_ms:.1f}ms)"
        
        return f"[{datetime.utcnow().isoformat()}] {record.levelname:8} {record.name} - {record.getMessage()}{extra}"


def configure_logging() -> None:
    """Configure structured logging for the application."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    
    # Choose formatter
    if settings.log_format.lower() == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(TextFormatter())
    
    root_logger.addHandler(handler)
    
    # Set specific loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    
    logging.info(f"Logging configured: level={settings.log_level}, format={settings.log_format}")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs every request with structured fields.
    
    Captures:
    - Request method, path, query params
    - Response status code
    - Duration in milliseconds
    - Tenant ID, user ID
    - Request ID for tracing
    - Client IP, user agent
    
    Logs errors with full context for debugging.
    """
    
    def __init__(self, app, log_requests: bool = True, log_responses: bool = True):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.logger = logging.getLogger("citadel.access")
    
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Generate or propagate request ID
        request_id = request.headers.get("X-Request-ID", f"req_{int(time.time() * 1000)}")
        request.state.request_id = request_id
        
        # Client info
        client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
        if isinstance(client_ip, str) and "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()
        
        user_agent = request.headers.get("User-Agent", "unknown")
        
        # Auth context (may not be set yet if auth middleware runs after)
        tenant_id = getattr(request.state, "tenant_id", None)
        user_id = getattr(request.state, "user_id", None)
        role = getattr(request.state, "role", None)
        
        if self.log_requests:
            extra = {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "action": f"{request.method} {request.url.path}",
                "resource": str(request.url),
            }
            self.logger.info(
                f"→ {request.method} {request.url.path} | ip={client_ip} | ua={user_agent[:50]}",
                extra=extra,
            )
        
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            extra = {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "action": f"{request.method} {request.url.path}",
                "resource": str(request.url),
                "duration_ms": duration_ms,
                "status_code": 500,
                "risk_level": "high",
            }
            self.logger.error(
                f"✗ {request.method} {request.url.path} - ERROR: {str(exc)} ({duration_ms:.1f}ms)",
                extra=extra,
                exc_info=True,
            )
            raise
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Determine risk level based on status code
        risk_level = "low"
        if response.status_code >= 500:
            risk_level = "high"
        elif response.status_code == 429:
            risk_level = "medium"
        elif response.status_code == 401 or response.status_code == 403:
            risk_level = "medium"
        
        if self.log_responses:
            extra = {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "action": f"{request.method} {request.url.path}",
                "resource": str(request.url),
                "duration_ms": duration_ms,
                "status_code": response.status_code,
                "risk_level": risk_level,
            }
            
            if response.status_code >= 400:
                self.logger.warning(
                    f"⚠ {request.method} {request.url.path} → {response.status_code} ({duration_ms:.1f}ms)",
                    extra=extra,
                )
            else:
                self.logger.info(
                    f"✓ {request.method} {request.url.path} → {response.status_code} ({duration_ms:.1f}ms)",
                    extra=extra,
                )
        
        # Add structured headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
        
        return response


def log_event(
    level: str,
    message: str,
    tenant_id: Optional[str] = None,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    resource: Optional[str] = None,
    risk_level: Optional[str] = None,
    duration_ms: Optional[float] = None,
    status_code: Optional[int] = None,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log a structured event with all governance context.
    
    Usage:
        log_event("warning", "Kill switch triggered", risk_level="critical", action="killswitch")
    """
    logger = logging.getLogger("citadel.events")
    
    extra = {}
    if tenant_id:
        extra["tenant_id"] = tenant_id
    if request_id:
        extra["request_id"] = request_id
    if user_id:
        extra["user_id"] = user_id
    if action:
        extra["action"] = action
    if resource:
        extra["resource"] = resource
    if risk_level:
        extra["risk_level"] = risk_level
    if duration_ms is not None:
        extra["duration_ms"] = duration_ms
    if status_code:
        extra["status_code"] = status_code
    if extra_fields:
        extra.update(extra_fields)
    
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(message, extra=extra)