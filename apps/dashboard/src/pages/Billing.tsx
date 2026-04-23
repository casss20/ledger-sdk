import React from 'react';
import { useBilling } from '../hooks/useBilling';
import { SectionHeader } from '../components/dashboard/SectionHeader';
import { StatusPill } from '../components/dashboard/StatusPill';
import { CreditCard, Zap, Shield, BarChart3, ArrowUpRight } from 'lucide-react';

export default function Billing() {
  const { summary, checkout } = useBilling();

  if (summary.isLoading) return <div className="p-8 text-slate-400">Loading billing data...</div>;
  if (!summary.data) return <div className="p-8 text-red-400">Error loading billing.</div>;

  const data = summary.data;

  return (
    <div className="p-8 space-y-8 animate-in fade-in duration-500">
      <SectionHeader 
        title="Billing & Quotas" 
        subtitle="Manage your subscription and monitor governance consumption."
      />

      {/* Plan Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
              <Zap size={20} />
            </div>
            <StatusPill status={data.status as any} />
          </div>
          <h3 className="text-sm font-medium text-slate-400">Current Plan</h3>
          <p className="text-2xl font-bold text-white capitalize mt-1">{data.plan}</p>
          <p className="text-xs text-slate-500 mt-2">
            Renewing on {data.current_period_end ? new Date(data.current_period_end).toLocaleDateString() : 'N/A'}
          </p>
        </div>

        <div className="col-span-2 p-6 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 backdrop-blur-sm relative overflow-hidden group">
          <div className="relative z-10">
            <h3 className="text-lg font-bold text-white mb-2">Upgrade to Enterprise</h3>
            <p className="text-slate-400 text-sm max-w-md mb-6">
              Unlock unlimited API calls, SSO, and 365-day audit retention for large scale governance.
            </p>
            <button 
              onClick={() => checkout.mutate()}
              disabled={checkout.isPending}
              className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium transition-all flex items-center gap-2 group-hover:gap-3"
            >
              {checkout.isPending ? 'Redirecting...' : 'Upgrade Now'}
              <ArrowUpRight size={18} />
            </button>
          </div>
          <div className="absolute -right-8 -bottom-8 text-indigo-500/10 transform rotate-12 group-hover:scale-110 transition-transform duration-700">
            <Shield size={200} />
          </div>
        </div>
      </div>

      {/* Usage Section */}
      <div className="p-8 rounded-3xl bg-slate-900/50 border border-slate-800">
        <div className="flex items-center gap-3 mb-8">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <BarChart3 size={20} />
          </div>
          <h3 className="text-lg font-bold text-white">Consumption Tracking</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
          {/* API Calls */}
          <UsageBar 
            label="API Calls" 
            current={data.usage.api_calls} 
            limit={data.limits.api_calls} 
            color="bg-indigo-500" 
          />
          {/* Active Agents */}
          <UsageBar 
            label="Active Agents" 
            current={data.usage.active_agents} 
            limit={data.limits.agents} 
            color="bg-emerald-500" 
          />
          {/* Approvals */}
          <UsageBar 
            label="Approval Requests" 
            current={data.usage.approval_requests} 
            limit={data.limits.approvals} 
            color="bg-amber-500" 
          />
        </div>
      </div>
    </div>
  );
}

function UsageBar({ label, current, limit, color }: { label: string, current: number, limit: number | null, color: string }) {
  const percentage = limit ? Math.min(100, (current / limit) * 100) : 0;
  
  return (
    <div className="space-y-3">
      <div className="flex justify-between items-end">
        <div>
          <span className="text-sm font-medium text-slate-400">{label}</span>
          <div className="text-xl font-bold text-white mt-1">
            {current.toLocaleString()} <span className="text-slate-600 text-sm font-normal">/ {limit?.toLocaleString() || '∞'}</span>
          </div>
        </div>
        <span className="text-xs font-mono text-slate-500">{percentage.toFixed(1)}%</span>
      </div>
      <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
        <div 
          className={`h-full ${color} transition-all duration-1000 ease-out`} 
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
