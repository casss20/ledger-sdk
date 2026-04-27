"""Commercial repository port (interface). Core code depends on this, not on Stripe."""

from typing import Protocol, Optional, Dict, Any, List
from datetime import datetime


class CommercialRepository(Protocol):
    """Port for commercial state access. Every provider adapter implements this."""

    # ── Read operations (core entitlement resolution) ───────────────────────

    async def get_subscription(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Return the tenant's current subscription record, or None."""
        ...

    async def get_plan(self, plan_code: str) -> Optional[Dict[str, Any]]:
        """Return a billing plan by its canonical code, or None."""
        ...

    async def get_overrides(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Return active entitlement overrides for a tenant."""
        ...

    async def get_usage(self, tenant_id: str, period_ym: str) -> Optional[Dict[str, Any]]:
        """Return usage for a tenant in a given YYYY-MM period, or None."""
        ...

    # ── Write operations (atomic usage tracking) ──────────────────────────

    async def increment_usage(
        self, tenant_id: str, period_ym: str, field: str, amount: int = 1
    ) -> None:
        """Atomically increment a usage counter. `field` must be alphanumeric + underscore."""
        ...

    # ── Write operations (event processing) ─────────────────────────────────

    async def upsert_subscription(
        self, tenant_id: str, plan_code: str, status: str, **kwargs: Any
    ) -> None:
        """Create or update a subscription record."""
        ...

    async def update_subscription_status(
        self,
        tenant_id: str,
        status: str,
        grace_until: Optional[datetime] = None,
    ) -> None:
        """Update subscription status and optional grace period."""
        ...
