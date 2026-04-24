# tests/simulate_downgrade.py
import asyncio
import httpx
import asyncpg
import json
from citadel.config import settings

async def simulate():
    print("--- Billing Downgrade Simulation ---")
    
    # 1. Setup DB
    conn = await asyncpg.connect(settings.database_url)
    tenant_id = "downgrade_tenant"
    stripe_sub_id = "sub_to_delete_123"
    
    try:
        # 2. Setup Pro state
        print(f"Setting tenant '{tenant_id}' to PRO status...")
        customer_id = await conn.fetchval(
            "INSERT INTO billing_customers (tenant_id, billing_email, stripe_customer_id) VALUES ($1, $2, $3) ON CONFLICT (tenant_id) DO UPDATE SET stripe_customer_id = $3 RETURNING id",
            tenant_id, "pro@test.com", "cus_test_123"
        )
        await conn.execute("""
            INSERT INTO billing_subscriptions (tenant_id, billing_customer_id, plan_code, stripe_subscription_id, status)
            VALUES ($1, $2, 'pro', $3, 'active')
            ON CONFLICT (tenant_id) DO UPDATE SET plan_code = 'pro', status = 'active'
        """, tenant_id, customer_id, stripe_sub_id)

        # 3. Trigger Mock Webhook for deletion
        print("Sending mock 'customer.subscription.deleted' webhook...")
        webhook_payload = {
            "id": "evt_test_delete",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": stripe_sub_id,
                    "customer": "cus_test_123",
                    "status": "canceled"
                }
            }
        }
        
        async with httpx.AsyncClient() as client:
            # Note: We skip signature verification for this simulation OR we mock the secret
            # For simplicity, we'll call the internal handler logic or use a header bypass if we added one.
            # Here we assume the server is running and we send it to the webhook endpoint.
            # (Note: In real test we'd need to sign it, but here we're demonstrating the flow)
            response = await client.post(
                "http://localhost:8000/v1/billing/webhooks/stripe",
                json=webhook_payload,
                headers={"X-Simulation": "true"} # We'd need to support this in the route
            )
            
            print(f"Webhook Response: {response.status_code}")
            
        # 4. Verify local DB state
        print("Verifying database state...")
        row = await conn.fetchrow("SELECT plan_code, status FROM billing_subscriptions WHERE tenant_id = $1", tenant_id)
        
        print(f"Current Plan: {row['plan_code']}")
        print(f"Current Status: {row['status']}")
        
        if row['plan_code'] == 'free':
            print("\nSUCCESS: Downgrade verified. Tenant returned to 'free' plan.")
        else:
            print("\nFAILURE: Tenant still on Pro.")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(simulate())
