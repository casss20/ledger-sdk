from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from citadel.api.dependencies import require_api_key

router = APIRouter(tags=["policies"])


class PolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str = Field("", max_length=2048)
    framework: str = Field("SOC2", pattern=r"^(SOC2|ISO27001|NIST|GDPR|HIPAA|PCI_DSS|CUSTOM)$")
    severity: str = Field("medium", pattern=r"^(low|medium|high|critical)$")


class PolicyPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    description: Optional[str] = Field(None, max_length=2048)
    framework: Optional[str] = Field(None, pattern=r"^(SOC2|ISO27001|NIST|GDPR|HIPAA|PCI_DSS|CUSTOM)$")
    severity: Optional[str] = Field(None, pattern=r"^(low|medium|high|critical)$")
    status: Optional[str] = Field(None, pattern=r"^(active|disabled|draft|toggle)$")


@router.get("/policies")
async def list_policies(request: Request, _: str = Depends(require_api_key)):
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    async with request.app.state.db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM governance_policies WHERE tenant_id = $1 ORDER BY created_at",
            tenant_id,
        )
    return {"policies": [dict(r) for r in rows]}


@router.post("/policies")
async def create_policy(body: PolicyCreate, request: Request, _: str = Depends(require_api_key)):
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
async def patch_policy(policy_id: str, body: PolicyPatch, request: Request, _: str = Depends(require_api_key)):
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
async def delete_policy(policy_id: str, request: Request, _: str = Depends(require_api_key)):
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
