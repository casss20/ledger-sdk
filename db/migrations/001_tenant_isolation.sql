-- ============================================================================
-- MIGRATION: Add tenant_id to core tables missing it
-- Stream 1: Tenant Isolation Model — STRICT RLS (no NULL bypass)
-- ============================================================================

-- Add tenant_id to capabilities (via actor reference, but explicit for RLS/query perf)
ALTER TABLE capabilities ADD COLUMN IF NOT EXISTS tenant_id TEXT;
CREATE INDEX IF NOT EXISTS idx_capabilities_tenant_id ON capabilities (tenant_id);

-- Add tenant_id to decisions (denormalized from actions for fast filtering)
ALTER TABLE decisions ADD COLUMN IF NOT EXISTS tenant_id TEXT;
CREATE INDEX IF NOT EXISTS idx_decisions_tenant_id ON decisions (tenant_id);
CREATE INDEX IF NOT EXISTS idx_decisions_tenant_status ON decisions (tenant_id, status);

-- Add tenant_id to approvals (denormalized from actions for fast filtering)
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS tenant_id TEXT;
CREATE INDEX IF NOT EXISTS idx_approvals_tenant_id ON approvals (tenant_id);
CREATE INDEX IF NOT EXISTS idx_approvals_tenant_status ON approvals (tenant_id, status);

-- Add tenant_id to execution_results (denormalized from actions)
ALTER TABLE execution_results ADD COLUMN IF NOT EXISTS tenant_id TEXT;
CREATE INDEX IF NOT EXISTS idx_execution_results_tenant_id ON execution_results (tenant_id);

-- ============================================================================
-- RLS POLICIES: Strict tenant isolation at the database level
-- NO NULL-context bypass. Tenant context REQUIRED for all access.
-- ============================================================================

-- Enable RLS on core tables
ALTER TABLE actors ENABLE ROW LEVEL SECURITY;
ALTER TABLE policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE capabilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE kill_switches ENABLE ROW LEVEL SECURITY;
ALTER TABLE actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE execution_results ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any (idempotent)
DO $$
BEGIN
    DROP POLICY IF EXISTS actors_tenant_isolation ON actors;
    DROP POLICY IF EXISTS actors_admin_bypass ON actors;
    DROP POLICY IF EXISTS policies_tenant_isolation ON policies;
    DROP POLICY IF EXISTS policies_admin_bypass ON policies;
    DROP POLICY IF EXISTS capabilities_tenant_isolation ON capabilities;
    DROP POLICY IF EXISTS capabilities_admin_bypass ON capabilities;
    DROP POLICY IF EXISTS kill_switches_tenant_isolation ON kill_switches;
    DROP POLICY IF EXISTS kill_switches_admin_bypass ON kill_switches;
    DROP POLICY IF EXISTS actions_tenant_isolation ON actions;
    DROP POLICY IF EXISTS actions_admin_bypass ON actions;
    DROP POLICY IF EXISTS decisions_tenant_isolation ON decisions;
    DROP POLICY IF EXISTS decisions_admin_bypass ON decisions;
    DROP POLICY IF EXISTS approvals_tenant_isolation ON approvals;
    DROP POLICY IF EXISTS approvals_admin_bypass ON approvals;
    DROP POLICY IF EXISTS audit_events_tenant_isolation ON audit_events;
    DROP POLICY IF EXISTS audit_events_admin_bypass ON audit_events;
    DROP POLICY IF EXISTS execution_results_tenant_isolation ON execution_results;
    DROP POLICY IF EXISTS execution_results_admin_bypass ON execution_results;
END $$;

-- Helper function to set tenant context from application
CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id TEXT)
RETURNS VOID AS $$
BEGIN
    PERFORM set_config('app.current_tenant_id', p_tenant_id, TRUE);
END;
$$ LANGUAGE plpgsql;

-- Helper function to get tenant context
CREATE OR REPLACE FUNCTION get_tenant_context()
RETURNS TEXT AS $$
BEGIN
    RETURN current_setting('app.current_tenant_id', TRUE);
END;
$$ LANGUAGE plpgsql;

-- Explicit admin bypass function — requires deliberate SET app.admin_bypass = 'true'
CREATE OR REPLACE FUNCTION admin_bypass_rls()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN current_setting('app.admin_bypass', TRUE) = 'true';
END;
$$ LANGUAGE plpgsql;

-- RLS policies: STRICT tenant isolation
-- No NULL-context bypass. A connection without tenant context is DENIED.
-- Admin bypass is available ONLY when explicitly enabled per-session.
CREATE POLICY actors_tenant_isolation ON actors
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

CREATE POLICY policies_tenant_isolation ON policies
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

CREATE POLICY capabilities_tenant_isolation ON capabilities
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

CREATE POLICY kill_switches_tenant_isolation ON kill_switches
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

CREATE POLICY actions_tenant_isolation ON actions
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

CREATE POLICY decisions_tenant_isolation ON decisions
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

CREATE POLICY approvals_tenant_isolation ON approvals
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

CREATE POLICY audit_events_tenant_isolation ON audit_events
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

CREATE POLICY execution_results_tenant_isolation ON execution_results
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

-- Force RLS for table owners too
ALTER TABLE actors FORCE ROW LEVEL SECURITY;
ALTER TABLE policies FORCE ROW LEVEL SECURITY;
ALTER TABLE capabilities FORCE ROW LEVEL SECURITY;
ALTER TABLE kill_switches FORCE ROW LEVEL SECURITY;
ALTER TABLE actions FORCE ROW LEVEL SECURITY;
ALTER TABLE decisions FORCE ROW LEVEL SECURITY;
ALTER TABLE approvals FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;
ALTER TABLE execution_results FORCE ROW LEVEL SECURITY;
