-- ============================================================================
-- MIGRATION 015: Orchestration Lineage Foundation
-- Adds parent/child/root decision ancestry, trace propagation, and workflow
-- lineage to support Supervisor/Worker, Handoff, and Planner/Worker/Solver.
-- ============================================================================

-- ============================================================================
-- ACTIONS: Add orchestration lineage fields
-- ============================================================================

ALTER TABLE actions
    ADD COLUMN IF NOT EXISTS root_decision_id UUID,
    ADD COLUMN IF NOT EXISTS parent_decision_id UUID,
    ADD COLUMN IF NOT EXISTS trace_id TEXT,
    ADD COLUMN IF NOT EXISTS parent_actor_id TEXT,
    ADD COLUMN IF NOT EXISTS workflow_id TEXT;

CREATE INDEX IF NOT EXISTS idx_actions_root_decision ON actions (root_decision_id);
CREATE INDEX IF NOT EXISTS idx_actions_parent_decision ON actions (parent_decision_id);
CREATE INDEX IF NOT EXISTS idx_actions_trace_id ON actions (trace_id);
CREATE INDEX IF NOT EXISTS idx_actions_workflow ON actions (workflow_id);
CREATE INDEX IF NOT EXISTS idx_actions_lineage_composite ON actions (root_decision_id, parent_decision_id, trace_id);

-- ============================================================================
-- DECISIONS: Add orchestration lineage fields
-- ============================================================================

ALTER TABLE decisions
    ADD COLUMN IF NOT EXISTS root_decision_id UUID,
    ADD COLUMN IF NOT EXISTS parent_decision_id UUID,
    ADD COLUMN IF NOT EXISTS trace_id TEXT,
    ADD COLUMN IF NOT EXISTS parent_actor_id TEXT,
    ADD COLUMN IF NOT EXISTS workflow_id TEXT;

CREATE INDEX IF NOT EXISTS idx_decisions_root_decision ON decisions (root_decision_id);
CREATE INDEX IF NOT EXISTS idx_decisions_parent_decision ON decisions (parent_decision_id);
CREATE INDEX IF NOT EXISTS idx_decisions_trace_id ON decisions (trace_id);
CREATE INDEX IF NOT EXISTS idx_decisions_lineage_composite ON decisions (root_decision_id, parent_decision_id, trace_id);

-- ============================================================================
-- GOVERNANCE_DECISIONS: Add orchestration lineage fields
-- ============================================================================

ALTER TABLE governance_decisions
    ADD COLUMN IF NOT EXISTS root_decision_id TEXT,
    ADD COLUMN IF NOT EXISTS parent_decision_id TEXT,
    ADD COLUMN IF NOT EXISTS parent_actor_id TEXT,
    ADD COLUMN IF NOT EXISTS workflow_id TEXT,
    ADD COLUMN IF NOT EXISTS superseded_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS superseded_reason TEXT;

CREATE INDEX IF NOT EXISTS idx_gov_decisions_root ON governance_decisions (root_decision_id);
CREATE INDEX IF NOT EXISTS idx_gov_decisions_parent ON governance_decisions (parent_decision_id);
CREATE INDEX IF NOT EXISTS idx_gov_decisions_trace ON governance_decisions (trace_id);
CREATE INDEX IF NOT EXISTS idx_gov_decisions_lineage ON governance_decisions (root_decision_id, parent_decision_id, trace_id);

-- ============================================================================
-- GOVERNANCE_TOKENS: Add parent linkage for scoped child grants
-- ============================================================================

ALTER TABLE governance_tokens
    ADD COLUMN IF NOT EXISTS parent_decision_id TEXT,
    ADD COLUMN IF NOT EXISTS parent_actor_id TEXT,
    ADD COLUMN IF NOT EXISTS workflow_id TEXT;

CREATE INDEX IF NOT EXISTS idx_gov_tokens_parent_decision ON governance_tokens (parent_decision_id);
CREATE INDEX IF NOT EXISTS idx_gov_tokens_parent_actor ON governance_tokens (parent_actor_id);

-- ============================================================================
-- AUDIT_EVENTS: Expand event_type enum for orchestration events
-- ============================================================================

-- PostgreSQL enums require ALTER TYPE to add values
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'audit_event_type_enum') THEN
        -- Check each value before adding
        IF NOT EXISTS (
            SELECT 1 FROM pg_enum
            WHERE enumlabel = 'delegate_created'
              AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'audit_event_type_enum')
        ) THEN
            ALTER TYPE audit_event_type_enum ADD VALUE 'delegate_created';
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM pg_enum
            WHERE enumlabel = 'handoff_performed'
              AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'audit_event_type_enum')
        ) THEN
            ALTER TYPE audit_event_type_enum ADD VALUE 'handoff_performed';
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM pg_enum
            WHERE enumlabel = 'gather_created'
              AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'audit_event_type_enum')
        ) THEN
            ALTER TYPE audit_event_type_enum ADD VALUE 'gather_created';
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM pg_enum
            WHERE enumlabel = 'branch_completed'
              AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'audit_event_type_enum')
        ) THEN
            ALTER TYPE audit_event_type_enum ADD VALUE 'branch_completed';
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM pg_enum
            WHERE enumlabel = 'authority_transferred'
              AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'audit_event_type_enum')
        ) THEN
            ALTER TYPE audit_event_type_enum ADD VALUE 'authority_transferred';
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM pg_enum
            WHERE enumlabel = 'introspection_failed'
              AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'audit_event_type_enum')
        ) THEN
            ALTER TYPE audit_event_type_enum ADD VALUE 'introspection_failed';
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM pg_enum
            WHERE enumlabel = 'kill_switch_blocked_orchestration'
              AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'audit_event_type_enum')
        ) THEN
            ALTER TYPE audit_event_type_enum ADD VALUE 'kill_switch_blocked_orchestration';
        END IF;
    END IF;
END $$;

-- ============================================================================
-- LINEAGE QUERY VIEW: Flattened orchestration tree for dashboard / audit
-- ============================================================================

CREATE OR REPLACE VIEW orchestration_lineage AS
SELECT
    a.action_id,
    a.actor_id,
    a.actor_type,
    a.action_name,
    a.resource,
    a.tenant_id,
    a.root_decision_id,
    a.parent_decision_id,
    a.trace_id,
    a.parent_actor_id,
    a.workflow_id,
    a.session_id,
    a.request_id,
    d.decision_id,
    d.status AS decision_status,
    d.winning_rule,
    d.reason AS decision_reason,
    d.risk_level,
    d.risk_score,
    d.path_taken,
    d.created_at AS decided_at,
    d.capability_token,
    a.created_at AS action_created_at
FROM actions a
LEFT JOIN decisions d ON a.action_id = d.action_id;

-- ============================================================================
-- BACKWARD COMPATIBILITY NOTE
-- All new columns are NULLable. Existing rows remain valid.
-- Old code that ignores lineage fields continues to work.
-- ============================================================================
