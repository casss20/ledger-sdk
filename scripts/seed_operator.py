import asyncio
import os
import asyncpg
from CITADEL.auth.operator import OperatorService

async def seed():
    # Load env variables
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/CITADEL")
    
    print(f"Connecting to {db_url}...")
    pool = await asyncpg.create_pool(db_url)
    
    service = OperatorService(pool)
    
    # Check if admin already exists
    async with pool.acquire() as conn:
        # Check if table exists
        exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'operators'
            )
        """)
        if not exists:
            print("Table 'operators' does not exist. Run migrations first.")
            await pool.close()
            return

        count = await conn.fetchval("SELECT COUNT(*) FROM operators WHERE username = 'admin'")
        if count > 0:
            print("Operator 'admin' already exists.")
        else:
            op_id = await service.create_operator(
                username="admin",
                email="admin@CITADEL.internal",
                password="admin", # In production, use a strong password
                tenant_id="acme",
                role="admin"
            )
            print(f"Created admin operator: {op_id}")
    
    await pool.close()

if __name__ == "__main__":
    asyncio.run(seed())
