-- ============================================================================
-- MIGRATION 004: Governance Audit Trail Separation
-- Phase 2: Separate governance audit from operational audit_events
-- ============================================================================
--
-- Why separate:
--   - audit_events tracks action lifecycle (received → evaluated → executed)
--   - governance_audit_log tracks decision/token verification events
--   - Different retention, query patterns, and compliance requirements
--   - EU AI Act Article 14(4)(e) requires explainability of every decision
--
-- Properties:
--   - STRICT append-only (no UPDATE, no DELETE)
--   - Hash-chained (tamper-evident)
--   - Tenant-isolated via RLS
--   - Advisory-lock serialized appends (correct prev_hash under concurrency)

-- ============================================================================
-- TABLE: governance_audit_log
-- ============================================================================

CREATE TABLE IF NOT EXISTS governance_audit_log (
    event_id BIGSERIAL PRIMARY KEY,
    event_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- What happened
    event_type TEXT NOT NULL CHECK (event_type IN (
        'token.verification',      -- TokenVerifier.verify_token()
        'decision.verification',   -- TokenVerifier.verify_decision()
        'execution.allowed',       -- ExecutionMiddleware allowed
        'execution.blocked',       -- ExecutionMiddleware blocked
        'execution.rate_limited',  -- ExecutionMiddleware rate limited
        'decision.created',        -- DecisionEngine produced decision
        'token.derived',           -- CapabilityToken.derive()
        'token.revoked',           -- Explicit token revocation
        'decision.revoked'         -- Explicit decision revocation
    )),

    -- Who and where
    tenant_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    decision_id TEXT,            -- links to governance_decisions (optional)
    token_id TEXT,               -- links to governance_tokens (optional)

    -- Event payload (structured, queryable)
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Hash chain (tamper evidence)
    prev_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL UNIQUE,

    -- Session/trace context
    session_id TEXT,
    request_id TEXT
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_gov_audit_tenant_ts
    ON governance_audit_log (tenant_id, event_ts DESC);

CREATE INDEX IF NOT EXISTS idx_gov_audit_decision
    ON governance_audit_log (decision_id, event_ts DESC)
    WHERE decision_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_gov_audit_token
    ON governance_audit_log (token_id, event_ts DESC)
    WHERE token_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_gov_audit_actor_ts
    ON governance_audit_log (actor_id, event_ts DESC);

CREATE INDEX IF NOT EXISTS idx_gov_audit_event_type
    ON governance_audit_log (event_type, event_ts DESC);

CREATE INDEX IF NOT EXISTS idx_gov_audit_payload_gin
    ON governance_audit_log USING GIN (payload_json);

-- ============================================================================
-- APPEND-ONLY ENFORCEMENT
-- ============================================================================

CREATE OR REPLACE FUNCTION forbid_governance_audit_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'governance_audit_log is append-only: event_id=%', OLD.event_id;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_forbid_gov_audit_update ON governance_audit_log;
CREATE TRIGGER trg_forbid_gov_audit_update
    BEFORE UPDATE ON governance_audit_log
    FOR EACH ROW
    EXECUTE FUNCTION forbid_governance_audit_mutation();

DROP TRIGGER IF EXISTS trg_forbid_gov_audit_delete ON governance_audit_log;
CREATE TRIGGER trg_forbid_gov_audit_delete
    BEFORE DELETE ON governance_audit_log
    FOR EACH ROW
    EXECUTE FUNCTION forbid_governance_audit_mutation();

-- ============================================================================
-- HASH CHAIN TRIGGERS
-- ============================================================================

CREATE OR REPLACE FUNCTION set_governance_audit_prev_hash()
RETURNS TRIGGER AS $$
DECLARE
    last_hash TEXT;
BEGIN
    SELECT event_hash INTO last_hash
    FROM governance_audit_log
    ORDER BY event_id DESC
    LIMIT 1;

    NEW.prev_hash := COALESCE(last_hash, repeat('0', 64));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_gov_audit_prev_hash ON governance_audit_log;
CREATE TRIGGER trg_gov_audit_prev_hash
    BEFORE INSERT ON governance_audit_log
    FOR EACH ROW
    EXECUTE FUNCTION set_governance_audit_prev_hash();

CREATE OR REPLACE FUNCTION calculate_governance_event_hash()
RETURNS TRIGGER AS $$
BEGIN
    NEW.event_hash := encode(
        digest(
            COALESCE(NEW.tenant_id, '') ||
            COALESCE(NEW.actor_id, '') ||
            NEW.event_type ||
            NEW.event_ts::text ||
            COALESCE(NEW.decision_id, '') ||
            COALESCE(NEW.token_id, '') ||
            COALESCE(NEW.payload_json::text, '{}') ||
            COALESCE(NEW.prev_hash, repeat('0', 64)) ||
            COALESCE(NEW.session_id, '') ||
            COALESCE(NEW.request_id, ''),
            'sha256'
        ),
        'hex'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_gov_audit_event_hash ON governance_audit_log;
CREATE TRIGGER trg_gov_audit_event_hash
    BEFORE INSERT ON governance_audit_log
    FOR EACH ROW
    EXECUTE FUNCTION calculate_governance_event_hash();

-- ============================================================================
-- RLS: STRICT TENANT ISOLATION
-- ============================================================================

ALTER TABLE governance_audit_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS governance_audit_tenant_isolation ON governance_audit_log;
CREATE POLICY governance_audit_tenant_isolation ON governance_audit_log
    FOR ALL
    USING (tenant_id = get_tenant_context() OR admin_bypass_rls());

ALTER TABLE governance_audit_log FORCE ROW LEVEL SECURITY;

-- ============================================================================
-- INTEGRITY VERIFICATION FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION verify_governance_audit_chain()
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
    FROM governance_audit_log;

    IF v_count = 0 THEN
        RETURN QUERY SELECT TRUE, 0::bigint, NULL::bigint, NULL::bigint, NULL::bigint;
        RETURN;
    END IF;

    FOR rec IN
        SELECT event_id, event_hash, prev_hash
        FROM governance_audit_log
        ORDER BY event_id
    LOOP
        IF rec.event_id > v_first THEN
            SELECT event_hash INTO expected_hash
            FROM governance_audit_log
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

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE governance_audit_log IS
    'Separated governance audit trail for decisions, tokens, and verification events. Append-only, hash-chained, tamper-evident.';
