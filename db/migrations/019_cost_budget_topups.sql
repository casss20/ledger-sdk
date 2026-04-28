-- ============================================================================
-- MIGRATION 019: Cost Budget Top-ups
-- ============================================================================
--
-- Adds an enterprise admin adjustment flow for LLM cost budgets.
-- Top-ups increase the configured cost_budgets.amount_cents cap and are
-- recorded append-only for auditability.

CREATE TABLE IF NOT EXISTS cost_budget_adjustments (
    adjustment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    budget_id UUID NOT NULL REFERENCES cost_budgets(budget_id) ON DELETE RESTRICT,
    tenant_id TEXT NOT NULL,
    adjustment_type TEXT NOT NULL CHECK (adjustment_type IN ('top_up')),
    amount_cents BIGINT NOT NULL CHECK (amount_cents > 0),
    previous_amount_cents BIGINT NOT NULL CHECK (previous_amount_cents >= 0),
    resulting_amount_cents BIGINT NOT NULL CHECK (resulting_amount_cents >= previous_amount_cents),
    reason TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_cost_budget_adjustments_budget_ts
    ON cost_budget_adjustments (budget_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cost_budget_adjustments_tenant_ts
    ON cost_budget_adjustments (tenant_id, created_at DESC);

CREATE OR REPLACE FUNCTION forbid_cost_budget_adjustment_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'cost_budget_adjustments is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_forbid_cost_budget_adjustment_update ON cost_budget_adjustments;
CREATE TRIGGER trg_forbid_cost_budget_adjustment_update
    BEFORE UPDATE ON cost_budget_adjustments
    FOR EACH ROW
    EXECUTE FUNCTION forbid_cost_budget_adjustment_mutation();

DROP TRIGGER IF EXISTS trg_forbid_cost_budget_adjustment_delete ON cost_budget_adjustments;
CREATE TRIGGER trg_forbid_cost_budget_adjustment_delete
    BEFORE DELETE ON cost_budget_adjustments
    FOR EACH ROW
    EXECUTE FUNCTION forbid_cost_budget_adjustment_mutation();

ALTER TABLE cost_budget_adjustments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS cost_budget_adjustments_tenant_isolation ON cost_budget_adjustments;
CREATE POLICY cost_budget_adjustments_tenant_isolation ON cost_budget_adjustments
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

ALTER TABLE cost_budget_adjustments FORCE ROW LEVEL SECURITY;

DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'governance_audit_log'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) LIKE '%event_type%';

    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE governance_audit_log DROP CONSTRAINT %I', constraint_name);
    END IF;
END $$;

ALTER TABLE governance_audit_log
    ADD CONSTRAINT governance_audit_log_event_type_check CHECK (event_type IN (
        'token.verification',
        'decision.verification',
        'execution.allowed',
        'execution.blocked',
        'execution.rate_limited',
        'decision.created',
        'token.derived',
        'token.revoked',
        'decision.revoked',
        'cost.budget_top_up'
    ));

COMMENT ON TABLE cost_budget_adjustments IS 'Append-only enterprise budget top-up and adjustment records.';
