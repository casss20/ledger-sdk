-- Migration 017: Trust Score Model — Hybrid Schema (Snapshots + Runtime Cache)
--
-- DESIGN CHOICE: Hybrid (C)
--   - Identity metadata stays on agent_identities (verification_status, etc.)
--   - Computed trust assessments move to actor_trust_snapshots (append-only, auditable)
--   - Runtime cache column on agents table for fast hot-path lookups
--
-- SAFETY:
--   - All new columns are NULLABLE (no table rewrite)
--   - New table is additive (no existing data impact)
--   - Indexes are created CONCURRENTLY-friendly (but we use CREATE INDEX for migration)
--   - Rollback: drop new table + nullable columns = instant
--   - Application can run against old schema during rollout

-- ============================================================================
-- PART 1: New table — actor_trust_snapshots
-- ============================================================================

CREATE TABLE IF NOT EXISTS actor_trust_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id TEXT NOT NULL REFERENCES actors(actor_id) ON DELETE CASCADE,

    -- Time bounding for validity
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ,  -- NULL = currently valid snapshot

    -- Score and band
    score DECIMAL(5,4) NOT NULL CHECK (score >= 0.0 AND score <= 1.0),
    band TEXT NOT NULL CHECK (band IN (
        'REVOKED',
        'PROBATION',
        'STANDARD',
        'TRUSTED',
        'HIGHLY_TRUSTED'
    )),

    -- Probation state
    probation_until TIMESTAMPTZ,  -- NULL if not in probation
    probation_reason TEXT,

    -- Explainability: why this score
    factors JSONB NOT NULL DEFAULT '{}',
    raw_inputs JSONB NOT NULL DEFAULT '{}',
    computation_method TEXT NOT NULL DEFAULT 'batch'  -- 'batch', 'event', 'override'
        CHECK (computation_method IN ('batch', 'event', 'override')),

    -- Audit linkage
    triggering_event TEXT,       -- e.g., 'ORCHESTRATE_KILL', 'POLICY_VIOLATION'
    triggering_event_id TEXT,      -- ID of the triggering audit event
    operator_id TEXT,              -- NULL for automated computation
    operator_reason TEXT,          -- Human override explanation

    -- Policy linkage: which snapshot was used for which decision
    -- This makes decisions reproducible
    policy_version_at_compute TEXT,

    -- Tenant isolation
    tenant_id TEXT,

    -- Correction support
    supersedes_snapshot_id UUID REFERENCES actor_trust_snapshots(snapshot_id),
    superseded_reason TEXT,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE actor_trust_snapshots IS 'Append-only trust assessments. Each row is an immutable snapshot of an actor''s computed trust at a point in time. NULL valid_until = currently active.';

-- ============================================================================
-- PART 2: Indexes
-- ============================================================================

-- Hot path: get current snapshot for an actor (most common query)
CREATE INDEX IF NOT EXISTS idx_trust_snapshots_actor_current
    ON actor_trust_snapshots (actor_id, computed_at DESC)
    WHERE valid_until IS NULL;

-- History: full timeline for an actor
CREATE INDEX IF NOT EXISTS idx_trust_snapshots_actor_timeline
    ON actor_trust_snapshots (actor_id, computed_at DESC);

-- Tenant-scoped band queries (for dashboards / batch operations)
CREATE INDEX IF NOT EXISTS idx_trust_snapshots_tenant_band
    ON actor_trust_snapshots (tenant_id, band, computed_at DESC)
    WHERE valid_until IS NULL;

-- Time-based queries (for cleanup / archiving)
CREATE INDEX IF NOT EXISTS idx_trust_snapshots_computed_at
    ON actor_trust_snapshots (computed_at DESC);

-- Supersedes lookup (for correction chains)
CREATE INDEX IF NOT EXISTS idx_trust_snapshots_supersedes
    ON actor_trust_snapshots (supersedes_snapshot_id);

-- Unique constraint: one current snapshot per actor
-- This ensures no ambiguity about "current" trust
CREATE UNIQUE INDEX IF NOT EXISTS idx_trust_snapshots_actor_current_unique
    ON actor_trust_snapshots (actor_id)
    WHERE valid_until IS NULL;

-- ============================================================================
-- PART 3: Add nullable columns to existing tables (no rewrite, no defaults)
-- ============================================================================

-- Add trust_snapshot_id to decisions for reproducibility
ALTER TABLE decisions
    ADD COLUMN IF NOT EXISTS trust_snapshot_id UUID
    REFERENCES actor_trust_snapshots(snapshot_id) ON DELETE SET NULL;

COMMENT ON COLUMN decisions.trust_snapshot_id IS 'References the trust snapshot that was active when this decision was made. Enables deterministic replay.';

-- Add trust_band cache to agents table for fast hot-path lookups
-- This is a denormalized cache of the latest snapshot's band.
-- It may lag behind the snapshot table by seconds but never by policy.
ALTER TABLE agents
    ADD COLUMN IF NOT EXISTS trust_band TEXT
    CHECK (trust_band IN ('REVOKED', 'PROBATION', 'STANDARD', 'TRUSTED', 'HIGHLY_TRUSTED'));

COMMENT ON COLUMN agents.trust_band IS 'Denormalized cache of current trust band from latest snapshot. Updated by trust computation job. NULL = not yet computed.';

-- Add probation_until to agents for fast probation checks
ALTER TABLE agents
    ADD COLUMN IF NOT EXISTS probation_until TIMESTAMPTZ;

COMMENT ON COLUMN agents.probation_until IS 'If set and > NOW(), agent is in probation regardless of trust band. Checked before trust band evaluation.';

-- ============================================================================
-- PART 4: Add trust event types to audit_events
-- ============================================================================

-- The audit_events table uses TEXT for event_type, so no schema change needed.
-- Standard event types used by the trust system:
--   TRUST_BAND_CHANGED   — Actor's trust band transitioned
--   TRUST_SCORE_COMPUTED — New snapshot created
--   TRUST_OVERRIDE       — Human operator manually set band
--   TRUST_PROBATION_ENDED — Probation period expired
--   TRUST_PROBATION_EXTENDED — Probation period extended
--   TRUST_REVOKED        — Actor explicitly revoked (emergency)
--   TRUST_RESTORED       — Actor restored from revoked state

-- ============================================================================
-- PART 5: Helper function for current snapshot lookup
-- ============================================================================

CREATE OR REPLACE FUNCTION get_actor_trust_snapshot(p_actor_id TEXT)
RETURNS TABLE (
    snapshot_id UUID,
    score DECIMAL(5,4),
    band TEXT,
    computed_at TIMESTAMPTZ,
    factors JSONB,
    probation_until TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ts.snapshot_id,
        ts.score,
        ts.band,
        ts.computed_at,
        ts.factors,
        ts.probation_until
    FROM actor_trust_snapshots ts
    WHERE ts.actor_id = p_actor_id
      AND ts.valid_until IS NULL
    ORDER BY ts.computed_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_actor_trust_snapshot(TEXT) IS 'Returns the currently active trust snapshot for an actor. Stable function suitable for use in policy queries.';

-- ============================================================================
-- PART 6: Row-Level Security on actor_trust_snapshots
-- ============================================================================

ALTER TABLE actor_trust_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY actor_trust_snapshots_tenant_isolation ON actor_trust_snapshots
    USING (tenant_id = current_setting('app.current_tenant', TRUE)::TEXT OR tenant_id IS NULL);

CREATE POLICY actor_trust_snapshots_admin_bypass ON actor_trust_snapshots
    USING (current_setting('app.is_admin', TRUE)::BOOLEAN = TRUE);

-- ============================================================================
-- PART 7: Backfill note (not executed automatically)
-- ============================================================================
--
-- Backfill is NOT part of this migration. Run separately after deployment:
--
--   1. Compute trust snapshots for all existing agents:
--      INSERT INTO actor_trust_snapshots (actor_id, score, band, ...)
--      SELECT agent_id, 0.5, 'STANDARD', NOW(), NOW(), ...
--      FROM agents;
--
--   2. Update agents.trust_band cache:
--      UPDATE agents a
--      SET trust_band = (
--          SELECT band FROM actor_trust_snapshots ts
--          WHERE ts.actor_id = a.agent_id AND ts.valid_until IS NULL
--          ORDER BY computed_at DESC LIMIT 1
--      );
--
--   3. Do this in batches of 1000 to avoid long transactions.
--
-- ============================================================================
