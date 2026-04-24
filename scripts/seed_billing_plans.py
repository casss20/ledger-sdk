# seed_billing_plans.py
import asyncio
import os
import json
import asyncpg
from CITADEL.config import settings

PLANS = [
    {
        "code": "free",
        "name": "Free",
        "monthly_price_cents": 0,
        "stripe_price_id": None,
        "api_calls_limit": 1000,
        "active_agents_limit": 1,
        "approval_requests_limit": 100,
        "seats_limit": 1,
        "audit_retention_days": 7,
        "features_json": {
            "dashboard": True,
            "api_access": True,
            "advanced_policy_engine": False,
            "sso": False,
            "custom_sla": False,
        },
    },
    {
        "code": "pro",
        "name": "Pro",
        "monthly_price_cents": 9900,
        "stripe_price_id": os.getenv("STRIPE_PRICE_PRO_ID"),
        "api_calls_limit": 10000,
        "active_agents_limit": 10,
        "approval_requests_limit": 2000,
        "seats_limit": 10,
        "audit_retention_days": 30,
        "features_json": {
            "dashboard": True,
            "api_access": True,
            "advanced_policy_engine": True,
            "sso": False,
            "custom_sla": False,
        },
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "monthly_price_cents": 0,
        "stripe_price_id": None,
        "api_calls_limit": None,
        "active_agents_limit": None,
        "approval_requests_limit": None,
        "seats_limit": None,
        "audit_retention_days": 365,
        "features_json": {
            "dashboard": True,
            "api_access": True,
            "advanced_policy_engine": True,
            "sso": True,
            "custom_sla": True,
        },
    },
]

async def seed():
    print(f"Connecting to {settings.database_url}...")
    conn = await asyncpg.connect(settings.database_url)
    try:
        for plan in PLANS:
            print(f"Seeding plan: {plan['name']} ({plan['code']})...")
            await conn.execute("""
                INSERT INTO billing_plans (
                    code, name, monthly_price_cents, stripe_price_id, 
                    api_calls_limit, active_agents_limit, approval_requests_limit, 
                    seats_limit, audit_retention_days, features_json
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    monthly_price_cents = EXCLUDED.monthly_price_cents,
                    stripe_price_id = EXCLUDED.stripe_price_id,
                    api_calls_limit = EXCLUDED.api_calls_limit,
                    active_agents_limit = EXCLUDED.active_agents_limit,
                    approval_requests_limit = EXCLUDED.approval_requests_limit,
                    seats_limit = EXCLUDED.seats_limit,
                    audit_retention_days = EXCLUDED.audit_retention_days,
                    features_json = EXCLUDED.features_json,
                    updated_at = NOW()
            """, 
            plan['code'], plan['name'], plan['monthly_price_cents'], plan['stripe_price_id'],
            plan['api_calls_limit'], plan['active_agents_limit'], plan['approval_requests_limit'],
            plan['seats_limit'], plan['audit_retention_days'], json.dumps(plan['features_json']))
        print("Seeding complete.")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(seed())
