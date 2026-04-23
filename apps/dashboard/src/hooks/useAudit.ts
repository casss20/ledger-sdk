import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../lib/api";

export interface AuditEvent {
  event_id: string;
  action_id: string;
  user_id: string;
  action_type: string;
  status: string;
  risk_score: number;
  created_at: string;
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
