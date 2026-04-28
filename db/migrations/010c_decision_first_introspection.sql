-- ============================================================================
-- MIGRATION 010: Decision-first runtime introspection metadata
-- ============================================================================
--
-- Evolves the existing governance_decisions / governance_tokens tables so
-- high-risk runtime introspection can walk token -> decision -> policy/approval
-- evidence without inferred relationships.

ALTER TABLE governance_decisions DROP CONSTRAINT IF EXISTS governance_decisions_decision_type_check;
ALTER TABLE governance_decisions
    ADD CONSTRAINT governance_decisions_decision_type_check
    CHECK (decision_type IN ('allow', 'deny', 'escalate', 'require_approval', 'pending', 'revoked'));

ALTER TABLE governance_decisions ADD COLUMN IF NOT EXISTS request_id TEXT;
ALTER TABLE governance_decisions ADD COLUMN IF NOT EXISTS trace_id TEXT;
ALTER TABLE governance_decisions ADD COLUMN IF NOT EXISTS workspace_id TEXT;
ALTER TABLE governance_decisions ADD COLUMN IF NOT EXISTS agent_id TEXT;
ALTER TABLE governance_decisions ADD COLUMN IF NOT EXISTS subject_type TEXT NOT NULL DEFAULT 'agent';
ALTER TABLE governance_decisions ADD COLUMN IF NOT EXISTS subject_id TEXT;
ALTER TABLE governance_decisions ADD COLUMN IF NOT EXISTS resource TEXT;
ALTER TABLE governance_decisions ADD COLUMN IF NOT EXISTS risk_level TEXT NOT NULL DEFAULT 'low';
ALTER TABLE governance_decisions ADD COLUMN IF NOT EXISTS policy_version TEXT NOT NULL DEFAULT 'unknown';
ALTER TABLE governance_decisions ADD COLUMN IF NOT EXISTS approval_state TEXT NOT NULL DEFAULT 'auto_approved';
ALTER TABLE governance_decisions ADD COLUMN IF NOT EXISTS approved_by TEXT;
ALTER TABLE governance_decisions ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
ALTER TABLE governance_decisions ADD COLUMN IF NOT EXISTS issued_token_id TEXT;
ALTER TABLE governance_decisions ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE governance_decisions ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ;
ALTER TABLE governance_decisions ADD COLUMN IF NOT EXISTS revoked_reason TEXT;

UPDATE governance_decisions
SET workspace_id = COALESCE(workspace_id, tenant_id),
    agent_id = COALESCE(agent_id, actor_id),
    subject_id = COALESCE(subject_id, actor_id),
    expires_at = COALESCE(expires_at, expiry)
WHERE workspace_id IS NULL
   OR agent_id IS NULL
   OR subject_id IS NULL
   OR expires_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_gd_workspace_created ON governance_decisions (workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gd_trace_id ON governance_decisions (trace_id) WHERE trace_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_gd_issued_token ON governance_decisions (issued_token_id) WHERE issued_token_id IS NOT NULL;

ALTER TABLE governance_tokens ADD COLUMN IF NOT EXISTS iss TEXT NOT NULL DEFAULT 'citadel';
ALTER TABLE governance_tokens ADD COLUMN IF NOT EXISTS subject TEXT;
ALTER TABLE governance_tokens ADD COLUMN IF NOT EXISTS audience TEXT NOT NULL DEFAULT 'citadel-runtime';
ALTER TABLE governance_tokens ADD COLUMN IF NOT EXISTS workspace_id TEXT;
ALTER TABLE governance_tokens ADD COLUMN IF NOT EXISTS tool TEXT;
ALTER TABLE governance_tokens ADD COLUMN IF NOT EXISTS action TEXT;
ALTER TABLE governance_tokens ADD COLUMN IF NOT EXISTS resource_scope TEXT;
ALTER TABLE governance_tokens ADD COLUMN IF NOT EXISTS risk_level TEXT NOT NULL DEFAULT 'low';
ALTER TABLE governance_tokens ADD COLUMN IF NOT EXISTS not_before TIMESTAMPTZ;
ALTER TABLE governance_tokens ADD COLUMN IF NOT EXISTS trace_id TEXT;
ALTER TABLE governance_tokens ADD COLUMN IF NOT EXISTS approval_ref TEXT;
ALTER TABLE governance_tokens ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ;
ALTER TABLE governance_tokens ADD COLUMN IF NOT EXISTS revoked_reason TEXT;

UPDATE governance_tokens gt
SET workspace_id = COALESCE(gt.workspace_id, gt.tenant_id),
    subject = COALESCE(gt.subject, gt.actor_id),
    action = COALESCE(gt.action, gd.action),
    resource_scope = COALESCE(gt.resource_scope, gd.resource),
    risk_level = COALESCE(gt.risk_level, gd.risk_level, 'low'),
    trace_id = COALESCE(gt.trace_id, gd.trace_id),
    approval_ref = COALESCE(gt.approval_ref, gd.approved_by)
FROM governance_decisions gd
WHERE gt.decision_id = gd.decision_id;

CREATE INDEX IF NOT EXISTS idx_gt_workspace ON governance_tokens (workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gt_trace_id ON governance_tokens (trace_id) WHERE trace_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_gt_revoked ON governance_tokens (revoked_at) WHERE revoked_at IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_gt_active_decision ON governance_tokens (decision_id)
    WHERE revoked_at IS NULL;
