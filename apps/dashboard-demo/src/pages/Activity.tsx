import React from 'react';
import { Activity as ActivityIcon, Shield, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import { useHealthLive, useHealthReady, useAuditVerify, useGovernanceAuditVerify } from '../hooks/useApi';

export const Activity: React.FC = () => {
  const { data: healthLive, isLoading: liveLoading } = useHealthLive();
  const { data: healthReady, isLoading: readyLoading } = useHealthReady();
  const { data: auditData, isLoading: auditLoading } = useAuditVerify();
  const { data: govAuditData, isLoading: govAuditLoading } = useGovernanceAuditVerify();

  const isLoading = liveLoading || readyLoading || auditLoading || govAuditLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white">Activity Explorer</h1>
          <p className="text-sm text-slate-500 mt-1">System health and audit status</p>
        </div>
        <ActivityIcon size={20} className="text-slate-500" />
      </div>

      {/* Health Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/50">
          <div className="flex items-center gap-3 mb-4">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              healthLive?.alive ? 'bg-emerald-500/10' : 'bg-red-500/10'
            }`}>
              <Shield size={20} className={healthLive?.alive ? 'text-emerald-500' : 'text-red-500'} />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-200">API Status</p>
              <p className="text-xs text-slate-500">Live health check</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${healthLive?.alive ? 'bg-emerald-500' : 'bg-red-500'}`} />
            <span className={`text-sm font-bold ${healthLive?.alive ? 'text-emerald-500' : 'text-red-500'}`}>
              {healthLive?.alive ? 'Healthy' : 'Down'}
            </span>
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/50">
          <div className="flex items-center gap-3 mb-4">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              healthReady?.ready ? 'bg-emerald-500/10' : 'bg-orange-500/10'
            }`}>
              <CheckCircle size={20} className={healthReady?.ready ? 'text-emerald-500' : 'text-orange-500'} />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-200">Database</p>
              <p className="text-xs text-slate-500">Connection status</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${healthReady?.ready ? 'bg-emerald-500' : 'bg-orange-500'}`} />
            <span className={`text-sm font-bold ${healthReady?.ready ? 'text-emerald-500' : 'text-orange-500'}`}>
              {healthReady?.database === 'connected' ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>

      {/* Audit Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/50">
          <div className="flex items-center gap-3 mb-4">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              auditData?.valid ? 'bg-emerald-500/10' : 'bg-red-500/10'
            }`}>
              <Shield size={20} className={auditData?.valid ? 'text-emerald-500' : 'text-red-500'} />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-200">Action Audit Chain</p>
              <p className="text-xs text-slate-500">Integrity verification</p>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${auditData?.valid ? 'bg-emerald-500' : 'bg-red-500'}`} />
              <span className={`text-sm font-bold ${auditData?.valid ? 'text-emerald-500' : 'text-red-500'}`}>
                {auditData?.valid ? 'Valid' : 'Broken'}
              </span>
            </div>
            <p className="text-xs text-slate-500">
              {auditData?.checked_count || 0} events verified
            </p>
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/50">
          <div className="flex items-center gap-3 mb-4">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              govAuditData?.valid ? 'bg-emerald-500/10' : 'bg-red-500/10'
            }`}>
              <Shield size={20} className={govAuditData?.valid ? 'text-emerald-500' : 'text-red-500'} />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-200">Governance Audit Chain</p>
              <p className="text-xs text-slate-500">Integrity verification</p>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${govAuditData?.valid ? 'bg-emerald-500' : 'bg-red-500'}`} />
              <span className={`text-sm font-bold ${govAuditData?.valid ? 'text-emerald-500' : 'text-red-500'}`}>
                {govAuditData?.valid ? 'Valid' : 'Broken'}
              </span>
            </div>
            <p className="text-xs text-slate-500">
              {govAuditData?.checked_count || 0} events verified
            </p>
          </div>
        </div>
      </div>

      {/* Recent Events Table */}
      <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/50">
        <h3 className="text-sm font-bold text-slate-200 mb-4">System Events</h3>
        <div className="space-y-3">
          <div className="flex items-center gap-4 p-3 rounded-xl bg-slate-950/50 border border-slate-800/50">
            <Clock size={16} className="text-slate-500" />
            <div className="flex-1">
              <p className="text-xs font-medium text-slate-300">Health check passed</p>
              <p className="text-[10px] text-slate-500">API and database responding normally</p>
            </div>
            <span className="text-[10px] text-slate-500">Just now</span>
          </div>
          <div className="flex items-center gap-4 p-3 rounded-xl bg-slate-950/50 border border-slate-800/50">
            <CheckCircle size={16} className="text-emerald-500" />
            <div className="flex-1">
              <p className="text-xs font-medium text-slate-300">Audit chain verified</p>
              <p className="text-[10px] text-slate-500">All {auditData?.checked_count || 0} events valid</p>
            </div>
            <span className="text-[10px] text-slate-500">Just now</span>
          </div>
          <div className="flex items-center gap-4 p-3 rounded-xl bg-slate-950/50 border border-slate-800/50">
            <AlertCircle size={16} className="text-blue-500" />
            <div className="flex-1">
              <p className="text-xs font-medium text-slate-300">Dashboard connected</p>
              <p className="text-[10px] text-slate-500">Successfully connected to api.citadelsdk.com</p>
            </div>
            <span className="text-[10px] text-slate-500">Just now</span>
          </div>
        </div>
      </div>
    </div>
  );
};
