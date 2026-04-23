"""
FastAPI middleware — injects tenant context on every request.

This is the KEY security layer. Without this, RLS doesn't work.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from ledger.middleware.tenant_context import (
    tenant_scope,
    TenantContextError,
)

logger = logging.getLogger(__name__)

class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Injects tenant_id from request header into context.
    
    Every request MUST have X-Tenant-ID header.
    Exceptions:
      - /health (no tenant required)
      - /v1/health (no tenant required)
      - /docs (no tenant required)
      - /openapi.json (no tenant required)
      - /redoc (no tenant required)
      - /metrics (no tenant required)
    """
    
    EXEMPT_PATHS = {
        "/health",
        "/v1/health",
        "/healthz",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/metrics",
    }
    
    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        tenant_id = request.headers.get("X-Tenant-ID")
        
        if not tenant_id or tenant_id.strip() == "":
            logger.error(
                f"Request missing X-Tenant-ID header: {request.url.path}"
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Missing X-Tenant-ID header",
                    "detail": "Every request must include X-Tenant-ID header",
                }
            )
        
        if not self._is_valid_tenant_id(tenant_id):
            logger.error(f"Invalid tenant_id format: {tenant_id}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Invalid X-Tenant-ID format",
                    "detail": "Tenant ID must be alphanumeric + underscore",
                }
            )
        
        user_id = request.headers.get("X-User-ID")
        
        try:
            async with tenant_scope(
                tenant_id=tenant_id,
                user_id=user_id,
            ):
                return await call_next(request)
                    
        except TenantContextError as e:
            logger.error(f"Tenant context error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Tenant context failed",
                    "detail": "Data isolation violated",
                }
            )
        except Exception as e:
            logger.exception(f"Middleware error: {e}")
            raise
    
    def _is_valid_tenant_id(self, tenant_id: str) -> bool:
        """Validate tenant_id format (alphanumeric + underscore + hyphen)"""
        return all(c.isalnum() or c in ('_', '-') for c in tenant_id)

def setup_tenant_middleware(app):
    """Register middleware on FastAPI app"""
    app.add_middleware(TenantContextMiddleware)
    return app
