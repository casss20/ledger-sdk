"""Stripe-specific CommercialRepository implementation.

This is the ONLY place that queries billing tables with Stripe-specific
columns (stripe_customer_id, stripe_price_id, etc.). Core code depends on
the CommercialRepository port, not on this concrete class.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import asyncpg

from ...interface import CommercialRepository

logger = logging.getLogger(__name__)


class StripeCommercialRepository:
    """Concrete repository backed by Citadel's billing tables.

    SQL here references Stripe columns (stripe_customer_id, stripe_price_id)
    because the database schema stores provider IDs. The interface methods
    return plain dicts so core code remains provider-agnostic.
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    # ── Read operations (core entitlement resolution) ───────────────────

    async def get_subscription(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        row = await self.pool.fetchrow(
            "SELECT * FROM billing_subscriptions WHERE tenant_id = $1", tenant_id
        )
        return dict(row) if row else None

    async def get_plan(self, code: str) -> Optional[Dict[str, Any]]:
        row = await self.pool.fetchrow(
            "SELECT * FROM billing_plans WHERE code = $1", code
        )
        return dict(row) if row else None

    async def get_overrides(self, tenant_id: str) -> List[Dict[str, Any]]:
        rows = await self.pool.fetch(
            "SELECT * FROM billing_entitlement_overrides WHERE tenant_id = $1", tenant_id
        )
        return [dict(r) for r in rows]

    async def get_usage(self, tenant_id: str, period_ym: str) -> Optional[Dict[str, Any]]:
        row = await self.pool.fetchrow(
            "SELECT * FROM billing_usage_monthly WHERE tenant_id = $1 AND period_ym = $2",
            tenant_id, period_ym
        )
        return dict(row) if row else None

    # ── Write operations (atomic usage tracking) ────────────────────────

    async def increment_usage(
        self, tenant_id: str, period_ym: str, field: str, amount: int = 1
    ) -> None:
        if not field or not field.replace("_", "").isalnum():
            raise ValueError(f"Invalid usage field name: {field}")
        query = (
            "INSERT INTO billing_usage_monthly (tenant_id, period_ym, " + field + ") "
            "VALUES ($1, $2, $3) "
            "ON CONFLICT (tenant_id, period_ym) DO UPDATE SET "
            + field + " = billing_usage_monthly." + field + " + $3, "
            "updated_at = NOW()"
        )
        await self.pool.execute(query, tenant_id, period_ym, amount)

    # ── Write operations (event processing) ─────────────────────────────

    async def upsert_subscription(
        self, tenant_id: str, plan_code: str, status: str, **kwargs: Any
    ) -> None:
        await self.pool.execute(
            """INSERT INTO billing_subscriptions (
                tenant_id, billing_customer_id, plan_code, stripe_subscription_id,
                stripe_price_id, status, collection_method, cancel_at_period_end,
                current_period_start, current_period_end, trial_start, trial_end,
                metadata_json, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW())
            ON CONFLICT (tenant_id) DO UPDATE SET
                plan_code = EXCLUDED.plan_code,
                stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                stripe_price_id = EXCLUDED.stripe_price_id,
                status = EXCLUDED.status,
                cancel_at_period_end = EXCLUDED.cancel_at_period_end,
                current_period_end = EXCLUDED.current_period_end,
                updated_at = NOW()""",
            tenant_id,
            kwargs.get("billing_customer_id"),
            plan_code,
            kwargs.get("stripe_subscription_id"),
            kwargs.get("stripe_price_id"),
            status,
            kwargs.get("collection_method"),
            kwargs.get("cancel_at_period_end", False),
            kwargs.get("current_period_start"),
            kwargs.get("current_period_end"),
            kwargs.get("trial_start"),
            kwargs.get("trial_end"),
            json.dumps(kwargs.get("metadata_json", {})),
        )

    async def update_subscription_status(
        self,
        tenant_id: str,
        status: str,
        grace_until: Optional[datetime] = None,
    ) -> None:
        await self.pool.execute(
            "UPDATE billing_subscriptions SET status = $1, grace_until = $2, updated_at = NOW() WHERE tenant_id = $3",
            status, grace_until, tenant_id
        )

    # ── Stripe-specific helpers (NOT part of CommercialRepository port) ─

    async def get_customer(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Fetch billing customer by tenant_id."""
        row = await self.pool.fetchrow(
            "SELECT * FROM billing_customers WHERE tenant_id = $1", tenant_id
        )
        return dict(row) if row else None

    async def get_customer_by_stripe_id(self, stripe_customer_id: str) -> Optional[Dict[str, Any]]:
        """Lookup customer by Stripe ID — used by webhook translator."""
        row = await self.pool.fetchrow(
            "SELECT * FROM billing_customers WHERE stripe_customer_id = $1", stripe_customer_id
        )
        return dict(row) if row else None

    async def get_plan_by_price_id(self, stripe_price_id: str) -> Optional[Dict[str, Any]]:
        """Lookup plan by Stripe price ID — used by webhook translator."""
        row = await self.pool.fetchrow(
            "SELECT * FROM billing_plans WHERE stripe_price_id = $1", stripe_price_id
        )
        return dict(row) if row else None

    async def create_customer(
        self, tenant_id: str, email: str, company: Optional[str], stripe_id: Optional[str]
    ) -> str:
        """Create a billing customer record."""
        return await self.pool.fetchval(
            """INSERT INTO billing_customers (tenant_id, billing_email, company_name, stripe_customer_id)
               VALUES ($1, $2, $3, $4) RETURNING id""",
            tenant_id, email, company, stripe_id
        )

    async def log_event(
        self, provider: str, event_id: str, event_type: str, payload: Dict[str, Any], status: str = "received"
    ) -> None:
        """Log an incoming provider event for idempotency / audit."""
        await self.pool.execute(
            """INSERT INTO billing_event_log (provider, provider_event_id, provider_event_type, payload_json, status)
               VALUES ($1, $2, $3, $4, $5) ON CONFLICT (provider_event_id) DO NOTHING""",
            provider, event_id, event_type, json.dumps(payload), status
        )

    async def mark_event_processed(self, event_id: str, error: Optional[str] = None) -> None:
        """Mark a logged event as processed or failed."""
        if error:
            await self.pool.execute(
                "UPDATE billing_event_log SET status = 'failed', error_text = $1 WHERE provider_event_id = $2",
                error, event_id
            )
        else:
            await self.pool.execute(
                "UPDATE billing_event_log SET status = 'processed', processed_at = NOW() WHERE provider_event_id = $1",
                event_id
            )
