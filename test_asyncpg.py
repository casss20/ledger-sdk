import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect("postgresql://ledger:ledger@127.0.0.1:5432/ledger_test")
    
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
    
    await conn.close()

asyncio.run(test())
