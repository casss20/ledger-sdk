# tests/test_billing_hardening.py
import pytest
import json
from datetime import datetime, timezone, timedelta
from CITADEL.billing.models import BillingStatus
from CITADEL.billing.entitlement_service import EntitlementService
from CITADEL.billing.usage_service import UsageService
from CITADEL.billing.repository import BillingRepository

class MockPool:
    async def fetchrow(self, query, *args):
        # Simulated responses for entitlement tests
        if "billing_plans" in query:
            return {
                "code": args[0],
                "features_json": {"advanced_policy_engine": True},
                "api_calls_limit": 1000,
                "active_agents_limit": 10,
                "approval_requests_limit": 100,
                "audit_retention_days": 30
            }
        if "billing_subscriptions" in query:
            # Return a past_due sub for testing grace
            return {
                "plan_code": "pro",
                "status": "past_due",
                "grace_until": datetime.now(timezone.utc) + timedelta(days=5)
            }
        return None

    async def fetch(self, query, *args): return []
    async def fetchval(self, query, *args): return "id_1"
    async def execute(self, query, *args): pass

@pytest.mark.asyncio
async def test_entitlement_grace_period():
    repo = BillingRepository(MockPool())
    service = EntitlementService(repo)
    
    # Test past_due with active grace
    entitlements = await service.resolve("tenant_1")
    assert entitlements.billing_status == BillingStatus.PAST_DUE
    assert entitlements.in_grace_period is True
    assert entitlements.can_access_api is True

@pytest.mark.asyncio
async def test_quota_enforcement_logic():
    # This simulates what the middleware does
    class QuotaRepo(BillingRepository):
        async def get_usage(self, t, p):
            return {"api_calls": 1200, "active_agents": 1, "approval_requests": 0, "governed_actions": 0, "unique_users": 0}
        async def get_subscription(self, t): return {"plan_code": "free", "status": "active", "grace_until": None}
        async def get_plan(self, c): return {"code": "free", "api_calls_limit": 1000, "features_json": {}}

    repo = QuotaRepo(None)
    ent_service = EntitlementService(repo)
    usage_service = UsageService(repo)
    
    entitlements = await ent_service.resolve("tenant_1")
    usage = await usage_service.get_snapshot("tenant_1")
    
    # Verify limit is exceeded
    assert entitlements.api_calls_limit == 1000
    assert usage.api_calls > entitlements.api_calls_limit
    # Middleware would block here
