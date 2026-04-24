import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../lib/api';

export interface CitadelStats {
  pending_approvals: number;
  active_agents: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  kill_switches_active: number;
  killswitches: {
    email_send: boolean;
    stripe_charge: boolean;
    db_write: boolean;
  };
  recent_events_count: number;
}

export function useCitadelStats() {
  return useQuery<CitadelStats>({
    queryKey: ['citadel-stats'],
    queryFn: () => apiFetch('/api/dashboard/stats'),
    refetchInterval: 5000,
  });
}
