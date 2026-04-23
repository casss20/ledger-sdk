"""
Tenant context injection — ensures every database connection 
knows which tenant it's serving.

Why separate file: Tenant context is used by middleware, kernel, 
and services. This keeps it centralized.
"""

import contextvars
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import AsyncIterator

# Context variable — automatically scoped to current async context
_tenant_context_var: contextvars.ContextVar['TenantContext | None'] = (
    contextvars.ContextVar("tenant_context", default=None)
)

@dataclass(frozen=True)
class TenantContext:
    """Immutable tenant context for current request"""
    tenant_id: str
    user_id: str | None = None
    is_admin: bool = False
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            object.__setattr__(self, 'created_at', datetime.now(timezone.utc))

class TenantContextError(Exception):
    """Raised when tenant context is missing or invalid"""
    pass

def get_tenant_context() -> TenantContext:
    """Get current tenant context (fails if not in scope)"""
    ctx = _tenant_context_var.get()
    if ctx is None:
        raise TenantContextError(
            "No tenant context. Every request must set tenant_id. "
            "This is a security violation."
        )
    if not ctx.tenant_id:
        raise TenantContextError(
            f"Tenant context has empty tenant_id. Invalid state."
        )
    return ctx

def get_tenant_id() -> str:
    """Get current tenant_id (convenience method)"""
    return get_tenant_context().tenant_id

def is_admin_context() -> bool:
    """Check if current context is admin (bypass) mode"""
    ctx = _tenant_context_var.get()
    return ctx.is_admin if ctx else False

@asynccontextmanager
async def tenant_scope(
    tenant_id: str,
    user_id: str | None = None,
    is_admin: bool = False,
) -> AsyncIterator[TenantContext]:
    """
    Enter tenant context scope.
    
    Usage:
        async with tenant_scope(tenant_id="acme", user_id="user1"):
            # All DB queries inside use tenant_id = "acme"
            result = await db.query(...)
        # Context automatically cleared here
    
    Args:
        tenant_id: The tenant to operate as
        user_id: Optional user within the tenant
        is_admin: If True, allows bypassing some RLS policies (migrations only)
    
    Security note:
        - is_admin should NEVER be True for user requests
        - is_admin should ONLY be True for:
          * Database migrations
          * System maintenance
          * Explicit admin API endpoints with MFA
    """
    ctx = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        is_admin=is_admin,
    )
    
    # Set in context variable (automatically cleared on scope exit)
    token = _tenant_context_var.set(ctx)
    
    try:
        yield ctx
    finally:
        # Automatic cleanup on scope exit
        _tenant_context_var.reset(token)

@asynccontextmanager
async def set_db_tenant_context(
    connection,
    tenant_id: str,
) -> AsyncIterator[None]:
    """
    Set PostgreSQL session variable for RLS.
    """
    await connection.execute(
        "SELECT set_tenant_context($1)",
        tenant_id
    )
    
    try:
        yield
    finally:
        try:
            await connection.execute("RESET app.current_tenant_id")
        except:
            pass

class TenantAwarePool:
    """Wraps an asyncpg Pool to automatically set tenant context on acquire()"""
    def __init__(self, pool):
        self._pool = pool
        
    @asynccontextmanager
    async def acquire(self):
        async with self._pool.acquire() as conn:
            try:
                if is_admin_context():
                    await conn.execute("SET app.admin_bypass = 'true'")
                else:
                    ctx = get_tenant_context()
                    await conn.execute("SELECT set_tenant_context($1)", ctx.tenant_id)
                yield conn
            finally:
                # Always reset context before returning to pool
                try:
                    await conn.execute("RESET app.current_tenant_id")
                    await conn.execute("RESET app.admin_bypass")
                except:
                    pass

    async def close(self):
        await self._pool.close()

class AdminBypassContext:
    """
    Context for admin operations that need to bypass RLS.
    
    DANGER: Only use for:
      - Database migrations
      - System maintenance
      - Explicit admin endpoints with MFA
    
    Never use for user-facing endpoints.
    
    Usage:
        async with AdminBypassContext(db).execute():
            # RLS is disabled here
            await db.query("UPDATE users SET role = 'admin'")
    """
    
    def __init__(self, connection):
        self.connection = connection
    
    @asynccontextmanager
    async def execute(self, tenant_id: str = "system"):
        """Execute code with RLS bypassed"""
        # Set app.bypass_rls = true (if you implement this at DB level)
        # OR rely on PostgreSQL BYPASSRLS role
        
        # For now, use a special system tenant
        async with tenant_scope(
            tenant_id=tenant_id,
            is_admin=True,
        ):
            # Disable RLS at session level (PostgreSQL 14+)
            await self.connection.execute(
                "SET SESSION SESSION AUTHORIZATION DEFAULT"
            )
            try:
                yield
            finally:
                await self.connection.execute(
                    "RESET SESSION SESSION AUTHORIZATION"
                )
