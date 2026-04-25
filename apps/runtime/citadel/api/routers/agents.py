from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(tags=["agents"])


class AgentCreate(BaseModel):
    agent_id: str
    name: str
    status: str = "healthy"
    health_score: int = 100
    token_spend: int = 0
    token_budget: int = 100000
    actions_today: int = 0
    owner: str = "op-1"
    quarantined: bool = False
    compliance: List[str] = []


class AgentPatch(BaseModel):
    health_score: Optional[int] = None
    status: Optional[str] = None
    actions_today: Optional[int] = None
    token_spend: Optional[int] = None


@router.get("/agents")
async def list_agents(request: Request):
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    async with request.app.state.db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM agents WHERE tenant_id = $1 ORDER BY created_at",
            tenant_id,
        )
    return {"agents": [dict(r) for r in rows]}


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, request: Request):
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    async with request.app.state.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM agents WHERE agent_id = $1 AND tenant_id = $2",
            agent_id,
            tenant_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    return dict(row)


@router.post("/agents")
async def create_agent(body: AgentCreate, request: Request):
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    async with request.app.state.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO agents (agent_id, tenant_id, name, status, health_score,
                token_spend, token_budget, actions_today, owner, quarantined, compliance)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (tenant_id, agent_id) DO NOTHING
            RETURNING *
            """,
            body.agent_id,
            tenant_id,
            body.name,
            body.status,
            body.health_score,
            body.token_spend,
            body.token_budget,
            body.actions_today,
            body.owner,
            body.quarantined,
            body.compliance,
        )
    if not row:
        raise HTTPException(status_code=409, detail="Agent already exists")
    return dict(row)


@router.post("/agents/{agent_id}/quarantine")
async def toggle_quarantine(agent_id: str, request: Request):
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    async with request.app.state.db_pool.acquire() as conn:
        current = await conn.fetchrow(
            "SELECT quarantined FROM agents WHERE agent_id = $1 AND tenant_id = $2",
            agent_id,
            tenant_id,
        )
        if not current:
            raise HTTPException(status_code=404, detail="Agent not found")

        new_quarantined = not current["quarantined"]
        # Zero out actions_today when quarantining
        new_actions_today = 0 if new_quarantined else None

        if new_actions_today is not None:
            row = await conn.fetchrow(
                """
                UPDATE agents
                SET quarantined = $1, actions_today = $2, updated_at = NOW()
                WHERE agent_id = $3 AND tenant_id = $4
                RETURNING *
                """,
                new_quarantined,
                new_actions_today,
                agent_id,
                tenant_id,
            )
        else:
            row = await conn.fetchrow(
                """
                UPDATE agents
                SET quarantined = $1, updated_at = NOW()
                WHERE agent_id = $2 AND tenant_id = $3
                RETURNING *
                """,
                new_quarantined,
                agent_id,
                tenant_id,
            )
    return dict(row)


@router.patch("/agents/{agent_id}")
async def patch_agent(agent_id: str, body: AgentPatch, request: Request):
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clauses = ", ".join(
        f"{col} = ${i + 2}" for i, col in enumerate(updates.keys())
    )
    set_clauses += f", updated_at = NOW()"
    values = list(updates.values())

    async with request.app.state.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            UPDATE agents
            SET {set_clauses}
            WHERE agent_id = $1 AND tenant_id = ${len(values) + 2}
            RETURNING *
            """,
            agent_id,
            *values,
            tenant_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    return dict(row)
