-- ============================================================================
-- LEDGER CONTROL-SYSTEM DATABASE SCHEMA
-- ============================================================================
-- 
-- Design principles:
-- 1. Append-only where possible (audit, policy versions, decisions)
-- 2. Mutable only for live state (capabilities, kill switches, approvals)
-- 3. Separate normalized action from audit trail
-- 4. Every decision must be replayable
--
-- Two logical stores:
-- - Operational store (Postgres): policies, approvals, actors, capabilities
-- - Audit/event store (Postgres): append-only action/decision/event history
-- - Redis (ephemeral): rate limits, locks, hot cache (not source of truth)
--
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- OPERATIONAL STORE: Live governance state
-- ============================================================================

-- ----------------------------------------------------------------------------
-- ACTORS: Who is allowed to act
-- ----------------------------------------------------------------------------
CREATE TABLE actors (
    actor_id TEXT PRIMARY KEY,
    actor_type TEXT NOT NULL CHECK (actor_type IN ('agent', 'workflow', 'service', 'user_proxy')),
    tenant_id TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'revoked')),
    metadata_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE actors IS 'Registry of all actors that can request actions';
COMMENT ON COLUMN actors.actor_type IS 'Type of actor: agent, workflow, service, or user_proxy';
COMMENT ON COLUMN actors.status IS 'Lifecycle status: active, suspended, or revoked';

CREATE INDEX idx_actors_tenant ON actors(tenant_id);
CREATE INDEX idx_actors_status ON actors(status) WHERE status = 'active';
CREATE INDEX idx_actors_type ON actors(actor_type);

-- ----------------------------------------------------------------------------
-- POLICIES: Current policy objects (versioned, immutable logic)
-- ----------------------------------------------------------------------------
CREATE TABLE policies (
    policy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id TEXT,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    scope_type TEXT NOT NULL CHECK (scope_type IN ('global', 'actor', 'action', 'resource', 'tenant')),
    scope_value TEXT NOT NULL,
    rules_json JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'retired')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ,
    
    UNIQUE(name, version)
);

COMMENT ON TABLE policies IS 'Policy definitions - never mutate active policy logic in place, create new version';
COMMENT ON COLUMN policies.scope_type IS 'Policy scope: global, actor-specific, action-specific, resource-specific, or tenant';
COMMENT ON COLUMN policies.status IS 'Draft -> Active -> Retired lifecycle';

CREATE INDEX idx_policies_tenant ON policies(tenant_id);
CREATE INDEX idx_policies_status ON policies(status) WHERE status = 'active';
CREATE INDEX idx_policies_scope ON policies(scope_type, scope_value);
CREATE INDEX idx_policies_active ON policies(tenant_id, scope_type, scope_value) WHERE status = 'active';

-- ----------------------------------------------------------------------------
-- POLICY_SNAPSHOTS: Immutable snapshots used by decisions (for replay)
-- ----------------------------------------------------------------------------
CREATE TABLE policy_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_id UUID NOT NULL REFERENCES policies(policy_id),
    policy_version TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL UNIQUE,
    snapshot_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE policy_snapshots IS 'Resolved immutable policy snapshots - critical for decision replay';
COMMENT ON COLUMN policy_snapshots.snapshot_hash IS 'SHA-256 hash of resolved policy for integrity verification';

CREATE INDEX idx_snapshots_policy ON policy_snapshots(policy_id);
CREATE INDEX idx_snapshots_hash ON policy_snapshots(snapshot_hash);

-- ----------------------------------------------------------------------------
-- CAPABILITIES: Scoped permission grants (mutable use count)
-- ----------------------------------------------------------------------------
CREATE TABLE capabilities (
    token_id TEXT PRIMARY KEY,
    actor_id TEXT NOT NULL REFERENCES actors(actor_id),
    action_scope TEXT NOT NULL,  -- e.g., "email:*", "stripe:charge"
    resource_scope TEXT NOT NULL, -- e.g., "outbound", "prod_customers"
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    max_uses INTEGER NOT NULL DEFAULT 1,
    uses INTEGER NOT NULL DEFAULT 0,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    metadata_json JSONB NOT NULL DEFAULT '{}',
    
    CONSTRAINT valid_uses CHECK (uses <= max_uses),
    CONSTRAINT valid_expiry CHECK (expires_at > issued_at)
);

COMMENT ON TABLE capabilities IS 'Token-based capability system - mutable use count, atomic updates required';
COMMENT ON COLUMN capabilities.token_id IS 'Unique capability token (e.g., cap_xxx) issued by Governor';

CREATE INDEX idx_capabilities_actor ON capabilities(actor_id);
CREATE INDEX idx_capabilities_active ON capabilities(actor_id, action_scope) 
    WHERE revoked = FALSE AND uses < max_uses AND expires_at > NOW();
CREATE INDEX idx_capabilities_expiry ON capabilities(expires_at) 
    WHERE revoked = FALSE;

-- ----------------------------------------------------------------------------
-- KILL_SWITCHES: Emergency controls (mutable enabled state)
-- ----------------------------------------------------------------------------
CREATE TABLE kill_switches (
    switch_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scope_type TEXT NOT NULL CHECK (scope_type IN ('global', 'tenant', 'actor', 'action', 'resource')),
    scope_value TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    reason TEXT,
    triggered_by TEXT,
    triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(scope_type, scope_value)
);

COMMENT ON TABLE kill_switches IS 'Emergency stop controls - fast lookup, mutable enabled state';

CREATE INDEX idx_killswitches_enabled ON kill_switches(scope_type, scope_value) 
    WHERE enabled = TRUE;

-- ----------------------------------------------------------------------------
-- APPROVALS: Human-in-the-loop state (mutable status)
-- ----------------------------------------------------------------------------
CREATE TABLE approvals (
    approval_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action_id UUID NOT NULL UNIQUE,  -- References actions table
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'expired', 'escalated')),
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    requested_by TEXT NOT NULL REFERENCES actors(actor_id),
    reviewed_by TEXT REFERENCES actors(actor_id),
    reason TEXT NOT NULL,  -- Why approval is needed
    decision_reason TEXT,  -- Why reviewer approved/rejected
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at TIMESTAMPTZ,
    escalated_to TEXT,  -- For escalation chains
    
    CONSTRAINT valid_decision CHECK (
        (status IN ('approved', 'rejected') AND decided_at IS NOT NULL AND reviewed_by IS NOT NULL)
        OR (status IN ('pending', 'expired') AND decided_at IS NULL)
    )
);

COMMENT ON TABLE approvals IS 'Approval queue for human-in-the-loop governance';

CREATE INDEX idx_approvals_status ON approvals(status);
CREATE INDEX idx_approvals_pending ON approvals(status, priority, created_at) 
    WHERE status = 'pending';
CREATE INDEX idx_approvals_expiry ON approvals(expires_at) 
    WHERE status = 'pending';
CREATE INDEX idx_approvals_requester ON approvals(requested_by);

-- ============================================================================
-- AUDIT/EVENT STORE: Append-only history (never mutate)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- ACTIONS: Canonical action record (normalized request)
-- ----------------------------------------------------------------------------
CREATE TABLE actions (
    action_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_id TEXT NOT NULL REFERENCES actors(actor_id),
    actor_type TEXT NOT NULL,
    action_name TEXT NOT NULL,  -- e.g., "send_email", "stripe_charge"
    resource TEXT NOT NULL,     -- e.g., "outbound", "customers"
    tenant_id TEXT,
    
    -- Request payload (normalized)
    payload_json JSONB NOT NULL DEFAULT '{}',
    
    -- Context at time of request
    context_json JSONB NOT NULL DEFAULT '{}',
    
    -- Session tracking
    session_id TEXT,
    request_id TEXT UNIQUE,     -- For idempotency
    idempotency_key TEXT,
    
    -- Timing
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Pre-computed for fast queries
    action_resource TEXT GENERATED ALWAYS AS (action_name || ':' || resource) STORED
);

COMMENT ON TABLE actions IS 'Canonical action requests - immutable record of what was requested';

CREATE INDEX idx_actions_actor ON actions(actor_id, created_at DESC);
CREATE INDEX idx_actions_tenant ON actions(tenant_id, created_at DESC);
CREATE INDEX idx_actions_resource ON actions(action_resource, created_at DESC);
CREATE INDEX idx_actions_session ON actions(session_id);
CREATE INDEX idx_actions_request ON actions(request_id) WHERE request_id IS NOT NULL;
CREATE INDEX idx_actions_time ON actions(created_at DESC);

-- ----------------------------------------------------------------------------
-- DECISIONS: Decision result for an action (append-only, one per action)
-- ----------------------------------------------------------------------------
CREATE TABLE decisions (
    decision_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action_id UUID NOT NULL UNIQUE REFERENCES actions(action_id),
    
    -- What policy was used (for replay)
    policy_snapshot_id UUID REFERENCES policy_snapshots(snapshot_id),
    
    -- Decision outcome
    status TEXT NOT NULL CHECK (status IN ('blocked', 'allowed', 'pending_approval', 'rejected', 'error')),
    winning_rule TEXT NOT NULL,  -- Which rule determined outcome
    reason TEXT NOT NULL,        -- Human-readable decision explanation
    
    -- Capability used (if any)
    capability_token TEXT,
    
    -- Risk assessment at time of decision
    risk_level TEXT CHECK (risk_level IN ('none', 'low', 'medium', 'high', 'critical')),
    risk_score INTEGER CHECK (risk_score >= 0 AND risk_score <= 100),
    
    -- Execution path taken (from RUNTIME.md)
    path_taken TEXT CHECK (path_taken IN ('fast', 'standard', 'structured', 'high_risk', 'bypass')),
    
    -- Timing
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    executed_at TIMESTAMPTZ,     -- When action was actually executed (if allowed)
    
    -- For chain verification
    decision_hash TEXT NOT NULL
);

COMMENT ON TABLE decisions IS 'Terminal decision for each action - immutable, replayable';
COMMENT ON COLUMN decisions.decision_hash IS 'Hash of decision for integrity verification';

CREATE INDEX idx_decisions_action ON decisions(action_id);
CREATE INDEX idx_decisions_status ON decisions(status);
CREATE INDEX idx_decisions_policy ON decisions(policy_snapshot_id);
CREATE INDEX idx_decisions_time ON decisions(created_at DESC);

-- ----------------------------------------------------------------------------
-- AUDIT_EVENTS: Full chronological story (append-only chain)
-- ----------------------------------------------------------------------------
CREATE TABLE audit_events (
    event_id BIGSERIAL PRIMARY KEY,
    
    -- Reference to action
    action_id UUID NOT NULL REFERENCES actions(action_id),
    
    -- Event classification
    event_type TEXT NOT NULL CHECK (event_type IN (
        'action_received',      -- Action entered system
        'policy_evaluated',     -- Policy checked
        'kill_switch_checked',  -- Kill switch verified
        'capability_checked',   -- Capability validated
        'risk_assessed',        -- Risk scored
        'approval_requested',   -- Approval queued
        'approval_granted',     -- Human approved
        'approval_denied',      -- Human rejected
        'decision_made',        -- Final decision recorded
        'action_executed',      -- Action completed
        'action_failed',        -- Execution error
        'escalation_triggered', -- Level 2/3 escalation
        'kill_switch_activated' -- Emergency stop
    )),
    
    -- Event payload (type-specific)
    event_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload_json JSONB NOT NULL DEFAULT '{}',
    
    -- Hash chain for integrity (tamper-proof)
    prev_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL UNIQUE,
    
    -- Optional: link to specific entities
    actor_id TEXT,
    tenant_id TEXT,
    policy_id UUID
);

COMMENT ON TABLE audit_events IS 'Full chronological audit trail - append-only, hash-chained';
COMMENT ON COLUMN audit_events.prev_hash IS 'Hash of previous event in chain';
COMMENT ON COLUMN audit_events.event_hash IS 'SHA-256 hash of this event for verification';

CREATE INDEX idx_audit_action ON audit_events(action_id, event_id);
CREATE INDEX idx_audit_type ON audit_events(event_type, event_ts DESC);
CREATE INDEX idx_audit_actor ON audit_events(actor_id, event_ts DESC);
CREATE INDEX idx_audit_tenant ON audit_events(tenant_id, event_ts DESC);
CREATE INDEX idx_audit_time ON audit_events(event_ts DESC);

-- ============================================================================
-- VIEWS: For common query patterns
-- ============================================================================

-- Active governance state (what's enforced right now)
CREATE VIEW active_governance_state AS
SELECT 
    'actor' as entity_type,
    actor_id as entity_id,
    status as state,
    metadata_json as config
FROM actors WHERE status = 'active'
UNION ALL
SELECT 
    'policy' as entity_type,
    policy_id::text as entity_id,
    status as state,
    jsonb_build_object('scope', scope_type || ':' || scope_value, 'version', version) as config
FROM policies WHERE status = 'active'
UNION ALL
SELECT 
    'kill_switch' as entity_type,
    switch_id::text as entity_id,
    CASE WHEN enabled THEN 'armed' ELSE 'disarmed' END as state,
    jsonb_build_object('scope', scope_type || ':' || scope_value, 'reason', reason) as config
FROM kill_switches;

-- Pending approvals queue
CREATE VIEW pending_approvals_queue AS
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

-- Decision history with action details (for replay)
CREATE VIEW decision_replay_log AS
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
-- FUNCTIONS: Integrity verification
-- ============================================================================

-- Verify audit chain integrity
CREATE OR REPLACE FUNCTION verify_audit_chain()
RETURNS TABLE (
    valid BOOLEAN,
    checked_count BIGINT,
    first_event_id BIGINT,
    last_event_id BIGINT
) AS $$
DECLARE
    v_valid BOOLEAN := TRUE;
    v_count BIGINT;
    v_first BIGINT;
    v_last BIGINT;
    rec RECORD;
    expected_hash TEXT;
BEGIN
    SELECT COUNT(*), MIN(event_id), MAX(event_id) 
    INTO v_count, v_first, v_last
    FROM audit_events;
    
    -- Check each link in chain
    FOR rec IN 
        SELECT event_id, event_hash, prev_hash 
        FROM audit_events 
        ORDER BY event_id
    LOOP
        IF rec.event_id > v_first THEN
            -- Verify prev_hash matches previous event's hash
            SELECT event_hash INTO expected_hash
            FROM audit_events 
            WHERE event_id = rec.event_id - 1;
            
            IF rec.prev_hash != expected_hash THEN
                v_valid := FALSE;
                EXIT;
            END IF;
        END IF;
    END LOOP;
    
    RETURN QUERY SELECT v_valid, v_count, v_first, v_last;
END;
$$ LANGUAGE plpgsql;

-- Calculate event hash (for insertion triggers)
CREATE OR REPLACE FUNCTION calculate_event_hash()
RETURNS TRIGGER AS $$
BEGIN
    NEW.event_hash := encode(
        digest(
            NEW.event_id::text || 
            COALESCE(NEW.action_id::text, '') || 
            NEW.event_type || 
            NEW.event_ts::text || 
            COALESCE(NEW.payload_json::text, '{}') ||
            NEW.prev_hash,
            'sha256'
        ),
        'hex'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Auto-set prev_hash on insert
CREATE OR REPLACE FUNCTION set_audit_prev_hash()
RETURNS TRIGGER AS $$
DECLARE
    last_hash TEXT;
BEGIN
    SELECT event_hash INTO last_hash
    FROM audit_events
    ORDER BY event_id DESC
    LIMIT 1;
    
    NEW.prev_hash := COALESCE(last_hash, '0' || repeat('0', 63));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to maintain hash chain
CREATE TRIGGER audit_event_hash_chain
    BEFORE INSERT ON audit_events
    FOR EACH ROW
    EXECUTE FUNCTION set_audit_prev_hash();

-- ============================================================================
-- REDIS SCHEMA (documented, not SQL)
-- ============================================================================
/*
REDIS KEY PATTERNS (ephemeral only, not source of truth):

Rate limiting:
  ratelimit:{actor_id}:{action} → sorted set of timestamps (sliding window)
  ratelimit:{tenant_id}:global → global rate limit counters

Approval queue fanout:
  approvals:pending → list of pending approval_ids (for pub/sub)
  approvals:priority:{priority} → priority-segregated queues

Distributed locks:
  lock:capability:{token_id} → lock for atomic capability use
  lock:approval:{approval_id} → lock for approval decision
  lock:action:{action_id} → lock for action execution

Hot cache (fast lookups, TTL short):
  cache:killswitch:{scope} → cached kill switch status (TTL: 5s)
  cache:policy:{tenant}:{scope} → cached active policy (TTL: 30s)
  cache:actor:{actor_id} → cached actor status (TTL: 60s)

Temporary dedupe:
  dedupe:{idempotency_key} → "1" (TTL: 5m, for idempotency)

NOT stored in Redis (Postgres is source of truth):
  - Audit log
  - Policy definitions
  - Final approval state
  - Capability authoritative state
  - Decision history
*/

-- ============================================================================
-- MINIMAL MVP STARTER SET
-- Uncomment to create minimal useful version
-- ============================================================================
/*
-- Minimal tables for MVP:
-- 1. actions - canonical action record
-- 2. decisions - decision results
-- 3. policies - current policies
-- 4. approvals - human-in-the-loop
-- 5. audit_events - append-only history
-- 6. kill_switches - emergency stops
-- Then add:
-- 7. capabilities - token-based permissions
-- 8. actors - actor registry
-- 9. policy_snapshots - for replay
*/

-- ============================================================================
-- INDEX SUMMARY
-- ============================================================================
/*
Core operational queries:
  - actors: tenant, status, type
  - policies: tenant, status, scope, active lookup
  - capabilities: actor, active, expiry
  - kill_switches: enabled lookup
  - approvals: status, pending queue, expiry

Audit queries:
  - actions: actor, tenant, resource, session, time
  - decisions: action, status, policy, time
  - audit_events: action, type, actor, tenant, time

All indexes support the governance control flow:
  1. Fast actor lookup
  2. Fast policy resolution
  3. Fast kill switch check
  4. Fast capability validation
  5. Fast approval queue
  6. Fast audit retrieval
*/
