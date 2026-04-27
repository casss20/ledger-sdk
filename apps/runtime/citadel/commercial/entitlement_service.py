"""Provider-agnostic entitlement resolution."""

import logging
from typing import Optional
from datetime import datetime, timezone

from .models import BillingStatus, TenantEntitlements
from .interface import CommercialRepository

logger = logging.getLogger(__name__)


class EntitlementService:
    """Resolves a tenant's effective entitlements from plan + overrides."""

    def __init__(self, repo: CommercialRepository):
        self._repo = repo

    async def resolve(self, tenant_id: str) -> TenantEntitlements:
        """Resolve entitlements for a tenant."""
        sub = await self._repo.get_subscription(tenant_id)
        plan_code = sub.get("plan_code") if sub else None
        status_str = sub.get("status") if sub else None

        # Default to free plan when no subscription exists
        if not plan_code:
            plan_code = "free"
            status_str = "active"

        plan = await self._repo.get_plan(plan_code)
        overrides = await self._repo.get_overrides(tenant_id)

        # Resolve status
        status = self._resolve_status(status_str, sub)

        # Build base entitlements from plan
        entitlements = TenantEntitlements(
            tenant_id=tenant_id,
            plan_code=plan_code,
            billing_status=status,
            api_calls_limit=plan.get("api_calls_limit", 0) if plan else 0,
            active_agents_limit=plan.get("active_agents_limit", 0) if plan else 0,
            approval_requests_limit=plan.get("approval_requests_limit", 0) if plan else 0,
            audit_retention_days=plan.get("audit_retention_days", 7) if plan else 7,
            can_access_api=True,
            can_manage_billing=True,
            in_grace_period=False,
            features=self._parse_features(plan),
        )

        # Apply overrides
        for override in overrides:
            self._apply_override(entitlements, override)

        # Determine access based on status
        if status in (BillingStatus.PAST_DUE, BillingStatus.CANCELED, BillingStatus.UNPAID):
            entitlements.can_access_api = False
            entitlements.can_manage_billing = False

            # Grace period exception for past_due
            if status == BillingStatus.PAST_DUE and sub:
                grace_until = sub.get("grace_until")
                if grace_until and isinstance(grace_until, datetime):
                    now = datetime.now(timezone.utc)
                    if grace_until > now:
                        entitlements.can_access_api = True
                        entitlements.in_grace_period = True

        return entitlements

    def _resolve_status(self, status_str: Optional[str], sub: Optional[dict]) -> BillingStatus:
        """Map raw status string to canonical BillingStatus."""
        if not status_str:
            return BillingStatus.ACTIVE
        try:
            return BillingStatus(status_str)
        except ValueError:
            logger.warning("Unknown billing status %r — defaulting to ACTIVE", status_str)
            return BillingStatus.ACTIVE

    def _parse_features(self, plan: Optional[dict]) -> dict:
        """Extract feature flags from plan record."""
        if not plan:
            return {}
        features = plan.get("features_json")
        if isinstance(features, dict):
            return features
        if isinstance(features, str):
            import json
            try:
                return json.loads(features)
            except json.JSONDecodeError:
                return {}
        return {}

    def _apply_override(self, entitlements: TenantEntitlements, override: dict) -> None:
        """Apply a single entitlement override."""
        key = override.get("feature_key")
        value = override.get("value_json")
        if not key:
            return

        # Numeric overrides for limits
        if key == "api_calls_limit" and isinstance(value, (int, float)):
            entitlements.api_calls_limit = int(value)
        elif key == "active_agents_limit" and isinstance(value, (int, float)):
            entitlements.active_agents_limit = int(value)
        elif key == "approval_requests_limit" and isinstance(value, (int, float)):
            entitlements.approval_requests_limit = int(value)
        elif key == "audit_retention_days" and isinstance(value, (int, float)):
            entitlements.audit_retention_days = int(value)
        # Feature flag overrides
        elif key.startswith("feature:"):
            feature_name = key[8:]
            entitlements.features[feature_name] = bool(value)
