"""Canonical action models for the governance engine.

Both API requests and orchestrator plans use these models.
This is the single source of truth for action data structures.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class KernelStatus(Enum):
    """Terminal decision statuses matching the database schema."""
    BLOCKED_SCHEMA = "BLOCKED_SCHEMA"
    BLOCKED_EMERGENCY = "BLOCKED_EMERGENCY"
    BLOCKED_CAPABILITY = "BLOCKED_CAPABILITY"
    BLOCKED_POLICY = "BLOCKED_POLICY"
    RATE_LIMITED = "RATE_LIMITED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    REJECTED_APPROVAL = "REJECTED_APPROVAL"
    EXPIRED_APPROVAL = "EXPIRED_APPROVAL"
    ALLOWED = "ALLOWED"
    EXECUTED = "EXECUTED"
    FAILED_EXECUTION = "FAILED_EXECUTION"
    FAILED_AUDIT = "FAILED_AUDIT"


@dataclass
class Action:
    """Canonical action request.

    Used by:
    - API layer (incoming requests)
    - Orchestrator (planned actions)
    - Kernel (governance pipeline)
    - Repository (persistence)
    """
    action_id: uuid.UUID
    actor_id: str
    actor_type: str
    action_name: str
    resource: str
    tenant_id: Optional[str]
    payload: Dict[str, Any]
    context: Dict[str, Any]
    session_id: Optional[str]
    request_id: Optional[str]
    idempotency_key: Optional[str]
    created_at: datetime


@dataclass
class Decision:
    """Terminal decision for an action."""
    decision_id: uuid.UUID
    action_id: uuid.UUID
    status: KernelStatus
    winning_rule: str
    reason: str
    policy_snapshot_id: Optional[uuid.UUID]
    capability_token: Optional[str]
    risk_level: Optional[str]
    risk_score: Optional[int]
    path_taken: Optional[str]
    created_at: datetime


@dataclass
class KernelResult:
    """Result of kernel handling an action."""
    action: Action
    decision: Decision
    executed: bool
    result: Optional[Any]
    error: Optional[str]


__all__ = [
    "KernelStatus",
    "Action",
    "Decision",
    "KernelResult",
]
