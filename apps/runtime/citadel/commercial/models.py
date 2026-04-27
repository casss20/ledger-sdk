"""Provider-agnostic commercial data models."""

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass


class BillingStatus(str, Enum):
    """Canonical subscription states — provider-agnostic."""
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"


@dataclass
class TenantEntitlements:
    """Resolved commercial entitlements for a tenant."""
    tenant_id: str
    plan_code: str
    billing_status: BillingStatus
    api_calls_limit: int = 0
    active_agents_limit: int = 0
    approval_requests_limit: int = 0
    audit_retention_days: int = 7
    can_access_api: bool = True
    can_manage_billing: bool = True
    in_grace_period: bool = False
    features: Dict[str, Any] = None

    def __post_init__(self):
        if self.features is None:
            self.features = {}

    def is_allowed(self, feature: str) -> bool:
        """Check if a feature flag is enabled."""
        return self.features.get(feature, False)


@dataclass
class UsageSnapshot:
    """Point-in-time usage metrics for a tenant."""
    api_calls: int = 0
    active_agents: int = 0
    approval_requests: int = 0
    governed_actions: int = 0
    unique_users: int = 0
