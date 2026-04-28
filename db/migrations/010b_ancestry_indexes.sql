ALTER TABLE governance_decisions
    ADD COLUMN IF NOT EXISTS root_decision_id TEXT,
    ADD COLUMN IF NOT EXISTS parent_decision_id TEXT;

CREATE INDEX IF NOT EXISTS idx_governance_decisions_root
    ON governance_decisions(root_decision_id)
    WHERE root_decision_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_governance_decisions_parent
    ON governance_decisions(parent_decision_id)
    WHERE parent_decision_id IS NOT NULL;
