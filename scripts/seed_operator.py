#!/usr/bin/env python3
"""
Seed script: Create default operator for dashboard login.
Run this once to set up the first admin account.
"""

import asyncio
import asyncpg
import os
import sys

# Database connection - uses the same env var as the app
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_DSN")
if not DATABASE_URL:
    print("Error: Set DATABASE_URL or DATABASE_DSN env var")
    sys.exit(1)

async def seed():
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Check if operators table exists
    try:
        await conn.fetch("SELECT 1 FROM operators LIMIT 1")
    except asyncpg.exceptions.UndefinedTableError:
        print("Error: operators table doesn't exist. Run migrations first.")
        await conn.close()
        sys.exit(1)
    
    # Check if admin already exists
    existing = await conn.fetchval("SELECT COUNT(*) FROM operators WHERE username = 'admin'")
    if existing > 0:
        print("Admin user already exists. Skipping.")
        await conn.close()
        return
    
    # Create admin operator with password "admin123"
    import hashlib, secrets
    salt = secrets.token_hex(16)
    iterations = 100000
    key = hashlib.pbkdf2_hmac('sha256', b'admin123', salt.encode(), iterations)
    password_hash = f"pbkdf2:sha256:{iterations}:{salt}:{key.hex()}"
    
    await conn.execute("""
        INSERT INTO operators (operator_id, username, email, password_hash, tenant_id, role, is_active)
        VALUES ($1, $2, $3, $4, $5, $6, TRUE)
    """, "op_admin_default", "admin", "admin@citadel.dev", password_hash, "demo-tenant", "admin")
    
    print("✅ Created default admin operator:")
    print("   Username: admin")
    print("   Password: admin123")
    print("   Tenant: demo-tenant")
    print("   Role: admin")
    print("")
    print("Next steps:")
    print("1. Log in: POST /auth/login with username=admin, password=admin123")
    print("2. Create API key: POST /auth/keys with JWT token")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(seed())
