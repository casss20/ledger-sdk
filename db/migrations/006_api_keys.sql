-- ============================================================================
-- MIGRATION 006: API key runtime compatibility
-- ============================================================================
--
-- Earlier branches created api_keys with a smaller shape. The current runtime
-- needs Stripe-style key IDs plus hashed secrets, while older repository helper
-- methods still use key_hash/scopes. This migration makes either starting point
-- converge on the same compatible schema.

CREATE TABLE IF NOT EXISTS api_keys (
    id BIGSERIAL PRIMARY KEY,
    key_id TEXT NOT NULL UNIQUE DEFAULT ('gk_legacy_' || gen_random_uuid()::text),
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT 'API key',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS key_hash TEXT;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS key_secret_hash TEXT;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS environment TEXT NOT NULL DEFAULT 'live';
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMPTZ;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS revoked BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS scopes JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS permissions JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS rate_limit_rps INTEGER NOT NULL DEFAULT 1000;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'api_keys'
          AND column_name = 'key_id'
          AND data_type = 'uuid'
    ) THEN
        ALTER TABLE api_keys ALTER COLUMN key_id DROP DEFAULT;
        ALTER TABLE api_keys ALTER COLUMN key_id TYPE TEXT USING key_id::text;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'api_keys'
          AND column_name = 'key_hash'
          AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE api_keys ALTER COLUMN key_hash DROP NOT NULL;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'api_keys'
          AND column_name = 'key_secret_hash'
          AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE api_keys ALTER COLUMN key_secret_hash DROP NOT NULL;
    END IF;
END $$;

ALTER TABLE api_keys ALTER COLUMN key_id SET DEFAULT ('gk_legacy_' || gen_random_uuid()::text);

UPDATE api_keys SET name = 'API key' WHERE name IS NULL;
UPDATE api_keys SET environment = 'live' WHERE environment IS NULL;
UPDATE api_keys SET status = 'active' WHERE status IS NULL;
UPDATE api_keys SET revoked = FALSE WHERE revoked IS NULL;
UPDATE api_keys SET scopes = '[]'::jsonb WHERE scopes IS NULL;
UPDATE api_keys SET permissions = '[]'::jsonb WHERE permissions IS NULL;
UPDATE api_keys SET rate_limit_rps = 1000 WHERE rate_limit_rps IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_key_id ON api_keys (key_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_key_hash_unique ON api_keys (key_hash) WHERE key_hash IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys (tenant_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_secret_hash ON api_keys (key_secret_hash);

ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS api_keys_tenant_isolation ON api_keys;
CREATE POLICY api_keys_tenant_isolation ON api_keys
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

ALTER TABLE api_keys FORCE ROW LEVEL SECURITY;
