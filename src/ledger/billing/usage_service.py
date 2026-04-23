from datetime import datetime, timezone
from typing import Optional
from .models import UsageSnapshot
from .repository import BillingRepository

class UsageService:
    def __init__(self, repo: BillingRepository):
        self.repo = repo

    def _get_period(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    async def increment(self, tenant_id: str, field: str, amount: int = 1):
        await self.repo.increment_usage(tenant_id, self._get_period(), field, amount)

    async def get_snapshot(self, tenant_id: str, period_ym: Optional[str] = None) -> UsageSnapshot:
        period = period_ym or self._get_period()
        row = await self.repo.get_usage(tenant_id, period)
        if not row:
            return UsageSnapshot()
        return UsageSnapshot(
            api_calls=row['api_calls'],
            active_agents=row['active_agents'],
            approval_requests=row['approval_requests'],
            governed_actions=row['governed_actions'],
            unique_users=row['unique_users']
        )
