// DEMO API Client — Returns mock data without hitting a real backend.
// Use this for sales demos, conference presentations, and onboarding.

const DEMO_DELAY_MS = 300; // Fake network latency

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ─── Mock Data ───

const MOCK_AGENTS: AgentIdentity[] = [
  {
    agent_id: "payment-agent-01",
    tenant_id: "demo",
    public_key: "ed25519_pk_abc123...",
    trust_level: "highly_trusted",
    verification_status: "verified",
    created_at: "2026-01-15T09:30:00Z",
    last_verified_at: "2026-04-25T14:20:00Z",
  },
  {
    agent_id: "data-processor-02",
    tenant_id: "demo",
    public_key: "ed25519_pk_def456...",
    trust_level: "trusted",
    verification_status: "verified",
    created_at: "2026-02-20T11:00:00Z",
    last_verified_at: "2026-04-24T10:15:00Z",
  },
  {
    agent_id: "email-agent-03",
    tenant_id: "demo",
    public_key: "ed25519_pk_ghi789...",
    trust_level: "standard",
    verification_status: "unverified",
    created_at: "2026-03-10T08:45:00Z",
  },
  {
    agent_id: "experimental-04",
    tenant_id: "demo",
    public_key: "ed25519_pk_jkl012...",
    trust_level: "unverified",
    verification_status: "revoked",
    created_at: "2026-03-25T16:20:00Z",
  },
];

const MOCK_TRUST_SCORES: Record<string, TrustScore> = {
  "payment-agent-01": {
    agent_id: "payment-agent-01",
    score: 0.92,
    level: "highly_trusted",
    factors: { verification: 0.25, age_bonus: 0.15, health: 0.20, quarantine: 0.10, action_rate: 0.10, compliance: 0.15, budget: 0.05 },
  },
  "data-processor-02": {
    agent_id: "data-processor-02",
    score: 0.74,
    level: "trusted",
    factors: { verification: 0.25, age_bonus: 0.12, health: 0.18, quarantine: 0.10, action_rate: 0.10, compliance: 0.15, budget: 0.02 },
  },
  "email-agent-03": {
    agent_id: "email-agent-03",
    score: 0.48,
    level: "standard",
    factors: { verification: 0.0, age_bonus: 0.06, health: 0.16, quarantine: 0.10, action_rate: 0.10, compliance: 0.15, budget: 0.05 },
  },
  "experimental-04": {
    agent_id: "experimental-04",
    score: 0.15,
    level: "revoked",
    factors: { verification: 0.0, age_bonus: 0.02, health: 0.10, quarantine: -0.30, action_rate: 0.10, compliance: -0.15, budget: 0.05 },
  },
};

const MOCK_STATS = {
  pending_approvals: 3,
  active_agents: 4,
  risk_level: "LOW",
  kill_switches_active: 0,
  killswitches: { email_send: false, stripe_charge: false, db_write: false },
  recent_events_count: 142,
  total_actions: 12847,
  approved_this_month: 892,
  blocked_this_month: 12,
  active_agents_24h: 4,
  agent_identities: {
    registered: 4,
    verified: 2,
    revoked: 1,
    avg_trust_score: 0.57,
    trust_level_breakdown: { highly_trusted: 1, trusted: 1, standard: 1, revoked: 1 },
  },
};

const MOCK_APPROVALS: Approval[] = [
  {
    approval_id: "app-001",
    action_id: "act-8812",
    status: "pending",
    priority: "high",
    reason: "Agent requests access to production database",
    requested_by: "data-processor-02",
  },
  {
    approval_id: "app-002",
    action_id: "act-8813",
    status: "pending",
    priority: "medium",
    reason: "Email blast to 10,000 users",
    requested_by: "email-agent-03",
  },
  {
    approval_id: "app-003",
    action_id: "act-8814",
    status: "pending",
    priority: "low",
    reason: "Scheduled report generation",
    requested_by: "payment-agent-01",
  },
];

const MOCK_METRICS = {
  actions_total: 12847,
  decisions_by_status: { approved: 892, rejected: 12, pending: 3, executed: 880 },
  pending_approvals: 3,
  audit_events: 28471,
  kill_switches_active: 0,
  capabilities_active: 8,
};

const MOCK_HEALTH = { alive: true, ready: true, database: "connected" };

// ─── API Client (Demo) ───

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// Health
export const healthApi = {
  live: async () => { await delay(DEMO_DELAY_MS); return MOCK_HEALTH; },
  ready: async () => { await delay(DEMO_DELAY_MS); return MOCK_HEALTH; },
};

// Metrics
export const metricsApi = {
  summary: async () => { await delay(DEMO_DELAY_MS); return MOCK_METRICS; },
};

// Approvals
export interface Approval {
  approval_id: string;
  action_id: string;
  status: string;
  priority: string;
  reason: string;
  requested_by: string;
  reviewed_by?: string;
  decided_at?: string;
  decision_reason?: string;
}

export const approvalsApi = {
  list: async (status?: string) => {
    await delay(DEMO_DELAY_MS);
    const items = status ? MOCK_APPROVALS.filter((a) => a.status === status) : MOCK_APPROVALS;
    return { approvals: items, total: items.length };
  },
  get: async (id: string) => {
    await delay(DEMO_DELAY_MS);
    const a = MOCK_APPROVALS.find((x) => x.approval_id === id);
    if (!a) throw new ApiError(404, "Approval not found");
    return a;
  },
  approve: async (id: string, reviewedBy: string, reason?: string) => {
    await delay(DEMO_DELAY_MS);
    const a = MOCK_APPROVALS.find((x) => x.approval_id === id);
    if (!a) throw new ApiError(404, "Approval not found");
    a.status = "approved";
    a.reviewed_by = reviewedBy;
    a.decision_reason = reason || "Approved via dashboard";
    a.decided_at = new Date().toISOString();
    return a;
  },
  reject: async (id: string, reviewedBy: string, reason?: string) => {
    await delay(DEMO_DELAY_MS);
    const a = MOCK_APPROVALS.find((x) => x.approval_id === id);
    if (!a) throw new ApiError(404, "Approval not found");
    a.status = "rejected";
    a.reviewed_by = reviewedBy;
    a.decision_reason = reason || "Rejected via dashboard";
    a.decided_at = new Date().toISOString();
    return a;
  },
};

// Actions
export interface Action {
  action_id: string;
  actor_id: string;
  action_name: string;
  resource: string;
  status: string;
  winning_rule: string;
  reason: string;
  executed: boolean;
  created_at?: string;
}

export const actionsApi = {
  get: async (id: string) => {
    await delay(DEMO_DELAY_MS);
    return {
      action_id: id,
      actor_id: "payment-agent-01",
      action_name: "stripe.charge",
      resource: "cus_demo_123",
      status: "allowed",
      winning_rule: "payment-auto-approve",
      reason: "Within budget and trust threshold",
      executed: true,
      created_at: new Date().toISOString(),
    } as Action;
  },
  submit: async (data: {
    actor_id: string;
    action_name: string;
    resource: string;
    payload?: Record<string, unknown>;
  }) => {
    await delay(DEMO_DELAY_MS);
    return {
      action_id: "act-" + Math.random().toString(36).slice(2, 8),
      actor_id: data.actor_id,
      action_name: data.action_name,
      resource: data.resource,
      status: "pending",
      winning_rule: "pending-review",
      reason: "Submitted for governance review",
      executed: false,
      created_at: new Date().toISOString(),
    } as Action;
  },
};

// Governance / Audit
export const auditApi = {
  verify: async () => {
    await delay(DEMO_DELAY_MS);
    return { valid: true, checked_count: 28471 };
  },
  governanceVerify: async () => {
    await delay(DEMO_DELAY_MS);
    return { valid: true, checked_count: 28471 };
  },
};

// Agent Identities
export interface AgentIdentity {
  agent_id: string;
  tenant_id: string;
  public_key: string;
  trust_level: string;
  verification_status: string;
  created_at: string;
  last_verified_at?: string;
  metadata?: Record<string, unknown>;
}

export interface TrustScore {
  agent_id: string;
  score: number;
  level: string;
  factors: Record<string, number>;
}

export interface CapabilityToken {
  type: string;
  agent_id: string;
  action: string;
  resource: string;
  issued_at: string;
  expires_at: string;
  trust_level: string;
}

export const agentIdentityApi = {
  list: async (tenantId?: string) => {
    await delay(DEMO_DELAY_MS);
    return { identities: MOCK_AGENTS, count: MOCK_AGENTS.length };
  },
  get: async (agentId: string) => {
    await delay(DEMO_DELAY_MS);
    const a = MOCK_AGENTS.find((x) => x.agent_id === agentId);
    if (!a) throw new ApiError(404, "Agent not found");
    return a;
  },
  register: async (data: { agent_id: string; name: string; tenant_id: string; owner?: string }) => {
    await delay(DEMO_DELAY_MS);
    return {
      agent_id: data.agent_id,
      api_key: "ak_demo_" + Math.random().toString(36).slice(2, 10),
      secret_key: "sk_demo_" + Math.random().toString(36).slice(2, 10),
      public_key: "ed25519_pk_new...",
      trust_score: 0.35,
      trust_level: "unverified",
    };
  },
  authenticate: async (agentId: string, secretKey: string) => {
    await delay(DEMO_DELAY_MS);
    const a = MOCK_AGENTS.find((x) => x.agent_id === agentId);
    if (!a) throw new ApiError(404, "Agent not found");
    return {
      agent_id: agentId,
      authenticated: true,
      tenant_id: a.tenant_id,
      trust_level: a.trust_level,
      verification_status: a.verification_status,
    };
  },
  trust: async (agentId: string) => {
    await delay(DEMO_DELAY_MS);
    const t = MOCK_TRUST_SCORES[agentId];
    if (!t) throw new ApiError(404, "Trust score not found");
    return t;
  },
  capability: async (agentId: string, action: string, resource: string, context?: Record<string, unknown>) => {
    await delay(DEMO_DELAY_MS);
    const a = MOCK_AGENTS.find((x) => x.agent_id === agentId);
    if (!a) throw new ApiError(404, "Agent not found");
    const token: CapabilityToken = {
      type: "capability",
      agent_id: agentId,
      action,
      resource,
      issued_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 3600000).toISOString(),
      trust_level: a.trust_level,
    };
    return { verified: true, authorized: a.trust_level !== "revoked", token };
  },
  revoke: async (agentId: string, reason: string) => {
    await delay(DEMO_DELAY_MS);
    const a = MOCK_AGENTS.find((x) => x.agent_id === agentId);
    if (!a) throw new ApiError(404, "Agent not found");
    a.verification_status = "revoked";
    a.trust_level = "revoked";
    return { agent_id: agentId, revoked: true, reason };
  },
};

// Dashboard Stats
export const dashboardApi = {
  stats: async () => {
    await delay(DEMO_DELAY_MS);
    return MOCK_STATS;
  },
  approvals: async () => {
    await delay(DEMO_DELAY_MS);
    return { approvals: MOCK_APPROVALS.map((a) => ({ ...a, id: a.approval_id })) };
  },
};

export type { ApiError };
