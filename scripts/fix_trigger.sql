-- Fix calculate_event_hash to handle NULL prev_hash
-- The issue: calculate_event_hash fires BEFORE set_audit_prev_hash alphabetically,
-- so NEW.prev_hash is NULL when hash calculation runs.
-- String concatenation with NULL returns NULL, causing digest(NULL) -> NULL.

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

-- Recreate trigger (ensures it's properly bound)
DROP TRIGGER IF EXISTS trg_audit_event_hash ON audit_events;
CREATE TRIGGER trg_audit_event_hash
    BEFORE INSERT ON audit_events
    FOR EACH ROW
    EXECUTE FUNCTION calculate_event_hash();
