from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class BillingStatus(str, Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"

class TenantEntitlements(BaseModel):
    tenant_id: str
    plan_code: str
    billing_status: BillingStatus
    api_calls_limit: Optional[int] = None
    active_agents_limit: Optional[int] = None
    approval_requests_limit: Optional[int] = None
    audit_retention_days: Optional[int] = None
    features: Dict[str, Any] = Field(default_factory=dict)
    current_period_end: Optional[datetime] = None
    in_grace_period: bool = False
    can_access_api: bool = True
    can_manage_billing: bool = True

class UsageSnapshot(BaseModel):
    api_calls: int = 0
    active_agents: int = 0
    approval_requests: int = 0
    governed_actions: int = 0
    unique_users: int = 0
