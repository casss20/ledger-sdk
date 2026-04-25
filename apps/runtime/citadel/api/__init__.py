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
from citadel.api.middleware import setup_middleware, setup_cors
from citadel.api.routers import actions, approvals, audit, governance, health, metrics, dashboard, agents, policies_crud, connectors as connectors_router
from citadel.api.routers.audit_rich import router as audit_rich_router
from citadel.billing.routes import router as billing_router
from citadel.billing.middleware import BillingMiddleware
from citadel.utils.telemetry import setup_telemetry

logger = logging.getLogger(__name__)


async def _run_migrations(pool):
    """Run SQL migrations on startup."""
    import os
    import glob
    
    migrations_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "db", "migrations")
    if not os.path.exists(migrations_dir):
        migrations_dir = "/app/db/migrations"
    
    if not os.path.exists(migrations_dir):
        logger.warning(f"Migrations directory not found: {migrations_dir}")
        return
    
    migration_files = sorted(glob.glob(os.path.join(migrations_dir, "*.sql")))
    
    async with pool.acquire() as conn:
        # Create migrations tracking table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        
        for filepath in migration_files:
            filename = os.path.basename(filepath)
            already_applied = await conn.fetchval(
                "SELECT 1 FROM _migrations WHERE filename = $1", filename
            )
            if already_applied:
                continue
            
            with open(filepath, "r") as f:
                sql = f.read()
            
            try:
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO _migrations (filename) VALUES ($1)", filename
                )
                logger.info(f"Applied migration: {filename}")
            except Exception as e:
                logger.error(f"Migration {filename} failed: {e}")
                # Fail loud — partial schema is worse than not booting.
                raise


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
        
        # Run migrations on startup
        try:
            await _run_migrations(_pool)
        except Exception as mig_exc:
            logger.warning(f"Migration runner warning: {mig_exc}")
        
        # Seed default admin only when an explicit bootstrap password is provided.
        # We never auto-create admin/admin123 anymore.
        try:
            import os as _os
            bootstrap_pw = _os.environ.get("CITADEL_ADMIN_BOOTSTRAP_PASSWORD")
            bootstrap_user = _os.environ.get("CITADEL_ADMIN_BOOTSTRAP_USERNAME", "admin")
            bootstrap_tenant = _os.environ.get("CITADEL_ADMIN_BOOTSTRAP_TENANT", "demo-tenant")
            if not bootstrap_pw:
                logger.info("Operator seed skipped (CITADEL_ADMIN_BOOTSTRAP_PASSWORD not set).")
            else:
                async with _pool.acquire() as conn:
                    row = await conn.fetchrow("SELECT COUNT(*) as cnt FROM operators")
                    if row and row['cnt'] == 0:
                        import hashlib, secrets
                        salt = secrets.token_hex(16)
                        iterations = 100000
                        key = hashlib.pbkdf2_hmac('sha256', bootstrap_pw.encode(), salt.encode(), iterations)
                        password_hash = f"pbkdf2:sha256:{iterations}:{salt}:{key.hex()}"
                        await conn.execute("""
                            INSERT INTO operators (operator_id, username, email, password_hash, tenant_id, role, is_active)
                            VALUES ($1, $2, $3, $4, $5, $6, TRUE)
                            ON CONFLICT (username) DO NOTHING
                        """, "op_admin_default", bootstrap_user, f"{bootstrap_user}@citadel.local", password_hash, bootstrap_tenant, "admin")
                        logger.info(f"Bootstrapped admin operator '{bootstrap_user}' for tenant '{bootstrap_tenant}'.")
        except Exception as seed_exc:
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
    import os as _os
    _jwt_secret = _os.environ.get("CITADEL_JWT_SECRET")
    if not _jwt_secret:
        if getattr(settings, "debug", False):
            _jwt_secret = "DEV_ONLY_DO_NOT_USE_IN_PROD"
            logger.warning("CITADEL_JWT_SECRET not set — using dev-only key. DO NOT deploy this way.")
        else:
            raise RuntimeError("CITADEL_JWT_SECRET environment variable must be set in production.")
    jwt_service = JWTService(secret_key=_jwt_secret)
    
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

    # CORS must be outermost — added last so it runs before auth on preflight
    setup_cors(app)

    # Routers
    app.include_router(actions.router, prefix="/v1")
    app.include_router(approvals.router, prefix="/v1")
    app.include_router(audit.router, prefix="/v1")
    app.include_router(governance.router, prefix="/v1")
    app.include_router(health.router, prefix="/v1")
    app.include_router(metrics.router, prefix="/v1")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(agents.router, prefix="/api")
    app.include_router(policies_crud.router, prefix="/api")
    app.include_router(connectors_router.router, prefix="/api")
    app.include_router(audit_rich_router, prefix="/api")
    app.include_router(billing_router)
    
    # Prometheus metrics (raw ASGI app at root /metrics)
    if settings.metrics_enabled:
        metrics_app = make_asgi_app()
        app.mount(settings.metrics_endpoint, metrics_app)
    
    return app


# Default app instance
app = create_app()
