-- ============================================================================
-- MIGRATION 018: Cost Controls & Budgets
-- ============================================================================
--
-- Adds tenant-first LLM spend controls to the commercial control plane.
--
-- Design:
--   - cost_budgets stores operator-configured caps.
--   - cost_spend_events records attributed LLM spend after execution.
--   - cost_enforcement_events records deterministic pre-request budget checks.
--
-- These tables are commercial/cost-control state. They do not replace
-- audit_events or governance_audit_log.

CREATE TABLE IF NOT EXISTS cost_budgets (
    budget_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    scope_type TEXT NOT NULL CHECK (scope_type IN ('tenant', 'project', 'agent', 'api_key')),
    scope_value TEXT NOT NULL,
    amount_cents BIGINT NOT NULL CHECK (amount_cents > 0),
    currency TEXT NOT NULL DEFAULT 'usd',
    reset_period TEXT NOT NULL CHECK (reset_period IN ('daily', 'weekly', 'monthly')),
    enforcement_action TEXT NOT NULL CHECK (enforcement_action IN ('block', 'require_approval', 'throttle')),
    warning_threshold_percent INTEGER NOT NULL DEFAULT 80 CHECK (
        warning_threshold_percent >= 1 AND warning_threshold_percent <= 100
    ),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cost_budgets_tenant_active
    ON cost_budgets (tenant_id, is_active);
CREATE INDEX IF NOT EXISTS idx_cost_budgets_scope
    ON cost_budgets (tenant_id, scope_type, scope_value)
    WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS cost_spend_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    event_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    provider TEXT,
    model TEXT,
    input_tokens BIGINT NOT NULL DEFAULT 0 CHECK (input_tokens >= 0),
    output_tokens BIGINT NOT NULL DEFAULT 0 CHECK (output_tokens >= 0),
    cost_cents BIGINT NOT NULL CHECK (cost_cents >= 0),
    currency TEXT NOT NULL DEFAULT 'usd',
    actor_id TEXT,
    project_id TEXT,
    api_key_id TEXT,
    request_id TEXT,
    decision_id TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_cost_spend_tenant_ts
    ON cost_spend_events (tenant_id, event_ts DESC);
CREATE INDEX IF NOT EXISTS idx_cost_spend_project_ts
    ON cost_spend_events (tenant_id, project_id, event_ts DESC)
    WHERE project_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cost_spend_actor_ts
    ON cost_spend_events (tenant_id, actor_id, event_ts DESC)
    WHERE actor_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cost_spend_api_key_ts
    ON cost_spend_events (tenant_id, api_key_id, event_ts DESC)
    WHERE api_key_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS cost_enforcement_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    event_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    budget_id UUID REFERENCES cost_budgets(budget_id) ON DELETE SET NULL,
    scope_type TEXT NOT NULL,
    scope_value TEXT NOT NULL,
    enforcement_action TEXT NOT NULL CHECK (enforcement_action IN ('allow', 'block', 'require_approval', 'throttle')),
    projected_cost_cents BIGINT NOT NULL CHECK (projected_cost_cents >= 0),
    current_spend_cents BIGINT NOT NULL CHECK (current_spend_cents >= 0),
    budget_amount_cents BIGINT,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    actor_id TEXT,
    project_id TEXT,
    api_key_id TEXT,
    request_id TEXT,
    decision_id TEXT,
    reason TEXT NOT NULL,
    context_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_cost_enforcement_tenant_ts
    ON cost_enforcement_events (tenant_id, event_ts DESC);
CREATE INDEX IF NOT EXISTS idx_cost_enforcement_budget_ts
    ON cost_enforcement_events (budget_id, event_ts DESC)
    WHERE budget_id IS NOT NULL;

CREATE OR REPLACE FUNCTION forbid_cost_event_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'cost event tables are append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_forbid_cost_spend_update ON cost_spend_events;
CREATE TRIGGER trg_forbid_cost_spend_update
    BEFORE UPDATE ON cost_spend_events
    FOR EACH ROW
    EXECUTE FUNCTION forbid_cost_event_mutation();

DROP TRIGGER IF EXISTS trg_forbid_cost_spend_delete ON cost_spend_events;
CREATE TRIGGER trg_forbid_cost_spend_delete
    BEFORE DELETE ON cost_spend_events
    FOR EACH ROW
    EXECUTE FUNCTION forbid_cost_event_mutation();

DROP TRIGGER IF EXISTS trg_forbid_cost_enforcement_update ON cost_enforcement_events;
CREATE TRIGGER trg_forbid_cost_enforcement_update
    BEFORE UPDATE ON cost_enforcement_events
    FOR EACH ROW
    EXECUTE FUNCTION forbid_cost_event_mutation();

DROP TRIGGER IF EXISTS trg_forbid_cost_enforcement_delete ON cost_enforcement_events;
CREATE TRIGGER trg_forbid_cost_enforcement_delete
    BEFORE DELETE ON cost_enforcement_events
    FOR EACH ROW
    EXECUTE FUNCTION forbid_cost_event_mutation();

DROP TRIGGER IF EXISTS trg_cost_budgets_updated_at ON cost_budgets;
CREATE TRIGGER trg_cost_budgets_updated_at
    BEFORE UPDATE ON cost_budgets
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

ALTER TABLE cost_budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_spend_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_enforcement_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS cost_budgets_tenant_isolation ON cost_budgets;
CREATE POLICY cost_budgets_tenant_isolation ON cost_budgets
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

DROP POLICY IF EXISTS cost_spend_tenant_isolation ON cost_spend_events;
CREATE POLICY cost_spend_tenant_isolation ON cost_spend_events
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

DROP POLICY IF EXISTS cost_enforcement_tenant_isolation ON cost_enforcement_events;
CREATE POLICY cost_enforcement_tenant_isolation ON cost_enforcement_events
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

ALTER TABLE cost_budgets FORCE ROW LEVEL SECURITY;
ALTER TABLE cost_spend_events FORCE ROW LEVEL SECURITY;
ALTER TABLE cost_enforcement_events FORCE ROW LEVEL SECURITY;

COMMENT ON TABLE cost_budgets IS 'Tenant-scoped LLM cost budgets with deterministic enforcement actions.';
COMMENT ON TABLE cost_spend_events IS 'Append-only LLM spend attribution events.';
COMMENT ON TABLE cost_enforcement_events IS 'Append-only pre-request cost-control enforcement decisions.';
