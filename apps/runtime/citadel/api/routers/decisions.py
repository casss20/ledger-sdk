"""
Decisions router — lineage / provenance query API.

Provides read-only endpoints for tracing decision ancestry and workflow trees.
All endpoints respect tenant isolation via RLS (enforced in repository layer).
"""

from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from citadel.api.dependencies import get_kernel, require_api_key
from citadel.execution.kernel import Kernel

router = APIRouter(prefix="/decisions", tags=["decisions"])


# ============================================================================
# Response models
# ============================================================================

class LineageNode(BaseModel):
    decision_id: uuid.UUID
    action_id: uuid.UUID
    parent_decision_id: Optional[uuid.UUID] = None
    root_decision_id: Optional[uuid.UUID] = None
    trace_id: Optional[str] = None
    workflow_id: Optional[str] = None
    status: str
    winning_rule: str
    reason: str
    risk_level: Optional[str] = None
    risk_score: Optional[int] = None
    created_at: str
    depth_level: int


class LineageResponse(BaseModel):
    decision_id: uuid.UUID
    depth_requested: int
    nodes: List[LineageNode]
    node_count: int


class WorkflowTreeResponse(BaseModel):
    workflow_id: str
    nodes: List[LineageNode]
    node_count: int


# ============================================================================
# Dependencies
# ============================================================================

async def _get_tenant_id(kernel: Kernel) -> Optional[str]:
    """Extract tenant_id from kernel context if available."""
    # The kernel or its repository may have tenant context set by middleware.
    # For now, rely on repository-level filtering (tenant_id passed explicitly).
    return None


# ============================================================================
# Routes
# ============================================================================

@router.get(
    "/{decision_id}/lineage",
    response_model=LineageResponse,
    summary="Get decision lineage (ancestors)",
    description="Return the ancestor chain for a decision up to `depth` levels using recursive CTE over parent_decision_id.",
)
async def get_decision_lineage(
    decision_id: uuid.UUID,
    depth: int = Query(default=5, ge=1, le=20, description="Maximum ancestor levels to traverse"),
    kernel: Kernel = Depends(get_kernel),
    authenticated_actor_id: str = Depends(require_api_key),
):
    """Return ancestor chain for a decision."""
    nodes = await kernel.repo.get_decision_lineage(
        decision_id=decision_id,
        depth=depth,
        tenant_id=None,  # RLS enforced at DB layer via repository CTE EXISTS clause
    )

    if not nodes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found or access denied",
        )

    return LineageResponse(
        decision_id=decision_id,
        depth_requested=depth,
        nodes=[LineageNode(**n) for n in nodes],
        node_count=len(nodes),
    )


@router.get(
    "/{decision_id}/descendants",
    response_model=LineageResponse,
    summary="Get decision descendants",
    description="Return the descendant chain for a decision down to `depth` levels using recursive CTE.",
)
async def get_decision_descendants(
    decision_id: uuid.UUID,
    depth: int = Query(default=5, ge=1, le=20, description="Maximum descendant levels to traverse"),
    kernel: Kernel = Depends(get_kernel),
    authenticated_actor_id: str = Depends(require_api_key),
):
    """Return descendant chain for a decision."""
    nodes = await kernel.repo.get_decision_descendants(
        decision_id=decision_id,
        depth=depth,
        tenant_id=None,
    )

    if not nodes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found or access denied",
        )

    return LineageResponse(
        decision_id=decision_id,
        depth_requested=depth,
        nodes=[LineageNode(**n) for n in nodes],
        node_count=len(nodes),
    )


@router.get(
    "/workflows/{workflow_id}/tree",
    response_model=WorkflowTreeResponse,
    summary="Get workflow decision tree",
    description="Return all decisions belonging to a workflow, ordered by creation time.",
)
async def get_workflow_tree(
    workflow_id: str,
    kernel: Kernel = Depends(get_kernel),
    authenticated_actor_id: str = Depends(require_api_key),
):
    """Return all decisions in a workflow."""
    nodes = await kernel.repo.get_workflow_tree(
        workflow_id=workflow_id,
        tenant_id=None,
    )

    return WorkflowTreeResponse(
        workflow_id=workflow_id,
        nodes=[LineageNode(**n) for n in nodes],
        node_count=len(nodes),
    )
