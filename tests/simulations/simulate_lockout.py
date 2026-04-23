# tests/simulate_lockout.py
import asyncio
import httpx
import asyncpg
from ledger.config import settings

async def simulate():
    print("--- Billing Quota Lockout Simulation ---")
    
    # 1. Setup DB connection
    conn = await asyncpg.connect(settings.database_url)
    tenant_id = "simulation_tenant"
    
    try:
        # 2. Ensure tenant and plan exist
        print(f"Ensuring tenant '{tenant_id}' is on Free plan (limit 1000)...")
        await conn.execute("INSERT INTO billing_customers (tenant_id, billing_email) VALUES ($1, $2) ON CONFLICT DO NOTHING", tenant_id, "sim@test.com")
        
        # 3. Inflate usage to 1001 (limit is 1000)
        period = "2026-04"
        print(f"Inflating usage to 1001 API calls for period {period}...")
        await conn.execute("""
            INSERT INTO billing_usage_monthly (tenant_id, period_ym, api_calls)
            VALUES ($1, $2, 1001)
            ON CONFLICT (tenant_id, period_ym) DO UPDATE SET api_calls = 1001
        """, tenant_id, period)
        
        # 4. Call a protected endpoint
        # We need a valid API key for this tenant to pass Auth first
        # For simulation purposes, we'll assume there is a mock/dev key or bypass auth
        # Actually, since we're testing the BillingMiddleware which runs AFTER Auth,
        # we'll simulate the request state in a mock call if possible, or just use a real one.
        
        print("Calling protected API endpoint /v1/actions/evaluate...")
        async with httpx.AsyncClient() as client:
            # We use the X-Tenant-Id header if our AuthMiddleware supports it for dev
            # OR we use a real API key.
            response = await client.post(
                "http://localhost:8000/v1/actions/evaluate",
                json={"action": "test"},
                headers={"X-API-Key": "dev-key", "X-Tenant-Id": tenant_id} # Assuming dev setup
            )
            
            print(f"Response Status: {response.status_code}")
            print(f"Response Body: {response.text}")
            
            if response.status_code == 429:
                print("\nSUCCESS: Lockout verified. 429 Too Many Requests received.")
                print(f"Plan: {response.json().get('plan')}")
                print(f"Usage: {response.json().get('current_usage')} / {response.json().get('limit')}")
            else:
                print("\nFAILURE: Did not receive 429. Ensure the server is running and billing middleware is active.")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(simulate())
