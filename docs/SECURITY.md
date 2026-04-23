# Security — Tenant Data Isolation

## Critical Security Constraint

**Every database connection must have tenant context set.**

Without tenant context:
- RLS policies don't work
- Queries can see other tenants' data
- Data isolation is compromised

## How It Works

1. FastAPI middleware intercepts every request
2. Extracts `X-Tenant-ID` header
3. Sets tenant context in Python (`contextvars`)
4. Upon `Pool.acquire()`, the `TenantAwarePool` automatically runs: `SELECT set_tenant_context('acme')`
5. RLS policies automatically filter by `current_setting('app.current_tenant_id')`
6. Context automatically clears when the connection is released to the pool.

## RLS Policies

All tables have policies similar to:
```sql
CREATE POLICY actions_tenant_isolation ON actions
  FOR ALL
  USING (tenant_id = get_tenant_context() OR admin_bypass_rls());
```

This means:
- SELECT only returns rows where tenant_id = `get_tenant_context()`
- UPDATE/DELETE only affects rows where tenant_id = `get_tenant_context()`
- INSERT must set tenant_id to `get_tenant_context()`

## Testing Data Isolation

```python
# Test that acme can't see competitor's data
async with tenant_scope(tenant_id="acme"):
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM actions WHERE id = 'competitor_action'")
        assert result is None  # RLS blocks it
```

## Admin Bypass (Migrations Only)

For database migrations, you can bypass RLS:

```python
async with tenant_scope(tenant_id="system", is_admin=True):
    async with pool.acquire() as conn:
        await conn.execute("UPDATE actions SET status = 'approved'")
```

**DANGER:** Only use for system maintenance. Never in user-facing endpoints.

## Deployment Checklist

Before deploying to production:

- [x] Middleware is registered on app startup
- [x] All tables have RLS policies enabled
- [x] RLS policies check `get_tenant_context()`
- [x] Test suite includes cross-tenant isolation tests
- [x] Logging captures all tenant context operations
- [x] Alerts fire on missing context attempts
- [x] Admin bypass is explicitly logged
