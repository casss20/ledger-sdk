from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["connectors"])


class ConnectBody(BaseModel):
    api_key: Optional[str] = None


@router.get("/connectors")
async def list_connectors(request: Request):
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    async with request.app.state.db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM connectors WHERE tenant_id = $1 ORDER BY connector_id",
            tenant_id,
        )
    return {"connectors": [dict(r) for r in rows]}


@router.post("/connectors/{connector_id}/connect")
async def connect_connector(connector_id: str, body: ConnectBody, request: Request):
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    # Store only the last 4 chars as a hint, never the full key
    hint = None
    if body.api_key:
        hint = f"...{body.api_key[-4:]}" if len(body.api_key) >= 4 else "****"

    async with request.app.state.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE connectors
            SET connected = TRUE, api_key_hint = $1, updated_at = NOW()
            WHERE connector_id = $2 AND tenant_id = $3
            RETURNING *
            """,
            hint,
            connector_id,
            tenant_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Connector not found")
    return dict(row)


@router.post("/connectors/{connector_id}/disconnect")
async def disconnect_connector(connector_id: str, request: Request):
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    async with request.app.state.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE connectors
            SET connected = FALSE, api_key_hint = NULL, updated_at = NOW()
            WHERE connector_id = $1 AND tenant_id = $2
            RETURNING *
            """,
            connector_id,
            tenant_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Connector not found")
    return dict(row)
