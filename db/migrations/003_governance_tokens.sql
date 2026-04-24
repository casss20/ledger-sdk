-- ============================================================================
-- MIGRATION: Governance decisions + capability tokens (decision-centric)
-- ============================================================================

-- Drop old tokens table if exists (from earlier iteration)
DROP TABLE IF EXISTS governance_tokens CASCADE;

-- ============================================================================
-- GOVERNANCE DECISIONS (first-class)
-- ============================================================================
CREATE TABLE IF NOT EXISTS governance_decisions (
    decision_id     TEXT PRIMARY KEY,
    decision_type   TEXT NOT NULL CHECK (decision_type IN ('allow', 'deny', 'pending', 'revoked')),
    tenant_id       TEXT NOT NULL,
    actor_id        TEXT NOT NULL,
    action          TEXT NOT NULL,
    scope_actions   TEXT[] NOT NULL DEFAULT '{}',
    scope_resources TEXT[] NOT NULL DEFAULT '{}',
    constraints     JSONB NOT NULL DEFAULT '{}',
    expiry          TIMESTAMPTZ,
    kill_switch_scope TEXT NOT NULL DEFAULT 'request',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reason          TEXT
);

CREATE INDEX IF NOT EXISTS idx_gd_tenant ON governance_decisions (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gd_actor  ON governance_decisions (actor_id,  created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gd_type   ON governance_decisions (decision_type, created_at DESC);

ALTER TABLE governance_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE governance_decisions FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS gd_tenant_isolation ON governance_decisions;
CREATE POLICY gd_tenant_isolation ON governance_decisions
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

REVOKE DELETE ON governance_decisions FROM PUBLIC;

-- ============================================================================
-- CAPABILITY TOKENS (optional derivations from decisions)
-- ============================================================================
CREATE TABLE IF NOT EXISTS governance_tokens (
    token_id      TEXT PRIMARY KEY,
    decision_id   TEXT REFERENCES governance_decisions(decision_id),
    tenant_id     TEXT NOT NULL,
    actor_id      TEXT NOT NULL,
    scope_actions TEXT[] NOT NULL DEFAULT '{}',
    scope_resources TEXT[] NOT NULL DEFAULT '{}',
    expiry        TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    chain_hash    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_gt_tenant    ON governance_tokens (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gt_decision  ON governance_tokens (decision_id);
CREATE INDEX IF NOT EXISTS idx_gt_actor     ON governance_tokens (actor_id, created_at DESC);

ALTER TABLE governance_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE governance_tokens FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS gt_tenant_isolation ON governance_tokens;
CREATE POLICY gt_tenant_isolation ON governance_tokens
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

REVOKE UPDATE, DELETE ON governance_tokens FROM PUBLIC;
