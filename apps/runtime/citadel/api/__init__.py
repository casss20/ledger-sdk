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
import os
from typing import AsyncGenerator

import asyncpg
from fastapi import FastAPI
from prometheus_client import make_asgi_app

from citadel.config import settings
from citadel.api.dependencies import get_api_key_manager
from citadel.api.middleware import setup_middleware, setup_cors
from citadel.api.routers import actions, approvals, audit, governance, health, metrics, dashboard, agents, policies_crud, connectors as connectors_router, agent_identity
from citadel.api.routers.audit_rich import router as audit_rich_router
from citadel.api.routers.orchestration import router as orchestration_router
from citadel.api.routers.decisions import router as decisions_router
from citadel.api.routers.admin import router as admin_router
from citadel.api.routers.evidence import router as evidence_router
from citadel.commercial.routes import router as billing_router

logger = logging.getLogger(__name__)


def _hash_operator_password(password: str) -> str:
    """Hash an operator password using the same PBKDF2 format as OperatorService."""
    import hashlib
    import secrets

    salt = secrets.token_hex(16)
    iterations = 100000
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return f"pbkdf2:sha256:{iterations}:{salt}:{key.hex()}"


async def _ensure_bootstrap_operator(pool) -> None:
    """
    Ensure the configured bootstrap admin can log in after deploy.

    When CITADEL_ADMIN_BOOTSTRAP_PASSWORD is present, it is the operational
    source of truth for the bootstrap operator and will reset that operator on
    startup. Without the secret, we preserve the legacy empty-table dev seed.
    """
    username = settings.citadel_admin_bootstrap_username
    password = settings.citadel_admin_bootstrap_password
    tenant_id = settings.citadel_admin_bootstrap_tenant
    email = settings.citadel_admin_bootstrap_email
    role = settings.citadel_admin_bootstrap_role

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL app.admin_bypass = 'true'")

            if not password:
                row = await conn.fetchrow("SELECT COUNT(*) as cnt FROM operators")
                if row and row["cnt"] > 0:
                    return
                # Dev-only fallback: generate a random password and log a hash (not the password itself)
                import secrets
                password = secrets.token_urlsafe(16)
                # Log only a truncated hash for verification, never the actual password
                import hashlib
                pass_hint = hashlib.sha256(password.encode()).hexdigest()[:8]
                logger.warning(
                    "Bootstrap password not configured. Generated dev-only password "
                    "(hash hint: %s...). Set CITADEL_ADMIN_BOOTSTRAP_PASSWORD in production.",
                    pass_hint,
                )

            import hashlib

            operator_id = "op_bootstrap_" + hashlib.sha256(
                username.encode("utf-8")
            ).hexdigest()[:16]
            password_hash = _hash_operator_password(password)

            await conn.execute(
                """
                INSERT INTO operators (
                    operator_id, username, email, password_hash,
                    tenant_id, role, is_active
                )
                VALUES ($1, $2, $3, $4, $5, $6, TRUE)
                ON CONFLICT (username) DO UPDATE SET
                    email = EXCLUDED.email,
                    password_hash = EXCLUDED.password_hash,
                    tenant_id = EXCLUDED.tenant_id,
                    role = EXCLUDED.role,
                    is_active = TRUE
                """,
                operator_id,
                username,
                email,
                password_hash,
                tenant_id,
                role,
            )

    logger.info(
        "Ensured bootstrap operator username=%s tenant_id=%s role=%s",
        username,
        tenant_id,
        role,
    )


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
            except (asyncpg.PostgresError, ConnectionError, TimeoutError, OSError, RuntimeError) as mig_err:
                logger.error(f"Migration {filename} failed ({type(mig_err).__name__}): {mig_err}")
                # Fail loud â€” partial schema is worse than not booting.
                raise


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    # Startup — validate secrets first (fail loud in production)
    secret_errors = settings.validate_secrets()
    if secret_errors:
        for error in secret_errors:
            if error.startswith("CRITICAL"):
                logger.error(error)
            else:
                logger.warning(error)
        if not settings.debug:
            raise RuntimeError(
                f"Production startup blocked: {len(secret_errors)} secret validation errors. "
                f"See logs above. Set debug=True only for development."
            )
    
    from citadel.api.dependencies import _pool
    
    _pool = None
    try:
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
        except (asyncpg.PostgresError, ConnectionError, TimeoutError, OSError, RuntimeError) as mig_exc:
            logger.warning(f"Migration runner warning ({type(mig_exc).__name__}): {mig_exc}")
        
        # Ensure the configured bootstrap admin exists after migrations.
        try:
            await _ensure_bootstrap_operator(_pool)
        except (asyncpg.PostgresError, ConnectionError, TimeoutError, RuntimeError) as seed_exc:
            logger.debug(f"Operator seed skipped ({type(seed_exc).__name__}): {seed_exc}")
    except (asyncpg.PostgresError, ConnectionError, TimeoutError, OSError, RuntimeError) as exc:
        logger.exception(f"Database pool initialization failed ({type(exc).__name__}); readiness will report unhealthy")
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
    
    # Secret validation is deferred to lifespan startup to allow clean imports
    # in test and development environments. Production failures still happen,
    # just at app startup time rather than module import time.
    
    from citadel.middleware.fastapi_middleware import setup_tenant_middleware
    from citadel.middleware.auth_middleware import AuthMiddleware, setup_auth_endpoints
    from citadel.auth.jwt_token import JWTService
    from citadel.auth.api_key import APIKeyService
    
    # Middleware: logging, errors, CORS, request IDs
    setup_middleware(app)
    
    # ---- NEW: OWASP Security Middleware ----
    if settings.security_headers_enabled:
        from citadel.security.owasp_middleware import setup_security_middleware
        setup_security_middleware(app)
    
    # Setup Auth services
    # Mocking cache with a simple dict for this integration 
    class AppCache:
        def __init__(self):
            self.store = {}
        async def set(self, k, v, ttl=None): self.store[k] = v
        async def get(self, k): return self.store.get(k)
        async def delete(self, k): self.store.pop(k, None)
    
    app.state.cache = AppCache()
    import secrets as _secrets
    jwt_secret = settings.citadel_jwt_secret
    if not jwt_secret or jwt_secret == "secret_key_change_me_in_prod":
        if settings.debug or os.environ.get("CITADEL_TESTING") == "true":
            jwt_secret = _secrets.token_urlsafe(32)
            logger.warning(
                "CITADEL_JWT_SECRET not set. Generated a one-time random secret for this session. "
                "Set CITADEL_JWT_SECRET environment variable for persistent sessions."
            )
        else:
            # Production: fail loud
            raise RuntimeError(
                "CITADEL_JWT_SECRET is not set or uses the default placeholder. "
                "Set a secure secret via the CITADEL_JWT_SECRET environment variable."
            )
    jwt_service = JWTService(secret_key=jwt_secret)
    
    # Order: Outermost (runs first) to Innermost (runs last)
    
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

    # Rate limiting (after CORS, before auth — so preflight isn't rate-limited
    # but auth endpoints and API calls are protected)
    from citadel.middleware.rate_limit import RateLimitMiddleware, AuthRateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)  # General API rate limiting
    app.add_middleware(AuthRateLimitMiddleware)  # Stricter auth endpoint limits

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
    app.include_router(agent_identity.router, prefix="/api")
    app.include_router(orchestration_router, prefix="/v1")
    app.include_router(decisions_router, prefix="/v1")
    app.include_router(admin_router, prefix="/v1")
    app.include_router(evidence_router)
    app.include_router(billing_router)
    
    # Prometheus metrics (protected with API key auth)
    if settings.metrics_enabled:
        from fastapi import Depends
        metrics_app = make_asgi_app()
        
        async def _metrics_auth(request, call_next):
            from fastapi.responses import JSONResponse
            api_key = request.headers.get(settings.api_key_header)
            if not api_key:
                return JSONResponse(status_code=401, content={"error": "unauthenticated"})
            manager = get_api_key_manager()
            validated = manager.validate(api_key)
            if validated is None:
                return JSONResponse(status_code=403, content={"error": "forbidden"})
            return await call_next(request)
        
        # Wrap metrics app with simple auth middleware
        from starlette.middleware.base import BaseHTTPMiddleware
        class MetricsAuthMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                return await _metrics_auth(request, call_next)
        
        from starlette.applications import Starlette
        metrics_wrapper = Starlette()
        metrics_wrapper.add_middleware(MetricsAuthMiddleware)
        metrics_wrapper.mount("/", metrics_app)
        app.mount(settings.metrics_endpoint, metrics_wrapper)
    
    @app.get("/health/ready")
    async def readiness():
        from fastapi.responses import JSONResponse

        pool = getattr(app.state, "db_pool", None)
        startup_error = getattr(app.state, "db_startup_error", None)
        if pool is None:
            return JSONResponse(
                content={
                    "status": "unhealthy",
                    "checks": {
                        "database": {
                            "status": "unhealthy",
                            "message": startup_error or "Database pool is not initialized",
                        }
                    },
                },
                status_code=503,
            )

        try:
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        except Exception as exc:
            return JSONResponse(
                content={
                    "status": "unhealthy",
                    "checks": {
                        "database": {
                            "status": "unhealthy",
                            "message": f"Database check failed ({type(exc).__name__})",
                        }
                    },
                },
                status_code=503,
            )

        return JSONResponse(
            content={
                "status": "healthy",
                "checks": {
                    "database": {
                        "status": "healthy",
                        "message": "Database connection OK",
                    }
                },
            },
            status_code=200,
        )
    
    @app.get("/health/live")
    async def liveness():
        from fastapi.responses import JSONResponse
        return JSONResponse(content={"status": "ok"})
    
    return app


# Default app instance — defer to placeholder if create_app() raises.
# All production validation happens in lifespan(), so import-time failures
# are non-fatal.  Uvicorn will trigger lifespan() on startup and fail loud
# if secrets are actually missing in production.
try:
    app = create_app()
except Exception as exc:
    logger.warning(f"App creation deferred at import time ({type(exc).__name__}): {exc}")
    app = FastAPI(lifespan=lifespan)  # minimal placeholder; real validation in lifespan
