import React, { useState } from 'react';
import { ShieldCheck, CheckCircle, XCircle, AlertCircle, Clock, User } from 'lucide-react';
import { useApprovals, useApproveApproval, useRejectApproval } from '../hooks/useApi';
import type { Approval } from '../api/client';

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const styles: Record<string, string> = {
    pending: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
    approved: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
    rejected: 'bg-red-500/10 text-red-500 border-red-500/20',
  };

  return (
    <span className={`px-2 py-1 rounded-lg text-[10px] font-bold uppercase tracking-tight border ${
      styles[status] || 'bg-slate-500/10 text-slate-500 border-slate-500/20'
    }`}>
      {status}
    </span>
  );
};

const PriorityBadge: React.FC<{ priority: string }> = ({ priority }) => {
  const styles: Record<string, string> = {
    critical: 'bg-red-500/10 text-red-500',
    high: 'bg-orange-500/10 text-orange-500',
    medium: 'bg-blue-500/10 text-blue-500',
    low: 'bg-slate-500/10 text-slate-500',
  };

  return (
    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
      styles[priority.toLowerCase()] || styles.low
    }`}>
      {priority}
    </span>
  );
};

export const Approvals: React.FC = () => {
  const [filter, setFilter] = useState<string>('');
  const { data, isLoading, error } = useApprovals(filter || undefined);
  const approveMutation = useApproveApproval();
  const rejectMutation = useRejectApproval();
  const [processingId, setProcessingId] = useState<string | null>(null);

  const handleApprove = async (id: string) => {
    setProcessingId(id);
    try {
      await approveMutation.mutateAsync({ id, reviewedBy: 'dashboard-admin' });
    } catch (err) {
      console.error('Approve failed:', err);
    } finally {
      setProcessingId(null);
    }
  };

  const handleReject = async (id: string) => {
    setProcessingId(id);
    try {
      await rejectMutation.mutateAsync({ id, reviewedBy: 'dashboard-admin' });
    } catch (err) {
      console.error('Reject failed:', err);
    } finally {
      setProcessingId(null);
    }
  };

  const pendingCount = data?.approvals.filter(a => a.status === 'pending').length || 0;
  const approvedCount = data?.approvals.filter(a => a.status === 'approved').length || 0;
  const rejectedCount = data?.approvals.filter(a => a.status === 'rejected').length || 0;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 rounded-2xl bg-red-500/10 border border-red-500/20">
        <div className="flex items-center gap-2">
          <AlertCircle size={16} className="text-red-500" />
          <p className="text-sm font-bold text-red-500">Failed to load approvals</p>
        </div>
        <p className="text-xs text-red-400 mt-1">{(error as Error).message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white">Approval Queue</h1>
          <p className="text-sm text-slate-500 mt-1">Review and manage pending approvals</p>
        </div>
        <ShieldCheck size={20} className="text-slate-500" />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-2xl bg-orange-500/5 border border-orange-500/10">
          <div className="flex items-center gap-2 mb-2">
            <Clock size={16} className="text-orange-500" />
            <span className="text-xs font-bold text-orange-500 uppercase">Pending</span>
          </div>
          <p className="text-2xl font-black text-white">{pendingCount}</p>
        </div>
        <div className="p-4 rounded-2xl bg-emerald-500/5 border border-emerald-500/10">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle size={16} className="text-emerald-500" />
            <span className="text-xs font-bold text-emerald-500 uppercase">Approved</span>
          </div>
          <p className="text-2xl font-black text-white">{approvedCount}</p>
        </div>
        <div className="p-4 rounded-2xl bg-red-500/5 border border-red-500/10">
          <div className="flex items-center gap-2 mb-2">
            <XCircle size={16} className="text-red-500" />
            <span className="text-xs font-bold text-red-500 uppercase">Rejected</span>
          </div>
          <p className="text-2xl font-black text-white">{rejectedCount}</p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2">
        {['all', 'pending', 'approved', 'rejected'].map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status === 'all' ? '' : status)}
            className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-tight transition-all ${
              (filter === status || (status === 'all' && !filter))
                ? 'bg-orange-600 text-white'
                : 'bg-slate-800/50 text-slate-400 hover:text-slate-200'
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      {/* Approvals Table */}
      <div className="rounded-2xl bg-slate-900/40 border border-slate-800/50 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-800/50">
                <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Action</th>
                <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Resource</th>
                <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Requested By</th>
                <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Status</th>
                <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Priority</th>
                <th className="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/30">
              {data?.approvals.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-sm text-slate-500">
                    No approvals found
                  </td>
                </tr>
              ) : (
                data?.approvals.map((approval: Approval) => (
                  <tr key={approval.approval_id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3">
                      <p className="text-xs font-medium text-slate-300">{approval.action_id}</p>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-xs text-slate-400">{approval.reason}</p>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <User size={12} className="text-slate-500" />
                        <span className="text-xs text-slate-400">{approval.requested_by}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={approval.status} />
                    </td>
                    <td className="px-4 py-3">
                      <PriorityBadge priority={approval.priority} />
                    </td>
                    <td className="px-4 py-3">
                      {approval.status === 'pending' && (
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleApprove(approval.approval_id)}
                            disabled={processingId === approval.approval_id}
                            className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 transition-colors disabled:opacity-50"
                          >
                            <CheckCircle size={14} />
                          </button>
                          <button
                            onClick={() => handleReject(approval.approval_id)}
                            disabled={processingId === approval.approval_id}
                            className="p-1.5 rounded-lg bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-colors disabled:opacity-50"
                          >
                            <XCircle size={14} />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
