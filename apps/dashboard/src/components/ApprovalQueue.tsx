import React from 'react';
import { CheckCircle, XCircle, AlertTriangle, Clock } from 'lucide-react';

export interface ApprovalRequest {
  id: string;
  action: string;
  resource: string;
  actorId: string;
  timestamp: string;
  riskScore: number;
  reason: string;
}

interface Props {
  requests: ApprovalRequest[];
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}

export const ApprovalQueue: React.FC<Props> = ({ requests, onApprove, onReject }) => {
  if (requests.length === 0) {
    return (
      <div className="text-center py-8">
        <CheckCircle size={32} className="text-emerald-500 mx-auto mb-2" />
        <p className="text-sm text-slate-400">No pending approvals</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-slate-200 uppercase tracking-tight">Approval Queue</h3>
        <span className="text-[10px] px-2 py-1 rounded-full bg-orange-500/10 text-orange-400 border border-orange-500/20">
          {requests.length} pending
        </span>
      </div>
      <div className="space-y-3">
        {requests.map((req) => (
          <div key={req.id} className="p-4 rounded-xl bg-slate-950/50 border border-slate-800/50">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <AlertTriangle size={14} className={req.riskScore > 0.9 ? 'text-red-500' : 'text-orange-500'} />
                  <span className="text-xs font-bold text-slate-200">{req.action}</span>
                </div>
                <p className="text-[10px] text-slate-500 font-mono">{req.resource}</p>
              </div>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${req.riskScore > 0.9 ? 'bg-red-500/10 text-red-400' : 'bg-orange-500/10 text-orange-400'}`}>
                Risk: {Math.round(req.riskScore * 100)}%
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-3">{req.reason}</p>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-[10px] text-slate-500">
                <span>{req.actorId}</span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Clock size={10} />
                  {new Date(req.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onReject(req.id)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-400 transition-all flex items-center gap-1"
                >
                  <XCircle size={12} />
                  Reject
                </button>
                <button
                  onClick={() => onApprove(req.id)}
                  className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white transition-all flex items-center gap-1"
                >
                  <CheckCircle size={12} />
                  Approve
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
