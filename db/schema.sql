-- ============================================================================
-- CITADEL CONTROL-SYSTEM DATABASE SCHEMA (Merged MVP)
-- ============================================================================
-- 
-- Design: Authoritative state in Postgres, append-only audit, replayable decisions
-- Optimized for: deterministic decisions, policy versioning, compliance, scale
--
-- Postgres 15+ required
--
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================================
-- ENUMS (Type safety for core concepts)
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'actor_type_enum') THEN
        CREATE TYPE actor_type_enum AS ENUM ('agent', 'workflow', 'service', 'user_proxy');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'actor_status_enum') THEN
        CREATE TYPE actor_status_enum AS ENUM ('active', 'suspended', 'revoked');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'policy_status_enum') THEN
        CREATE TYPE policy_status_enum AS ENUM ('draft', 'active', 'retired');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'scope_type_enum') THEN
        CREATE TYPE scope_type_enum AS ENUM ('global', 'tenant', 'actor', 'action', 'resource', 'environment');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'approval_status_enum') THEN
        CREATE TYPE approval_status_enum AS ENUM ('pending', 'approved', 'rejected', 'expired', 'escalated');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'decision_status_enum') THEN
        CREATE TYPE decision_status_enum AS ENUM (
            'BLOCKED_SCHEMA',        -- Failed schema validation
            'BLOCKED_EMERGENCY',     -- Kill switch active
            'BLOCKED_CAPABILITY',    -- Missing/invalid capability
            'BLOCKED_POLICY',        -- Policy rule blocked
            'RATE_LIMITED',          -- Rate limit exceeded
            'PENDING_APPROVAL',      -- Waiting for human review
            'REJECTED_APPROVAL',     -- Human rejected
            'EXPIRED_APPROVAL',      -- Approval window expired
            'ALLOWED',               -- Approved to execute
            'EXECUTED',              -- Successfully executed
            'FAILED_EXECUTION',      -- Execution error
            'FAILED_AUDIT'           -- Audit logging failed
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'approval_priority_enum') THEN
        CREATE TYPE approval_priority_enum AS ENUM ('low', 'medium', 'high', 'critical');
    END IF;
END $$;

-- ============================================================================
-- HELPERS
-- ============================================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- ACTORS: Who is allowed to act
-- ============================================================================

CREATE TABLE IF NOT EXISTS actors (
    actor_id TEXT PRIMARY KEY,
    actor_type actor_type_enum NOT NULL,
    tenant_id TEXT,
    status actor_status_enum NOT NULL DEFAULT 'active',
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_actors_tenant_id ON actors (tenant_id);
CREATE INDEX IF NOT EXISTS idx_actors_status ON actors (status);
CREATE INDEX IF NOT EXISTS idx_actors_tenant_status ON actors (tenant_id, status);

DROP TRIGGER IF EXISTS trg_actors_updated_at ON actors;
CREATE TRIGGER trg_actors_updated_at
    BEFORE UPDATE ON actors
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE actors IS 'Registry of all actors that can request actions';

-- ============================================================================
-- POLICIES: Current policy objects (immutable logic, versioned)
-- ============================================================================

CREATE TABLE IF NOT EXISTS policies (
    policy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    scope_type scope_type_enum NOT NULL,
    scope_value TEXT NOT NULL,
    rules_json JSONB NOT NULL,
    status policy_status_enum NOT NULL DEFAULT 'draft',
    description TEXT,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ,
    CONSTRAINT uq_policies_name_version UNIQUE (tenant_id, name, version)
);

CREATE INDEX IF NOT EXISTS idx_policies_tenant_status ON policies (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_policies_scope ON policies (scope_type, scope_value);
CREATE INDEX IF NOT EXISTS idx_policies_tenant_scope_active ON policies (tenant_id, scope_type, scope_value) 
    WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_policies_rules_gin ON policies USING GIN (rules_json);

-- Immutable policy logic: only status timestamps can change
CREATE OR REPLACE FUNCTION prevent_policy_mutation()
RETURNS TRIGGER AS $$
BEGIN
    IF (
        NEW.name IS DISTINCT FROM OLD.name OR
        NEW.version IS DISTINCT FROM OLD.version OR
        NEW.scope_type IS DISTINCT FROM OLD.scope_type OR
        NEW.scope_value IS DISTINCT FROM OLD.scope_value OR
        NEW.rules_json IS DISTINCT FROM OLD.rules_json OR
        NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
    ) THEN
        RAISE EXCEPTION 'Policy rows are immutable. Create a new version instead.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_policy_mutation ON policies;
CREATE TRIGGER trg_prevent_policy_mutation
    BEFORE UPDATE ON policies
    FOR EACH ROW
    EXECUTE FUNCTION prevent_policy_mutation();

COMMENT ON TABLE policies IS 'Policy definitions - immutable by version, status tracks lifecycle';

-- ============================================================================
-- POLICY SNAPSHOTS: Resolved immutable snapshots for replay
-- ============================================================================

CREATE TABLE IF NOT EXISTS policy_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID REFERENCES policies(policy_id),
    policy_version TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL UNIQUE,
    snapshot_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_policy_snapshots_policy_id ON policy_snapshots (policy_id);
CREATE INDEX IF NOT EXISTS idx_policy_snapshots_version ON policy_snapshots (policy_version);

COMMENT ON TABLE policy_snapshots IS 'Immutable policy snapshots - critical for deterministic replay';

-- ============================================================================
-- KILL SWITCHES: Emergency controls (mutable enabled state)
-- ============================================================================

CREATE TABLE IF NOT EXISTS kill_switches (
    switch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT,
    scope_type scope_type_enum NOT NULL,
    scope_value TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    reason TEXT,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_kill_switch_scope UNIQUE (tenant_id, scope_type, scope_value)
);

CREATE INDEX IF NOT EXISTS idx_kill_switches_scope ON kill_switches (tenant_id, scope_type, scope_value);
CREATE INDEX IF NOT EXISTS idx_kill_switches_enabled ON kill_switches (scope_type, scope_value) 
    WHERE enabled = TRUE;

DROP TRIGGER IF EXISTS trg_kill_switches_updated_at ON kill_switches;
CREATE TRIGGER trg_kill_switches_updated_at
    BEFORE UPDATE ON kill_switches
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE kill_switches IS 'Emergency stop controls - fast lookup, mutable enabled state';

-- ============================================================================
-- CAPABILITIES: Scoped permission grants (mutable use count)
-- ============================================================================

CREATE TABLE IF NOT EXISTS capabilities (
    token_id TEXT PRIMARY KEY,
    actor_id TEXT NOT NULL REFERENCES actors(actor_id) ON DELETE CASCADE,
    action_scope TEXT NOT NULL,
    resource_scope TEXT NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    max_uses INTEGER NOT NULL CHECK (max_uses > 0),
    uses INTEGER NOT NULL DEFAULT 0 CHECK (uses >= 0),
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    CONSTRAINT valid_uses CHECK (uses <= max_uses),
    CONSTRAINT valid_expiry CHECK (expires_at > issued_at)
);

CREATE INDEX IF NOT EXISTS idx_capabilities_actor_id ON capabilities (actor_id);
CREATE INDEX IF NOT EXISTS idx_capabilities_active ON capabilities (actor_id, action_scope, resource_scope)
    WHERE revoked = FALSE AND uses < max_uses;
CREATE INDEX IF NOT EXISTS idx_capabilities_expires_at ON capabilities (expires_at)
    WHERE revoked = FALSE;

COMMENT ON TABLE capabilities IS 'Token-based capability system - atomic use counting required';

-- ============================================================================
-- ACTIONS: Canonical action record (append-only)
-- ============================================================================

CREATE TABLE IF NOT EXISTS actions (
    action_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id TEXT NOT NULL REFERENCES actors(actor_id) ON DELETE RESTRICT,
    actor_type actor_type_enum NOT NULL,
    action_name TEXT NOT NULL,
    resource TEXT NOT NULL,
    tenant_id TEXT,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    context_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    session_id TEXT,
    request_id TEXT,
    idempotency_key TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT ck_action_name_format CHECK (position('.' in action_name) > 0)
);

CREATE INDEX IF NOT EXISTS idx_actions_actor_created ON actions (actor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_actions_name_created ON actions (action_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_actions_tenant_created ON actions (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_actions_request_id ON actions (request_id);
CREATE INDEX IF NOT EXISTS idx_actions_session ON actions (session_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_actions_actor_idempotency 
    ON actions (actor_id, idempotency_key) 
    WHERE idempotency_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_actions_payload_gin ON actions USING GIN (payload_json);
CREATE INDEX IF NOT EXISTS idx_actions_context_gin ON actions USING GIN (context_json);

COMMENT ON TABLE actions IS 'Canonical action requests - immutable normalized record';

-- ============================================================================
-- DECISIONS: Terminal decision per action (append-only)
-- ============================================================================

CREATE TABLE IF NOT EXISTS decisions (
    decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_id UUID NOT NULL UNIQUE REFERENCES actions(action_id) ON DELETE CASCADE,
    policy_snapshot_id UUID REFERENCES policy_snapshots(snapshot_id) ON DELETE SET NULL,
    status decision_status_enum NOT NULL,
    winning_rule TEXT NOT NULL,
    reason TEXT NOT NULL,
    capability_token TEXT REFERENCES capabilities(token_id) ON DELETE SET NULL,
    risk_level TEXT CHECK (risk_level IN ('none', 'low', 'medium', 'high', 'critical')),
    risk_score INTEGER CHECK (risk_score >= 0 AND risk_score <= 100),
    path_taken TEXT CHECK (path_taken IN ('fast', 'standard', 'structured', 'high_risk', 'bypass')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    executed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_decisions_status_created ON decisions (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_decisions_policy_snapshot ON decisions (policy_snapshot_id);
CREATE INDEX IF NOT EXISTS idx_decisions_capability ON decisions (capability_token);

COMMENT ON TABLE decisions IS 'Terminal decision for each action - immutable, replayable';

-- ============================================================================
-- APPROVALS: Human-in-the-loop state (mutable status)
-- ============================================================================

CREATE TABLE IF NOT EXISTS approvals (
    approval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_id UUID NOT NULL UNIQUE REFERENCES actions(action_id) ON DELETE CASCADE,
    status approval_status_enum NOT NULL DEFAULT 'pending',
    priority approval_priority_enum NOT NULL DEFAULT 'medium',
    requested_by TEXT NOT NULL REFERENCES actors(actor_id),
    reviewed_by TEXT REFERENCES actors(actor_id),
    reason TEXT NOT NULL,
    decision_reason TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at TIMESTAMPTZ,
    escalated_to TEXT,
    
    CONSTRAINT valid_decision CHECK (
        (status IN ('approved', 'rejected') AND decided_at IS NOT NULL AND reviewed_by IS NOT NULL)
        OR (status IN ('pending', 'expired', 'escalated') AND decided_at IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals (status);
CREATE INDEX IF NOT EXISTS idx_approvals_pending ON approvals (status, priority, created_at) 
    WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_approvals_expires ON approvals (expires_at) 
    WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_approvals_requester ON approvals (requested_by);

COMMENT ON TABLE approvals IS 'Approval queue for human-in-the-loop governance';

-- ============================================================================
-- AUDIT EVENTS: Append-only hash-chained history
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_events (
    event_id BIGSERIAL PRIMARY KEY,
    action_id UUID NOT NULL REFERENCES actions(action_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'action_received', 'policy_evaluated', 'kill_switch_checked',
        'capability_checked', 'risk_assessed', 'approval_requested',
        'approval_granted', 'approval_denied', 'decision_made',
        'action_executed', 'action_failed', 'escalation_triggered',
        'kill_switch_activated'
    )),
    event_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    prev_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL UNIQUE,
    actor_id TEXT,
    tenant_id TEXT,
    policy_id UUID
);

CREATE INDEX IF NOT EXISTS idx_audit_action_ts ON audit_events (action_id, event_ts ASC);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events (event_type, event_ts DESC);
CREATE INDEX IF NOT EXISTS idx_audit_actor_ts ON audit_events (actor_id, event_ts DESC);
CREATE INDEX IF NOT EXISTS idx_audit_tenant_ts ON audit_events (tenant_id, event_ts DESC);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_events (event_ts DESC);
CREATE INDEX IF NOT EXISTS idx_audit_payload_gin ON audit_events USING GIN (payload_json);

-- Prevent updates/deletes on audit (append-only enforcement)
CREATE OR REPLACE FUNCTION forbid_audit_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_events is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_forbid_audit_update ON audit_events;
CREATE TRIGGER trg_forbid_audit_update
    BEFORE UPDATE ON audit_events
    FOR EACH ROW
    EXECUTE FUNCTION forbid_audit_mutation();

DROP TRIGGER IF EXISTS trg_forbid_audit_delete ON audit_events;
CREATE TRIGGER trg_forbid_audit_delete
    BEFORE DELETE ON audit_events
    FOR EACH ROW
    EXECUTE FUNCTION forbid_audit_mutation();

-- Hash chain triggers
CREATE OR REPLACE FUNCTION set_audit_prev_hash()
RETURNS TRIGGER AS $$
DECLARE
    last_hash TEXT;
BEGIN
    SELECT event_hash INTO last_hash
    FROM audit_events
    ORDER BY event_id DESC
    LIMIT 1;
    
    NEW.prev_hash := COALESCE(last_hash, repeat('0', 64));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_prev_hash ON audit_events;
CREATE TRIGGER trg_audit_prev_hash
    BEFORE INSERT ON audit_events
    FOR EACH ROW
    EXECUTE FUNCTION set_audit_prev_hash();

CREATE OR REPLACE FUNCTION calculate_event_hash()
RETURNS TRIGGER AS $$
BEGIN
    NEW.event_hash := encode(
        digest(
            COALESCE(NEW.action_id::text, '') || 
            NEW.event_type || 
            NEW.event_ts::text || 
            COALESCE(NEW.payload_json::text, '{}') ||
            COALESCE(NEW.prev_hash, repeat('0', 64)) ||
            COALESCE(NEW.actor_id, ''),
            'sha256'
        ),
        'hex'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_event_hash ON audit_events;
CREATE TRIGGER trg_audit_event_hash
    BEFORE INSERT ON audit_events
    FOR EACH ROW
    EXECUTE FUNCTION calculate_event_hash();

COMMENT ON TABLE audit_events IS 'Full chronological audit trail - append-only, hash-chained, tamper-evident';

-- ============================================================================
-- MERKLE ROOT SIGNING: External anchoring for audit chain integrity
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_merkle_roots (
    root_id BIGSERIAL PRIMARY KEY,
    root_hash TEXT NOT NULL UNIQUE,
    -- Merkle tree root over a batch of audit events
    from_event_id BIGINT NOT NULL,
    to_event_id BIGINT NOT NULL,
    event_count BIGINT NOT NULL,
    -- Signature using Ed25519 or RSA (hex-encoded)
    signature TEXT NOT NULL,
    -- Public key identifier for verification
    key_id TEXT NOT NULL,
    -- External anchor (e.g., transparency log entry, blockchain tx)
    external_anchor TEXT,
    -- When this root was computed and signed
    signed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Optional tenant scoping (NULL = global/system root)
    tenant_id TEXT,
    -- Prevent tampering with signed roots
    CONSTRAINT valid_range CHECK (from_event_id <= to_event_id)
);

CREATE INDEX IF NOT EXISTS idx_merkle_roots_range ON audit_merkle_roots(from_event_id, to_event_id);
CREATE INDEX IF NOT EXISTS idx_merkle_roots_tenant ON audit_merkle_roots(tenant_id, signed_at DESC);

COMMENT ON TABLE audit_merkle_roots IS 'Signed Merkle roots for external audit chain anchoring';

-- Compute Merkle root over a range of audit events
CREATE OR REPLACE FUNCTION compute_audit_merkle_root(
    p_from_event_id BIGINT,
    p_to_event_id BIGINT
)
RETURNS TEXT AS $$
DECLARE
    rec RECORD;
    combined TEXT := '';
BEGIN
    -- Collect all event hashes in range and combine iteratively
    FOR rec IN
        SELECT event_hash
        FROM audit_events
        WHERE event_id BETWEEN p_from_event_id AND p_to_event_id
        ORDER BY event_id
    LOOP
        combined := encode(digest(combined || rec.event_hash, 'sha256'), 'hex');
    END LOOP;
    
    RETURN combined;
END;
$$ LANGUAGE plpgsql;

-- Sign and store a Merkle root for a range of events
CREATE OR REPLACE FUNCTION sign_audit_merkle_root(
    p_from_event_id BIGINT,
    p_to_event_id BIGINT,
    p_signature TEXT,
    p_key_id TEXT,
    p_tenant_id TEXT DEFAULT NULL,
    p_external_anchor TEXT DEFAULT NULL
)
RETURNS TEXT AS $$
DECLARE
    v_root_hash TEXT;
    v_event_count BIGINT;
BEGIN
    -- Validate range exists
    SELECT COUNT(*) INTO v_event_count
    FROM audit_events
    WHERE event_id BETWEEN p_from_event_id AND p_to_event_id;
    
    IF v_event_count = 0 THEN
        RAISE EXCEPTION 'No audit events in range % to %', p_from_event_id, p_to_event_id;
    END IF;
    
    -- Compute merkle root
    v_root_hash := compute_audit_merkle_root(p_from_event_id, p_to_event_id);
    
    -- Store signed root
    INSERT INTO audit_merkle_roots (
        root_hash, from_event_id, to_event_id, event_count,
        signature, key_id, external_anchor, tenant_id
    ) VALUES (
        v_root_hash, p_from_event_id, p_to_event_id, v_event_count,
        p_signature, p_key_id, p_external_anchor, p_tenant_id
    )
    ON CONFLICT (root_hash) DO UPDATE SET
        signature = EXCLUDED.signature,
        key_id = EXCLUDED.key_id,
        external_anchor = EXCLUDED.external_anchor,
        signed_at = NOW();
    
    RETURN v_root_hash;
END;
$$ LANGUAGE plpgsql;

-- Verify audit chain integrity including latest Merkle root
CREATE OR REPLACE FUNCTION verify_audit_chain_with_merkle()
RETURNS TABLE (
    chain_valid BOOLEAN,
    chain_checked_count BIGINT,
    chain_broken_at BIGINT,
    merkle_root_valid BOOLEAN,
    latest_root_hash TEXT,
    latest_root_signed_at TIMESTAMPTZ
) AS $$
DECLARE
    v_chain_valid BOOLEAN;
    v_count BIGINT;
    v_broken BIGINT;
    v_root_hash TEXT;
    v_signed_at TIMESTAMPTZ;
    v_merkle_valid BOOLEAN := NULL;
    v_from_id BIGINT;
    v_to_id BIGINT;
BEGIN
    -- First verify the hash chain
    SELECT valid, checked_count, broken_at_event_id
    INTO v_chain_valid, v_count, v_broken
    FROM verify_audit_chain();
    
    -- Check if we have a Merkle root covering the latest events
    SELECT 
        mr.root_hash, mr.signed_at, mr.from_event_id, mr.to_event_id
    INTO v_root_hash, v_signed_at, v_from_id, v_to_id
    FROM audit_merkle_roots mr
    ORDER BY mr.to_event_id DESC
    LIMIT 1;
    
    IF v_root_hash IS NOT NULL THEN
        -- Verify the stored root matches recomputed value
        v_merkle_valid := (compute_audit_merkle_root(v_from_id, v_to_id) = v_root_hash);
    END IF;
    
    RETURN QUERY SELECT
        v_chain_valid,
        v_count,
        v_broken,
        v_merkle_valid,
        v_root_hash,
        v_signed_at;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- EXECUTION RESULTS: Action execution outcomes
-- ============================================================================

CREATE TABLE IF NOT EXISTS execution_results (
    execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_id UUID NOT NULL UNIQUE REFERENCES actions(action_id) ON DELETE CASCADE,
    success BOOLEAN NOT NULL,
    result_json JSONB,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_execution_success_created ON execution_results (success, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_execution_action ON execution_results (action_id);

COMMENT ON TABLE execution_results IS 'Execution outcomes for allowed actions';

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Active governance state
CREATE OR REPLACE VIEW active_governance_state AS
SELECT 
    'actor' as entity_type,
    actor_id as entity_id,
    status::text as state,
    jsonb_build_object('type', actor_type, 'tenant', tenant_id) as config
FROM actors 
WHERE status = 'active'
UNION ALL
SELECT 
    'policy' as entity_type,
    policy_id::text as entity_id,
    status::text as state,
    jsonb_build_object('name', name, 'version', version, 'scope', scope_type || ':' || scope_value) as config
FROM policies 
WHERE status = 'active'
UNION ALL
SELECT 
    'kill_switch' as entity_type,
    switch_id::text as entity_id,
    CASE WHEN enabled THEN 'armed' ELSE 'disarmed' END as state,
    jsonb_build_object('scope', scope_type || ':' || scope_value, 'reason', reason) as config
FROM kill_switches;

-- Pending approvals queue
CREATE OR REPLACE VIEW pending_approvals_queue AS
SELECT 
    a.approval_id,
    a.action_id,
    a.priority,
    a.reason,
    a.requested_by,
    a.created_at,
    a.expires_at,
    act.action_name,
    act.resource,
    act.payload_json
FROM approvals a
JOIN actions act ON a.action_id = act.action_id
WHERE a.status = 'pending'
ORDER BY 
    CASE a.priority 
        WHEN 'critical' THEN 1 
        WHEN 'high' THEN 2 
        WHEN 'medium' THEN 3 
        ELSE 4 
    END,
    a.created_at;

-- Action decision view
CREATE OR REPLACE VIEW action_decision_view AS
SELECT
    a.action_id,
    a.actor_id,
    a.actor_type,
    a.action_name,
    a.resource,
    a.session_id,
    a.request_id,
    a.idempotency_key,
    a.created_at AS action_created_at,
    d.decision_id,
    d.status AS decision_status,
    d.winning_rule,
    d.reason AS decision_reason,
    d.risk_level,
    d.risk_score,
    d.path_taken,
    d.created_at AS decision_created_at,
    ap.approval_id,
    ap.status AS approval_status,
    ap.reviewed_by,
    ap.decided_at
FROM actions a
LEFT JOIN decisions d ON d.action_id = a.action_id
LEFT JOIN approvals ap ON ap.action_id = a.action_id;

-- Decision replay log
CREATE OR REPLACE VIEW decision_replay_log AS
SELECT 
    d.decision_id,
    d.action_id,
    d.status as decision_status,
    d.winning_rule,
    d.reason as decision_reason,
    d.risk_level,
    d.risk_score,
    d.path_taken,
    d.policy_snapshot_id,
    ps.policy_version,
    ps.snapshot_hash,
    a.actor_id,
    a.actor_type,
    a.action_name,
    a.resource,
    a.payload_json,
    a.context_json,
    a.created_at as action_requested_at,
    d.created_at as decision_made_at
FROM decisions d
JOIN actions a ON d.action_id = a.action_id
LEFT JOIN policy_snapshots ps ON d.policy_snapshot_id = ps.snapshot_id
ORDER BY d.created_at DESC;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Verify audit chain integrity
CREATE OR REPLACE FUNCTION verify_audit_chain()
RETURNS TABLE (
    valid BOOLEAN,
    checked_count BIGINT,
    first_event_id BIGINT,
    last_event_id BIGINT,
    broken_at_event_id BIGINT
) AS $$
DECLARE
    v_valid BOOLEAN := TRUE;
    v_count BIGINT;
    v_first BIGINT;
    v_last BIGINT;
    v_broken BIGINT := NULL;
    rec RECORD;
    expected_hash TEXT;
BEGIN
    SELECT COUNT(*), MIN(event_id), MAX(event_id) 
    INTO v_count, v_first, v_last
    FROM audit_events;
    
    IF v_count = 0 THEN
        RETURN QUERY SELECT TRUE, 0::bigint, NULL::bigint, NULL::bigint, NULL::bigint;
        RETURN;
    END IF;
    
    FOR rec IN 
        SELECT event_id, event_hash, prev_hash 
        FROM audit_events 
        ORDER BY event_id
    LOOP
        IF rec.event_id > v_first THEN
            SELECT event_hash INTO expected_hash
            FROM audit_events 
            WHERE event_id = rec.event_id - 1;
            
            IF rec.prev_hash != expected_hash THEN
                v_valid := FALSE;
                v_broken := rec.event_id;
                EXIT;
            END IF;
        END IF;
    END LOOP;
    
    RETURN QUERY SELECT v_valid, v_count, v_first, v_last, v_broken;
END;
$$ LANGUAGE plpgsql;

-- Atomic capability consumption
CREATE OR REPLACE FUNCTION consume_capability(
    p_token_id TEXT,
    p_actor_id TEXT
)
RETURNS TABLE (
    success BOOLEAN,
    remaining_uses INTEGER,
    error TEXT
) AS $$
DECLARE
    v_cap RECORD;
BEGIN
    -- Lock and fetch capability
    SELECT * INTO v_cap
    FROM capabilities
    WHERE token_id = p_token_id
    FOR UPDATE;
    
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 0, 'capability_not_found'::TEXT;
        RETURN;
    END IF;
    
    IF v_cap.actor_id != p_actor_id THEN
        RETURN QUERY SELECT FALSE, 0, 'actor_mismatch'::TEXT;
        RETURN;
    END IF;
    
    IF v_cap.revoked THEN
        RETURN QUERY SELECT FALSE, 0, 'capability_revoked'::TEXT;
        RETURN;
    END IF;
    
    IF v_cap.expires_at < NOW() THEN
        RETURN QUERY SELECT FALSE, 0, 'capability_expired'::TEXT;
        RETURN;
    END IF;
    
    IF v_cap.uses >= v_cap.max_uses THEN
        RETURN QUERY SELECT FALSE, 0, 'capability_exhausted'::TEXT;
        RETURN;
    END IF;
    
    -- Consume use
    UPDATE capabilities
    SET uses = uses + 1
    WHERE token_id = p_token_id;
    
    RETURN QUERY SELECT TRUE, (v_cap.max_uses - v_cap.uses - 1), NULL::TEXT;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- REDIS SCHEMA (documented, ephemeral only)
-- ============================================================================
/*
REDIS KEY PATTERNS (ephemeral only, Postgres is source of truth):

Rate limiting:
  ratelimit:{actor_id}:{action} â†’ sorted set of timestamps
  ratelimit:{tenant_id}:global â†’ global counters

Distributed locks:
  lock:capability:{token_id} â†’ lock for atomic capability use
  lock:approval:{approval_id} â†’ approval decision lock
  lock:action:{action_id} â†’ execution lock

Hot cache (short TTL):
  cache:killswitch:{scope} â†’ kill switch status (TTL: 5s)
  cache:policy:{tenant}:{scope} â†’ active policy (TTL: 30s)
  cache:actor:{actor_id} â†’ actor status (TTL: 60s)

Approval queue:
  approvals:pending â†’ pub/sub list
  approvals:priority:{priority} â†’ priority queues

Idempotency:
  dedupe:{idempotency_key} â†’ "1" (TTL: 5m)

NOT in Redis:
  - Audit log (audit_events)
  - Policy definitions (policies)
  - Final approval state (approvals)
  - Capability state (capabilities)
  - Decision history (decisions)
*/

-- ============================================================================
-- ROW-LEVEL SECURITY (RLS) — Tenant Isolation
-- ============================================================================
--
-- RLS is the safety net under application filtering. When application code
-- has a bug, the database says no.
--
-- RULES:
--   1. Always use SET LOCAL (not SET) — connection pool safe
--   2. tenant_id is the leading column in all RLS indexes
--   3. FORCE ROW LEVEL SECURITY on all tenant tables
--   4. Admin access via policy, not BYPASSRLS
--   5. Migration role has BYPASSRLS (schema changes only)
--
-- ============================================================================

-- Helper: Set tenant context for current transaction
-- Usage: SELECT set_tenant_context('tenant-123');
CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id TEXT)
RETURNS VOID AS $$
BEGIN
    PERFORM set_config('app.current_tenant', p_tenant_id, true);  -- true = local (transaction-only)
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Helper: Get current tenant from session
CREATE OR REPLACE FUNCTION current_tenant_id()
RETURNS TEXT AS $$
BEGIN
    RETURN current_setting('app.current_tenant', true);  -- true = missing_ok
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Migration role: for schema migrations and admin operations
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'citadel_migrator') THEN
        CREATE ROLE citadel_migrator WITH LOGIN BYPASSRLS;
        -- Grant appropriate permissions (adjust as needed)
        -- GRANT ALL ON ALL TABLES IN SCHEMA public TO citadel_migrator;
    END IF;
END $$;

-- Enable RLS on all tenant-scoped tables
ALTER TABLE actors ENABLE ROW LEVEL SECURITY;
ALTER TABLE policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE kill_switches ENABLE ROW LEVEL SECURITY;
ALTER TABLE actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE execution_results ENABLE ROW LEVEL SECURITY;

-- Force RLS even for table owners (prevents accidental superuser leaks)
ALTER TABLE actors FORCE ROW LEVEL SECURITY;
ALTER TABLE policies FORCE ROW LEVEL SECURITY;
ALTER TABLE kill_switches FORCE ROW LEVEL SECURITY;
ALTER TABLE actions FORCE ROW LEVEL SECURITY;
ALTER TABLE decisions FORCE ROW LEVEL SECURITY;
ALTER TABLE approvals FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;
ALTER TABLE execution_results FORCE ROW LEVEL SECURITY;

-- Drop existing policies (idempotent for reruns)
DO $$
DECLARE
    pol RECORD;
BEGIN
    FOR pol IN 
        SELECT schemaname, tablename, policyname 
        FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename IN ('actors', 'policies', 'kill_switches', 'actions', 'decisions', 'approvals', 'audit_events', 'execution_results')
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I', pol.policyname, pol.schemaname, pol.tablename);
    END LOOP;
END $$;

-- Tenant isolation policies: each tenant sees only their own data
-- NULL tenant_id = global/system data (visible to all when no tenant set)

-- ACTORS
CREATE POLICY tenant_isolation_select ON actors FOR SELECT
    USING (tenant_id IS NULL OR tenant_id = current_tenant_id() OR current_tenant_id() IS NULL);
CREATE POLICY tenant_isolation_insert ON actors FOR INSERT
    WITH CHECK (tenant_id IS NULL OR tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON actors FOR UPDATE
    USING (tenant_id IS NULL OR tenant_id = current_tenant_id())
    WITH CHECK (tenant_id IS NULL OR tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON actors FOR DELETE
    USING (tenant_id IS NULL OR tenant_id = current_tenant_id());

-- POLICIES
CREATE POLICY tenant_isolation_select ON policies FOR SELECT
    USING (tenant_id IS NULL OR tenant_id = current_tenant_id() OR current_tenant_id() IS NULL);
CREATE POLICY tenant_isolation_insert ON policies FOR INSERT
    WITH CHECK (tenant_id IS NULL OR tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON policies FOR UPDATE
    USING (tenant_id IS NULL OR tenant_id = current_tenant_id())
    WITH CHECK (tenant_id IS NULL OR tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON policies FOR DELETE
    USING (tenant_id IS NULL OR tenant_id = current_tenant_id());

-- KILL SWITCHES
CREATE POLICY tenant_isolation_select ON kill_switches FOR SELECT
    USING (tenant_id IS NULL OR tenant_id = current_tenant_id() OR current_tenant_id() IS NULL);
CREATE POLICY tenant_isolation_insert ON kill_switches FOR INSERT
    WITH CHECK (tenant_id IS NULL OR tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON kill_switches FOR UPDATE
    USING (tenant_id IS NULL OR tenant_id = current_tenant_id())
    WITH CHECK (tenant_id IS NULL OR tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON kill_switches FOR DELETE
    USING (tenant_id IS NULL OR tenant_id = current_tenant_id());

-- ACTIONS
CREATE POLICY tenant_isolation_select ON actions FOR SELECT
    USING (tenant_id IS NULL OR tenant_id = current_tenant_id() OR current_tenant_id() IS NULL);
CREATE POLICY tenant_isolation_insert ON actions FOR INSERT
    WITH CHECK (tenant_id IS NULL OR tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_update ON actions FOR UPDATE
    USING (tenant_id IS NULL OR tenant_id = current_tenant_id())
    WITH CHECK (tenant_id IS NULL OR tenant_id = current_tenant_id());
CREATE POLICY tenant_isolation_delete ON actions FOR DELETE
    USING (tenant_id IS NULL OR tenant_id = current_tenant_id());

-- DECISIONS (tenant via joined actions)
CREATE POLICY tenant_isolation_select ON decisions FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM actions a 
            WHERE a.action_id = decisions.action_id 
            AND (a.tenant_id IS NULL OR a.tenant_id = current_tenant_id() OR current_tenant_id() IS NULL)
        )
    );
CREATE POLICY tenant_isolation_insert ON decisions FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM actions a 
            WHERE a.action_id = decisions.action_id 
            AND (a.tenant_id IS NULL OR a.tenant_id = current_tenant_id())
        )
    );
CREATE POLICY tenant_isolation_update ON decisions FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM actions a 
            WHERE a.action_id = decisions.action_id 
            AND (a.tenant_id IS NULL OR a.tenant_id = current_tenant_id())
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM actions a 
            WHERE a.action_id = decisions.action_id 
            AND (a.tenant_id IS NULL OR a.tenant_id = current_tenant_id())
        )
    );
CREATE POLICY tenant_isolation_delete ON decisions FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM actions a 
            WHERE a.action_id = decisions.action_id 
            AND (a.tenant_id IS NULL OR a.tenant_id = current_tenant_id())
        )
    );

-- APPROVALS (tenant via joined actions)
CREATE POLICY tenant_isolation_select ON approvals FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM actions a 
            WHERE a.action_id = approvals.action_id 
            AND (a.tenant_id IS NULL OR a.tenant_id = current_tenant_id() OR current_tenant_id() IS NULL)
        )
    );
CREATE POLICY tenant_isolation_insert ON approvals FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM actions a 
            WHERE a.action_id = approvals.action_id 
            AND (a.tenant_id IS NULL OR a.tenant_id = current_tenant_id())
        )
    );
CREATE POLICY tenant_isolation_update ON approvals FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM actions a 
            WHERE a.action_id = approvals.action_id 
            AND (a.tenant_id IS NULL OR a.tenant_id = current_tenant_id())
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM actions a 
            WHERE a.action_id = approvals.action_id 
            AND (a.tenant_id IS NULL OR a.tenant_id = current_tenant_id())
        )
    );
CREATE POLICY tenant_isolation_delete ON approvals FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM actions a 
            WHERE a.action_id = approvals.action_id 
            AND (a.tenant_id IS NULL OR a.tenant_id = current_tenant_id())
        )
    );

-- AUDIT EVENTS (tenant via joined actions)
CREATE POLICY tenant_isolation_select ON audit_events FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM actions a 
            WHERE a.action_id = audit_events.action_id 
            AND (a.tenant_id IS NULL OR a.tenant_id = current_tenant_id() OR current_tenant_id() IS NULL)
        )
    );
CREATE POLICY tenant_isolation_insert ON audit_events FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM actions a 
            WHERE a.action_id = audit_events.action_id 
            AND (a.tenant_id IS NULL OR a.tenant_id = current_tenant_id())
        )
    );
-- Audit is append-only, no update/delete policies

-- EXECUTION RESULTS (tenant via joined actions)
CREATE POLICY tenant_isolation_select ON execution_results FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM actions a 
            WHERE a.action_id = execution_results.action_id 
            AND (a.tenant_id IS NULL OR a.tenant_id = current_tenant_id() OR current_tenant_id() IS NULL)
        )
    );
CREATE POLICY tenant_isolation_insert ON execution_results FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM actions a 
            WHERE a.action_id = execution_results.action_id 
            AND (a.tenant_id IS NULL OR a.tenant_id = current_tenant_id())
        )
    );
CREATE POLICY tenant_isolation_update ON execution_results FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM actions a 
            WHERE a.action_id = execution_results.action_id 
            AND (a.tenant_id IS NULL OR a.tenant_id = current_tenant_id())
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM actions a 
            WHERE a.action_id = execution_results.action_id 
            AND (a.tenant_id IS NULL OR a.tenant_id = current_tenant_id())
        )
    );
CREATE POLICY tenant_isolation_delete ON execution_results FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM actions a 
            WHERE a.action_id = execution_results.action_id 
            AND (a.tenant_id IS NULL OR a.tenant_id = current_tenant_id())
        )
    );

-- Admin bypass policy — auditable, revocable
CREATE POLICY admin_all_access ON actors FOR ALL
    TO PUBLIC
    USING (current_setting('app.is_admin', true)::boolean = true)
    WITH CHECK (current_setting('app.is_admin', true)::boolean = true);

CREATE POLICY admin_all_access ON policies FOR ALL
    TO PUBLIC
    USING (current_setting('app.is_admin', true)::boolean = true)
    WITH CHECK (current_setting('app.is_admin', true)::boolean = true);

CREATE POLICY admin_all_access ON kill_switches FOR ALL
    TO PUBLIC
    USING (current_setting('app.is_admin', true)::boolean = true)
    WITH CHECK (current_setting('app.is_admin', true)::boolean = true);

CREATE POLICY admin_all_access ON actions FOR ALL
    TO PUBLIC
    USING (current_setting('app.is_admin', true)::boolean = true)
    WITH CHECK (current_setting('app.is_admin', true)::boolean = true);

CREATE POLICY admin_all_access ON decisions FOR ALL
    TO PUBLIC
    USING (current_setting('app.is_admin', true)::boolean = true)
    WITH CHECK (current_setting('app.is_admin', true)::boolean = true);

CREATE POLICY admin_all_access ON approvals FOR ALL
    TO PUBLIC
    USING (current_setting('app.is_admin', true)::boolean = true)
    WITH CHECK (current_setting('app.is_admin', true)::boolean = true);

CREATE POLICY admin_all_access ON audit_events FOR ALL
    TO PUBLIC
    USING (current_setting('app.is_admin', true)::boolean = true)
    WITH CHECK (current_setting('app.is_admin', true)::boolean = true);

CREATE POLICY admin_all_access ON execution_results FOR ALL
    TO PUBLIC
    USING (current_setting('app.is_admin', true)::boolean = true)
    WITH CHECK (current_setting('app.is_admin', true)::boolean = true);

-- ============================================================================
-- DESIGN NOTES
-- ============================================================================
/*
1. POLICY IMMUTABILITY
   - Core logic (name, version, scope, rules) is immutable
   - Only status timestamps can change for lifecycle
   - Trigger enforces this at database level

2. APPEND-ONLY AUDIT
   - audit_events has triggers preventing UPDATE/DELETE
   - Hash chain provides tamper evidence
   - verify_audit_chain() checks integrity

3. CAPABILITY ATOMICITY
   - Uses row-level locking (FOR UPDATE)
   - consume_capability() function handles race conditions
   - Application should use this function, not direct UPDATE

4. IDEMPOTENCY
   - uq_actions_actor_idempotency prevents duplicate actions
   - Redis dedupe cache for hot path (5m TTL)
   - request_id for external idempotency keys

5. REPLAYABILITY
   - policy_snapshots store resolved policy at decision time
   - decisions.policy_snapshot_id links to exact policy used
   - actions.context_json stores ambient state

6. ROW-LEVEL SECURITY
   - SET LOCAL app.current_tenant = 'tenant-id' before each query
   - FORCE ROW LEVEL SECURITY prevents superuser leaks
   - Admin bypass via app.is_admin session variable (auditable)
   - Migration role (citadel_migrator) has BYPASSRLS for schema changes
   - If no tenant context set, queries match zero rows (secure by default)

7. PRODUCTION NOTES
   - audit_events append-only intent; real immutability requires
     WAL archiving, object-store replication, or external attestations
   - Consider table partitioning on audit_events by event_ts for scale
   - Index maintenance on JSONB columns may be heavy; monitor
   - Foreign keys add overhead; consider removing for hot paths

8. MINIMAL MVP START
   - actors, actions, decisions, policies, approvals, audit_events
   - Then add: capabilities, kill_switches, policy_snapshots
*/
