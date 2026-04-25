type ApiResponse = Record<string, unknown> | unknown[] | string | number | boolean | null;

const mockResponses: Record<string, ApiResponse> = {
  "/api/dashboard/stats": {
    blocked_this_month: 516,
    pending_approvals: 3,
    active_agents: 12,
    risk_level: "LOW",
    kill_switches_active: 0,
    killswitches: {
      email_send: false,
      stripe_charge: false,
      db_write: false,
    },
    recent_events_count: 142,
  },
  "/api/audit?limit=50": { entries: [] },
  "/api/policies": { policies: [] },
  "/api/connectors": { connectors: [] },
  "/api/dashboard/approvals": { approvals: [] },
  "/api/agents": { agents: [] },
  "/v1/billing/summary": {
    tenant_id: "demo",
    plan: "enterprise",
    status: "active",
    limits: {
      api_calls: null,
      agents: null,
      approvals: null,
    },
    usage: {
      api_calls: 12847,
      active_agents: 12,
      approval_requests: 3,
    },
    features: {
      governance: true,
      audit_export: true,
      kill_switches: true,
    },
    current_period_end: null,
  },
  "/v1/billing/checkout": { url: "#" },
};

export async function apiFetch<T>(path: string, _options?: RequestInit): Promise<T> {
  const response = mockResponses[path];
  if (response !== undefined) {
    return response as T;
  }

  return {} as T;
}
