-- 008_billing.sql
-- Stripe-backed billing and entitlements infrastructure

-- 1. Billing Customers
CREATE TABLE billing_customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL UNIQUE,
    account_owner_user_id UUID NULL,
    billing_email TEXT NOT NULL,
    company_name TEXT NULL,
    stripe_customer_id TEXT UNIQUE,
    stripe_default_payment_method_id TEXT NULL,
    status TEXT NOT NULL DEFAULT 'active', -- active | disabled
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Billing Plans
CREATE TABLE billing_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT NOT NULL UNIQUE, -- free | pro | enterprise
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

-- 3. Billing Subscriptions
CREATE TABLE billing_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL UNIQUE,
    billing_customer_id UUID NOT NULL REFERENCES billing_customers(id) ON DELETE CASCADE,
    plan_code TEXT NOT NULL REFERENCES billing_plans(code),
    stripe_subscription_id TEXT NULL UNIQUE,
    stripe_price_id TEXT NULL,
    status TEXT NOT NULL, -- trialing | active | past_due | unpaid | canceled | incomplete | incomplete_expired
    collection_method TEXT NULL, -- charge_automatically | send_invoice
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

-- 4. Billing Usage Monthly
CREATE TABLE billing_usage_monthly (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    period_ym TEXT NOT NULL, -- 2026-04
    api_calls BIGINT NOT NULL DEFAULT 0,
    active_agents BIGINT NOT NULL DEFAULT 0,
    approval_requests BIGINT NOT NULL DEFAULT 0,
    governed_actions BIGINT NOT NULL DEFAULT 0,
    unique_users BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, period_ym)
);

-- 5. Billing Event Log (Idempotency)
CREATE TABLE billing_event_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL, -- stripe
    provider_event_id TEXT NOT NULL UNIQUE,
    provider_event_type TEXT NOT NULL,
    tenant_id TEXT NULL,
    status TEXT NOT NULL DEFAULT 'received', -- received | processed | failed | ignored
    payload_json JSONB NOT NULL,
    error_text TEXT NULL,
    processed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Billing Entitlement Overrides
CREATE TABLE billing_entitlement_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    feature_key TEXT NOT NULL,
    enabled BOOLEAN NOT NULL,
    reason TEXT NULL,
    expires_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, feature_key)
);

-- Indexes for performance
CREATE INDEX idx_billing_customers_tenant ON billing_customers(tenant_id);
CREATE INDEX idx_billing_subscriptions_tenant ON billing_subscriptions(tenant_id);
CREATE INDEX idx_billing_usage_tenant_period ON billing_usage_monthly(tenant_id, period_ym);
CREATE INDEX idx_billing_event_log_provider_id ON billing_event_log(provider_event_id);
