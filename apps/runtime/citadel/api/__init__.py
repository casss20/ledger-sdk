"""
Citadel API - Production HTTP surface over the governance kernel.

Structure:
- App factory with lifespan management
- Router-based organization
- Middleware for logging, errors, auth
- Prometheus metrics

Run: uvicorn citadel.api:app --reload
     uvicorn citadel.api:app --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from citadel.config import settings
from citadel.api.middleware import setup_middleware
from citadel.api.routers import actions, approvals, audit, governance, health, metrics, dashboard
from citadel.billing.routes import router as billing_router
from citadel.billing.middleware import BillingMiddleware
from citadel.utils.telemetry import setup_telemetry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    # Startup
    from citadel.api.dependencies import _pool
    
    _pool = None
    try:
        import asyncpg

        _pool = await asyncpg.create_pool(
            settings.database_dsn,
            min_size=settings.db_min_size,
            max_size=settings.db_max_size,
        )
        app.state.db_pool = _pool
        app.state.db_startup_error = None
        
        # Seed default admin if operators table exists and is empty
        try:
            async with _pool.acquire() as conn:
                row = await conn.fetchrow("SELECT COUNT(*) as cnt FROM operators")
                if row and row['cnt'] == 0:
                    import hashlib, secrets
                    salt = secrets.token_hex(16)
                    iterations = 100000
                    key = hashlib.pbkdf2_hmac('sha256', b'admin123', salt.encode(), iterations)
                    password_hash = f"pbkdf2:sha256:{iterations}:{salt}:{key.hex()}"
                    await conn.execute("""
                        INSERT INTO operators (operator_id, username, email, password_hash, tenant_id, role, is_active)
                        VALUES ($1, $2, $3, $4, $5, $6, TRUE)
                        ON CONFLICT (username) DO NOTHING
                    """, "op_admin_default", "admin", "admin@citadel.dev", password_hash, "demo-tenant", "admin")
                    logger.info("Seeded default admin operator (admin / admin123)")
        except Exception as seed_exc:
            # Table might not exist yet (migrations not run)
            logger.debug(f"Operator seed skipped: {seed_exc}")
    except Exception as exc:
        logger.exception("Database pool initialization failed; readiness will report unhealthy")
        app.state.db_pool = None
        app.state.db_startup_error = str(exc)
    
    yield
    
    # Shutdown
    if _pool:
        await _pool.close()


def create_app() -> FastAPI:
    """Factory: Create configured FastAPI application."""
    app = FastAPI(
        title="Citadel Governance API",
        description="Production API for the Citadel governance kernel. "
                    "Enforces kill switches, capabilities, policies, approvals, and audit.",
        version=settings.app_version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )
    
    # Initialize OpenTelemetry
    setup_telemetry(service_name="citadel-api")
    
    from citadel.middleware.fastapi_middleware import setup_tenant_middleware
    from citadel.middleware.auth_middleware import AuthMiddleware, setup_auth_endpoints
    from citadel.auth.jwt_token import JWTService
    from citadel.auth.api_key import APIKeyService
    
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
    
    # Order: Outermost (runs first) to Innermost (runs last)
    
    # 3. Billing enforcement (depends on Auth)
    app.add_middleware(BillingMiddleware)
    
    # 2. Tenant context (sets up scoped context)
    setup_tenant_middleware(app)
    
    # 1. Auth (identifies user and sets tenant_id)
    app.add_middleware(
        AuthMiddleware, 
        jwt_service=jwt_service
    )
    
    # Auth endpoints
    setup_auth_endpoints(app, jwt_service)
    
    # Routers
    app.include_router(actions.router, prefix="/v1")
    app.include_router(approvals.router, prefix="/v1")
    app.include_router(audit.router, prefix="/v1")
    app.include_router(governance.router, prefix="/v1")
    app.include_router(health.router, prefix="/v1")
    app.include_router(metrics.router, prefix="/v1")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(billing_router)
    
    # Prometheus metrics (raw ASGI app at root /metrics)
    if settings.metrics_enabled:
        metrics_app = make_asgi_app()
        app.mount(settings.metrics_endpoint, metrics_app)
    
    return app


# Default app instance
app = create_app()
