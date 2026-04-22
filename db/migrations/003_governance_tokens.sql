-- Governance tokens table (strict RLS)
-- Phase 1: gt_ Governance Token System

CREATE TABLE IF NOT EXISTS governance_tokens (
    token_id TEXT PRIMARY KEY,
    token_type TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    agent_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    content_hash TEXT NOT NULL,
    chain_hash TEXT NOT NULL,
    decision_trace JSONB NOT NULL,
    policy_version TEXT,
    previous_token_id TEXT REFERENCES governance_tokens(token_id)
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_gt_tenant ON governance_tokens (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gt_agent ON governance_tokens (agent_id, created_at DESC) WHERE agent_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_gt_chain ON governance_tokens (previous_token_id);

-- Enable RLS (strict, no escape hatch)
ALTER TABLE governance_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE governance_tokens FORCE ROW LEVEL SECURITY;

-- Tenant isolation policy
CREATE POLICY tenant_isolation ON governance_tokens
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

-- Tokens are append-only (no UPDATE/DELETE)
REVOKE UPDATE, DELETE ON governance_tokens FROM PUBLIC;
