import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { healthApi, metricsApi, approvalsApi, actionsApi, auditApi, traceabilityApi } from '../api/client';
import type { Approval, Action, TraceabilityGraphResponse } from '../api/client';

// Health
export function useHealthLive() {
  return useQuery({
    queryKey: ['health', 'live'],
    queryFn: healthApi.live,
    refetchInterval: 30000,
  });
}

export function useHealthReady() {
  return useQuery({
    queryKey: ['health', 'ready'],
    queryFn: healthApi.ready,
    refetchInterval: 30000,
  });
}

// Metrics
export function useMetricsSummary() {
  return useQuery({
    queryKey: ['metrics', 'summary'],
    queryFn: metricsApi.summary,
    refetchInterval: 10000,
  });
}

// Approvals
export function useApprovals(status?: string) {
  return useQuery({
    queryKey: ['approvals', status],
    queryFn: () => approvalsApi.list(status),
  });
}

export function useApproval(id: string) {
  return useQuery({
    queryKey: ['approval', id],
    queryFn: () => approvalsApi.get(id),
    enabled: !!id,
  });
}

export function useApproveApproval() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, reviewedBy, reason }: { id: string; reviewedBy: string; reason?: string }) =>
      approvalsApi.approve(id, reviewedBy, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      queryClient.invalidateQueries({ queryKey: ['metrics', 'summary'] });
    },
  });
}

export function useRejectApproval() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, reviewedBy, reason }: { id: string; reviewedBy: string; reason?: string }) =>
      approvalsApi.reject(id, reviewedBy, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      queryClient.invalidateQueries({ queryKey: ['metrics', 'summary'] });
    },
  });
}

// Actions
export function useAction(id: string) {
  return useQuery({
    queryKey: ['action', id],
    queryFn: () => actionsApi.get(id),
    enabled: !!id,
  });
}

export function useSubmitAction() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: actionsApi.submit,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['metrics', 'summary'] });
    },
  });
}

// Audit
export function useAuditVerify() {
  return useQuery({
    queryKey: ['audit', 'verify'],
    queryFn: auditApi.verify,
  });
}

export function useGovernanceAuditVerify() {
  return useQuery({
    queryKey: ['governance', 'audit', 'verify'],
    queryFn: auditApi.governanceVerify,
  });
}

export function useTraceabilityGraph(decisionId?: string) {
  return useQuery({
    queryKey: ['governance', 'traceability', decisionId || 'latest'],
    queryFn: () => traceabilityApi.graph(decisionId),
    refetchInterval: 15000,
  });
}

export type { Approval, Action, TraceabilityGraphResponse };
