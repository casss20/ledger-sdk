"""Tests for the billing module."""

import pytest
from datetime import datetime, timezone

from citadel.billing.models import (
    BillingCustomer,
    BillingSubscription,
    BillingUsageRecord,
    QuotaSet,
)
from citadel.billing.entitlement_service import EntitlementService
from citadel.billing.usage_service import UsageService


class TestBillingModels:
    """Unit tests for billing data models."""

    def test_quota_set_creation(self):
        q = QuotaSet(
            api_calls_limit=1000,
            agent_count_limit=5,
            retention_days=30,
        )
        assert q.api_calls_limit == 1000
        assert q.agent_count_limit == 5
        assert q.retention_days == 30

    def test_quota_set_unlimited(self):
        q = QuotaSet(api_calls_limit=-1, agent_count_limit=-1)
        assert q.api_calls_limit == -1
        assert q.agent_count_limit == -1

    def test_billing_customer(self):
        customer = BillingCustomer(
            customer_id="cust_123",
            tenant_id="tenant-1",
            stripe_customer_id="cus_stripe_123",
            email="billing@example.com",
            name="Test Corp",
            status="active",
        )
        assert customer.customer_id == "cust_123"
        assert customer.tenant_id == "tenant-1"
        assert customer.is_active is True

    def test_billing_subscription(self):
        sub = BillingSubscription(
            subscription_id="sub_123",
            customer_id="cust_123",
            tenant_id="tenant-1",
            plan_id="pro",
            status="active",
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc),
            quota=QuotaSet(api_calls_limit=5000, agent_count_limit=10),
        )
        assert sub.plan_id == "pro"
        assert sub.status == "active"
        assert sub.quota.api_calls_limit == 5000

    def test_billing_usage_record(self):
        record = BillingUsageRecord(
            record_id="rec_123",
            customer_id="cust_123",
            tenant_id="tenant-1",
            metric_name="api_calls",
            quantity=1,
            timestamp=datetime.now(timezone.utc),
        )
        assert record.metric_name == "api_calls"
        assert record.quantity == 1


class TestEntitlementService:
    """Unit tests for entitlement checking."""

    def test_check_quota_within_limit(self):
        service = EntitlementService()
        quota = QuotaSet(api_calls_limit=100, agent_count_limit=5)
        result = service.check_quota(
            current_usage={"api_calls": 50, "agent_count": 3},
            quota=quota,
        )
        assert result.allowed is True
        assert result.reason is None

    def test_check_quota_exceeded(self):
        service = EntitlementService()
        quota = QuotaSet(api_calls_limit=100, agent_count_limit=5)
        result = service.check_quota(
            current_usage={"api_calls": 101, "agent_count": 3},
            quota=quota,
        )
        assert result.allowed is False
        assert "api_calls" in result.reason

    def test_check_quota_unlimited(self):
        service = EntitlementService()
        quota = QuotaSet(api_calls_limit=-1)
        result = service.check_quota(
            current_usage={"api_calls": 999999},
            quota=quota,
        )
        assert result.allowed is True

    def test_check_quota_agent_count(self):
        service = EntitlementService()
        quota = QuotaSet(agent_count_limit=3)
        result = service.check_quota(
            current_usage={"agent_count": 4},
            quota=quota,
        )
        assert result.allowed is False
        assert "agent_count" in result.reason

    def test_grace_period_logic(self):
        service = EntitlementService()
        # past_due with grace period should allow access
        result = service.check_subscription_status(
            status="past_due",
            grace_period_days=7,
            days_past_due=3,
        )
        assert result.allowed is True
        assert result.in_grace_period is True

    def test_grace_period_expired(self):
        service = EntitlementService()
        result = service.check_subscription_status(
            status="past_due",
            grace_period_days=7,
            days_past_due=10,
        )
        assert result.allowed is False
        assert result.in_grace_period is False

    def test_cancelled_subscription_blocked(self):
        service = EntitlementService()
        result = service.check_subscription_status(
            status="cancelled",
            grace_period_days=7,
            days_past_due=0,
        )
        assert result.allowed is False


class TestUsageService:
    """Unit tests for usage tracking."""

    def test_increment_usage(self):
        service = UsageService()
        service.increment("tenant-1", "api_calls", 5)
        assert service.get_usage("tenant-1", "api_calls") == 5

    def test_increment_multiple_metrics(self):
        service = UsageService()
        service.increment("tenant-1", "api_calls", 3)
        service.increment("tenant-1", "agent_minutes", 10)
        assert service.get_usage("tenant-1", "api_calls") == 3
        assert service.get_usage("tenant-1", "agent_minutes") == 10

    def test_tenant_isolation(self):
        service = UsageService()
        service.increment("tenant-a", "api_calls", 5)
        service.increment("tenant-b", "api_calls", 10)
        assert service.get_usage("tenant-a", "api_calls") == 5
        assert service.get_usage("tenant-b", "api_calls") == 10

    def test_reset_usage(self):
        service = UsageService()
        service.increment("tenant-1", "api_calls", 100)
        service.reset("tenant-1", "api_calls")
        assert service.get_usage("tenant-1", "api_calls") == 0

    def test_get_all_metrics(self):
        service = UsageService()
        service.increment("tenant-1", "api_calls", 3)
        service.increment("tenant-1", "storage_mb", 50)
        all_usage = service.get_all_usage("tenant-1")
        assert all_usage["api_calls"] == 3
        assert all_usage["storage_mb"] == 50
