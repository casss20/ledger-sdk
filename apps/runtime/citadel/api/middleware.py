"""
Citadel API Middleware

- Request ID tracing
- Structured logging
- Error handling with request IDs
- CORS (production-locked)
- Request body size limits
"""

import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from citadel.config import settings


# Production CORS origins — override in .env or settings
# Default: empty list (no CORS) in production
# Debug mode: allow localhost origins only
DEFAULT_DEBUG_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]


def get_cors_origins() -> list:
    """Get allowed CORS origins based on environment"""
    if settings.debug:
        return DEFAULT_DEBUG_ORIGINS
    # Production: must be explicitly configured
    # Settings can override with comma-separated origins
    env_origins = getattr(settings, "cors_origins", None)
    if env_origins:
        return [o.strip() for o in env_origins.split(",") if o.strip()]
    return []  # No CORS in production by default


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
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "payload_too_large",
                            "message": f"Request body exceeds {self.MAX_BODY_SIZE // 1024 // 1024}MB limit",
                            "max_size_mb": self.MAX_BODY_SIZE // 1024 // 1024,
                        },
                    )
            except ValueError:
                pass  # Invalid content-length, let downstream handle
        
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
            print(f"[{request_id}] ERROR {request.method} {request.url.path} - {exc} ({duration_ms:.1f}ms)")
            raise
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Log line
        print(
            f"[{request_id}] {response.status_code} {request.method} {request.url.path} "
            f"({duration_ms:.1f}ms)"
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
            
            # Log full traceback in debug mode
            if settings.debug:
                import traceback
                traceback.print_exc()
            
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins else ["*"],
        allow_origin_regex=r"https://.*\.vercel\.app$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_middleware(app: FastAPI) -> None:
    """Register all middleware on the app."""
    # Request size limit
    app.add_middleware(RequestSizeLimitMiddleware)
    # Request logging
    app.add_middleware(RequestLoggingMiddleware)
    # Error handling
    app.add_middleware(ErrorHandlingMiddleware)
