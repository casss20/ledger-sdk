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
from ledger.api.routers import actions, approvals, audit, governance, health, metrics


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
    
    # Middleware: logging, errors, CORS, request IDs
    setup_middleware(app)
    
    # Routers
    app.include_router(actions.router, prefix="/v1")
    app.include_router(approvals.router, prefix="/v1")
    app.include_router(audit.router, prefix="/v1")
    app.include_router(governance.router, prefix="/v1")
    app.include_router(health.router, prefix="/v1")
    app.include_router(metrics.router, prefix="/v1")
    
    # Prometheus metrics (raw ASGI app at root /metrics)
    if settings.metrics_enabled:
        metrics_app = make_asgi_app()
        app.mount(settings.metrics_endpoint, metrics_app)
    
    return app


# Default app instance
app = create_app()
