"""
Audit Router

GET /v1/audit/verify - Verify audit chain integrity
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from citadel.execution.kernel import Kernel
from citadel.api.dependencies import get_kernel, require_api_key

router = APIRouter(tags=["audit"])


class AuditVerifyResponse(BaseModel):
    valid: bool
    checked_count: int
    first_event_id: Optional[int] = None
    last_event_id: Optional[int] = None
    broken_at_event_id: Optional[int] = None


@router.get("/audit/verify", response_model=AuditVerifyResponse)
async def verify_audit(
    kernel: Kernel = Depends(get_kernel),
    _: str = Depends(require_api_key),
):
    """Verify the audit chain integrity."""
    result = await kernel.repo.verify_audit_chain()
    
    return AuditVerifyResponse(
        valid=result['valid'],
        checked_count=result['checked_count'],
        first_event_id=result.get('first_event_id'),
        last_event_id=result.get('last_event_id'),
        broken_at_event_id=result.get('broken_at_event_id'),
    )
