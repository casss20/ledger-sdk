from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import hashlib
import secrets

router = APIRouter(tags=["agents"])


class AgentCreate(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_\-\.]+$")
    name: str = Field(..., min_length=1, max_length=256)
    status: str = Field("healthy", pattern=r"^(healthy|unhealthy|inactive|quarantined)$")
    health_score: int = Field(100, ge=0, le=100)
    token_spend: int = Field(0, ge=0)
    token_budget: int = Field(100000, ge=1, le=1_000_000_000)
    actions_today: int = Field(0, ge=0)
    owner: str = Field("op-1", min_length=1, max_length=128)
    quarantined: bool = False
    compliance: List[str] = []


class AgentPatch(BaseModel):
    health_score: Optional[int] = Field(None, ge=0, le=100)
    status: Optional[str] = Field(None, pattern=r"^(healthy|unhealthy|inactive|quarantined)$")
    actions_today: Optional[int] = Field(None, ge=0)
    token_spend: Optional[int] = Field(None, ge=0)
    token_budget: Optional[int] = Field(None, ge=1, le=1_000_000_000)


class AgentTrustScoreResponse(BaseModel):
    """Trust score response (computed from agent + identity tables)."""
    agent_id: str
    trust_score: float
    trust_level: str
    factors: Dict[str, Any]


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


# ============================================================================
# Agent Identity Trust Score (reads from agent_identity module)
# ============================================================================

@router.get("/agents/{agent_id}/trust", response_model=AgentTrustScoreResponse)
async def get_agent_trust_score(agent_id: str, request: Request):
    """
    Get the current trust score for an agent.
    
    This endpoint reads from the agent_identities table maintained by the
    agent_identity module. It provides a lightweight read-only view for
    dashboard and agent listings.
    """
    from citadel.agent_identity.trust_score import TrustScorer, TrustLevel
    
    async with request.app.state.db_pool.acquire() as conn:
        identity = await conn.fetchrow(
            """
            SELECT id, trust_score, trust_level, verified, created_at, updated_at,
                   failed_challenges, challenge_count
            FROM agent_identities
            WHERE agent_id = $1 AND revoked = FALSE
            """,
            agent_id,
        )
        if not identity:
            raise HTTPException(status_code=404, detail="Agent identity not found")
        
        agent = await conn.fetchrow(
            "SELECT health_score, quarantined, actions_today, token_spend, token_budget, compliance, created_at "
            "FROM agents WHERE agent_id = $1",
            agent_id,
        )
        
        scorer = TrustScorer()
        score, level, factors = scorer.compute_score(
            verified=identity["verified"],
            health_score=agent["health_score"] if agent else 100,
            quarantined=agent["quarantined"] if agent else False,
            actions_today=agent["actions_today"] if agent else 0,
            token_spend=agent["token_spend"] if agent else 0,
            token_budget=agent["token_budget"] if agent else 100000,
            compliance_tags=agent["compliance"] if agent else [],
            created_at=identity["created_at"],
            failed_challenges=identity["failed_challenges"] or 0,
            challenge_count=identity["challenge_count"] or 0,
        )
    
    return AgentTrustScoreResponse(
        agent_id=agent_id,
        trust_score=score,
        trust_level=level.value,
        factors=factors,
    )
