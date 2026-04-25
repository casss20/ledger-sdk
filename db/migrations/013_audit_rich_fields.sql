-- ============================================================================
-- MIGRATION 013: Enrich governance_audit_log for elite traceability
-- Adds: trace_id, initiator_role, agent_id, policy_id, policy_name,
--       reason, approver_id, approver_role, environment
-- ============================================================================

ALTER TABLE governance_audit_log
  ADD COLUMN IF NOT EXISTS trace_id        TEXT,
  ADD COLUMN IF NOT EXISTS initiator_role  TEXT,
  ADD COLUMN IF NOT EXISTS agent_id        TEXT,
  ADD COLUMN IF NOT EXISTS policy_id       TEXT,
  ADD COLUMN IF NOT EXISTS policy_name     TEXT,
  ADD COLUMN IF NOT EXISTS reason          TEXT,
  ADD COLUMN IF NOT EXISTS approver_id     TEXT,
  ADD COLUMN IF NOT EXISTS approver_role   TEXT,
  ADD COLUMN IF NOT EXISTS environment     TEXT DEFAULT 'production';

CREATE INDEX IF NOT EXISTS idx_gov_audit_trace_id
    ON governance_audit_log (trace_id)
    WHERE trace_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_gov_audit_agent_id
    ON governance_audit_log (agent_id, event_ts DESC)
    WHERE agent_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_gov_audit_policy_id
    ON governance_audit_log (policy_id, event_ts DESC)
    WHERE policy_id IS NOT NULL;

-- ============================================================================
-- SEED: Demo audit entries for a default tenant
-- (No-op if governance_audit_log already has rows for this tenant)
-- ============================================================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM governance_audit_log WHERE tenant_id = 'demo'
  ) THEN
    INSERT INTO governance_audit_log
      (event_type, tenant_id, actor_id, payload_json,
       trace_id, initiator_role, agent_id, policy_id, policy_name,
       reason, approver_id, approver_role, environment)
    VALUES
      ('execution.allowed', 'demo', 'sarah.chen',
       '{"action":"stripe.refund_create","latency_ms":1.2,"verified":true}'::jsonb,
       'trc-001-a2f9', 'executive', 'nova-v2', 'pol-refund-limit', 'Refund Limit Guard',
       'Amount within $500 threshold. Policy satisfied.', NULL, NULL, 'production'),

      ('execution.blocked', 'demo', 'system',
       '{"action":"s3.bucket_delete","latency_ms":0.8,"verified":true}'::jsonb,
       'trc-002-c4d1', 'operator', 'forge-v1', 'pol-destruction-guard', 'Destruction Guard',
       'Bucket contains active production data. Deletion blocked by irreversibility policy.', NULL, NULL, 'production'),

      ('execution.allowed', 'demo', 'marcus.johnson',
       '{"action":"db.phi_query","latency_ms":2.1,"verified":true}'::jsonb,
       'trc-003-e7b2', 'admin', 'cipher-v1', 'pol-hipaa-access', 'HIPAA PHI Access',
       'Escalated for human review — PHI scope exceeded operator threshold.', 'priya.patel', 'auditor', 'production'),

      ('execution.allowed', 'demo', 'alex.rivera',
       '{"action":"slack.message_send","latency_ms":0.6,"verified":true}'::jsonb,
       'trc-004-f0a3', 'operator', 'sentinel-v3', 'pol-comms-ok', 'Communications Policy',
       'Message content passed PII scrub. Channel is approved.', NULL, NULL, 'production'),

      ('execution.allowed', 'demo', 'sarah.chen',
       '{"action":"github.pr_merge","latency_ms":1.0,"verified":true}'::jsonb,
       'trc-005-b8c9', 'executive', 'nova-v2', 'pol-ci-approved', 'CI Gate Policy',
       'All required checks passed. Branch protection satisfied.', NULL, NULL, 'staging'),

      ('execution.blocked', 'demo', 'system',
       '{"action":"aws.iam_escalate","latency_ms":0.9,"verified":true}'::jsonb,
       'trc-006-d2e5', 'operator', 'ghost-v1', 'pol-privilege-guard', 'Privilege Escalation Guard',
       'Requested IAM role exceeds agent permission envelope. Zero-trust violation.', NULL, NULL, 'production'),

      ('execution.allowed', 'demo', 'marcus.johnson',
       '{"action":"openai.chat_complete","latency_ms":3.2,"verified":true}'::jsonb,
       'trc-007-g6h4', 'admin', 'atlas-v2', 'pol-token-budget', 'Token Budget Policy',
       'Monthly spend at 61% of budget. Request within allocation.', NULL, NULL, 'production'),

      ('decision.created', 'demo', 'system',
       '{"action":"db.customer_export","latency_ms":1.8,"verified":true}'::jsonb,
       'trc-008-k1l7', 'operator', 'drift-v2', 'pol-gdpr-check', 'GDPR Export Control',
       'Export scope includes EU citizens. Escalated pending DPO sign-off.', 'priya.patel', 'auditor', 'production'),

      ('execution.allowed', 'demo', 'alex.rivera',
       '{"action":"stripe.invoice_void","latency_ms":1.1,"verified":true}'::jsonb,
       'trc-009-m3n8', 'operator', 'forge-v1', 'pol-invoice-guard', 'Invoice Guard',
       'Invoice is unpaid and within 48h window. Void permitted.', NULL, NULL, 'production'),

      ('execution.blocked', 'demo', 'system',
       '{"action":"s3.object_delete","latency_ms":0.7,"verified":true}'::jsonb,
       'trc-010-p5q2', 'operator', 'nova-v2', 'pol-destruction-guard', 'Destruction Guard',
       'Object tagged retention:7yr. Cannot delete before 2031-04-24.', NULL, NULL, 'production'),

      ('execution.allowed', 'demo', 'marcus.johnson',
       '{"action":"api.key_rotate","latency_ms":4.5,"verified":true}'::jsonb,
       'trc-011-r7s0', 'admin', 'cipher-v1', 'pol-security-maint', 'Security Maintenance',
       'Key is 91 days old. Rotation is within policy window (90–120d).', NULL, NULL, 'production'),

      ('execution.allowed', 'demo', 'system',
       '{"action":"pagerduty.incident","latency_ms":2.3,"verified":true}'::jsonb,
       'trc-012-t9u6', 'operator', 'sentinel-v3', 'pol-incident-response', 'Incident Response',
       'P1 alert threshold crossed. Autonomous escalation authorised by policy.', 'sarah.chen', 'executive', 'production');
  END IF;
END $$;
