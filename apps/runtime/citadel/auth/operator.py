import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
import hashlib
import secrets

logger = logging.getLogger(__name__)

@dataclass
class Operator:
    operator_id: str
    username: str
    email: str
    password_hash: str
    tenant_id: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

class OperatorService:
    """Manage dashboard operators (admin users)"""
    
    def __init__(self, db_pool):
        self.db = db_pool

    def hash_password(self, password: str) -> str:
        """Hash password using PBKDF2 (simple alternative if passlib is missing)"""
        salt = secrets.token_hex(16)
        iterations = 100000
        key = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            iterations
        )
        return f"pbkdf2:sha256:{iterations}:{salt}:{key.hex()}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against stored hash"""
        try:
            parts = password_hash.split(':')
            if len(parts) != 5 or parts[0] != 'pbkdf2' or parts[1] != 'sha256':
                return False
            
            iterations = int(parts[2])
            salt = parts[3]
            stored_key = parts[4]
            
            new_key = hashlib.pbkdf2_hmac(
                'sha256', 
                password.encode('utf-8'), 
                salt.encode('utf-8'), 
                iterations
            )
            return new_key.hex() == stored_key
        except (ValueError, IndexError, TypeError, RuntimeError) as verify_err:
            logger.error(f"Password verification error ({type(verify_err).__name__}): {verify_err}")
            return False

    async def authenticate(self, username: str, password: str) -> Optional[Operator]:
        """Authenticate an operator by username and password"""
        query = """
            SELECT operator_id, username, email, password_hash, tenant_id, role, is_active, created_at, last_login
            FROM operators
            WHERE username = $1 AND is_active = TRUE
        """
        async with self.db.acquire() as conn:
            async with conn.transaction():
                # Login happens before a tenant is known, so use the explicit
                # per-transaction RLS bypass while verifying credentials only.
                await conn.execute("SET LOCAL app.admin_bypass = 'true'")
                row = await conn.fetchrow(query, username)
                
                if not row:
                    return None
                
                if self.verify_password(password, row['password_hash']):
                    await conn.execute(
                        "UPDATE operators SET last_login = NOW() WHERE operator_id = $1",
                        row['operator_id']
                    )
                    return Operator(**dict(row))
                
                return None

    async def create_operator(self, username: str, email: str, password: str, tenant_id: str, role: str = 'operator') -> str:
        """Create a new operator (internal use or admin only)"""
        operator_id = f"op_{secrets.token_hex(8)}"
        password_hash = self.hash_password(password)
        
        query = """
            INSERT INTO operators (operator_id, username, email, password_hash, tenant_id, role)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING operator_id
        """
        async with self.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SET LOCAL app.admin_bypass = 'true'")
                return await conn.fetchval(query, operator_id, username, email, password_hash, tenant_id, role)
