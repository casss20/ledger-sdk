"""
Citadel API Middleware

- Request ID tracing
- Structured logging (JSON or text)
- Error handling with request IDs
- CORS (production-locked)
- Request body size limits
"""

import json
import logging
import time
import uuid
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from citadel.security.owasp_middleware import (
    SecurityHeadersMiddleware,
    InputValidationMiddleware,
    SSRFProtectionMiddleware,
)
from citadel.config import settings


# ---------------------------------------------------------------------------
# Structured Logging Setup
# ---------------------------------------------------------------------------

class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    def format(self, record):
        log_obj = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Add extra fields if present
        for key in ["request_id", "method", "path", "status_code", "duration_ms", "error"]:
            if hasattr(record, key):
                log_obj[key] = getattr(record, key)
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def _setup_logging():
    """Configure root logger based on settings."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    
    # Remove existing handlers to avoid duplicates
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    
    handler = logging.StreamHandler()
    if settings.log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
    root.addHandler(handler)


_setup_logging()
logger = logging.getLogger("citadel.middleware")


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

DEFAULT_DEBUG_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]


def get_cors_origins() -> list:
    """Get allowed CORS origins based on environment"""
    # Re-resolve settings dynamically so monkeypatch in tests works.
    from citadel import config as _config
    s = _config.settings
    if s.debug:
        return DEFAULT_DEBUG_ORIGINS
    env_origins = getattr(s, "cors_origins", None)
    if env_origins:
        return [o.strip() for o in env_origins.split(",") if o.strip()]
    return []


# ---------------------------------------------------------------------------
# Middleware Classes
# ---------------------------------------------------------------------------

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Block requests with body larger than max size"""
    
    MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB default
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.MAX_BODY_SIZE:
                    from fastapi.responses import JSONResponse
                    logger.warning(
                        "Request rejected: payload too large",
                        extra={
                            "request_id": getattr(request.state, "request_id", "unknown"),
                            "size": size,
                            "max_size": self.MAX_BODY_SIZE,
                        }
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "payload_too_large",
                            "message": f"Request body exceeds {self.MAX_BODY_SIZE // 1024 // 1024}MB limit",
                            "max_size_mb": self.MAX_BODY_SIZE // 1024 // 1024,
                        },
                    )
            except ValueError:
                pass
        
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with timing, status, and request ID."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request error: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 1),
                    "error": str(exc),
                },
                exc_info=True,
            )
            raise
        
        duration_ms = (time.time() - start_time) * 1000
        status_code = response.status_code
        
        # Determine log level based on status
        log_level = logging.INFO if status_code < 400 else logging.WARNING
        if status_code >= 500:
            log_level = logging.ERROR
        
        logger.log(
            log_level,
            f"{request.method} {request.url.path} {status_code}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 1),
            }
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return structured error responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", "unknown")
            
            logger.error(
                f"Unhandled exception: {exc}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                },
                exc_info=True,
            )
            
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_error",
                    "message": str(exc) if settings.debug else "Internal server error",
                    "request_id": request_id,
                },
            )


def setup_cors(app: FastAPI) -> None:
    """Add CORS as the outermost middleware so it handles preflight before auth."""
    origins = settings.allowed_cors_origins
    if not origins:
        raise RuntimeError(
            "CORS_ORIGINS / settings.allowed_cors_origins must be configured "
            "(comma-separated list). Refusing to start with wildcard + credentials."
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-API-Secret", "X-Tenant-ID"],
    )


def setup_middleware(app: FastAPI) -> None:
    """Register all middleware on the app."""
    # OWASP security headers (outermost — applies to all responses)
    app.add_middleware(SecurityHeadersMiddleware)
    # SSRF protection on URL parameters
    app.add_middleware(SSRFProtectionMiddleware)
    # Input validation / injection detection
    app.add_middleware(InputValidationMiddleware)
    # Request size limit
    app.add_middleware(RequestSizeLimitMiddleware)
    # Request logging
    app.add_middleware(RequestLoggingMiddleware)
    # Error handling (innermost — catches everything)
    app.add_middleware(ErrorHandlingMiddleware)
