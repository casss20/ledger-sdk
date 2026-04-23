"""
Ledger API - Production HTTP surface over the governance kernel.

Structure:
- App factory with lifespan management
- Router-based organization
- Middleware for logging, errors, auth
- Prometheus metrics

Run: uvicorn ledger.api:app --reload
     uvicorn ledger.api:app --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from ledger.config import settings
from ledger.api.middleware import setup_middleware
from ledger.api.routers import actions, approvals, audit, governance, health, metrics, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    # Startup
    import asyncpg
    from ledger.api.dependencies import _pool
    
    _pool = await asyncpg.create_pool(
        settings.database_dsn,
        min_size=settings.db_min_size,
        max_size=settings.db_max_size,
    )
    app.state.db_pool = _pool
    
    yield
    
    # Shutdown
    if _pool:
        await _pool.close()


def create_app() -> FastAPI:
    """Factory: Create configured FastAPI application."""
    app = FastAPI(
        title="Ledger Governance API",
        description="Production API for the Ledger governance kernel. "
                    "Enforces kill switches, capabilities, policies, approvals, and audit.",
        version=settings.app_version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )
    
    from ledger.middleware.fastapi_middleware import setup_tenant_middleware
    from ledger.middleware.auth_middleware import AuthMiddleware, setup_auth_endpoints
    from ledger.auth.jwt_token import JWTService
    from ledger.auth.api_key import APIKeyService
    
    # Middleware: logging, errors, CORS, request IDs
    setup_middleware(app)
    
    # Setup Auth services
    # Mocking cache with a simple dict for this integration 
    class AppCache:
        def __init__(self):
            self.store = {}
        async def set(self, k, v, ttl=None): self.store[k] = v
        async def get(self, k): return self.store.get(k)
        async def delete(self, k): self.store.pop(k, None)
    
    app.state.cache = AppCache()
    jwt_service = JWTService(secret_key="secret_key_change_me_in_prod")
    api_key_service = APIKeyService(db_pool=_pool, cache=app.state.cache)
    
    # Add AuthMiddleware before TenantContextMiddleware
    app.add_middleware(
        AuthMiddleware, 
        jwt_service=jwt_service, 
        api_key_service=api_key_service
    )
    
    # Tenant context middleware (must run AFTER ErrorHandlingMiddleware but BEFORE routers)
    setup_tenant_middleware(app)
    
    # Auth endpoints
    setup_auth_endpoints(app, jwt_service, api_key_service)
    
    # Routers
    app.include_router(actions.router, prefix="/v1")
    app.include_router(approvals.router, prefix="/v1")
    app.include_router(audit.router, prefix="/v1")
    app.include_router(governance.router, prefix="/v1")
    app.include_router(health.router, prefix="/v1")
    app.include_router(metrics.router, prefix="/v1")
    app.include_router(dashboard.router, prefix="/api")
    
    # Prometheus metrics (raw ASGI app at root /metrics)
    if settings.metrics_enabled:
        metrics_app = make_asgi_app()
        app.mount(settings.metrics_endpoint, metrics_app)
    
    return app


# Default app instance
app = create_app()
