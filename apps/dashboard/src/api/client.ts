// API Client for Citadel Dashboard
// Connects to the deployed API at api.citadelsdk.com

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://api.citadelsdk.com/v1';
const TENANT_ID = import.meta.env.VITE_TENANT_ID || 'demo-tenant';
const API_KEY = import.meta.env.VITE_API_KEY || 'dev-key-for-testing';

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function fetchApi<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const url = new URL(`${API_BASE_URL}${endpoint}`);
  
  if (options.params) {
    Object.entries(options.params).forEach(([key, value]) => {
      url.searchParams.append(key, value);
    });
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Tenant-ID': TENANT_ID,
    ...((options.headers as Record<string, string>) || {}),
  };

  if (API_KEY) {
    headers['X-API-Key'] = API_KEY;
  }

  const response = await fetch(url.toString(), {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(response.status, error.detail || error.error || 'Request failed');
  }

  return response.json();
}

// Health
export const healthApi = {
  live: () => fetchApi<{ alive: boolean }>('/health/live'),
  ready: () => fetchApi<{ ready: boolean; database: string }>('/health/ready'),
};

// Metrics
export const metricsApi = {
  summary: () => fetchApi<{
    actions_total: number;
    decisions_by_status: Record<string, number>;
    pending_approvals: number;
    audit_events: number;
    kill_switches_active: number;
    capabilities_active: number;
  }>('/metrics/summary'),
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
  list: (status?: string) => fetchApi<{ approvals: Approval[]; total: number }>('/approvals', {
    params: status ? { status_filter: status } : undefined,
  }),
  get: (id: string) => fetchApi<Approval>(`/approvals/${id}`),
  approve: (id: string, reviewedBy: string, reason?: string) =>
    fetchApi<Approval>(`/approvals/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ reviewed_by: reviewedBy, reason: reason || 'Approved via dashboard' }),
    }),
  reject: (id: string, reviewedBy: string, reason?: string) =>
    fetchApi<Approval>(`/approvals/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reviewed_by: reviewedBy, reason: reason || 'Rejected via dashboard' }),
    }),
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
  get: (id: string) => fetchApi<Action>(`/actions/${id}`),
  submit: (data: {
    actor_id: string;
    action_name: string;
    resource: string;
    payload?: Record<string, unknown>;
  }) =>
    fetchApi<Action>('/actions', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

// Governance / Audit
export const auditApi = {
  verify: () => fetchApi<{
    valid: boolean;
    checked_count: number;
    first_event_id?: number;
    last_event_id?: number;
    broken_at_event_id?: number;
  }>('/audit/verify'),
  governanceVerify: () => fetchApi<{
    valid: boolean;
    checked_count: number;
    first_event_id?: number;
    last_event_id?: number;
    broken_at_event_id?: number;
  }>('/governance/audit/verify'),
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
  list: (tenantId?: string) =>
    fetchApi<{ identities: AgentIdentity[]; count: number }>(
      '/agent-identities',
      { params: tenantId ? { tenant_id: tenantId } : undefined }
    ),
  get: (agentId: string) =>
    fetchApi<AgentIdentity>(`/agent-identities/${agentId}`),
  register: (data: { agent_id: string; name: string; tenant_id: string; owner?: string }) =>
    fetchApi<{ agent_id: string; api_key: string; secret_key: string; public_key: string; trust_score: number; trust_level: string }>(
      '/agent-identities',
      { method: 'POST', body: JSON.stringify(data) }
    ),
  authenticate: (agentId: string, secretKey: string) =>
    fetchApi<{ agent_id: string; authenticated: boolean; tenant_id: string; trust_level: string; verification_status: string }>(
      `/agent-identities/${agentId}/authenticate`,
      { method: 'POST', body: JSON.stringify({ secret_key: secretKey }) }
    ),
  trust: (agentId: string) =>
    fetchApi<TrustScore>(`/agent-identities/${agentId}/trust`),
  capability: (agentId: string, action: string, resource: string, context?: Record<string, unknown>) =>
    fetchApi<{ verified: boolean; authorized: boolean; token: CapabilityToken | null; error?: string }>(
      `/agent-identities/${agentId}/capability`,
      {
        method: 'POST',
        body: JSON.stringify({ action, resource, context }),
      }
    ),
  revoke: (agentId: string, reason: string) =>
    fetchApi<{ agent_id: string; revoked: boolean; reason: string }>(
      `/agent-identities/${agentId}/revoke`,
      { method: 'POST', body: JSON.stringify({ reason }) }
    ),
};

export type { ApiError };
