-- ============================================================================
-- MIGRATION 009: Runtime compatibility guardrails
-- ============================================================================
--
-- Safe to run after the base schema and all earlier migrations. It repairs
-- databases created from older branches so the current Citadel API can boot,
-- authenticate dashboard users, create SDK keys, and write tenant-aware rows.

-- Core tenant columns expected by Repository writes.
ALTER TABLE capabilities ADD COLUMN IF NOT EXISTS tenant_id TEXT;
ALTER TABLE decisions ADD COLUMN IF NOT EXISTS tenant_id TEXT;
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS tenant_id TEXT;
ALTER TABLE execution_results ADD COLUMN IF NOT EXISTS tenant_id TEXT;

CREATE INDEX IF NOT EXISTS idx_capabilities_tenant_id ON capabilities (tenant_id);
CREATE INDEX IF NOT EXISTS idx_decisions_tenant_id ON decisions (tenant_id);
CREATE INDEX IF NOT EXISTS idx_decisions_tenant_status ON decisions (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_approvals_tenant_id ON approvals (tenant_id);
CREATE INDEX IF NOT EXISTS idx_approvals_tenant_status ON approvals (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_execution_results_tenant_id ON execution_results (tenant_id);

-- Helper functions required by tenant RLS policies.
CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id TEXT)
RETURNS VOID AS $$
BEGIN
    PERFORM set_config('app.current_tenant_id', p_tenant_id, TRUE);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_tenant_context()
RETURNS TEXT AS $$
BEGIN
    RETURN current_setting('app.current_tenant_id', TRUE);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION admin_bypass_rls()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN current_setting('app.admin_bypass', TRUE) = 'true';
END;
$$ LANGUAGE plpgsql;

-- Operators needed for dashboard login.
CREATE TABLE IF NOT EXISTS operators (
    operator_id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'operator' CHECK (role IN ('admin', 'operator', 'auditor')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_operators_username ON operators (username);
CREATE INDEX IF NOT EXISTS idx_operators_tenant ON operators (tenant_id);

ALTER TABLE operators ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS operators_tenant_isolation ON operators;
CREATE POLICY operators_tenant_isolation ON operators
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());
ALTER TABLE operators FORCE ROW LEVEL SECURITY;

-- API keys: compatible with both current APIKeyService and older Repository helpers.
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

-- Billing tables queried by /v1/billing routes.
CREATE TABLE IF NOT EXISTS billing_customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL UNIQUE,
    account_owner_user_id UUID NULL,
    billing_email TEXT NOT NULL,
    company_name TEXT NULL,
    stripe_customer_id TEXT UNIQUE,
    stripe_default_payment_method_id TEXT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS billing_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    monthly_price_cents INTEGER NOT NULL DEFAULT 0,
    stripe_price_id TEXT NULL UNIQUE,
    api_calls_limit INTEGER NULL,
    active_agents_limit INTEGER NULL,
    approval_requests_limit INTEGER NULL,
    seats_limit INTEGER NULL,
    audit_retention_days INTEGER NULL,
    features_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_public BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS billing_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL UNIQUE,
    billing_customer_id UUID NOT NULL REFERENCES billing_customers(id) ON DELETE CASCADE,
    plan_code TEXT NOT NULL REFERENCES billing_plans(code),
    stripe_subscription_id TEXT NULL UNIQUE,
    stripe_price_id TEXT NULL,
    status TEXT NOT NULL,
    collection_method TEXT NULL,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    current_period_start TIMESTAMPTZ NULL,
    current_period_end TIMESTAMPTZ NULL,
    trial_start TIMESTAMPTZ NULL,
    trial_end TIMESTAMPTZ NULL,
    last_invoice_id TEXT NULL,
    last_invoice_status TEXT NULL,
    last_payment_status TEXT NULL,
    grace_until TIMESTAMPTZ NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS billing_usage_monthly (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    period_ym TEXT NOT NULL,
    api_calls BIGINT NOT NULL DEFAULT 0,
    active_agents BIGINT NOT NULL DEFAULT 0,
    approval_requests BIGINT NOT NULL DEFAULT 0,
    governed_actions BIGINT NOT NULL DEFAULT 0,
    unique_users BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, period_ym)
);

CREATE TABLE IF NOT EXISTS billing_event_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    provider_event_id TEXT NOT NULL UNIQUE,
    provider_event_type TEXT NOT NULL,
    tenant_id TEXT NULL,
    status TEXT NOT NULL DEFAULT 'received',
    payload_json JSONB NOT NULL,
    error_text TEXT NULL,
    processed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS billing_entitlement_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    feature_key TEXT NOT NULL,
    enabled BOOLEAN NOT NULL,
    reason TEXT NULL,
    expires_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, feature_key)
);

CREATE INDEX IF NOT EXISTS idx_billing_customers_tenant ON billing_customers (tenant_id);
CREATE INDEX IF NOT EXISTS idx_billing_subscriptions_tenant ON billing_subscriptions (tenant_id);
CREATE INDEX IF NOT EXISTS idx_billing_usage_tenant_period ON billing_usage_monthly (tenant_id, period_ym);
CREATE INDEX IF NOT EXISTS idx_billing_event_log_provider_id ON billing_event_log (provider_event_id);

INSERT INTO billing_plans (
    code,
    name,
    monthly_price_cents,
    api_calls_limit,
    active_agents_limit,
    approval_requests_limit,
    audit_retention_days,
    features_json
) VALUES (
    'free',
    'Free',
    0,
    10000,
    5,
    100,
    30,
    '{"dashboard": true, "api_keys": true}'::jsonb
) ON CONFLICT (code) DO NOTHING;
