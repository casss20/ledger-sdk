from datetime import datetime, timezone
from typing import Optional
from .models import TenantEntitlements, BillingStatus
from .repository import BillingRepository

class EntitlementService:
    def __init__(self, repo: BillingRepository):
        self.repo = repo

    async def resolve(self, tenant_id: str) -> TenantEntitlements:
        # 1. Get base data
        sub = await self.repo.get_subscription(tenant_id)
        overrides = await self.repo.get_overrides(tenant_id)
        
        plan_code = sub['plan_code'] if sub else "free"
        plan = await self.repo.get_plan(plan_code)
        
        # 2. Base entitlements from plan
        raw_features = plan['features_json'] if plan else {}
        # Handle both dict and string (asyncpg JSONB parsing edge cases)
        if isinstance(raw_features, str):
            import json
            features = json.loads(raw_features) if raw_features else {}
        else:
            features = dict(raw_features) if raw_features else {}
        status = BillingStatus(sub['status']) if sub else BillingStatus.ACTIVE
        
        # 3. Apply Overrides
        now = datetime.now(timezone.utc)
        for o in overrides:
            if o['expires_at'] is None or o['expires_at'] > now:
                features[o['feature_key']] = o['enabled']
        
        # 4. Determine Access & Grace
        in_grace = False
        if sub and sub['grace_until'] and sub['grace_until'] > now:
            in_grace = True
            
        can_access = True
        if status in {BillingStatus.UNPAID, BillingStatus.CANCELED, BillingStatus.INCOMPLETE_EXPIRED}:
            can_access = False
        if status == BillingStatus.PAST_DUE and not in_grace:
            can_access = False
            
        return TenantEntitlements(
            tenant_id=tenant_id,
            plan_code=plan_code,
            billing_status=status,
            api_calls_limit=plan['api_calls_limit'],
            active_agents_limit=plan['active_agents_limit'],
            approval_requests_limit=plan['approval_requests_limit'],
            audit_retention_days=plan['audit_retention_days'],
            features=features,
            current_period_end=sub.get('current_period_end') if sub else None,
            in_grace_period=in_grace,
            can_access_api=can_access
        )
