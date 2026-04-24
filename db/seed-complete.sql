-- ============================================================================
-- COMPLETE CITADEL DATABASE SETUP
-- Run this in Neon's SQL Editor to create all tables and seed data
-- ============================================================================

-- Tenant context helper functions
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

-- Core tables
CREATE TABLE IF NOT EXISTS actions (
    action_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    payload JSONB,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    action_id TEXT,
    status TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    action_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    requested_by TEXT,
    approved_by TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    action_type TEXT NOT NULL,
    status TEXT,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS kill_switches (
    switch_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    name TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS capabilities (
    capability_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    name TEXT NOT NULL,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    max_uses INTEGER,
    uses INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Operators table
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

-- API keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id BIGSERIAL PRIMARY KEY,
    key_id TEXT NOT NULL UNIQUE,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT 'API key',
    key_hash TEXT,
    key_secret_hash TEXT,
    environment TEXT NOT NULL DEFAULT 'live',
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'active',
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb,
    rate_limit_rps INTEGER NOT NULL DEFAULT 1000,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed default admin
INSERT INTO operators (
    operator_id, username, email, password_hash, tenant_id, role, is_active
) VALUES (
    'op_admin_default',
    'admin',
    'admin@citadel.dev',
    'pbkdf2:sha256:100000:5db6f33028b4733bbbe3056fa0baac71:f2197b34857f8db589d8ff002b9a605f62e3b39d6200feb3df1da202be1c2d95',
    'demo-tenant',
    'admin',
    TRUE
) ON CONFLICT (username) DO NOTHING;

-- Seed some demo data
INSERT INTO actions (action_id, tenant_id, action_type, status)
VALUES 
    ('act_001', 'demo-tenant', 'email.send', 'allowed'),
    ('act_002', 'demo-tenant', 'db.write', 'allowed'),
    ('act_003', 'demo-tenant', 'stripe.charge', 'pending')
ON CONFLICT DO NOTHING;

INSERT INTO decisions (decision_id, tenant_id, action_id, status)
VALUES
    ('dec_001', 'demo-tenant', 'act_001', 'executed'),
    ('dec_002', 'demo-tenant', 'act_002', 'executed'),
    ('dec_003', 'demo-tenant', 'act_003', 'pending')
ON CONFLICT DO NOTHING;

INSERT INTO approvals (approval_id, tenant_id, action_id, status, requested_by, reason)
VALUES
    ('app_001', 'demo-tenant', 'act_003', 'pending', 'agent-1', 'High-value transaction needs approval')
ON CONFLICT DO NOTHING;

INSERT INTO audit_events (event_id, tenant_id, action_type, status)
VALUES
    ('evt_001', 'demo-tenant', 'email.send', 'allowed'),
    ('evt_002', 'demo-tenant', 'db.write', 'allowed'),
    ('evt_003', 'demo-tenant', 'stripe.charge', 'pending')
ON CONFLICT DO NOTHING;

INSERT INTO kill_switches (switch_id, tenant_id, name, enabled)
VALUES
    ('ks_001', 'demo-tenant', 'email_send', FALSE),
    ('ks_002', 'demo-tenant', 'stripe_charge', FALSE),
    ('ks_003', 'demo-tenant', 'db_write', FALSE)
ON CONFLICT DO NOTHING;

INSERT INTO capabilities (capability_id, tenant_id, name, revoked, max_uses, uses)
VALUES
    ('cap_001', 'demo-tenant', 'email', FALSE, 100, 5),
    ('cap_002', 'demo-tenant', 'database', FALSE, 1000, 50),
    ('cap_003', 'demo-tenant', 'payments', FALSE, 50, 0)
ON CONFLICT DO NOTHING;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_actions_tenant ON actions (tenant_id);
CREATE INDEX IF NOT EXISTS idx_decisions_tenant ON decisions (tenant_id);
CREATE INDEX IF NOT EXISTS idx_approvals_tenant ON approvals (tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_tenant ON audit_events (tenant_id);
CREATE INDEX IF NOT EXISTS idx_operators_username ON operators (username);
CREATE INDEX IF NOT EXISTS idx_operators_tenant ON operators (tenant_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys (tenant_id);

-- RLS policies
ALTER TABLE actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE operators ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE capabilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE kill_switches ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS actions_tenant ON actions;
CREATE POLICY actions_tenant ON actions FOR ALL USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

DROP POLICY IF EXISTS decisions_tenant ON decisions;
CREATE POLICY decisions_tenant ON decisions FOR ALL USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

DROP POLICY IF EXISTS approvals_tenant ON approvals;
CREATE POLICY approvals_tenant ON approvals FOR ALL USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

DROP POLICY IF EXISTS audit_events_tenant ON audit_events;
CREATE POLICY audit_events_tenant ON audit_events FOR ALL USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

DROP POLICY IF EXISTS operators_tenant ON operators;
CREATE POLICY operators_tenant ON operators FOR ALL USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

DROP POLICY IF EXISTS api_keys_tenant ON api_keys;
CREATE POLICY api_keys_tenant ON api_keys FOR ALL USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

DROP POLICY IF EXISTS capabilities_tenant ON capabilities;
CREATE POLICY capabilities_tenant ON capabilities FOR ALL USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

DROP POLICY IF EXISTS kill_switches_tenant ON kill_switches;
CREATE POLICY kill_switches_tenant ON kill_switches FOR ALL USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

-- Force RLS
ALTER TABLE actions FORCE ROW LEVEL SECURITY;
ALTER TABLE decisions FORCE ROW LEVEL SECURITY;
ALTER TABLE approvals FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;
ALTER TABLE operators FORCE ROW LEVEL SECURITY;
ALTER TABLE api_keys FORCE ROW LEVEL SECURITY;
ALTER TABLE capabilities FORCE ROW LEVEL SECURITY;
ALTER TABLE kill_switches FORCE ROW LEVEL SECURITY;

-- Verify
SELECT 'Tables created successfully' as status;
SELECT COUNT(*) as operators_count FROM operators;
SELECT COUNT(*) as actions_count FROM actions;
SELECT COUNT(*) as approvals_count FROM approvals WHERE status = 'pending';
