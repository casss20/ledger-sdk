"""
Health Router

GET /v1/health         - Basic health
GET /v1/health/ready   - Readiness probe (DB connectivity)
GET /v1/health/live    - Liveness probe (always 200)
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from citadel.api.dependencies import require_api_key

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str


class ReadinessResponse(BaseModel):
    ready: bool
    database: str


@router.get("/health")
async def health_check(request: Request):
    """Basic health check."""
    from citadel.config import settings
    
    pool = getattr(request.app.state, "db_pool", None)
    db_status = "connected" if pool else "disconnected"
    
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        database=db_status,
    )


@router.get("/health/ready")
async def readiness_check(request: Request):
    """Readiness probe: verify database connectivity."""
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        startup_error = getattr(request.app.state, "db_startup_error", None)
        detail = "Database pool not initialized"
        if startup_error:
            detail = f"{detail}: {startup_error}"
        raise HTTPException(status_code=503, detail=detail)
    
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return ReadinessResponse(ready=True, database="connected")
    except (asyncpg.PostgresError, ConnectionError, TimeoutError, OSError) as db_err:
        raise HTTPException(status_code=503, detail=f"Database unreachable: {type(db_err).__name__}")


@router.get("/health/live")
async def liveness_check():
    """Liveness probe: always returns 200 if process is running."""
    return {"alive": True}
