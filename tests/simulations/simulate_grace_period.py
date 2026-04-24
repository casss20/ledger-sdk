# tests/simulate_grace_period.py
import asyncio
import httpx
import asyncpg
from datetime import datetime, timezone, timedelta
from CITADEL.config import settings

async def simulate():
    print("--- Billing Grace Period Simulation ---")
    
    conn = await asyncpg.connect(settings.database_url)
    tenant_id = "grace_period_tenant"
    
    try:
        # 1. Setup Pro state
        print(f"Setting tenant '{tenant_id}' to PRO status...")
        customer_id = await conn.fetchval(
            "INSERT INTO billing_customers (tenant_id, billing_email) VALUES ($1, $2) ON CONFLICT (tenant_id) DO UPDATE SET status = 'active' RETURNING id",
            tenant_id, "grace@test.com"
        )
        await conn.execute("""
            INSERT INTO billing_subscriptions (tenant_id, billing_customer_id, plan_code, status)
            VALUES ($1, $2, 'pro', 'active')
            ON CONFLICT (tenant_id) DO UPDATE SET plan_code = 'pro', status = 'active', grace_until = NULL
        """, tenant_id, customer_id)

        # 2. Simulate Payment Failure (Triggers Grace Period)
        print("Simulating 'invoice.payment_failed' (Grace Period Start)...")
        grace_end = datetime.now(timezone.utc) + timedelta(days=7)
        await conn.execute("""
            UPDATE billing_subscriptions 
            SET status = 'past_due', grace_until = $1 
            WHERE tenant_id = $2
        """, grace_end, tenant_id)

        # 3. Test API access (Should be ALLOWED)
        print("Testing API access during ACTIVE grace period (Should be 200)...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/v1/actions/evaluate",
                json={"action": "test"},
                headers={"X-API-Key": "dev-key", "X-Tenant-Id": tenant_id}
            )
            print(f"Response Status: {response.status_code}")
            if response.status_code == 200:
                print("SUCCESS: Access allowed during grace period.")
            else:
                print(f"FAILURE: Access blocked unexpectedly. Body: {response.text}")

        # 4. Simulate Grace Period Expiry
        print("\nSimulating Grace Period EXPIRY (setting grace_until to the past)...")
        expired_grace = datetime.now(timezone.utc) - timedelta(hours=1)
        await conn.execute("""
            UPDATE billing_subscriptions 
            SET grace_until = $1 
            WHERE tenant_id = $2
        """, expired_grace, tenant_id)

        # 5. Test API access (Should be BLOCKED)
        print("Testing API access after EXPIRED grace period (Should be 402)...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/v1/actions/evaluate",
                json={"action": "test"},
                headers={"X-API-Key": "dev-key", "X-Tenant-Id": tenant_id}
            )
            print(f"Response Status: {response.status_code}")
            if response.status_code == 402:
                print("SUCCESS: Access blocked after grace period expiry.")
            else:
                print(f"FAILURE: Did not receive 402 Payment Required. Status: {response.status_code}")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(simulate())
