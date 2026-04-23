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
}

export function useBilling() {
  const summary = useQuery<BillingSummary>({
    queryKey: ['billing-summary'],
    queryFn: () => apiFetch('/v1/billing/summary'),
  });

  const checkout = useMutation({
    mutationFn: () => apiFetch('/v1/billing/checkout', { method: 'POST' }),
    onSuccess: (data: { url: string }) => {
      window.location.href = data.url;
    },
  });

  return { summary, checkout };
}
