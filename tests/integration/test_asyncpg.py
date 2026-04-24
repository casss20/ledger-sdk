import asyncio
import asyncpg
import pytest

@pytest.mark.asyncio
async def test_asyncpg_connection():
    try:
        conn = await asyncpg.connect("postgresql://CITADEL:CITADEL@127.0.0.1:5432/citadel_test")
    except asyncpg.exceptions.InvalidAuthorizationSpecificationError:
        pytest.skip("PostgreSQL database 'CITADEL' not available")
    except Exception as e:
        pytest.skip(f"Database connection failed: {e}")
        
    try:
        # Insert action
        await conn.execute("""
            INSERT INTO actions (action_id, actor_id, actor_type, action_name, resource)
            VALUES ('e1a676ed-a13f-454d-9bbc-294457f54975', 'test_agent', 'agent', 'test.action', 'test')
            ON CONFLICT DO NOTHING
        """)
        
        # Insert audit event with explicit values (no parameters)
        row = await conn.fetchrow("""
            INSERT INTO audit_events (action_id, event_type, payload_json, actor_id)
            VALUES ('e1a676ed-a13f-454d-9bbc-294457f54975', 'action_received', '{}', 'test_agent')
            RETURNING event_hash
        """)
        
        print(f"event_hash: {row['event_hash']}")
    finally:
        await conn.close()
