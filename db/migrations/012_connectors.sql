CREATE TABLE IF NOT EXISTS connectors (
  connector_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL DEFAULT 'dev_tenant',
  name TEXT NOT NULL,
  provider TEXT NOT NULL,
  icon TEXT NOT NULL DEFAULT 'Cloud',
  description TEXT NOT NULL DEFAULT '',
  connected BOOLEAN NOT NULL DEFAULT FALSE,
  api_key_hint TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO connectors (connector_id, tenant_id, name, provider, icon, description, connected) VALUES
  ('c1','dev_tenant','AWS Bedrock','Amazon','Cloud','Managed foundation model access via AWS.',true),
  ('c2','dev_tenant','OpenAI','OpenAI','Brain','GPT-4, GPT-4 Turbo, and embeddings.',true),
  ('c3','dev_tenant','Anthropic Claude','Anthropic','MessageSquare','Claude 3 Opus, Sonnet, Haiku.',false),
  ('c4','dev_tenant','Azure OpenAI','Microsoft','Cloud','Enterprise OpenAI in your Azure tenant.',false),
  ('c5','dev_tenant','Google Vertex','Google','Globe','Gemini and PaLM via Google Cloud.',false),
  ('c6','dev_tenant','Cohere','Cohere','Brain','Command and Embed for enterprise RAG.',false)
ON CONFLICT (connector_id) DO NOTHING;
