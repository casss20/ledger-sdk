-- ============================================================================
-- MIGRATION 007: Operator User Management
-- ============================================================================

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

-- Indexes for lookup
CREATE INDEX IF NOT EXISTS idx_operators_username ON operators (username);
CREATE INDEX IF NOT EXISTS idx_operators_tenant ON operators (tenant_id);

-- RLS: Strict tenant isolation
ALTER TABLE operators ENABLE ROW LEVEL SECURITY;

CREATE POLICY operators_tenant_isolation ON operators
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

ALTER TABLE operators FORCE ROW LEVEL SECURITY;

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_operators_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_operators_timestamp
    BEFORE UPDATE ON operators
    FOR EACH ROW
    EXECUTE FUNCTION update_operators_timestamp();

-- Comment
COMMENT ON TABLE operators IS 'Administrative dashboard operators and security personnel.';
