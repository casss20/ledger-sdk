"""Provider-agnostic usage tracking."""

import logging
from datetime import datetime, timezone
from typing import Optional

from .models import UsageSnapshot
from .interface import CommercialRepository

logger = logging.getLogger(__name__)


class UsageService:
    """Tracks and queries per-tenant usage against plan limits."""

    def __init__(self, repo: CommercialRepository):
        self._repo = repo

    async def increment(
        self, tenant_id: str, field: str, amount: int = 1
    ) -> None:
        """Atomically increment a usage counter for the current period."""
        period_ym = self._current_period()
        await self._repo.increment_usage(tenant_id, period_ym, field, amount)

    async def get_snapshot(self, tenant_id: str) -> UsageSnapshot:
        """Return current-period usage snapshot."""
        period_ym = self._current_period()
        row = await self._repo.get_usage(tenant_id, period_ym)
        if not row:
            return UsageSnapshot()
        return UsageSnapshot(
            api_calls=row.get("api_calls", 0) or 0,
            active_agents=row.get("active_agents", 0) or 0,
            approval_requests=row.get("approval_requests", 0) or 0,
            governed_actions=row.get("governed_actions", 0) or 0,
            unique_users=row.get("unique_users", 0) or 0,
        )

    def _current_period(self) -> str:
        """Return current billing period as YYYY-MM."""
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m")
