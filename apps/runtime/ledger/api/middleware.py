"""
Ledger API Middleware

- Request ID tracing
- Structured logging
- Error handling with request IDs
- CORS
"""

import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from ledger.config import settings


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


def setup_middleware(app: FastAPI) -> None:
    """Register all middleware on the app."""
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Request logging (first = outermost)
    app.add_middleware(RequestLoggingMiddleware)
    
    # Error handling (inner = last resort)
    app.add_middleware(ErrorHandlingMiddleware)
