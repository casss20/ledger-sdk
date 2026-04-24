"""Middleware package for Citadel SDK."""

from .auth_middleware import AuthMiddleware, setup_auth_endpoints
from .fastapi_middleware import TenantContextMiddleware, setup_tenant_middleware
from .tenant_context import (
    tenant_scope,
    TenantContext,
    TenantContextError,
    get_tenant_context,
    get_tenant_id,
    is_admin_context,
    TenantAwarePool,
    AdminBypassContext,
    set_db_tenant_context,
)
from .rate_limit import RateLimitMiddleware, AuthRateLimitMiddleware

__all__ = [
    "AuthMiddleware",
    "setup_auth_endpoints",
    "TenantContextMiddleware",
    "setup_tenant_middleware",
    "tenant_scope",
    "TenantContext",
    "TenantContextError",
    "get_tenant_context",
    "get_tenant_id",
    "is_admin_context",
    "TenantAwarePool",
    "AdminBypassContext",
    "set_db_tenant_context",
    "RateLimitMiddleware",
    "AuthRateLimitMiddleware",
]
