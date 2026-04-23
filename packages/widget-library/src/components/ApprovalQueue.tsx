import React from 'react';
import { Check, X, Shield, User, Terminal, AlertTriangle } from 'lucide-react';
import { cn } from '../lib/utils';

export interface ApprovalRequest {
  id: string;
  action: string;
  resource: string;
  actorId: string;
  timestamp: string;
  riskScore: number;
  reason: string;
}

export interface ApprovalQueueProps {
  requests: ApprovalRequest[];
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  className?: string;
}

export const ApprovalQueue: React.FC<ApprovalQueueProps> = ({ requests, onApprove, onReject, className }) => {
  return (
    <div className={cn('flex flex-col gap-4', className)}>
      <div className="flex items-center justify-between px-2 mb-2">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold text-slate-100">Pending Approvals</h3>
          <span className="flex items-center justify-center w-5 h-5 text-[10px] font-bold bg-orange-500 text-white rounded-full">
            {requests.length}
          </span>
        </div>
      </div>

      <div className="space-y-4">
        {requests.map((request) => (
          <div
            key={request.id}
            className="group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md shadow-lg"
          >
            {/* Risk Indicator Header */}
            <div className={cn(
              "h-1.5 w-full",
              request.riskScore > 0.7 ? "bg-red-500" : "bg-orange-500"
            )} />

            <div className="p-4">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-slate-800 border border-slate-700">
                    <Shield size={18} className="text-orange-400" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-100 uppercase tracking-tight">
                      {request.action}
                    </h4>
                    <p className="text-xs text-slate-400 font-mono mt-0.5">
                      {request.resource}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                    Risk Score
                  </span>
                  <div className={cn(
                    "text-lg font-black tabular-nums leading-none mt-1",
                    request.riskScore > 0.7 ? "text-red-400" : "text-orange-400"
                  )}>
                    {(request.riskScore * 100).toFixed(0)}%
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-5">
                <div className="flex items-center gap-2 p-2 rounded-lg bg-slate-950/50 border border-slate-800/50">
                  <User size={14} className="text-slate-500" />
                  <span className="text-xs text-slate-300 truncate font-medium">
                    {request.actorId}
                  </span>
                </div>
                <div className="flex items-center gap-2 p-2 rounded-lg bg-slate-950/50 border border-slate-800/50">
                  <Terminal size={14} className="text-slate-500" />
                  <span className="text-xs text-slate-300 truncate font-medium">
                    {new Date(request.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>

              <div className="flex items-start gap-2 p-3 rounded-xl bg-orange-500/5 border border-orange-500/10 mb-5">
                <AlertTriangle size={14} className="text-orange-500 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-orange-200/80 leading-relaxed italic">
                  "{request.reason}"
                </p>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => onReject(request.id)}
                  className={cn(
                    "flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl border border-slate-800 font-semibold text-xs transition-all",
                    "text-slate-400 hover:text-white hover:bg-slate-800 hover:border-slate-700"
                  )}
                >
                  <X size={14} />
                  Reject
                </button>
                <button
                  onClick={() => onApprove(request.id)}
                  className={cn(
                    "flex-[2] flex items-center justify-center gap-2 py-2.5 rounded-xl font-bold text-xs transition-all",
                    "bg-orange-600 text-white hover:bg-orange-500 shadow-lg shadow-orange-900/20 active:scale-[0.98]"
                  )}
                >
                  <Check size={14} />
                  Approve Execution
                </button>
              </div>
            </div>
          </div>
        ))}

        {requests.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 px-4 rounded-2xl border border-dashed border-slate-800 text-slate-500">
            <Shield size={40} className="mb-4 opacity-10" />
            <p className="text-sm font-medium">No actions pending approval</p>
            <p className="text-xs text-slate-600 mt-1 italic">Governance is currently autonomous</p>
          </div>
        )}
      </div>
    </div>
  );
};
