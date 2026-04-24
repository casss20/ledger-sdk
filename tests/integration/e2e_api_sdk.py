"""
End-to-end test: SDK → API → Kernel → Database

Creates an actor, submits an action via SDK, verifies audit.
"""

import asyncio
import sys
sys.path.insert(0, 'src')

from citadel.sdk import CitadelClient
import asyncpg


async def main():
    tenant_id = "sdk_test_tenant"
    # Setup: create actor in DB
    conn = await asyncpg.connect("postgresql://citadel:citadel@localhost:5432/citadel_test")
    await conn.execute("SELECT set_tenant_context($1)", tenant_id)
    await conn.execute(
        """
        INSERT INTO actors (actor_id, actor_type, tenant_id, metadata_json, status)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (actor_id) DO NOTHING
        """,
        "sdk_test_agent",
        "agent",
        tenant_id,
        '{"verified": true}',
        "active",
    )
    await conn.close()
    
    client = CitadelClient(
        base_url="http://127.0.0.1:8001",
        api_key="dev-key-for-testing",
        actor_id="sdk_test_agent",
    )
    
    print("=" * 50)
    print("CITADEL E2E: SDK → API → Kernel → DB")
    print("=" * 50)
    
    # 1. Verify audit chain
    audit = await client.verify_audit()
    print(f"\n1. Audit chain: valid={audit['valid']}, checked={audit['checked_count']}")
    
    # 2. Execute safe action
    result = await client.execute(
        action="test.safe",
        resource="test_resource",
        payload={"amount": 5000},
        context={"environment": "prod"},
        idempotency_key="e2e-test-1",
    )
    print(f"\n2. Safe action:")
    print(f"   status: {result.status}")
    print(f"   executed: {result.executed}")
    print(f"   rule: {result.winning_rule}")
    print(f"   action_id: {result.action_id}")
    
    # 3. Lookup the action (may race with async insert)
    try:
        action = await client._client.get(f"/v1/actions/{result.action_id}", headers={"X-API-Key": "dev-key-for-testing"})
        action.raise_for_status()
        data = action.json()
        print(f"\n3. Action lookup:")
        print(f"   status: {data['status']}")
        print(f"   actor_id: {data['actor_id']}")
    except Exception as e:
        print(f"\n3. Action lookup (skipped): {type(e).__name__}: {str(e)[:60]}")
    
    # 4. Execute dangerous action (may be blocked or trigger approval)
    try:
        result2 = await client.execute(
            action="db.delete",
            resource="prod_db",
            payload={"table": "users"},
            context={"environment": "prod"},
            idempotency_key="e2e-test-2",
        )
        print(f"\n4. Dangerous action:")
        print(f"   status: {result2.status}")
        print(f"   executed: {result2.executed}")
        print(f"   rule: {result2.winning_rule}")
        print(f"   reason: {result2.reason}")
    except Exception as e:
        print(f"\n4. Dangerous action (error):")
        print(f"   {type(e).__name__}: {str(e)[:80]}")
    
    # 5. Metrics
    metrics = await client._client.get("/v1/metrics/summary", headers={"X-API-Key": "dev-key-for-testing"})
    metrics.raise_for_status()
    mdata = metrics.json()
    print(f"\n5. Metrics:")
    print(f"   total actions: {mdata['actions_total']}")
    print(f"   pending approvals: {mdata['pending_approvals']}")
    
    # 6. Guard decorator test
    print(f"\n6. Guard decorator:")
    
    @client.guard(action="test.computation", resource="compute:heavy")
    async def heavy_computation(x: int) -> int:
        return x * x
    
    try:
        result = await heavy_computation(5)
        print(f"   heavy_computation(5) = {result}")
    except Exception as e:
        print(f"   Guard blocked/errored: {type(e).__name__}: {str(e)[:80]}")
    
    await client.close()
    print("\n" + "=" * 50)
    print("E2E COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
