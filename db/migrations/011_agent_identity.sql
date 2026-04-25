-- Migration: Agent Identity Trust Tables
-- Adds cryptographic identity, challenge-response, and trust scoring support

-- Agent identities table: stores cryptographic credentials for each agent
CREATE TABLE IF NOT EXISTS agent_identities (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL UNIQUE,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'dev_tenant',
    public_key TEXT NOT NULL,
    secret_hash TEXT NOT NULL,
    api_key VARCHAR(128) NOT NULL UNIQUE,
    trust_score DECIMAL(3,2) NOT NULL DEFAULT 0.50,
    trust_level VARCHAR(32) NOT NULL DEFAULT 'unverified',
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    verification_method VARCHAR(64),
    verified_at TIMESTAMPTZ,
    challenge_count INTEGER NOT NULL DEFAULT 0,
    failed_challenges INTEGER NOT NULL DEFAULT 0,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_at TIMESTAMPTZ,
    revocation_reason TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast tenant-scoped lookups
CREATE INDEX IF NOT EXISTS idx_agent_identities_tenant 
    ON agent_identities(tenant_id);

CREATE INDEX IF NOT EXISTS idx_agent_identities_trust 
    ON agent_identities(trust_score DESC);

-- Agent challenges table: stores challenge-response nonces
CREATE TABLE IF NOT EXISTS agent_challenges (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL REFERENCES agent_identities(agent_id) ON DELETE CASCADE,
    challenge TEXT NOT NULL,
    response TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_challenges_agent 
    ON agent_challenges(agent_id, used);

CREATE INDEX IF NOT EXISTS idx_agent_challenges_expires 
    ON agent_challenges(expires_at) 
    WHERE used = FALSE;

-- Add identity-related columns to agents table if not present
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'agents' AND column_name = 'identity_verified'
    ) THEN
        ALTER TABLE agents ADD COLUMN identity_verified BOOLEAN DEFAULT FALSE;
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'agents' AND column_name = 'identity_id'
    ) THEN
        ALTER TABLE agents ADD COLUMN identity_id INTEGER 
            REFERENCES agent_identities(id) ON DELETE SET NULL;
    END IF;
END $$;

-- Add trust_score to agents table if not present
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'agents' AND column_name = 'trust_score'
    ) THEN
        ALTER TABLE agents ADD COLUMN trust_score DECIMAL(3,2) DEFAULT 0.50;
    END IF;
END $$;
