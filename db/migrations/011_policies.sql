CREATE TABLE IF NOT EXISTS governance_policies (
  policy_id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
  tenant_id TEXT NOT NULL DEFAULT 'dev_tenant',
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  framework TEXT NOT NULL DEFAULT 'SOC2',
  status TEXT NOT NULL DEFAULT 'draft',
  severity TEXT NOT NULL DEFAULT 'medium',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
