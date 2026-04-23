import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../lib/api";

export interface Approval {
  approval_id: string;
  action_id: string;
  status: 'pending' | 'approved' | 'rejected';
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  reason: string;
  requested_by: string;
  reviewed_by?: string;
  decided_at?: string;
  decision_reason?: string;
  // UI extended fields (mocked or mapped from backend)
  agent?: string;
  action?: string;
  target?: string;
  policy?: string;
  requestedAt?: string;
  waiting?: string;
}

export function useApprovals() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["approvals"],
    queryFn: async () => {
      const data = await apiFetch("/api/dashboard/approvals") as { approvals: Approval[] };
      return (data.approvals || []) as Approval[];
    },
    refetchInterval: 10000, // 10 seconds
  });

  const approveMutation = useMutation({
    mutationFn: async ({ id, reviewer, reason }: { id: string; reviewer: string; reason: string }) => {
      return apiFetch(`/api/dashboard/approvals/${id}/approve`, {
        method: "POST",
        body: JSON.stringify({ reviewed_by: reviewer, reason }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      queryClient.invalidateQueries({ queryKey: ["ledger-stats"] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async ({ id, reviewer, reason }: { id: string; reviewer: string; reason: string }) => {
      return apiFetch(`/api/dashboard/approvals/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reviewed_by: reviewer, reason }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      queryClient.invalidateQueries({ queryKey: ["ledger-stats"] });
    },
  });

  return {
    ...query,
    approve: approveMutation.mutateAsync,
    reject: rejectMutation.mutateAsync,
    isProcessing: approveMutation.isPending || rejectMutation.isPending,
  };
}
