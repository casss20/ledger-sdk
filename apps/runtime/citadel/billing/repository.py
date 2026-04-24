import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import asyncpg

class BillingRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_customer(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        return await self.pool.fetchrow(
            "SELECT * FROM billing_customers WHERE tenant_id = $1", tenant_id
        )

    async def get_customer_by_stripe_id(self, stripe_customer_id: str) -> Optional[Dict[str, Any]]:
        return await self.pool.fetchrow(
            "SELECT * FROM billing_customers WHERE stripe_customer_id = $1", stripe_customer_id
        )

    async def get_plan(self, code: str) -> Optional[Dict[str, Any]]:
        return await self.pool.fetchrow(
            "SELECT * FROM billing_plans WHERE code = $1", code
        )

    async def get_plan_by_price_id(self, stripe_price_id: str) -> Optional[Dict[str, Any]]:
        return await self.pool.fetchrow(
            "SELECT * FROM billing_plans WHERE stripe_price_id = $1", stripe_price_id
        )

    async def get_subscription(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        return await self.pool.fetchrow(
            "SELECT * FROM billing_subscriptions WHERE tenant_id = $1", tenant_id
        )

    async def get_overrides(self, tenant_id: str) -> List[Dict[str, Any]]:
        return await self.pool.fetch(
            "SELECT * FROM billing_entitlement_overrides WHERE tenant_id = $1", tenant_id
        )

    async def get_usage(self, tenant_id: str, period_ym: str) -> Optional[Dict[str, Any]]:
        return await self.pool.fetchrow(
            "SELECT * FROM billing_usage_monthly WHERE tenant_id = $1 AND period_ym = $2",
            tenant_id, period_ym
        )

    async def create_customer(self, tenant_id: str, email: str, company: Optional[str], stripe_id: Optional[str]) -> str:
        return await self.pool.fetchval(
            """INSERT INTO billing_customers (tenant_id, billing_email, company_name, stripe_customer_id)
               VALUES ($1, $2, $3, $4) RETURNING id""",
            tenant_id, email, company, stripe_id
        )

    async def upsert_subscription(self, data: Dict[str, Any]):
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
            data['tenant_id'], data['billing_customer_id'], data['plan_code'], data.get('stripe_subscription_id'),
            data.get('stripe_price_id'), data['status'], data.get('collection_method'), data.get('cancel_at_period_end', False),
            data.get('current_period_start'), data.get('current_period_end'), data.get('trial_start'), data.get('trial_end'),
            json.dumps(data.get('metadata_json', {}))
        )

    async def increment_usage(self, tenant_id: str, period_ym: str, field: str, amount: int = 1):
        await self.pool.execute(
            f"""INSERT INTO billing_usage_monthly (tenant_id, period_ym, {field})
               VALUES ($1, $2, $3)
               ON CONFLICT (tenant_id, period_ym) DO UPDATE SET
               {field} = billing_usage_monthly.{field} + $3,
               updated_at = NOW()""",
            tenant_id, period_ym, amount
        )

    async def log_event(self, provider: str, event_id: str, event_type: str, payload: Dict[str, Any], status: str = 'received'):
        await self.pool.execute(
            """INSERT INTO billing_event_log (provider, provider_event_id, provider_event_type, payload_json, status)
               VALUES ($1, $2, $3, $4, $5) ON CONFLICT (provider_event_id) DO NOTHING""",
            provider, event_id, event_type, json.dumps(payload), status
        )

    async def mark_event_processed(self, event_id: str, error: Optional[str] = None):
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
