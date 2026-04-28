import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../lib/api";

export interface AuditEvent {
  event_id: string;
  action_id: string;
  decision_id?: string | null;
  trust_snapshot_id?: string | null;
  user_id: string;
  action_type: string;
  status: string;
  risk_score: number;
  created_at: string;
  trace_id?: string | null;
}

export function useAudit() {
  return useQuery({
    queryKey: ["audit"],
    queryFn: async () => {
      const data = await apiFetch("/api/dashboard/audit") as { events: AuditEvent[] };
      return (data.events || []) as AuditEvent[];
    },
    refetchInterval: 30000, // 30 seconds
  });
}

export interface TrustFactorBreakdown {
  key: string;
  label: string;
  contribution: number;
  direction: 'positive' | 'negative' | 'neutral';
}

export interface DecisionTrustBreakdown {
  decision_id: string;
  trust_snapshot_id: string | null;
  available: boolean;
  reason?: string;
  actor_id?: string;
  score?: number;
  band?: string;
  computed_at?: string;
  computation_method?: string;
  factors?: Record<string, number>;
  factor_breakdown?: TrustFactorBreakdown[];
  raw_inputs?: Record<string, unknown>;
}

export function useDecisionTrustBreakdown(decisionId?: string | null) {
  return useQuery({
    queryKey: ["decision-trust-breakdown", decisionId],
    enabled: Boolean(decisionId),
    queryFn: async () => {
      return await apiFetch(`/api/dashboard/decisions/${decisionId}/trust`) as DecisionTrustBreakdown;
    },
  });
}
