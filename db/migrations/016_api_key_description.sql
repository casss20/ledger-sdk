-- ============================================================================
-- MIGRATION 016: API key description column
-- ============================================================================
--
-- The APIKeyService.create() method inserts a description field but the
-- column was never added to the schema. This migration adds it.

ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS description TEXT;
