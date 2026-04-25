from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["policies"])


class PolicyCreate(BaseModel):
    name: str
    description: str = ""
    framework: str = "SOC2"
    severity: str = "medium"


class PolicyPatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    framework: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None


@router.get("/policies")
async def list_policies(request: Request):
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    async with request.app.state.db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM governance_policies WHERE tenant_id = $1 ORDER BY created_at",
            tenant_id,
        )
    return {"policies": [dict(r) for r in rows]}


@router.post("/policies")
async def create_policy(body: PolicyCreate, request: Request):
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    async with request.app.state.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO governance_policies (tenant_id, name, description, framework, severity)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            tenant_id,
            body.name,
            body.description,
            body.framework,
            body.severity,
        )
    return dict(row)


@router.patch("/policies/{policy_id}")
async def patch_policy(policy_id: str, body: PolicyPatch, request: Request):
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Toggle status convenience: if only status is provided and value is 'toggle',
    # flip active<->disabled
    if updates.get("status") == "toggle":
        async with request.app.state.db_pool.acquire() as conn:
            current = await conn.fetchrow(
                "SELECT status FROM governance_policies WHERE policy_id = $1 AND tenant_id = $2",
                policy_id,
                tenant_id,
            )
            if not current:
                raise HTTPException(status_code=404, detail="Policy not found")
            new_status = "disabled" if current["status"] == "active" else "active"
            row = await conn.fetchrow(
                """
                UPDATE governance_policies
                SET status = $1, updated_at = NOW()
                WHERE policy_id = $2 AND tenant_id = $3
                RETURNING *
                """,
                new_status,
                policy_id,
                tenant_id,
            )
        return dict(row)

    set_clauses = ", ".join(
        f"{col} = ${i + 2}" for i, col in enumerate(updates.keys())
    )
    set_clauses += ", updated_at = NOW()"
    values = list(updates.values())

    async with request.app.state.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            UPDATE governance_policies
            SET {set_clauses}
            WHERE policy_id = $1 AND tenant_id = ${len(values) + 2}
            RETURNING *
            """,
            policy_id,
            *values,
            tenant_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Policy not found")
    return dict(row)


@router.delete("/policies/{policy_id}")
async def delete_policy(policy_id: str, request: Request):
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    async with request.app.state.db_pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM governance_policies WHERE policy_id = $1 AND tenant_id = $2",
            policy_id,
            tenant_id,
        )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"deleted": policy_id}
