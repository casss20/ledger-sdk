CREATE TABLE IF NOT EXISTS api_keys (
    id BIGSERIAL PRIMARY KEY,
    key_id VARCHAR(255) NOT NULL UNIQUE,
    tenant_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    key_secret_hash VARCHAR(255) NOT NULL,
    environment VARCHAR(50) NOT NULL,  -- 'live' or 'test'
    created_at TIMESTAMP NOT NULL,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- 'active', 'revoked', 'expired'
    permissions JSONB DEFAULT '[]',
    rate_limit_rps INTEGER DEFAULT 1000,
    
    CONSTRAINT valid_environment CHECK (environment IN ('live', 'test')),
    CONSTRAINT valid_status CHECK (status IN ('active', 'revoked', 'expired'))
);

CREATE INDEX IF NOT EXISTS idx_api_keys_key_id ON api_keys(key_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id);
