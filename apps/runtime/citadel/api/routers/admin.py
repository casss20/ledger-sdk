"""
Admin router — governance capacity visibility.

Provides read-only endpoints for operators to assess approval queue capacity
and estimate staffing needs using queueing theory (Little's Law).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from citadel.execution.kernel import Kernel
from citadel.api.dependencies import get_kernel, require_api_key

router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================================
# Response models
# ============================================================================

class CapacityEstimate(BaseModel):
    estimated_approvers_needed: Optional[float]
    current_queue_depth: int
    avg_wait_seconds: float
    avg_service_seconds: float
    throughput_per_hour: int
    arrival_rate_per_hour: int
    utilization_factor: Optional[float]
    recommendation: str
    computed_at: str


class CapacityResponse(BaseModel):
    capacity: CapacityEstimate


# ============================================================================
# Routes
# ============================================================================

@router.get("/capacity", response_model=CapacityResponse)
async def get_admin_capacity(
    kernel: Kernel = Depends(get_kernel),
    authenticated_actor_id: str = Depends(require_api_key),
):
    """
    Estimate approver capacity needs from approval queue metrics.

    Uses Little's Law (L = λW) over the last hour of resolved approvals
    to estimate how many approvers are needed to keep wait times healthy.
    """
    metrics = await kernel.repo.get_approval_queue_metrics(tenant_id=None)

    queue_depth = metrics.get("queue_depth", 0)
    avg_wait = metrics.get("avg_wait_seconds", 0.0)
    avg_service = metrics.get("avg_service_seconds", 0.0)
    throughput = metrics.get("throughput_per_hour", 0)
    arrival_rate = metrics.get("arrival_rate_per_hour", 0)
    load_factor = metrics.get("observed_load_factor")
    computed_at = metrics.get("computed_at", "")

    # Estimate approvers needed: if we know service time and arrival rate,
    # servers_needed = λ * W_s (where W_s = avg service time in hours)
    estimated_approvers = None
    recommendation = "insufficient data"

    if avg_service > 0:
        service_time_hours = avg_service / 3600.0
        if arrival_rate > 0:
            # M/M/c heuristic: c ≈ λ * S (minimum servers to handle load)
            estimated_approvers = round(arrival_rate * service_time_hours, 2)

            if load_factor is not None:
                if load_factor > 2.0:
                    recommendation = "critical backlog — add approvers immediately"
                elif load_factor > 1.0:
                    recommendation = "elevated load — consider adding approvers"
                elif load_factor > 0.7:
                    recommendation = "healthy but monitor closely"
                else:
                    recommendation = "healthy capacity"
            else:
                recommendation = "monitoring — collect more data"
        else:
            recommendation = "no recent arrivals — capacity cannot be estimated"
    else:
        recommendation = "no recent resolutions — capacity cannot be estimated"

    return CapacityResponse(
        capacity=CapacityEstimate(
            estimated_approvers_needed=estimated_approvers,
            current_queue_depth=queue_depth,
            avg_wait_seconds=avg_wait,
            avg_service_seconds=avg_service,
            throughput_per_hour=throughput,
            arrival_rate_per_hour=arrival_rate,
            utilization_factor=load_factor,
            recommendation=recommendation,
            computed_at=computed_at,
        )
    )
