"""Tests for the provider-agnostic commercial core.

These tests prove that core commercial logic (entitlements, usage, events)
works with ANY adapter — not just Stripe. We use a FakeCommercialRepository
that satisfies the CommercialRepository port.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from citadel.commercial.models import BillingStatus, TenantEntitlements, UsageSnapshot
from citadel.commercial.interface import CommercialRepository
from citadel.commercial.entitlement_service import EntitlementService
from citadel.commercial.usage_service import UsageService
from citadel.commercial.events import CommercialEvent, CommercialEventProcessor


class FakeCommercialRepository:
    """In-memory fake that satisfies the CommercialRepository port.

    This proves the boundary: core code depends on the interface,
    not on Stripe or any concrete provider.
    """

    def __init__(self):
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
        self.plans: Dict[str, Dict[str, Any]] = {
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
        self.overrides: Dict[str, List[Dict[str, Any]]] = {}
        self.usage: Dict[tuple, Dict[str, Any]] = {}

    async def get_subscription(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        return self.subscriptions.get(tenant_id)

    async def get_plan(self, plan_code: str) -> Optional[Dict[str, Any]]:
        return self.plans.get(plan_code)

    async def get_overrides(self, tenant_id: str) -> List[Dict[str, Any]]:
        return self.overrides.get(tenant_id, [])

    async def get_usage(self, tenant_id: str, period_ym: str) -> Optional[Dict[str, Any]]:
        return self.usage.get((tenant_id, period_ym))

    async def increment_usage(
        self, tenant_id: str, period_ym: str, field: str, amount: int = 1
    ) -> None:
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

    async def upsert_subscription(
        self, tenant_id: str, plan_code: str, status: str, **kwargs: Any
    ) -> None:
        self.subscriptions[tenant_id] = {
            "tenant_id": tenant_id,
            "plan_code": plan_code,
            "status": status,
            **kwargs,
        }

    async def update_subscription_status(
        self, tenant_id: str, status: str, grace_until: Optional[datetime] = None
    ) -> None:
        sub = self.subscriptions.get(tenant_id, {})
        sub["status"] = status
        if grace_until is not None:
            sub["grace_until"] = grace_until
        else:
            sub.pop("grace_until", None)
        self.subscriptions[tenant_id] = sub

    async def get_customer_by_stripe_id(self, stripe_customer_id: str) -> Optional[Dict[str, Any]]:
        for sub in self.subscriptions.values():
            if sub.get("stripe_customer_id") == stripe_customer_id:
                return sub
        return None
    def seed_subscription(self, tenant_id: str, plan_code: str, status: str = "active", **kwargs):
        self.subscriptions[tenant_id] = {
            "tenant_id": tenant_id,
            "plan_code": plan_code,
            "status": status,
            **kwargs,
        }

    def seed_override(self, tenant_id: str, feature_key: str, value: Any):
        self.overrides.setdefault(tenant_id, []).append({
            "feature_key": feature_key,
            "value_json": value,
        })


@pytest.fixture
def fake_repo():
    return FakeCommercialRepository()


@pytest.fixture
def entitlement_service(fake_repo):
    return EntitlementService(fake_repo)


@pytest.fixture
def usage_service(fake_repo):
    return UsageService(fake_repo)


@pytest.fixture
def event_processor(fake_repo):
    return CommercialEventProcessor(fake_repo)


class TestEntitlementService:
    """Entitlement resolution with a fake repository."""

    @pytest.mark.asyncio
    async def test_resolve_free_plan(self, fake_repo, entitlement_service):
        fake_repo.seed_subscription("t1", "free")
        ent = await entitlement_service.resolve("t1")
        assert ent.plan_code == "free"
        assert ent.api_calls_limit == 100
        assert ent.can_access_api is True

    @pytest.mark.asyncio
    async def test_resolve_pro_plan(self, fake_repo, entitlement_service):
        fake_repo.seed_subscription("t2", "pro")
        ent = await entitlement_service.resolve("t2")
        assert ent.plan_code == "pro"
        assert ent.api_calls_limit == 5000
        assert ent.features.get("advanced_analytics") is True

    @pytest.mark.asyncio
    async def test_resolve_no_subscription_defaults_to_free(self, fake_repo, entitlement_service):
        ent = await entitlement_service.resolve("t3")
        assert ent.plan_code == "free"
        assert ent.billing_status == BillingStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_past_due_blocked(self, fake_repo, entitlement_service):
        fake_repo.seed_subscription("t1", "pro", status="past_due")
        ent = await entitlement_service.resolve("t1")
        assert ent.billing_status == BillingStatus.PAST_DUE
        assert ent.can_access_api is False

    @pytest.mark.asyncio
    async def test_past_due_with_grace_allowed(self, fake_repo, entitlement_service):
        grace = datetime.now(timezone.utc) + timedelta(days=5)
        fake_repo.seed_subscription("t1", "pro", status="past_due", grace_until=grace)
        ent = await entitlement_service.resolve("t1")
        assert ent.billing_status == BillingStatus.PAST_DUE
        assert ent.can_access_api is True
        assert ent.in_grace_period is True

    @pytest.mark.asyncio
    async def test_expired_grace_blocked(self, fake_repo, entitlement_service):
        grace = datetime.now(timezone.utc) - timedelta(days=1)
        fake_repo.seed_subscription("t1", "pro", status="past_due", grace_until=grace)
        ent = await entitlement_service.resolve("t1")
        assert ent.can_access_api is False
        assert ent.in_grace_period is False

    @pytest.mark.asyncio
    async def test_canceled_blocked(self, fake_repo, entitlement_service):
        fake_repo.seed_subscription("t1", "pro", status="canceled")
        ent = await entitlement_service.resolve("t1")
        assert ent.can_access_api is False

    @pytest.mark.asyncio
    async def test_override_applied(self, fake_repo, entitlement_service):
        fake_repo.seed_subscription("t1", "free")
        fake_repo.seed_override("t1", "api_calls_limit", 500)
        ent = await entitlement_service.resolve("t1")
        assert ent.api_calls_limit == 500

    @pytest.mark.asyncio
    async def test_feature_override(self, fake_repo, entitlement_service):
        fake_repo.seed_subscription("t1", "free")
        fake_repo.seed_override("t1", "feature:custom_flag", True)
        ent = await entitlement_service.resolve("t1")
        assert ent.features.get("custom_flag") is True


class TestUsageService:
    """Usage tracking with a fake repository."""

    @pytest.mark.asyncio
    async def test_increment_usage(self, fake_repo, usage_service):
        await usage_service.increment("t1", "api_calls", 5)
        snap = await usage_service.get_snapshot("t1")
        assert snap.api_calls == 5

    @pytest.mark.asyncio
    async def test_increment_multiple_metrics(self, fake_repo, usage_service):
        await usage_service.increment("t1", "api_calls", 3)
        await usage_service.increment("t1", "governed_actions", 10)
        snap = await usage_service.get_snapshot("t1")
        assert snap.api_calls == 3
        assert snap.governed_actions == 10

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, fake_repo, usage_service):
        await usage_service.increment("ta", "api_calls", 5)
        await usage_service.increment("tb", "api_calls", 10)
        snap_a = await usage_service.get_snapshot("ta")
        snap_b = await usage_service.get_snapshot("tb")
        assert snap_a.api_calls == 5
        assert snap_b.api_calls == 10

    @pytest.mark.asyncio
    async def test_empty_usage_snapshot(self, fake_repo, usage_service):
        snap = await usage_service.get_snapshot("t1")
        assert snap.api_calls == 0
        assert isinstance(snap, UsageSnapshot)


class TestCommercialEventProcessor:
    """Event processing with a fake repository."""

    @pytest.mark.asyncio
    async def test_subscription_deleted_downgrades_to_free(self, fake_repo, event_processor):
        fake_repo.seed_subscription("t1", "pro", status="active")
        event = CommercialEvent(
            event_type="subscription.deleted",
            tenant_id="t1",
            payload={"subscription_id": "sub_123"},
        )
        await event_processor.process(event)
        sub = fake_repo.subscriptions["t1"]
        # Processor calls update_subscription_status(status="canceled")
        # then upsert_subscription(plan_code="free", status="active")
        # Final state: free plan, active status
        assert sub["plan_code"] == "free"
        assert sub["status"] == "active"

    @pytest.mark.asyncio
    async def test_payment_failed_enters_grace(self, fake_repo, event_processor):
        fake_repo.seed_subscription("t1", "pro", status="active")
        event = CommercialEvent(
            event_type="invoice.payment_failed",
            tenant_id="t1",
            payload={"invoice_id": "inv_123"},
        )
        await event_processor.process(event)
        sub = fake_repo.subscriptions["t1"]
        assert sub["status"] == "past_due"
        assert "grace_until" in sub
        grace = sub["grace_until"]
        assert grace > datetime.now(timezone.utc)
        assert grace <= datetime.now(timezone.utc) + timedelta(days=8)

    @pytest.mark.asyncio
    async def test_payment_succeeded_clears_grace(self, fake_repo, event_processor):
        fake_repo.seed_subscription("t1", "pro", status="past_due", grace_until=datetime.now(timezone.utc))
        event = CommercialEvent(
            event_type="invoice.payment_succeeded",
            tenant_id="t1",
            payload={"invoice_id": "inv_123"},
        )
        await event_processor.process(event)
        sub = fake_repo.subscriptions["t1"]
        assert sub["status"] == "active"
        assert sub.get("grace_until") is None

    @pytest.mark.asyncio
    async def test_subscription_updated(self, fake_repo, event_processor):
        fake_repo.seed_subscription("t1", "free", status="active")
        event = CommercialEvent(
            event_type="subscription.updated",
            tenant_id="t1",
            payload={"plan_code": "pro", "status": "active", "current_period_end": "2026-12-31"},
        )
        await event_processor.process(event)
        sub = fake_repo.subscriptions["t1"]
        assert sub["plan_code"] == "pro"
        assert sub["status"] == "active"

    @pytest.mark.asyncio
    async def test_unknown_event_type_ignored(self, fake_repo, event_processor):
        fake_repo.seed_subscription("t1", "pro", status="active")
        event = CommercialEvent(
            event_type="some.weird.event",
            tenant_id="t1",
            payload={},
        )
        # Should not raise
        await event_processor.process(event)
        # State unchanged
        sub = fake_repo.subscriptions["t1"]
        assert sub["status"] == "active"


class TestCommercialRepositoryPort:
    """Verify that FakeCommercialRepository satisfies the port."""

    def test_fake_implements_port(self, fake_repo):
        """Structural check: FakeCommercialRepository can be used where CommercialRepository is expected."""
        # This is a compile-time / structural check
        import inspect

        port_methods = {
            name for name, _ in inspect.getmembers(CommercialRepository)
            if not name.startswith("_")
        }
        fake_methods = {
            name for name, _ in inspect.getmembers(FakeCommercialRepository)
            if not name.startswith("_") and callable(getattr(FakeCommercialRepository, name))
        }
        # Fake may have additional test helpers; it must cover all port methods
        for method in port_methods:
            assert hasattr(fake_repo, method), f"FakeCommercialRepository missing port method: {method}"
