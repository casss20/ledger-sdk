-- ============================================================================
-- MIGRATION: API keys
-- ============================================================================
--
-- This table intentionally supports both the current dashboard/API-key service
-- and the older Repository helper methods. Keep future changes additive so
-- existing deployments can run migrations safely.

CREATE TABLE IF NOT EXISTS api_keys (
    id BIGSERIAL PRIMARY KEY,
    key_id TEXT NOT NULL UNIQUE DEFAULT ('gk_legacy_' || gen_random_uuid()::text),
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT 'API key',
    key_hash TEXT UNIQUE,
    key_secret_hash TEXT,
    environment TEXT NOT NULL DEFAULT 'live',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'active',
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb,
    rate_limit_rps INTEGER NOT NULL DEFAULT 1000,

    CONSTRAINT valid_api_key_environment CHECK (environment IN ('live', 'test')),
    CONSTRAINT valid_api_key_status CHECK (status IN ('active', 'revoked', 'expired'))
);

CREATE INDEX IF NOT EXISTS idx_api_keys_key_id ON api_keys (key_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant_id ON api_keys (tenant_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys (key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_secret_hash ON api_keys (key_secret_hash);

ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS api_keys_tenant_isolation ON api_keys;
CREATE POLICY api_keys_tenant_isolation ON api_keys
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

ALTER TABLE api_keys FORCE ROW LEVEL SECURITY;
