const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface DashboardStats {
  total_actions: number;
  approved_this_month: number;
  blocked_this_month: number;
  active_agents_24h: number;
}

export interface AuditEvent {
  id: string;
  type: string;
  actor: string;
  resource: string;
  status: 'approved' | 'blocked' | 'pending' | 'rejected' | 'failed' | 'executed' | 'BLOCKED_POLICY' | 'ALLOWED';
  timestamp: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

export interface Approval {
  id: string;
  action: string;
  resource: string;
  risk: 'low' | 'medium' | 'high' | 'critical';
  requested_at: string;
  expires_at: string;
  assigned_to?: string;
  reason?: string;
}

export interface ApprovalThresholdPayload {
  risk_score_threshold: number;
  approval_priority: 'low' | 'medium' | 'high' | 'critical';
  approval_expiry_hours: number;
  reason?: string;
}

export interface NoCodePolicy {
  policy_id?: string;
  name: string;
  version: string;
  scope_type: string;
  scope_value: string;
  status: string;
  description: string;
  rules_json: {
    rules: Array<{
      name: string;
      effect: string;
      condition: string;
      approval_priority?: string;
      approval_expiry_hours?: number;
      reason?: string;
    }>;
    generated_by?: string;
    control?: Record<string, unknown>;
  };
}

export interface CostBudgetPayload {
  name: string;
  scope_type: 'tenant' | 'project' | 'agent' | 'api_key';
  scope_value?: string;
  amount_cents: number;
  currency?: string;
  reset_period: 'daily' | 'weekly' | 'monthly';
  enforcement_action: 'block' | 'require_approval' | 'throttle';
  warning_threshold_percent?: number;
}

export interface CostBudgetDecision {
  allowed: boolean;
  enforcement_action: 'allow' | 'block' | 'require_approval' | 'throttle';
  requires_approval: boolean;
  throttled: boolean;
  reason: string;
  projected_cost_cents: number;
  current_spend_cents: number;
  budget_amount_cents: number | null;
  warning: boolean;
  period_start: string;
  period_end: string;
  budget: {
    budget_id?: string;
    name: string;
    scope_type: string;
    scope_value: string;
    enforcement_action: string;
  } | null;
}

export interface CostBudgetTopUpPayload {
  amount_cents: number;
  reason: string;
}

export async function apiFetch<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('auth_token');
  const headers = new Headers(init.headers);

  if (!headers.has('Content-Type') && init.body) {
    headers.set('Content-Type', 'application/json');
  }
  // Tenant should ultimately come from JWT claim server-side. Only forward
  // a tenant header if the user explicitly stored one (e.g. tenant switcher).
  const tenantId = localStorage.getItem('tenant_id');
  if (tenantId && !headers.has('X-Tenant-ID')) {
    headers.set('X-Tenant-ID', tenantId);
  }
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });

  if (response.status === 402) {
    alert('Payment required. Please update billing.');
  }
  if (response.status === 429) {
    alert('Rate limit exceeded. Please upgrade your plan.');
  }
  if (response.status === 401) {
    console.warn('Unauthorized API call. Run backend with LEDGER_DEV_MODE=true');
  }

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  getStats(): Promise<DashboardStats> {
    return apiFetch<DashboardStats>('/api/dashboard/stats');
  },

  async getAuditEvents(limit = 50, offset = 0): Promise<AuditEvent[]> {
    const data = await apiFetch<{ events: AuditEvent[] }>(
      `/api/dashboard/audit?limit=${limit}&offset=${offset}`,
    );
    return data.events;
  },

  async getApprovals(): Promise<Approval[]> {
    const data = await apiFetch<{ approvals: Approval[] }>('/api/dashboard/approvals');
    return data.approvals;
  },

  async approveApproval(approvalId: string, reviewedBy: string, reason?: string): Promise<void> {
    await apiFetch(`/api/dashboard/approvals/${approvalId}/approve`, {
      method: 'POST',
      body: JSON.stringify({
        reviewed_by: reviewedBy,
        reason: reason || 'Approved from dashboard',
      }),
    });
  },

  async rejectApproval(approvalId: string, reviewedBy: string, reason?: string): Promise<void> {
    await apiFetch(`/api/dashboard/approvals/${approvalId}/reject`, {
      method: 'POST',
      body: JSON.stringify({
        reviewed_by: reviewedBy,
        reason: reason || 'Rejected from dashboard',
      }),
    });
  },

  async getApprovalThresholdPolicy(): Promise<NoCodePolicy | null> {
    const data = await apiFetch<{ policy: NoCodePolicy | null }>(
      '/api/policies/no-code/approval-threshold',
    );
    return data.policy;
  },

  async previewApprovalThresholdPolicy(
    payload: ApprovalThresholdPayload,
  ): Promise<NoCodePolicy> {
    const data = await apiFetch<{ policy: NoCodePolicy }>(
      '/api/policies/no-code/approval-threshold/preview',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
    );
    return data.policy;
  },

  async applyApprovalThresholdPolicy(
    payload: ApprovalThresholdPayload,
  ): Promise<NoCodePolicy> {
    const data = await apiFetch<{ policy: NoCodePolicy }>(
      '/api/policies/no-code/approval-threshold',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
    );
    return data.policy;
  },

  async createCostBudget(payload: CostBudgetPayload) {
    const data = await apiFetch<{ budget: unknown }>('/v1/billing/budgets', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return data.budget;
  },

  async checkCostBudget(payload: {
    projected_cost_cents: number;
    actor_id?: string;
    project_id?: string;
    api_key_id?: string;
    provider?: string;
    model?: string;
    request_id?: string;
  }): Promise<CostBudgetDecision> {
    return apiFetch<CostBudgetDecision>('/v1/billing/cost/check', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async topUpCostBudget(budgetId: string, payload: CostBudgetTopUpPayload) {
    return apiFetch('/api/dashboard/billing/budgets/' + budgetId + '/top-up', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  killSwitch(
    scope: 'agent' | 'tenant' | 'global',
    targetId?: string,
    reason?: string,
  ): Promise<{ status: string; kill_switch_id: string }> {
    return apiFetch<{ status: string; kill_switch_id: string }>('/api/dashboard/kill-switch', {
      method: 'POST',
      body: JSON.stringify({
        scope,
        target_id: targetId,
        reason,
      }),
    });
  },
};
