-- ============================================================================
-- MIGRATION 014: Make agents primary key tenant-scoped
-- Fixes a multi-tenancy bug where two tenants could not have agents with the
-- same agent_id (e.g. "nova-v2") — and ON CONFLICT (agent_id) silently
-- swallowed inserts across tenants.
-- ============================================================================

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'agents_pkey'
  ) AND NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE tablename = 'agents'
      AND indexdef ILIKE '%(tenant_id, agent_id)%'
  ) THEN
    ALTER TABLE agents DROP CONSTRAINT agents_pkey;
    ALTER TABLE agents ADD PRIMARY KEY (tenant_id, agent_id);
  END IF;
END $$;
