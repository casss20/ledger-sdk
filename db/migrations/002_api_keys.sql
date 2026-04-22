-- ============================================================================
-- MIGRATION: API Key Provisioning (Stream 2)
-- STRICT RLS — no NULL-context bypass.
-- ============================================================================

CREATE TABLE IF NOT EXISTS api_keys (
    key_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       TEXT NOT NULL,
    key_hash        TEXT NOT NULL UNIQUE,
    name            TEXT,
    scopes          JSONB DEFAULT '[]',
    expires_at      TIMESTAMPTZ,
    last_used_at    TIMESTAMPTZ,
    revoked         BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_tenant_id ON api_keys (tenant_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys (key_hash);

-- Enable strict RLS
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys FORCE ROW LEVEL SECURITY;

-- Strict policy: tenant context required, explicit admin bypass only
CREATE POLICY api_keys_tenant_isolation ON api_keys
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());
