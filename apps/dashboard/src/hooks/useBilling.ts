import { useQuery, useMutation } from '@tanstack/react-query';
import { apiFetch } from '../lib/api';

export interface BillingSummary {
  tenant_id: string;
  plan: string;
  status: string;
  limits: {
    api_calls: number | null;
    agents: number | null;
    approvals: number | null;
  };
  usage: {
    api_calls: number;
    active_agents: number;
    approval_requests: number;
  };
  features: Record<string, boolean>;
  current_period_end: string | null;
  cost_controls?: {
    monthly_spend_cents: number;
    monthly_period_start: string;
    monthly_period_end: string;
    budgets: Array<{
      budget_id: string;
      name: string;
      scope_type: 'tenant' | 'project' | 'agent' | 'api_key';
      scope_value: string;
      amount_cents: number;
      currency: string;
      reset_period: 'daily' | 'weekly' | 'monthly';
      enforcement_action: 'block' | 'require_approval' | 'throttle';
      warning_threshold_percent: number;
      is_active: boolean;
    }>;
    recent_spend_events: Array<{
      event_id: string;
      event_ts: string;
      provider?: string;
      model?: string;
      cost_cents: number;
      actor_id?: string;
      project_id?: string;
      api_key_id?: string;
    }>;
  };
}

export function useBilling() {
  const summary = useQuery<BillingSummary>({
    queryKey: ['billing-summary'],
    queryFn: () => apiFetch('/v1/billing/summary'),
  });

  const checkout = useMutation({
    mutationFn: () => apiFetch<{ url: string }>('/v1/billing/checkout', { method: 'POST' }),
    onSuccess: (data: { url: string }) => {
      window.location.href = data.url;
    },
  });

  return { summary, checkout };
}
