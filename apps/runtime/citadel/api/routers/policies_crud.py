from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from citadel.api.dependencies import require_api_key
from citadel.services.policy_controls import (
    ApprovalThresholdControl,
    NoCodePolicyControlService,
    preview_approval_threshold_policy,
)

router = APIRouter(tags=["policies"])


class PolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str = Field("", max_length=2048)
    framework: str = Field("SOC2", pattern=r"^(SOC2|ISO27001|NIST|GDPR|HIPAA|PCI_DSS|CUSTOM)$")
    severity: str = Field("medium", pattern=r"^(low|medium|high|critical)$")


class PolicyPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = Field(None, max_length=2048)
    framework: str | None = Field(None, pattern=r"^(SOC2|ISO27001|NIST|GDPR|HIPAA|PCI_DSS|CUSTOM)$")
    severity: str | None = Field(None, pattern=r"^(low|medium|high|critical)$")
    status: str | None = Field(None, pattern=r"^(active|disabled|draft|toggle)$")


class ApprovalThresholdRequest(BaseModel):
    risk_score_threshold: int = Field(..., ge=0, le=100)
    approval_priority: str = Field("high", pattern=r"^(low|medium|high|critical)$")
    approval_expiry_hours: int = Field(24, ge=1, le=168)
    reason: str | None = Field(None, max_length=512)


@router.get("/policies")
async def list_policies(request: Request, _: str = Depends(require_api_key)):
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    async with request.app.state.db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM governance_policies WHERE tenant_id = $1 ORDER BY created_at",
            tenant_id,
        )
    return {"policies": [dict(r) for r in rows]}


@router.get("/policies/no-code/approval-threshold")
async def get_approval_threshold_policy(request: Request, _: str = Depends(require_api_key)):
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    service = NoCodePolicyControlService(request.app.state.db_pool)
    policy = await service.get_active_approval_threshold(tenant_id)
    return {"policy": policy}


@router.post("/policies/no-code/approval-threshold/preview")
async def preview_approval_threshold(
    body: ApprovalThresholdRequest,
    request: Request,
    _: str = Depends(require_api_key),
):
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    control = ApprovalThresholdControl(**body.model_dump())
    try:
        policy = preview_approval_threshold_policy(control, tenant_id=tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"policy": policy}


@router.post("/policies/no-code/approval-threshold")
async def apply_approval_threshold(
    body: ApprovalThresholdRequest,
    request: Request,
    _: str = Depends(require_api_key),
):
    tenant_id = getattr(request.state, "tenant_id", "dev_tenant")
    created_by = getattr(request.state, "user_id", None) or "api_key"
    control = ApprovalThresholdControl(**body.model_dump())
    service = NoCodePolicyControlService(request.app.state.db_pool)
    try:
        policy = await service.apply_approval_threshold(
            tenant_id,
            control,
            created_by=created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"policy": policy}


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
