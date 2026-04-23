import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../lib/api';

export interface LedgerStats {
  pending_approvals: number;
  active_agents: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  killswitches: {
    email_send: boolean;
    stripe_charge: boolean;
    db_write: boolean;
  };
  recent_events_count: number;
}

export function useLedgerStats() {
  return useQuery<LedgerStats>({
    queryKey: ['ledger-stats'],
    queryFn: () => apiFetch('/api/dashboard/stats'),
    refetchInterval: 5000, // Refresh every 5 seconds
  });
}
