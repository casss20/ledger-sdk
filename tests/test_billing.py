"""Tests for the billing module."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from citadel.billing.models import (
    BillingStatus,
    TenantEntitlements,
    UsageSnapshot,
)
from citadel.billing.entitlement_service import EntitlementService
from citadel.billing.usage_service import UsageService
from citadel.billing.repository import BillingRepository


class FakeBillingRepository:
    """Fake repository for unit testing billing services."""

    def __init__(self):
        self.subscriptions = {}
        self.plans = {
            "free": {
                "code": "free",
                "api_calls_limit": 100,
                "active_agents_limit": 1,
                "approval_requests_limit": 10,
                "audit_retention_days": 7,
                "features_json": {},
            },
            "pro": {
                "code": "pro",
                "api_calls_limit": 5000,
                "active_agents_limit": 10,
                "approval_requests_limit": 100,
                "audit_retention_days": 90,
                "features_json": {"advanced_analytics": True},
            },
        }
        self.overrides = {}
        self.usage = {}
        self.customers = {}

    async def get_subscription(self, tenant_id: str):
        return self.subscriptions.get(tenant_id)

    async def get_plan(self, code: str):
        return self.plans.get(code)

    async def get_overrides(self, tenant_id: str):
        return self.overrides.get(tenant_id, [])

    async def get_usage(self, tenant_id: str, period_ym: str):
        key = (tenant_id, period_ym)
        return self.usage.get(key)

    async def increment_usage(self, tenant_id: str, period_ym: str, field: str, amount: int):
        key = (tenant_id, period_ym)
        if key not in self.usage:
            self.usage[key] = {
                "tenant_id": tenant_id,
                "period_ym": period_ym,
                "api_calls": 0,
                "active_agents": 0,
                "approval_requests": 0,
                "governed_actions": 0,
                "unique_users": 0,
            }
        self.usage[key][field] = self.usage[key].get(field, 0) + amount

    def add_subscription(self, tenant_id: str, plan_code: str, status: str = "active"):
        self.subscriptions[tenant_id] = {
            "tenant_id": tenant_id,
            "plan_code": plan_code,
            "status": status,
            "grace_until": None,
            "current_period_end": datetime(2026, 12, 31, tzinfo=timezone.utc),
        }


@pytest.fixture
def fake_repo():
    return FakeBillingRepository()


@pytest.fixture
def entitlement_service(fake_repo):
    return EntitlementService(repo=fake_repo)


@pytest.fixture
def usage_service(fake_repo):
    return UsageService(repo=fake_repo)


class TestBillingModels:
    """Unit tests for billing data models."""

    def test_tenant_entitlements_creation(self):
        ent = TenantEntitlements(
            tenant_id="tenant-1",
            plan_code="pro",
            billing_status=BillingStatus.ACTIVE,
            api_calls_limit=1000,
            active_agents_limit=5,
            can_access_api=True,
        )
        assert ent.tenant_id == "tenant-1"
        assert ent.plan_code == "pro"
        assert ent.can_access_api is True

    def test_tenant_entitlements_defaults(self):
        ent = TenantEntitlements(
            tenant_id="tenant-1",
            plan_code="free",
            billing_status=BillingStatus.TRIALING,
        )
        assert ent.can_access_api is True
        assert ent.can_manage_billing is True
        assert ent.in_grace_period is False

    def test_billing_status_enum(self):
        assert BillingStatus.ACTIVE.value == "active"
        assert BillingStatus.PAST_DUE.value == "past_due"
        assert BillingStatus.CANCELED.value == "canceled"

    def test_usage_snapshot(self):
        snap = UsageSnapshot(api_calls=100, active_agents=2)
        assert snap.api_calls == 100
        assert snap.active_agents == 2
        assert snap.approval_requests == 0  # default


class TestEntitlementService:
    """Unit tests for entitlement checking."""

    @pytest.mark.asyncio
    async def test_resolve_free_plan(self, fake_repo, entitlement_service):
        fake_repo.add_subscription("tenant-1", "free")
        ent = await entitlement_service.resolve("tenant-1")
        
        assert ent.tenant_id == "tenant-1"
        assert ent.plan_code == "free"
        assert ent.api_calls_limit == 100
        assert ent.active_agents_limit == 1
        assert ent.can_access_api is True

    @pytest.mark.asyncio
    async def test_resolve_pro_plan(self, fake_repo, entitlement_service):
        fake_repo.add_subscription("tenant-2", "pro")
        ent = await entitlement_service.resolve("tenant-2")
        
        assert ent.plan_code == "pro"
        assert ent.api_calls_limit == 5000
        assert ent.features.get("advanced_analytics") is True

    @pytest.mark.asyncio
    async def test_resolve_no_subscription(self, fake_repo, entitlement_service):
        ent = await entitlement_service.resolve("tenant-3")
        
        assert ent.plan_code == "free"
        assert ent.billing_status == BillingStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_past_due_blocked(self, fake_repo, entitlement_service):
        fake_repo.add_subscription("tenant-1", "pro", status="past_due")
        ent = await entitlement_service.resolve("tenant-1")
        
        assert ent.billing_status == BillingStatus.PAST_DUE
        assert ent.can_access_api is False
        assert ent.in_grace_period is False

    @pytest.mark.asyncio
    async def test_canceled_blocked(self, fake_repo, entitlement_service):
        fake_repo.add_subscription("tenant-1", "pro", status="canceled")
        ent = await entitlement_service.resolve("tenant-1")
        
        assert ent.can_access_api is False

    @pytest.mark.asyncio
    async def test_unpaid_blocked(self, fake_repo, entitlement_service):
        fake_repo.add_subscription("tenant-1", "pro", status="unpaid")
        ent = await entitlement_service.resolve("tenant-1")
        
        assert ent.can_access_api is False


class TestUsageService:
    """Unit tests for usage tracking."""

    @pytest.mark.asyncio
    async def test_increment_usage(self, fake_repo, usage_service):
        await usage_service.increment("tenant-1", "api_calls", 5)
        
        snap = await usage_service.get_snapshot("tenant-1")
        assert snap.api_calls == 5

    @pytest.mark.asyncio
    async def test_increment_multiple_metrics(self, fake_repo, usage_service):
        await usage_service.increment("tenant-1", "api_calls", 3)
        await usage_service.increment("tenant-1", "governed_actions", 10)
        
        snap = await usage_service.get_snapshot("tenant-1")
        assert snap.api_calls == 3
        assert snap.governed_actions == 10

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, fake_repo, usage_service):
        await usage_service.increment("tenant-a", "api_calls", 5)
        await usage_service.increment("tenant-b", "api_calls", 10)
        
        snap_a = await usage_service.get_snapshot("tenant-a")
        snap_b = await usage_service.get_snapshot("tenant-b")
        
        assert snap_a.api_calls == 5
        assert snap_b.api_calls == 10

    @pytest.mark.asyncio
    async def test_empty_usage_snapshot(self, fake_repo, usage_service):
        snap = await usage_service.get_snapshot("tenant-1")
        
        assert snap.api_calls == 0
        assert snap.active_agents == 0
        assert isinstance(snap, UsageSnapshot)
